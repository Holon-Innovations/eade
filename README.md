The **Encryption and Distribution Engine** is a robust system designed for secure file encryption, distribution, and reassembly. Comprised of two main components—**EaDEngine** (Encryption and Distribution) and **RaDEngine** (Reassembly and Decryption)—this engine enables the secure division and distribution of files, using AES256 encryption and erasure coding principles, to allow for later reconstruction, even if parts of the data are missing.

1. **EaDEngine (Encryption and Distribution)**: This component is responsible for encrypting a file, splitting it into encrypted segments, and distributing those segments to a designated output directory. Using **AES256 encryption**, the EaDEngine securely encrypts the file with a specified key and IV. It then applies **erasure coding** (with the `zfec` library) to split the file into a configurable number of segments, or “shares,” with a minimum threshold required for reassembly. This process ensures that the file can be reconstructed even if some shares are lost.

   - **AES256 Encryption**: The file is encrypted using a 32-byte AES256 key and a 16-byte initialization vector (IV) for high security.
   - **Erasure Coding**: Through Reed-Solomon encoding, EaDEngine divides the encrypted file into multiple shares, ensuring only a subset of these shares is needed for reconstruction.
   - **Hashing for Integrity**: EaDEngine can optionally generate SHA256 hashes for the original, encrypted, and segmented files, which can later be used to verify data integrity.

2. **RaDEngine (Reassembly and Decryption)**: The RaDEngine performs the inverse of the EaDEngine’s process, taking the minimum number of segments required and reassembling them into the original file. It reassembles the encrypted data, then decrypts it, producing the original content.

   - **Reassembly**: RaDEngine reconstructs the encrypted file from the provided segments, using the erasure coding properties that make it resilient to data loss.
   - **Decryption**: After reassembly, RaDEngine decrypts the data using AES256, restoring the original content.
   - **Integrity Verification**: RaDEngine can generate a SHA256 hash of the restored file to compare it with the original hash, verifying the file’s integrity.

### Key Features of the Encryption and Distribution Engine

- **Secure Distribution of Sensitive Data**: With encryption and erasure coding, files are both encrypted and split into segments, ensuring data security and resilience. Unauthorized users cannot reconstruct the file without sufficient segments, the encryption key, and IV.
- **Partial Share Reconstruction**: The system can reconstruct files from only a subset of shares, making it robust against data loss.
- **Asynchronous Processing**: Both engines operate in separate threads, providing real-time progress updates and completion callbacks, ideal for applications needing non-blocking operations.
- **Customizable Callbacks**: Users can define custom callback functions for completion, progress, and exception handling, making it highly suitable for integration in web applications or GUIs.
- **Hash Verification**: The optional SHA256 hashing feature offers an extra layer of data integrity, ensuring that each segment and the final reconstructed file remain unchanged.

### Example Workflow

1. **Encryption and Distribution (EaDEngine)**:
   - A user initiates EaDEngine to encrypt and split a file (e.g., "file.txt").
   - EaDEngine encrypts the file and divides it into multiple encrypted segments.
   - Each segment is saved in the output directory, allowing future reconstruction if at least the required number of segments is available.

2. **Reassembly and Decryption (RaDEngine)**:
   - A user provides the minimum required segments to RaDEngine to reconstruct the file.
   - RaDEngine reassembles the encrypted file, decrypts it, and restores the original data.
   - The hash of the reconstructed file, if generated, can verify its integrity.

### Summary

The Encryption and Distribution Engine combines strong encryption, fault tolerance, and integrity verification, offering a secure solution for distributing, storing, and restoring sensitive files. With its resilience to partial data loss and capability to verify data integrity, this engine is ideal for scenarios where security and reliability are critical.

---

## EaDEngineAPI

The `EaDEngineAPI` provides a simplified interface to split a file into encrypted shares using the `EaDEngine` class. This API abstracts the complexity of AES256 encryption, file splitting, and progress tracking.

### Class Definition
```python
class EaDEngineAPI:
    def __init__(
	    self,
	    file_path: str,
	    required_shares: int,
	    total_shares: int,
	    output_path: str,
	    key: bytes = None,
	    iv: bytes = None,
	    success_callback = None,
	    exception_callback = None,
        progress_callback = None,
        hash_results: bool = True
    ):
```

#### Parameters
- `file_path` (str): Path to the file to be split.
- `required_shares` (int): Minimum number of shares needed to reconstruct the file.
- `total_shares` (int): Total number of shares to create.
- `output_path` (str): Directory path to save the split files.
- `key` (bytes, optional): 32-byte AES256 encryption key. If `None`, a key is auto-generated.
- `iv` (bytes, optional): 16-byte AES encryption initialization vector. If `None`, an IV is auto-generated.
- `success_callback` (callable, optional): Function called on successful completion.
- `exception_callback` (callable, optional): Function called if an exception occurs.
- `progress_callback` (callable, optional): Function to track progress.
- `hash_results` (bool, optional): If `True`, generates SHA256 hashes for the file and shares.

