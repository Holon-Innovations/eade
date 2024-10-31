import threading
import time
import uuid
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import zfec
import struct
import hashlib

from eade.base_engine import BaseEngine

# length of the header in each segment
# this includes 16 bytes for the ID, 4 bytes for total_shares, 4 bytes for required_shares, and 8 bytes for data_length
HEADER_LENGTH = 32

class RaDEngine(BaseEngine):
    def __init__(
            self,
            output_path: str,
            key: bytes,
            iv: bytes,
            segments: list,
            success_callback_func=None,
            exception_callback_func=None,
            progress_callback_func=None,
            restored_file_name: str = None,
            hash_results: bool = True):
        """
        Initializes the engine with decryption parameters.
        :param output_path: The directory where the reconstructed file will be saved.
        :param key: AES256 key used for encryption (must be 32 bytes).
        :param iv: Initialization vector used for AES encryption (must be 16 bytes).
        :param segments: List of file paths to the minimum required segments.
        :param success_callback_func: Optional callback to be called when processing is complete.
        :param exception_callback_func: Optional callback to be called when an exception occurs.
        :param progress_callback_func: Optional callback to be called when progress is updated.
        :param restored_file_name: Optional name for the restored file. If not provided, the file will be named "restored.blob".
        :param hash_results: Optional flag to hash the original file, encrypted file, and segments.
        """

        # get metadata from the first segment
        segment_path = segments[0]
        id = None
        with open(segment_path, 'rb') as segment_file:
            # read the first 32 bytes to get the metadata (16 bytes for ID, 4 for total_shares, 4 for required_shares, and 8 for data_length)
            header = segment_file.read(HEADER_LENGTH)
            id_bytes, self._total_shares, self._required_shares, self._data_length = struct.unpack(">16sIIQ", header)

            # convert the id from bytes to string
            id = str(uuid.UUID(bytes=id_bytes))

        super().__init__(
            id=id,
            key=key,
            iv=iv,
            output_path=output_path,
            success_callback_func=success_callback_func,
            exception_callback_func=exception_callback_func,
            progress_callback_func=progress_callback_func,
            hash_results=hash_results)

        # local properties
        self._segments = segments
        self._restore_file_name = restored_file_name
        self._decrypt_file_path = None

    @property
    def decrypt_file_path(self):
        with self._lock:
            return self._decrypt_file_path

    def _restore_file_thread(self):
        """
        Threaded method to reconstruct and decrypt the original file.
        :param segment_paths: List of file paths to the minimum required segments.
        """
        try:
            # make sure we have enough segments to rebuild the file
            if len(self._segments) < self._required_shares:
                raise ValueError("Insufficient number of segments to rebuild data.")

            # rebuild encrypted data from segments
            encrypted_file_path = self._rebuild_encrypted_data()

            # decrypt the rebuilt data
            decrypted_file_path = self._decrypt_data(encrypted_file_path)

            # set the decrypted file path
            self._decrypt_file_path = decrypted_file_path

            # are we hashing the results?
            if self._hash_results:
                # hash the restored file
                with open(decrypted_file_path, 'rb') as file:
                    data = file.read()
                    hash_value = hashlib.sha256(data).hexdigest()
                    with open(decrypted_file_path + ".sha256", 'w') as hash_file:
                        hash_file.write(hash_value)

                # hash the encrypted file
                with open(encrypted_file_path, 'rb') as file:
                    data = file.read()
                    hash_value = hashlib.sha256(data).hexdigest()
                    with open(encrypted_file_path + ".sha256", 'w') as hash_file:
                        hash_file.write(hash_value)

            # trigger callback if set
            if self._success_callback_func:
                self._success_callback_func(self._id, decrypted_file_path)

            # mark processing as complete
            self._update_completed(True)

        except Exception as e:
            # write the exception to output folder
            with open(os.path.join(self._output_path, "exception.txt"), 'w') as exception_file:
                exception_file.write(str(e))

            # trigger exception callback if set
            if self._exception_callback_func:
                self._exception_callback_func(self._id, e)

            # mark processing as complete
            self._update_completed(True, e)

    def _rebuild_encrypted_data(self, from_percent: int = 0, to_percent: int = 50) -> str:
        # rebuilds the encrypted data from the provided segments and writes it directly to disk
        shares_we_have = len(self._segments)
        total_shares = self._total_shares
        output_file_path = os.path.join(self._output_path, f"restored.enc" if not self._restore_file_name else self._restore_file_name + ".enc")

        # read the segments and determine their indices and encrypted length, regardless of order
        segments = []
        indices = []
        for path in self._segments:
            with open(path, 'rb') as segment_file:
                # skip the header and read the remaining data
                segment_file.seek(HEADER_LENGTH)
                segments.append(segment_file.read())
                index = int(os.path.basename(path).split('.')[-1])
                indices.append(index)

        # check if we have the required number of shares to decode
        if len(segments) < shares_we_have:
            raise ValueError("Insufficient number of segments to rebuild data.")

        # initialize the decoder with explicit indices for decoding
        decoder = zfec.Decoder(shares_we_have, total_shares)
        decoded_data = b''.join(decoder.decode(segments, indices))

        # truncate to the original encrypted data length to remove padding
        decoded_data = decoded_data[:self._data_length]

        # write the truncated data to disk in chunks to manage memory usage
        chunk_size = 64 * 1024  # 64KB chunks
        total_chunks = len(decoded_data) // chunk_size + (1 if len(decoded_data) % chunk_size > 0 else 0)
        with open(output_file_path, 'wb') as output_file:
            for i in range(total_chunks):
                output_file.write(decoded_data[i * chunk_size:(i + 1) * chunk_size])

                # update progress for each chunk processed
                self._update_progress(from_percent + int(((i + 1) / total_chunks) * (to_percent - from_percent)))

        return output_file_path

    def _decrypt_data(self, encrypted_file_path: str, from_percent: int = 50, to_percent: int = 100) -> str:
        # decrypts the aes256-encrypted file directly from disk and writes the decrypted data to disk
        cipher = Cipher(algorithms.AES(self._key), modes.CFB(self._iv), backend=default_backend())
        decryptor = cipher.decryptor()
        output_file_path = os.path.join(self._output_path, f"restored.blob" if not self._restore_file_name else self._restore_file_name)

        # calculate total chunks for progress tracking
        total_size = os.path.getsize(encrypted_file_path)
        chunk_size = 64 * 1024
        total_chunks = total_size // chunk_size + (1 if total_size % chunk_size > 0 else 0)

        with open(encrypted_file_path, 'rb') as infile, open(output_file_path, 'wb') as outfile:
            for i in range(total_chunks):
                chunk = infile.read(chunk_size)
                decrypted_chunk = decryptor.update(chunk)
                outfile.write(decrypted_chunk)

                # update progress for each chunk processed
                self._update_progress(from_percent + int((i + 1) / total_chunks * (to_percent - from_percent)))

            # finalize decryption
            outfile.write(decryptor.finalize())

        return output_file_path

    def restore_file(self):
        """
        Reassemble and decrypts the original file from the minimum required segments in a separate thread.
        """
        self._progress = 0
        thread = threading.Thread(target=self._restore_file_thread)
        thread.start()

