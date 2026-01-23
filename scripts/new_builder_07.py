import argparse
from pathlib import Path


# ---------- FILE → BITS → 36-BIT BLOCKS ----------


def file_to_bitstring(path: Path, ascii7: bool = False) -> str:
    """
    Convert a file to one long bitstring.

    If ascii7 is False (default):
        - Treat file as raw bytes
        - Each byte -> 8 bits (f"{b:08b}")
        - Works for ANY file type (binary-safe)

    If ascii7 is True:
        - Treat file as text (UTF-8)
        - Each character -> 7 bits (format(ord(c), "07b"))
        - Only makes sense for plain-text data
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


def bitstring_to_blocks(bits: str, block_size: int = 36) -> list[str]:
    """
    Split a long bitstring into fixed-size blocks (36 bits).
    Last block is right-padded with '0' if needed.
    """
    blocks = [bits[i: i + block_size] for i in range(0, len(bits), block_size)]
    if len(blocks[-1]) < block_size:
        blocks[-1] = blocks[-1].ljust(block_size, "0")
    return blocks


# ---------- PROTOCOL GENERATION ----------


def build_multiblock_protocol(
    data_path: Path,
    blocks: list[str],
    output_py: Path,
    transfer_vol: float,
    brick_stock: float | None,
    mix_times: int,
    mix_vol: float | None,
    asp_flow: float | None,
    asp_depth: float | None,
) -> None:
    """
    Build a single OT-2 Python protocol that encodes all blocks into brick mixes.
    """

    num_blocks = len(blocks)
    if num_blocks == 0:
        raise ValueError("No blocks to encode.")

    # If brick stock not specified, choose enough for 15 blocks per brick + 5 µL margin
    if brick_stock is None:
        brick_stock = transfer_vol * 15 + 5.0

    # Python literal for the blocks list
    blocks_literal = "[\n" + "".join(f'    "{b}",\n' for b in blocks) + "]"

    file_name = data_path.name

    code = f"""from opentrons import protocol_api

metadata = {{
    "protocolName": "BRICK MIX - MULTIBLOCK ({file_name})",
    "author": "Franci / auto-generated",
    "description": "Encode file '{file_name}' into {num_blocks} DNA brick mixes (36 bits per block).",
}}

requirements = {{
    "robotType": "OT-2",
    "apiLevel": "2.15",
}}

# ---- CONFIG (baked in by builder) ----

BLOCK_SIZE = 36  # bits per block
TRANSFER_VOL = {transfer_vol}  # µL per brick transfer
BRICK_STOCK = {brick_stock}  # starting stock volume per brick well (µL)

MIX_TIMES = {mix_times}       # pre-aspiration mixing cycles (0 = no mix)
MIX_VOL = {mix_vol if mix_vol is not None else "None"}   # µL; None -> use TRANSFER_VOL
ASP_FLOW = {asp_flow if asp_flow is not None else "None"}  # µL/s; None -> leave default
ASP_DEPTH = {asp_depth if asp_depth is not None else "None"}  # mm from bottom; None -> 1.0

# Each element is a 36-character string of '0'/'1'.
# Bit i (0-based) -> brick (i + 2) (bricks 2..37). Bricks 1 and 38 always UNMOD.
BLOCKS = {blocks_literal}

# Deck layout (EDIT THESE TO MATCH YOUR ROBOT)
#  - 6 tip racks -> up to 15 blocks per cycle (38 tips × 15 = 570 tips < 6×96 = 576)
TIP_SLOTS = ["1", "3", "6", "8", "9", "11"]  # adjust if needed
UNMOD_SLOT = "5"  # 96-well plate with UNMOD bricks
MOD_SLOT = "4"    # 96-well plate with MOD bricks (no bricks for 1 and 38)
MIX_SLOT = "2"    # 96-well destination plate for brick mixes

TIP_RACK_NAME = "geb_96_tiprack_10ul"              # tip rack loadName
BRICK_PLATE_NAME = "opentronspcrrack_96_wellplate_100ul"  # brick stock custom labware loadName
DEST_PLATE_NAME = BRICK_PLATE_NAME                 # using same model for brick mix

# Tip constraint: we designed for 6 racks, 15 blocks per cycle
BLOCKS_PER_TIP_CYCLE = 15