---
### Methods

#### `split_file`
```python
def split_file(self)
```

#### Description
Begins the asynchronous process of encrypting and splitting the specified file into multiple segments. This method initiates encryption, performs erasure coding to create redundant shares, and saves these segments to an output directory. It also tracks the progress of this process and updates via a callback function if specified.

#### Usage
- **Asynchronous**: This method runs in a separate thread, allowing the main program to continue executing without blocking. Users can monitor progress through `get_progress()` and check if the operation has completed with `is_completed()`.
- **Callbacks**: Success and exception callbacks are called upon completion or failure, respectively.

---
### Callback Function Types

The `split_file` method is commonly used with the following callback functions to provide status updates and handle events:

- **Success Callback**: Invoked when the file is successfully split and all segments are saved.
  ```python
  def my_success_callback(id, segments):
      print(f"File split successfully! ID: {id}")
      print("Generated segments:", segments)
  ```

- **Exception Callback**: Invoked if an error occurs during processing, passing the exception details.
  ```python
  def my_exception_callback(id, exception):
      print(f"Error splitting file with ID {id}: {exception}")
  ```

- **Progress Callback**: Invoked periodically to provide a progress update.
  ```python
  def my_progress_callback(id, progress):
      print(f"Progress for ID {id}: {progress}%")
  ```

---
### Properties

#### `id`
```python
@property
def id(self) -> str
```
Unique identifier generated for each processing session, useful for tracking operations.

- **Type**: `str`
- **Description**: Unique identifier (UUID) of the current session.

---
#### `key`
```python
@property
def key(self) -> bytes
```
Returns the AES256 encryption key used for encrypting or decrypting the file.

- **Type**: `bytes`
- **Description**: AES256 key used in encryption/decryption.

---
#### `iv`
```python
@property
def iv(self) -> bytes
```
Returns the initialization vector (IV) used in AES encryption/decryption.

- **Type**: `bytes`
- **Description**: 16-byte initialization vector (IV).

---
#### `output_path`
```python
@property
def output_path(self) -> str
```
Returns the path to the directory where encrypted segments are stored. Note, this is appended with the ID (i.e. /output_path/id)

- **Type**: `str`
- **Description**: Output directory containing the segments.

---
#### `progress`
```python
@property
def progress(self) -> int
```
Returns the progress of the ongoing operation as a percentage (0–100).

- **Type**: `int`
- **Description**: Progress percentage for split (EaDEngine) or reassembly (RaDEngine) operations.

---
#### `completed`
```python
@property
def completed(self) -> bool
```
Indicates whether the engine has completed its operation.

- **Type**: `bool`
- **Description**: `True` if the process is complete, otherwise `False`.

---
#### `exception`
```python
@property
def exception(self) -> Exception | None
```
Returns any exception encountered during processing, or `None` if no errors occurred.

- **Type**: `Exception` or `None`
- **Description**: Captures any error encountered during the operation for debugging purposes.

---
#### `file_path`
```python
@property
def file_path(self) -> str
```
Returns the original file path of the file being encrypted and split.

- **Type**: `str`
- **Description**: Path to the input file for processing.

---
#### `required_shares`
```python
@property
def required_shares(self) -> int
```
Returns the minimum number of shares required to reconstruct the original file.

- **Type**: `int`
- **Description**: Number of shares needed for successful reassembly.

---
#### `total_shares`
```python
@property
def total_shares(self) -> int
```
Returns the total number of shares created from the original file.

- **Type**: `int`
- **Description**: Total number of shares generated.

---
#### `segments`
```python
@property
def segments(self) -> list
```
Returns the list of file paths to each generated segment.

- **Type**: `list`
- **Description**: List of file paths for each segment created from the file.

---
### Example Usage

```python
api = EaDEngineAPI(
    file_path="path/to/file.txt",
    required_shares=3,
    total_shares=5,
    output_path="path/to/output",
    key=my_key,
    iv=my_iv,
    success_callback=my_success_callback,
    exception_callback=my_exception_callback,
    progress_callback=my_progress_callback
)

# Start the file split operation
api.split_file()

# Monitor progress
while not api.is_completed():
    print(f"Progress: {api.get_progress()}%")

# Get segment paths after completion
segments = api.get_segments()
```

---

## RaDEngineAPI

The `RaDEngineAPI` class provides a simplified interface to reconstruct and decrypt a file from its shares using the `RaDEngine` class.

### Class Definition
```python
class RaDEngineAPI:
    def __init__(self,
	    output_path: str,
	    key: bytes,
	    iv: bytes,
	    segments: list,
        success_callback = None,
        exception_callback = None,
        progress_callback = None,
        restored_file_name: str = None,
        hash_results: bool = True
    ):
```

