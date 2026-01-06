import pytest
from scripts.winUser.brickMixAndSAOT2 import bitstring_to_blocks

def test_bitstring_to_blocks_exact():
    bits = "0" * 36
    blocks = bitstring_to_blocks(bits, block_size=36)
    assert blocks == ["0" * 36]

def test_bitstring_to_blocks_padding():
    bits = "1" * 5
    blocks = bitstring_to_blocks(bits, block_size=36)
    assert len(blocks) == 1
    assert blocks[0].startswith("1" * 5)
    assert len(blocks[0]) == 36
    assert blocks[0][5:] == "0" * (36 - 5)

def test_bitstring_empty_raises():
    with pytest.raises(ValueError):
        bitstring_to_blocks("", block_size=36)
