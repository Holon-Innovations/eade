import dis
import os
import random
from re import T

import test
from eade import rad_engine
from eade import ead_engine
from eade.ead_engine import EaDEngine
from eade.rad_engine import RaDEngine

def distribute_file(test_file: str) -> EaDEngine:
    # create an instance of the engine and distribute the file
    eadengine = EaDEngine(
        file_path="tests/random_files/largeblob1.bin",
        total_shares=10,
        required_shares=5,
        output_path="tests/dist/")
    eadengine.split_file()

    # wait for the engine to complete
    if not eadengine.wait_on_complete():
        raise Exception(eadengine.exception)
    else:
        assert True

    return eadengine

def restore_file(eadengine: EaDEngine, test_segments: list) -> RaDEngine:
    # restore the file
    radengine = RaDEngine(
        output_path="tests/dist/",
        key=eadengine.key,
        iv=eadengine.iv,
        segments=test_segments)
    radengine.restore_file()

    # wait for the engine to complete
    if not radengine.wait_on_complete():
        raise Exception(radengine.exception)
    else:
        assert True

    return radengine

def test_large_file_complete_segments():
    # create an instance of the engine and distribute the file
    ead_eng = distribute_file(test_file="tests/random_files/largeblob1.bin")

    # restore the file
    rad_eng = restore_file(eadengine=ead_eng, test_segments=ead_eng.segments)

    # compare the original file with the restored file, readin file hashs
    original_hash_file_name = f"tests/dist/{rad_eng.id}/largeblob1.bin.sha256"
    restored_hash_file_name = f"tests/dist/{rad_eng.id}/restored.blob.sha256"
    with open(original_hash_file_name, "r") as file:
        original_hash = file.read()
    with open(restored_hash_file_name, "r") as file:
        restored_hash = file.read()
    if original_hash == restored_hash:
        assert True
    else:
        assert False

def test_large_file_missing_segments():
    # create an instance of the engine and distribute the file
    ead_eng = distribute_file(test_file="tests/random_files/largeblob1.bin")

    # remove some segments
    test_segments = ead_eng.segments.copy()
    for i in range(3):
        random_index = random.randint(0, len(test_segments) - 1)
        test_segments.pop(random_index)

    # restore the file
    rad_eng = restore_file(eadengine=ead_eng, test_segments=test_segments)

    # compare the original file with the restored file, readin file hashs
    original_hash_file_name = f"tests/dist/{rad_eng.id}/largeblob1.bin.sha256"
    restored_hash_file_name = f"tests/dist/{rad_eng.id}/restored.blob.sha256"
    with open(original_hash_file_name, "r") as file:
        original_hash = file.read()
    with open(restored_hash_file_name, "r") as file:
        restored_hash = file.read()
    if original_hash == restored_hash:
        assert True
    else:
        assert False

def test_large_file_missing_too_many_segments():
    # create an instance of the engine and distribute the file
    ead_eng = distribute_file(test_file="tests/random_files/largeblob1.bin")

    # remove some segments
    test_segments = ead_eng.segments.copy()
    for i in range(6):
        random_index = random.randint(0, len(test_segments) - 1)
        test_segments.pop(random_index)

    # restore the file with too many missing segments
    try:
        rad_eng = restore_file(eadengine=ead_eng, test_segments=test_segments)
        assert False
    except Exception as e:
        assert True