#### Parameters
- `output_path` (str): Directory path where the restored file will be saved.
- `key` (bytes): AES256 encryption key (32 bytes) for decryption.
- `iv` (bytes): AES encryption initialization vector (16 bytes) for decryption.
- `segments` (list): List of paths to segment files needed for reconstruction.
- `success_callback` (callable, optional): Function called on successful restoration.
- `exception_callback` (callable, optional): Function called if an exception occurs.
- `progress_callback` (callable, optional): Function to track progress.
- `restored_file_name` (str, optional): Name for the restored file. Defaults to `restored.blob`.
- `hash_results` (bool, optional): If `True`, generates SHA256 hash of the restored file.

---
### Methods

The **restore** method in the RaDEngine reconstructs an encrypted file from provided segments and decrypts it to produce the original content. This method operates asynchronously and includes support for callbacks to monitor progress, handle exceptions, and notify upon completion.

#### `restore_file`
```python
def restore_file(self)
```

#### Description
Begins the asynchronous process of reconstructing the original file from its segments and decrypting it. This method verifies that enough segments are provided to reconstruct the file, reassembles the encrypted data, decrypts it using AES256, and saves the restored file in the specified output directory.

#### Usage
- **Asynchronous**: Runs in a separate thread, enabling the main program to continue executing. Users can monitor progress with `get_progress()` and check for completion using `is_completed()`.
- **Callbacks**: Success, exception, and progress callbacks allow real-time monitoring and error handling.

---
### Callback Function Types

The `restore_file` method supports the following callback functions to track the status of the operation and handle events:

- **Success Callback**: Invoked when the file is successfully restored and saved to the output directory.
  ```python
  def my_success_callback(id, restored_file_path):
      print(f"File restored successfully! ID: {id}")
      print("Restored file path:", restored_file_path)
  ```

- **Exception Callback**: Invoked if an error occurs during restoration, passing the exception details.
  ```python
  def my_exception_callback(id, exception):
      print(f"Error restoring file with ID {id}: {exception}")
  ```

- **Progress Callback**: Invoked periodically to provide a progress update.
  ```python
  def my_progress_callback(id, progress):
      print(f"Progress for ID {id}: {progress}%")
  ```

---
### Properties

#### `id`
```python
@property
def id(self) -> str
```
Unique identifier generated for each processing session, useful for tracking operations.

- **Type**: `str`
- **Description**: Unique identifier (UUID) of the current session.

---
#### `key`
```python
@property
def key(self) -> bytes
```
Returns the AES256 encryption key used for encrypting or decrypting the file.

- **Type**: `bytes`
- **Description**: AES256 key used in encryption/decryption.

---
#### `iv`
```python
@property
def iv(self) -> bytes
```
Returns the initialization vector (IV) used in AES encryption/decryption.

- **Type**: `bytes`
- **Description**: 16-byte initialization vector (IV).

---
#### `output_path`
```python
@property
def output_path(self) -> str
```
Returns the path to the directory where encrypted segments are stored. Note, this is appended with the ID (i.e. /output_path/id)

- **Type**: `str`
- **Description**: Output directory containing the segments.

---
#### `progress`
```python
@property
def progress(self) -> int
```
Returns the progress of the ongoing operation as a percentage (0–100).

- **Type**: `int`
- **Description**: Progress percentage for split (EaDEngine) or reassembly (RaDEngine) operations.

---
#### `completed`
```python
@property
def completed(self) -> bool
```
Indicates whether the engine has completed its operation.

- **Type**: `bool`
- **Description**: `True` if the process is complete, otherwise `False`.

---
#### `exception`
```python
@property
def exception(self) -> Exception | None
```
Returns any exception encountered during processing, or `None` if no errors occurred.

- **Type**: `Exception` or `None`
- **Description**: Captures any error encountered during the operation for debugging purposes.

---
#### `decrypt_file_path`
```python
@property
def decrypt_file_path(self) -> str | None
```
Returns the path to the decrypted (restored) file once the operation completes.

- **Type**: `str` or `None`
- **Description**: Path to the restored file, available after successful completion. Returns `None` if restoration is incomplete.

---
#### `segments`
```python
@property
def segments(self) -> list
```
Returns the list of file paths provided as input segments for reassembly.

- **Type**: `list`
- **Description**: List of segment paths used for reassembly.

---
### Example Usage

```python
api = RaDEngineAPI(
    output_path="path/to/output",
    key=my_key,
    iv=my_iv,
    segments=segment_paths,
    success_callback=my_success_callback,
    exception_callback=my_exception_callback,
    progress_callback=my_progress_callback,
    restored_file_name="my_restored_file"
)

# Start the file restoration process
api.restore_file()

# Monitor progress
while not api.is_completed():
    print(f"Progress: {api.get_progress()}%")

# Get the path of the restored file after completion
restored_path = api.get_restored_file_path()
print(f"Restored file saved at: {restored_path}")
```

---

This API provides a straightforward way for users to:
- Split files using encryption (`EaDEngineAPI`).
- Reconstruct and decrypt files from segments (`RaDEngineAPI`).

The callback functions enable asynchronous handling of completion, exceptions, and progress updates, making these APIs suitable for web or GUI applications that require real-time status monitoring.