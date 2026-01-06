from pathlib import Path
import pytest

from scripts.winUser.brickMixAndSAOT2 import word_to_bitstring, file_to_bitstring

def test_word_to_bitstring_ascii7_default():
    # 'A' = 65 = 1000001 in 7-bit
    assert word_to_bitstring("A", ascii7=True) == "1000001"

def test_word_to_bitstring_utf8_bytes():
    # 'A' = 65 = 01000001 in 8-bit
    assert word_to_bitstring("A", ascii7=False) == "01000001"

def test_word_empty_raises():
    with pytest.raises(ValueError):
        word_to_bitstring("", ascii7=True)

def test_file_to_bitstring_bytes(tmp_path: Path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"\x01\xff")
    assert file_to_bitstring(p, ascii7=False) == "0000000111111111"

def test_file_empty_raises(tmp_path: Path):
    p = tmp_path / "empty.bin"
    p.write_bytes(b"")
    with pytest.raises(ValueError):
        file_to_bitstring(p, ascii7=False)