def run(protocol: protocol_api.ProtocolContext) -> None:
    # ---- LABWARE & INSTRUMENTS ----
    tip_racks = [protocol.load_labware(TIP_RACK_NAME, slot) for slot in TIP_SLOTS]
    pipette = protocol.load_instrument("p10_single", mount="left", tip_racks=tip_racks)

    unmod_plate = protocol.load_labware(
        BRICK_PLATE_NAME, UNMOD_SLOT, "unmod bricks"
    )
    mod_plate = protocol.load_labware(
        BRICK_PLATE_NAME, MOD_SLOT, "mod bricks"
    )
    mix_plate = protocol.load_labware(
        DEST_PLATE_NAME, MIX_SLOT, "brick mix destination"
    )

    # ---- DESTINATION WELL ACCESS (SPARSE ROWS A, C, E, G, H) ----
    # We only use these rows for brick mixes: A, C, E, G, H
    # => row indices [0, 2, 4, 6, 7] in plate.rows()
    DEST_ROW_INDICES = [0, 2, 4, 6, 7]

    def dest_well_for_block(plate, block_index: int):
        \"\"\"Map block index 0..59 to:
           A1–A12, C1–C12, E1–E12, G1–G12, H1–H12 (60 tubes total).
        \"\"\"
        rows = plate.rows()
        num_cols = len(rows[0])  # assume 12
        wells_per_row = num_cols
        max_blocks = wells_per_row * len(DEST_ROW_INDICES)  # 60

        if block_index < 0 or block_index >= max_blocks:
            raise RuntimeError(
                f"Block index {{block_index}} exceeds capacity of one destination rack ({{max_blocks}} mixes)."
            )

        row_block = block_index // wells_per_row   # 0..4 => A, C, E, G, H
        col_idx = block_index % wells_per_row      # 0..11
        row_idx = DEST_ROW_INDICES[row_block]
        return rows[row_idx][col_idx]

    # Volumes tracked per brick index (1..38)
    brick_unmod_vol = {{i: BRICK_STOCK for i in range(1, 39)}}
    brick_mod_vol = {{i: BRICK_STOCK for i in range(2, 38)}}  # only 2..37 have mod bricks

    # Destination capacity: 60 tubes per rack (A/C/E/G/H rows used)
    blocks_per_plate = 60
    blocks_in_plate = 0
    blocks_in_tip_cycle = 0

    low_unmod = set()
    low_mod = set()

    def brick_source(brick_num: int, kind: str):
        \"\"\"Map brick index 1..38 to your PCR-tube layout on brick plates:

           1–12  -> row A, cols 1–12
           13–24 -> row C, cols 1–12
           25–36 -> row E, cols 1–12
           37–38 -> row G, cols 1–2
        \"\"\"
        if brick_num < 1 or brick_num > 38:
            raise ValueError(f"Brick index out of range: {{brick_num}}")

        plate = unmod_plate if kind == "unmod" else mod_plate
        rows = plate.rows()

        if 1 <= brick_num <= 12:
            row_idx = 0      # A
            col_idx = brick_num - 1
        elif 13 <= brick_num <= 24:
            row_idx = 2      # C
            col_idx = brick_num - 13
        elif 25 <= brick_num <= 36:
            row_idx = 4      # E
            col_idx = brick_num - 25
        else:  # 37–38
            row_idx = 6      # G
            col_idx = brick_num - 37

        return rows[row_idx][col_idx]

    def update_volume_and_flags(brick_num: int, kind: str):
        \"\"\"Update volume tracking and flag bricks that drop below threshold.\"\"\"
        threshold = TRANSFER_VOL + 5.0  # pause when vol < transfer_vol + 5 µL
        if kind == "unmod":
            brick_unmod_vol[brick_num] -= TRANSFER_VOL
            if brick_unmod_vol[brick_num] < threshold:
                low_unmod.add(brick_num)
        else:
            brick_mod_vol[brick_num] -= TRANSFER_VOL
            if brick_mod_vol[brick_num] < threshold:
                low_mod.add(brick_num)

    def do_transfer(brick_num: int, kind: str, dest):
        src = brick_source(brick_num, kind)

        pipette.pick_up_tip()

        # Optional pre-aspiration mixing
        if MIX_TIMES and MIX_TIMES > 0:
            mv = MIX_VOL if MIX_VOL is not None else TRANSFER_VOL
            pipette.mix(MIX_TIMES, mv, src)

        # Optional aspirate flow rate + depth
        if ASP_FLOW is not None:
            pipette.flow_rate.aspirate = ASP_FLOW
        depth = ASP_DEPTH if ASP_DEPTH is not None else 1.0

        pipette.aspirate(TRANSFER_VOL, src.bottom(depth))
        pipette.dispense(TRANSFER_VOL, dest.bottom(1.0))
        pipette.drop_tip()

        update_volume_and_flags(brick_num, kind)

    total_blocks = len(BLOCKS)

    for block_idx, bits in enumerate(BLOCKS):
        # ---- Assign destination tube for this block ----
        if blocks_in_plate >= blocks_per_plate and (block_idx < total_blocks):
            protocol.pause(
                "Destination rack full (60 mixes in rows A/C/E/G/H). "
                "Replace plate in slot "
                + MIX_SLOT
                + " with a NEW empty rack of capped tubes, then press RESUME."
            )
            blocks_in_plate = 0

        dest = dest_well_for_block(mix_plate, blocks_in_plate)
        blocks_in_plate += 1
        blocks_in_tip_cycle += 1

        # Debug comment: where is this block going?
        try:
            dest_name = dest.well_name
        except AttributeError:
            dest_name = dest.display_name
        protocol.comment(
            f"Block {{block_idx + 1}}/{{total_blocks}} -> dest {{dest_name}}, bits={{bits}}"
        )

        # ---- Perform 38 transfers for this block ----
        # 1. Brick 1 (always UNMOD)
        do_transfer(1, "unmod", dest)

        # 2. Bricks 2..37 based on 36 bits
        if len(bits) != BLOCK_SIZE:
            raise RuntimeError(
                f"Block {{block_idx}} has length {{len(bits)}}, expected {{BLOCK_SIZE}}."
            )

        for bit_index, bit_char in enumerate(bits):
            brick_num = bit_index + 2  # bit 0 -> brick 2, bit 35 -> brick 37
            kind = "mod" if bit_char == "1" else "unmod"
            if kind == "mod" and brick_num not in brick_mod_vol:
                raise RuntimeError(f"No mod brick defined for index {{brick_num}}.")
            do_transfer(brick_num, kind, dest)

        # 3. Brick 38 (always UNMOD)
        do_transfer(38, "unmod", dest)

        # ---- Decide whether to pause ----
        pause_reasons = []
        need_tip_reset = False

        # Condition 1: any brick stock below TRANSFER_VOL + 5 µL
        if (low_unmod or low_mod) and (block_idx + 1 < total_blocks):
            msg_lines = [
                "Brick stock volumes low (below TRANSFER_VOL + 5 µL). Refill these bricks:"
            ]
            if low_unmod:
                msg_lines.append(
                    "  Unmod bricks: " + ", ".join(str(b) for b in sorted(low_unmod))
                )
            if low_mod:
                msg_lines.append(
                    "  Mod bricks: " + ", ".join(str(b) for b in sorted(low_mod))
                )
            pause_reasons.append("\\n".join(msg_lines))

        # Condition 2: after every BLOCKS_PER_TIP_CYCLE blocks (tip refill)
        if (
            blocks_in_tip_cycle >= BLOCKS_PER_TIP_CYCLE
            and (block_idx + 1 < total_blocks)
        ):
            pause_reasons.append(
                f"{{BLOCKS_PER_TIP_CYCLE}} blocks completed. "
                "Refill all tip racks, then press RESUME."
            )
            need_tip_reset = True

        # Condition 3: destination rack full handled above

        if pause_reasons:
            protocol.pause("\\n\\n".join(pause_reasons))

            # After pause: assume user refilled low bricks
            for b in low_unmod:
                brick_unmod_vol[b] = BRICK_STOCK
            for b in low_mod:
                brick_mod_vol[b] = BRICK_STOCK
            low_unmod.clear()
            low_mod.clear()

            # After refilling tips, reset tip tracking
            if need_tip_reset:
                pipette.reset_tipracks()
                blocks_in_tip_cycle = 0

    protocol.comment(f"Finished encoding {{total_blocks}} blocks from file '{file_name}'.")
