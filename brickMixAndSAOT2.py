import argparse
from pathlib import Path


# ---------- FILE / WORD → BITS → 36-BIT BLOCKS ----------


def file_to_bitstring(path: Path, ascii7: bool = False) -> str:
    """
    Convert a file to one long bitstring.

    If ascii7 is False (default):
        - Treat file as raw bytes (binary-safe, works for any file type)
        - Each byte -> 8 bits

    If ascii7 is True:
        - Treat file as text (UTF-8)
        - Each character -> 7-bit ASCII
    """
    if ascii7:
        text = path.read_text(encoding="utf-8")
        if not text:
            raise ValueError(f"Input file {path} is empty.")
        return "".join(format(ord(ch), "07b") for ch in text)
    else:
        data = path.read_bytes()
        if not data:
            raise ValueError(f"Input file {path} is empty.")
        return "".join(f"{b:08b}" for b in data)


def word_to_bitstring(word: str, ascii7: bool = True) -> str:
    """
    Convert a literal word/string to a bitstring.

    By default we use 7-bit ASCII for words (ascii7=True).
    If ascii7=False, we encode the word as UTF-8 bytes and use 8 bits per byte.
    """
    if not word:
        raise ValueError("Word/string is empty.")
    if ascii7:
        return "".join(format(ord(ch), "07b") for ch in word)
    else:
        data = word.encode("utf-8")
        return "".join(f"{b:08b}" for b in data)


def bitstring_to_blocks(bits: str, block_size: int = 36) -> list[str]:
    """
    Split a long bitstring into fixed-size blocks (36 bits).
    Last block is right-padded with '0' if needed.
    """
    if not bits:
        raise ValueError("No bits to encode (empty file/word).")
    blocks = [bits[i:i + block_size] for i in range(0, len(bits), block_size)]
    if len(blocks[-1]) < block_size:
        blocks[-1] = blocks[-1].ljust(block_size, "0")
    return blocks


# ---------- BUILD FULL BM + SA PROTOCOL ----------


def build_multiblock_protocol(
    source_label: str,
    blocks: list[str],
    output_py: Path,
    transfer_vol: float,
    brick_stock: float | None,
    mix_times: int,
    mix_vol: float | None,
    asp_flow: float | None,
    asp_depth: float | None,
    temp_vol: float,
) -> None:
    """
    Build a single OT-2 Python protocol that:
      1) Creates brick mixes for each 36-bit block.
      2) Sets up self-assembly reactions (1 µL BM + template + buffer to 20 µL).
      3) Runs the thermocycler program.

    source_label: human-readable label (either file name or the literal word).
    """
    num_blocks = len(blocks)
    if num_blocks == 0:
        raise ValueError("No blocks to encode.")

    # One destination rack = 60 tubes (rows A, C, E, G, H)
    if num_blocks > 60:
        raise ValueError(
            f"This builder currently supports at most 60 blocks per run, "
            f"but you have {num_blocks}. Split your input or run multiple protocols."
        )

    # If brick stock not specified, choose enough for ~15 blocks per brick + 5 µL
    if brick_stock is None:
        brick_stock = transfer_vol * 15 + 5.0

    RXN_TOTAL_VOL = 20.0
    BM_VOL = 1.0
    if temp_vol <= 0 or temp_vol >= RXN_TOTAL_VOL - BM_VOL:
        raise ValueError(
            f"temp-vol must be > 0 and < {RXN_TOTAL_VOL - BM_VOL}, got {temp_vol}"
        )
    buffer_vol = RXN_TOTAL_VOL - BM_VOL - temp_vol

    # Python literal for blocks
    blocks_literal = "[\n" + "".join(f'    "{b}",\n' for b in blocks) + "]"
    file_name = source_label

    code = f

    output_py.write_text(code)
    print(f"Built multi-block protocol: {output_py}")
    print(f"  Source: {file_name}")
    print(f"  Blocks: {num_blocks}")
    print(f"  Transfer volume: {transfer_vol} µL")
    print(f"  Brick stock: {brick_stock} µL per brick well (initial)")
    print(
        f"  Self-assembly: 1 µL BM + {temp_vol} µL template + {buffer_vol} µL buffer = {RXN_TOTAL_VOL} µL"
    )


