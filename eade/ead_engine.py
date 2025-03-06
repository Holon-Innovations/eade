import threading
import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import zfec
import struct
import math
import uuid
import hashlib

from eade.base_engine import BaseEngine

class EaDEngine(BaseEngine):
    def __init__(
            self,
            file_path: str,
            required_shares: int,
            total_shares: int,
            output_path: str,
            key: bytes = None,
            iv: bytes = None,
            success_callback_func = None,
            exception_callback_func = None,
            progress_callback_func = None,
            hash_results: bool = True):
        """
        Initializes the engine.
        :param file_path: The path to the file to process.
        :param output_path: The directory where output will be stored.
        :param key: AES256 key used for encryption (must be 32 bytes).
        :param iv: Initialization vector used for AES encryption (must be 16 bytes).
        :param required_shares: the number of shares required to reconstruct the data.
        :param total_shares: the total number of shares to create.
        :param success_callback_func: Optional callback to be called when processing is complete.
        :param exception_callback_func: Optional callback to be called when an exception occurs.
        :param progress_callback_func: Optional callback to be called when progress is updated.
        :param hash_results: Optional flag to hash the original file, encrypted file, and segments.
        """

        # generate aes256 key and iv if not provided
        key = key or os.urandom(32)  # aes256 requires a 32-byte key
        iv = iv or os.urandom(16)    # initialization vector for aes

        # generate a unique id (guid)
        id = str(uuid.uuid4())

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
        self._total_shares = total_shares
        self._required_shares = required_shares
        self._file_path = file_path
        self._segments = []

    @property
    def file_path(self):
        return self._file_path

    @property
    def required_shares(self):
        return self._required_shares

    @property
    def total_shares(self):
        return self._total_shares

    @property
    def segments(self):
        return self._segments

    def _split_file_thread(self):
        try:
            # encrypt the file and write to the ID directory
            encrypted_file_path = self._encrypt_file()

            # split the encrypted file into shares and write each segment to a file
            segment_paths = self._split_file_and_write(encrypted_file_path=encrypted_file_path)

            # store the segment paths
            self._segments = segment_paths

            # trigger callback function if set, passing the segment file paths
            if self._success_callback_func:
                self._success_callback_func(self._id, segment_paths)

            # are we hashing the segments?
            if self._hash_results:
                # hash the original file
                with open(self._file_path, 'rb') as file:
                    data = file.read()
                    hash_value = hashlib.sha256(data).hexdigest()
                    with open(os.path.join(self.output_path, os.path.basename(self._file_path)) + ".sha256", 'w') as hash_file:
                        hash_file.write(hash_value)

                # hash the encrypted file
                with open(encrypted_file_path, 'rb') as file:
                    data = file.read()
                    hash_value = hashlib.sha256(data).hexdigest()
                    with open(encrypted_file_path + ".sha256", 'w') as hash_file:
                        hash_file.write(hash_value)

                # hash the segments
                for segment_path in segment_paths:
                    with open(segment_path, 'rb') as segment_file:
                        data = segment_file.read()
                        hash_value = hashlib.sha256(data).hexdigest()
                        with open(segment_path + ".sha256", 'w') as hash_file:
                            hash_file.write(hash_value)

            # mark processing as complete
            self._update_completed(True)

        except Exception as e:
            # write the exception to output folder
            with open(os.path.join(self.output_path, "exception.txt"), 'w') as exception_file:
                exception_file.write(str(e))

            # trigger exception callback if set
            if self._exception_callback_func:
                self._exception_callback_func(self._id, e)

            # mark processing as complete
            self._update_completed(True, e)

    def _encrypt_file(self, from_percent: int = 0, to_percent: int = 50) -> str:
        # encrypt the file and write to the ID directory
        encrypted_file_path = os.path.join(self.output_path, f"distribute.enc")  # path for the encrypted file
        cipher = Cipher(algorithms.AES(self._key), modes.CFB(self._iv), backend=default_backend())
        encryptor = cipher.encryptor()

        total_size = os.path.getsize(self._file_path)
        processed_size = 0

        # read the file in chunks and encrypt each chunk
        with open(self._file_path, 'rb') as infile, open(encrypted_file_path, 'wb') as outfile:
            while chunk := infile.read(64 * 1024):  # read the file in 64KB chunks
                encrypted_chunk = encryptor.update(chunk)
                outfile.write(encrypted_chunk)
                processed_size += len(chunk)

                # update progress for each chunk processed
                self._update_progress(from_percent + int((processed_size / total_size) * (to_percent - from_percent)))

            outfile.write(encryptor.finalize())  # finalize encryption

        return encrypted_file_path

    def _split_file_and_write(self, encrypted_file_path: str, from_percent: int = 50, to_percent: int = 100) -> list:
        # split the encrypted file into shares and write each segment to a file
        with open(encrypted_file_path, 'rb') as file:
            encrypted_data = file.read()

        # calculate the size of each block
        data_len = len(encrypted_data)
        block_size = math.ceil(data_len / self._required_shares)

        # pad the data to fit perfectly into 'required_shares' blocks
        padded_data = encrypted_data.ljust(block_size * self._required_shares, b'\0')

        # split the padded data into 'required_shares' blocks
        blocks = [padded_data[i * block_size:(i + 1) * block_size] for i in range(self._required_shares)]

        # encode the blocks into 'total_shares' parts
        encoder = zfec.Encoder(self._required_shares, self._total_shares)
        encoded_blocks = encoder.encode(blocks)

        # add the original data length as a 4-byte header in each segment and write it to a file
        segment_paths = []

        # create id
        data_id = uuid.UUID(self._id).bytes

        # create a segment for each encoded block
        for i, segment in enumerate(encoded_blocks):
            header = self.pack_header(data_id=data_id, total_shares=self._total_shares, required_shares=self._required_shares, which_segment=i, data_len=data_len)
            segment_with_header = header + segment  # concatenate header and segment
            segment_path = os.path.join(self.output_path, f"segment.{i}")
            with open(segment_path, 'wb') as segment_file:
                segment_file.write(segment_with_header)
            segment_paths.append(segment_path)

            # update progress for each segment written
            self._update_progress(from_percent + int(((i + 1) / self._total_shares) * (to_percent - from_percent)))

        return segment_paths

    def split_file(self):
        """
        Distribute the file in a separate thread.
        """
        self._progress = 0
        thread = threading.Thread(target=self._split_file_thread)
        thread.start()