"""


    output_py.write_text(code)
    print(f"Built multi-block protocol: {output_py}")
    print(f"  File: {file_name}")
    print(f"  Blocks: {num_blocks}")
    print(f"  Transfer volume: {transfer_vol} µL")
    print(f"  Brick stock: {brick_stock} µL per brick well (initial)")


# ---------- CLI ----------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build a multi-block OT-2 protocol that encodes an arbitrary file "
            "into DNA brick mixes (36 bits per block)."
        )
    )
    parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="Path to the input data file to encode.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output .py protocol filename (default: BRICK_MIX_<FILENAME>.py).",
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
        help="Number of pre-aspiration mixing cycles (default: 0, i.e., no mixing).",
    )
    parser.add_argument(
        "--mix-vol",
        type=float,
        default=None,
        help="Mix volume in µL (default: None → use transfer volume).",
    )
    parser.add_argument(
        "--asp-flow",
        type=float,
        default=None,
        help="Aspirate flow rate in µL/s (default: None → use instrument default).",
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
            "Interpret the file as text and encode each character as 7-bit ASCII. "
            "Default is binary-safe 8 bits per byte."
        ),
    )

    args = parser.parse_args()

    data_path = Path(args.file).resolve()
    if not data_path.is_file():
        raise SystemExit(f"Input file not found: {data_path}")

    bits = file_to_bitstring(data_path, ascii7=args.ascii7)
    blocks = bitstring_to_blocks(bits, block_size=36)

    # Decide filename
    if args.output:
        filename = args.output
    else:
        stem = data_path.name.replace(" ", "_")
        filename = f"BRICK_MIX_{stem}.py"

    # Force output directory to the BRICK MIX PROTOCOLS folder on Desktop
    output_dir = Path(
        r"/mnt/c/Users/franc/Desktop/OT-2_protocols/BRICK MIX PROTOCOLS"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_py = (output_dir / filename).resolve()

    build_multiblock_protocol(
        data_path=data_path,
        blocks=blocks,
        output_py=output_py,
        transfer_vol=args.transfer_vol,
        brick_stock=args.brick_stock,
        mix_times=args.mix_times,
        mix_vol=args.mix_vol,
        asp_flow=args.asp_flow,
        asp_depth=args.asp_depth,
    )


if __name__ == "__main__":
    main()
