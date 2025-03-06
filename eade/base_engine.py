import os
import threading
import time
import struct
import uuid

# header length in bytes
# this includes 16 bytes for the ID, 4 bytes for total_shares, 4 bytes for required_shares, which_segment (4 bytes), reserved (4 bytes), reserved (8 bytes), and data_length (8 bytes)
HEADER_LENGTH = 48

class BaseEngine:
    def __init__(
            self,
            id: str,
            key: bytes,
            iv: bytes,
            output_path: str,
            success_callback_func,
            exception_callback_func,
            progress_callback_func,
            hash_results: bool):

        if not id:
            raise ValueError("ID must be a unique identifier for the engine.")

        # ensure key and iv are bytes-like and of correct length
        if key and (not isinstance(key, bytes) or len(key) != 32):
            raise ValueError("Key must be a 32-byte AES256 key in bytes format.")
        if iv and (not isinstance(iv, bytes) or len(iv) != 16):
            raise ValueError("IV must be a 16-byte initialization vector in bytes format.")

        # create the output directory with guid as folder name
        self._output_path = os.path.join(output_path, id)
        os.makedirs(self._output_path, exist_ok=True)

        self._id = id
        self._key = key
        self._iv = iv
        self._progress = 0
        self._completed = False
        self._success_callback_func = success_callback_func
        self._exception_callback_func = exception_callback_func
        self._progress_callback_func = progress_callback_func
        self._exception = None
        self._hash_results = hash_results
        self._lock = threading.Lock()

    @property
    def id(self) -> str:
        return self._id

    @property
    def key(self) -> bytes:
        return self._key

    @property
    def iv(self) -> bytes:
        return self._iv

    @property
    def output_path(self) -> str:
        return self._output_path

    @property
    def progress(self) -> int:
        with self._lock:
            return self._progress

    @property
    def completed(self) -> bool:
        with self._lock:
            return self._completed

    @property
    def exception(self) -> None | Exception:
        with self._lock:
            return self._exception

    def _update_progress(self, value: int) -> None:
        with self._lock:
            self._progress = value
            if self._progress_callback_func:
                self._progress_callback_func(self._id, value)

    def _update_completed(self, value: bool, exception: Exception = None) -> None:
        with self._lock:
            self._completed = value
            if exception:
                self._exception = exception

    def wait_on_complete(self) -> bool:
        """
        Blocks until the engine has completed processing.
        :return: True if processing was successful, False otherwise.
        """
        try:
            while not self.completed:
                time.sleep(0.1)
        finally:
            if self._exception:
                return False
            return True

    def pack_header(self, data_id: bytes, total_shares: int, required_shares: int, which_segment: int, data_len: int) -> bytes:
        # create a header, 48 bytes, with the following
        # data_id (16 bytes)
        # total_shares (4 bytes)
        # required_shares (4 bytes)
        # which_segment (4 bytes)
        # reserved (4 bytes)
        # reserved (8 bytes)
        # data_len (8 bytes)
        return struct.pack(">16sIIIIQQ", data_id, total_shares, required_shares, which_segment, 0, 0, data_len)

    def unpack_header(self, header: bytes) -> dict:
        return struct.unpack(">16sIIIIQQ", header)

    def decode_header(self, segment_path: str) -> dict:
        """
        Decodes the header of the file to get the key and iv.
        :param segment_path: The path to the segment file.
        :return: A dictionary with the header fields.
        """
        # The header is a 48-byte string with the following format:
        # 16 bytes: data_id (binary identifier)
        # 4 bytes: total_shares
        # 4 bytes: required_shares
        # 4 bytes: which_segment
        # 4 bytes: reserved
        # 8 bytes: reserved
        # 8 bytes: data_len

        # decode for a given segment
        with open(segment_path, "rb") as f:
            header = f.read(48)
            if len(header) != 48:
                raise ValueError(f"Invalid header size: expected 48 bytes, got {len(header)} bytes")
            try:
                data_id, total_shares, required_shares, which_segment, res1, res2, data_len = struct.unpack(">16sIIIIQQ", header)
                return {
                    "data_id": data_id,
                    "data_id_str": str(uuid.UUID(bytes=data_id)),
                    "total_shares": total_shares,
                    "required_shares": required_shares,
                    "which_segment": which_segment,
                    "is_parity": 1 if which_segment + 1 > required_shares else 0,
                    "data_len": data_len
                }
            except struct.error as e:
                raise ValueError(f"Failed to decode header: {str(e)}")