# ---------- CLI ----------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build a multi-block OT-2 protocol that encodes a word OR file "
            "into DNA brick mixes (36 bits per block) and sets up self-assembly reactions."
        )
    )
    parser.add_argument(
        "--word",
        "-w",
        help="Literal word/string to encode (mutually exclusive with --file).",
    )
    parser.add_argument(
        "--file",
        "-f",
        help="Path to the input data file to encode (mutually exclusive with --word).",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output .py protocol filename (default: BRICK_MIX_<WORD>.py or BRICK_MIX_<FILENAME>.py).",
    )
    parser.add_argument(
        "--transfer-vol",
        type=float,
        default=2.0,
        help="Transfer volume per brick in µL (default: 2.0).",
    )
    parser.add_argument(
        "--brick-stock",
        type=float,
        default=None,
        help=(
            "Initial stock volume per brick well in µL. "
            "If omitted, defaults to transfer_vol * 15 + 5."
        ),
    )
    parser.add_argument(
        "--mix-times",
        type=int,
        default=0,
        help="Number of pre-aspiration mixing cycles for bricks (default: 0).",
    )
    parser.add_argument(
        "--mix-vol",
        type=float,
        default=None,
        help="Brick pre-mix volume in µL (default: None → use transfer volume).",
    )
    parser.add_argument(
        "--asp-flow",
        type=float,
        default=None,
        help="Aspirate flow rate in µL/s (default: None → instrument default).",
    )
    parser.add_argument(
        "--asp-depth",
        type=float,
        default=None,
        help="Aspirate depth from bottom in mm (default: None → 1.0 mm).",
    )
    parser.add_argument(
        "--ascii7",
        action="store_true",
        help=(
            "For FILE: interpret as text and encode each character as 7-bit ASCII. "
            "Default is binary-safe 8 bits per byte.\n"
            "For WORD: if set, use 7-bit ASCII per character (default); "
            "if not set, encode the word as UTF-8 bytes (8 bits per byte)."
        ),
    )
    parser.add_argument(
        "--temp-vol",
        type=float,
        required=True,
        help="Template DNA volume per reaction in µL (1 µL BM + temp + buffer = 20 µL total).",
    )

    args = parser.parse_args()

    # Enforce: exactly one of --word or --file
    if args.word and args.file:
        raise SystemExit("Please use EITHER --word OR --file, not both.")
    if not args.word and not args.file:
        raise SystemExit("You must provide either --word or --file.")

    # Build bits + blocks
    if args.word:
        bits = word_to_bitstring(args.word, ascii7=args.ascii7 or True)
        source_label = args.word
    else:
        data_path = Path(args.file).resolve()
        if not data_path.is_file():
            raise SystemExit(f"Input file not found: {data_path}")
        bits = file_to_bitstring(data_path, ascii7=args.ascii7)
        source_label = data_path.name

    blocks = bitstring_to_blocks(bits, block_size=36)

    # Output filename
    if args.output:
        filename = args.output
    else:
        if args.word:
            stem = args.word.replace(" ", "_")
        else:
            stem = source_label.replace(" ", "_")
        filename = f"BRICK_MIX_{stem}.py"

    output_dir = Path(r"/mnt/c/Users/franc/Desktop/OT-2_protocols/BRICK MIX PROTOCOLS")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_py = (output_dir / filename).resolve()

    build_multiblock_protocol(
        source_label=source_label,
        blocks=blocks,
        output_py=output_py,
        transfer_vol=args.transfer_vol,
        brick_stock=args.brick_stock,
        mix_times=args.mix_times,
        mix_vol=args.mix_vol,
        asp_flow=args.asp_flow,
        asp_depth=args.asp_depth,
        temp_vol=args.temp_vol,
    )


if __name__ == "__main__":
    main()