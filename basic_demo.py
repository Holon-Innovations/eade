import os
import random
import shutil
import time

from eade.ead_engine import EaDEngine
from eade.rad_engine import RaDEngine

def test_file(test_total_shares: int, test_remove_segments: int):
    # create a random file blob that is a random size between 50MB and 100MB
    random_file_size = random.randint(50, 100)
    random_file_size *= 1024 * 1024
    random_file = os.urandom(random_file_size)
    random_file_path = f"tests/random_files/{random_file_size}_mb_blob.bin"
    with open(random_file_path, "wb") as file:
        file.write(random_file)
    try:
        # make required shares = total shares random / 2
        test_required_shares = int(test_total_shares / 2)
        print(f"Random file created: {random_file_path}, testing with {test_total_shares} total shares, {test_required_shares} required shares and {test_remove_segments} missing segments.")
        test_segments = []
        last_percent = 0

        def on_progress(id, progress):
            nonlocal last_percent
            if progress % 10 == 0:
                if last_percent == progress:
                    return
                print(f"{id} - Progress: {progress}%")
                last_percent = progress

        def on_distribute_complete(id, segments):
            print(f"{id} - Distribute complete. File split into {len(segments)} segments.")
            nonlocal test_segments
            nonlocal test_remove_segments
            for segment in segments:
                test_segments.append(segment)

            # for testing, remove the segments from random positions
            if test_remove_segments > 0:
                for i in range(test_remove_segments):
                    random_index = random.randint(0, len(test_segments) - 1)
                    test_segments.pop(random_index)
                    print(f"Removed segment at index {random_index}.")


        def on_rebuild_complete(id, decrypted_file_path):
            print(f"{id} - Restored file saved to {decrypted_file_path} using {len(test_segments)} segments.")

        def on_exception(id, exception):
            print(f"{id} - An exception occurred: {exception}")

        # keys
        key = "UlW_heN5uzEle9rb4_CqrO5nkFgS4HH1".encode()
        iv  = "tswn0VXbEK0KXqhS".encode()

        # create an instance of the engine and distribute the file
        eadengine = EaDEngine(
            file_path=random_file_path,
            total_shares=test_total_shares,
            required_shares=test_required_shares,
            output_path="tests/dist/",
            key=key,
            iv=iv,
            success_callback_func=on_distribute_complete,
            exception_callback_func=on_exception,
            progress_callback_func=on_progress)
        eadengine.split_file()

        # wait for the engine to complete
        if not eadengine.wait_on_complete():
            print("Encyption and distribution failed!")
            return
        else:
            print("Encryption and distribution complete!")

        # restore the file
        radengine = RaDEngine(
            output_path="tests/dist/",
            key=key,
            iv=iv,
            segments=test_segments,
            success_callback_func=on_rebuild_complete,
            exception_callback_func=on_exception,
            progress_callback_func=on_progress)
        radengine.restore_file()

        # wait for the engine to complete
        if not radengine.wait_on_complete():
            print("Decryption and restoration failed!")
            return
        else:
            print("Decryption and restoration complete!")

        # compare the original file with the restored file, readin file hashs
        original_hash_file_name = os.path.join(f"tests/dist/{radengine.id}/", os.path.basename(random_file_path)) + ".sha256"
        restored_hash_file_name = f"tests/dist/{radengine.id}/restored.blob.sha256"
        with open(original_hash_file_name, "r") as file:
            original_hash = file.read()
        with open(restored_hash_file_name, "r") as file:
            restored_hash = file.read()
        if original_hash == restored_hash:
            print(f"File hashes match! {original_hash} == {restored_hash}")
        else:
            print("File hashes DO NOT match!")

    finally:
        # remove the random file
        os.remove(random_file_path)

if __name__ == '__main__':

    # remove all files in the test directory
    shutil.rmtree("tests/dist/", ignore_errors=True)
    time.sleep(1)

    # run the test N times
    for i in range(5):
        print(f"Test run {i + 1}")
        random_total_files = random.randint(5, 10)
        random_required_files = random.randint(3, 7)
        random_missing_files = random.randint(0, 2)
        test_file(test_total_shares=random_total_files, test_remove_segments=random_missing_files)