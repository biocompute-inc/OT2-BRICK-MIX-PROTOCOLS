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

    code = f"""from opentrons import protocol_api

metadata = {{
    "protocolName": "BRICK MIX + SA - MULTIBLOCK ({file_name})",
    "author": "Franci / auto-generated",
    "description": "Encode '{file_name}' into {num_blocks} DNA brick mixes (36 bits per block) and set up self-assembly reactions.",
}}

requirements = {{
    "robotType": "OT-2",
    "apiLevel": "2.15",
}}

BLOCK_SIZE = 36  # bits per block
TRANSFER_VOL = {transfer_vol}  # µL per brick transfer
BRICK_STOCK = {brick_stock}  # starting stock per brick well (µL)

MIX_TIMES = {mix_times}  # pre-aspiration mixing cycles for bricks
MIX_VOL = {mix_vol if mix_vol is not None else 'None'}  # µL; None → use TRANSFER_VOL
ASP_FLOW = {asp_flow if asp_flow is not None else 'None'}  # µL/s; None → default
ASP_DEPTH = {asp_depth if asp_depth is not None else 'None'}  # mm from bottom; None → 1.0

RXN_TOTAL_VOL = {RXN_TOTAL_VOL}  # self-assembly total volume
BM_VOL = {BM_VOL}  # brick mix volume per SA reaction
TEMP_VOL = {temp_vol}  # template DNA volume per SA reaction
BUFFER_VOL = {buffer_vol}  # TAE/Mg2+ buffer volume per SA reaction

# Each element is a 36-bit string ('0'/'1').
BLOCKS = {blocks_literal}

# Deck layout:
#   ThermocyclerModuleV1 in slot 7 (occupies 7,8,10,11)
#   UNMOD bricks plate in slot 5
#   MOD bricks plate in slot 4
#   BRICK MIX destination plate in slot 2
#   TIP RACKS in slots 1,3,6,9 (safe with TC footprint)
TIP_SLOTS = ["1", "3", "6", "9"]
UNMOD_SLOT = "5"  # unmodified bricks (later: TEMPLATE DNA)
MOD_SLOT = "4"    # modified bricks (later: BUFFER)
MIX_SLOT = "2"    # brick mix destination rack

TIP_RACK_NAME = "geb_96_tiprack_10ul"
BRICK_PLATE_NAME = "opentronspcrrack_96_wellplate_100ul"
DEST_PLATE_NAME = BRICK_PLATE_NAME

SA_PLATE_NAME = "nest_96_wellplate_100ul_pcr_full_skirt"

# 4 tip racks × 96 tips = 384 tips → ~10 blocks (38 tips per block)
BLOCKS_PER_TIP_CYCLE = 10


def run(protocol: protocol_api.ProtocolContext) -> None:
    \"\"\"Executed on the OT-2.\"\"\"
    # ---- LABWARE & INSTRUMENTS ----
    tip_racks = [protocol.load_labware(TIP_RACK_NAME, slot) for slot in TIP_SLOTS]
    pipette = protocol.load_instrument("p10_single", mount="left", tip_racks=tip_racks)

    unmod_plate = protocol.load_labware(BRICK_PLATE_NAME, UNMOD_SLOT, "unmod bricks")
    mod_plate = protocol.load_labware(BRICK_PLATE_NAME, MOD_SLOT, "mod bricks")
    mix_plate = protocol.load_labware(DEST_PLATE_NAME, MIX_SLOT, "brick mix destination")

    # Use explicit ThermocyclerModuleV1 in slot 7 (matches PD behavior)
    tc = protocol.load_module("thermocyclerModuleV1", "7")
    sa_plate = tc.load_labware(SA_PLATE_NAME, label="self-assembly plate")
    tc.open_lid()

    # ---- DESTINATION WELLS FOR BRICK MIX ----
    DEST_ROW_INDICES = [0, 2, 4, 6, 7]  # A, C, E, G, H

    def dest_well_for_block(plate, block_index: int):
        rows = plate.rows()
        num_cols = len(rows[0])  # assume 12
        wells_per_row = num_cols
        max_blocks = wells_per_row * len(DEST_ROW_INDICES)  # 60
        if block_index < 0 or block_index >= max_blocks:
            raise RuntimeError(
                f"Block {{block_index}} exceeds capacity of one brick-mix rack ({{max_blocks}} mixes)."
            )
        row_block = block_index // wells_per_row
        col_idx = block_index % wells_per_row
        row_idx = DEST_ROW_INDICES[row_block]
        return rows[row_idx][col_idx]

    # Track remaining volumes per brick (1..38)
    brick_unmod_vol = {{i: BRICK_STOCK for i in range(1, 39)}}
    brick_mod_vol = {{i: BRICK_STOCK for i in range(2, 38)}}  # mod bricks only 2..37

    blocks_per_plate = 60
    blocks_in_plate = 0
    blocks_in_tip_cycle = 0

    low_unmod = set()
    low_mod = set()

    def brick_source(brick_num: int, kind: str):
        # 1–12 → A1..A12; 13–24 → C1..C12; 25–36 → E1..E12; 37–38 → G1..G2
        if brick_num < 1 or brick_num > 38:
            raise ValueError(f"Brick index out of range: {{brick_num}}")
        plate = unmod_plate if kind == "unmod" else mod_plate
        rows = plate.rows()
        if 1 <= brick_num <= 12:
            row_idx = 0  # A
            col_idx = brick_num - 1
        elif 13 <= brick_num <= 24:
            row_idx = 2  # C
            col_idx = brick_num - 13
        elif 25 <= brick_num <= 36:
            row_idx = 4  # E
            col_idx = brick_num - 25
        else:
            row_idx = 6  # G
            col_idx = brick_num - 37
        return rows[row_idx][col_idx]

    def update_volume_and_flags(brick_num: int, kind: str):
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
        # optional pre-mix for brick stocks
        if MIX_TIMES and MIX_TIMES > 0:
            mv = MIX_VOL if MIX_VOL is not None else TRANSFER_VOL
            pipette.mix(MIX_TIMES, mv, src)
        if ASP_FLOW is not None:
            pipette.flow_rate.aspirate = ASP_FLOW
        depth = ASP_DEPTH if ASP_DEPTH is not None else 1.0
        pipette.aspirate(TRANSFER_VOL, src.bottom(depth))
        pipette.dispense(TRANSFER_VOL, dest.bottom(1.0))
        pipette.drop_tip()
        update_volume_and_flags(brick_num, kind)

    total_blocks = len(BLOCKS)

    # ---- STAGE 1: BUILD BRICK MIXES ----
    for block_idx, bits in enumerate(BLOCKS):
        if blocks_in_plate >= blocks_per_plate and (block_idx < total_blocks):
            protocol.pause(
                "Brick-mix rack full (60 mixes in rows A/C/E/G/H). "
                "Replace plate in slot " + MIX_SLOT + " with a NEW capped rack, then RESUME."
            )
            blocks_in_plate = 0

        dest = dest_well_for_block(mix_plate, blocks_in_plate)
        blocks_in_plate += 1
        blocks_in_tip_cycle += 1
        dest_name = getattr(dest, "well_name", getattr(dest, "display_name", "dest"))
        protocol.comment(
            f"Block {{block_idx + 1}}/{{total_blocks}} → brick-mix dest {{dest_name}}, bits={{bits}}"
        )

        # Brick 1 (always UNMOD)
        do_transfer(1, "unmod", dest)

        if len(bits) != BLOCK_SIZE:
            raise RuntimeError(
                f"Block {{block_idx}} has length {{len(bits)}}, expected {{BLOCK_SIZE}}."
            )

        # Bricks 2..37 from bits
        for bit_index, bit_char in enumerate(bits):
            brick_num = bit_index + 2  # 2..37
            kind = "mod" if bit_char == "1" else "unmod"
            if kind == "mod" and brick_num not in brick_mod_vol:
                raise RuntimeError(f"No mod brick defined for index {{brick_num}}.")
            do_transfer(brick_num, kind, dest)

        # Brick 38 (always UNMOD)
        do_transfer(38, "unmod", dest)

        # ---- Pause logic ----
        pause_reasons = []
        need_tip_reset = False

        if (low_unmod or low_mod) and (block_idx + 1 < total_blocks):
            lines_msg = [
                "Brick stock volumes low (below TRANSFER_VOL + 5 µL). Refill these bricks:"
            ]
            if low_unmod:
                lines_msg.append(
                    "  Unmod bricks: " + ", ".join(str(b) for b in sorted(low_unmod))
                )
            if low_mod:
                lines_msg.append(
                    "  Mod bricks: " + ", ".join(str(b) for b in sorted(low_mod))
                )
            pause_reasons.append("\\n".join(lines_msg))

        if blocks_in_tip_cycle >= BLOCKS_PER_TIP_CYCLE and (block_idx + 1 < total_blocks):
            pause_reasons.append(
                f"{{BLOCKS_PER_TIP_CYCLE}} blocks completed. "
                "Refill all tip racks, then RESUME."
            )
            need_tip_reset = True

        if pause_reasons:
            protocol.pause("\\n\\n".join(pause_reasons))
            # assume bricks + tips refilled
            for b in low_unmod:
                brick_unmod_vol[b] = BRICK_STOCK
            for b in low_mod:
                brick_mod_vol[b] = BRICK_STOCK
            low_unmod.clear()
            low_mod.clear()
            if need_tip_reset:
                pipette.reset_tipracks()
                blocks_in_tip_cycle = 0

    protocol.comment(f"Finished encoding {{total_blocks}} blocks into brick mixes.")

    # ---- STAGE 2: SELF-ASSEMBLY SETUP ----
    protocol.pause(
        "Brick mix preparation complete.\\n\\n"
        "For self-assembly, before RESUME:\\n"
        f"  - Remove UNMOD brick plate from slot {{UNMOD_SLOT}} and load TEMPLATE DNA in the same slot.\\n"
        f"  - Remove MOD brick plate from slot {{MOD_SLOT}} and load TAE/Mg2+ BUFFER in the same slot.\\n"
        "  - Refill all tip racks in slots: "
        + ", ".join(TIP_SLOTS)
        + ".\\n"
        "\\nAfter this, press RESUME to set up 1 µL BM + template + buffer to 20 µL in the thermocycler plate."
    )

    pipette.reset_tipracks()

    # Now: unmod_plate = TEMPLATE, mod_plate = BUFFER
    template_source = unmod_plate.wells()[0]  # A1
    buffer_source = mod_plate.wells()[0]      # A1

    # ---- STAGE 2: SETUP SA REACTIONS ----
    for block_idx in range(total_blocks):
        bm_source = dest_well_for_block(mix_plate, block_index=block_idx)
        sa_dest = sa_plate.wells()[block_idx]  # A1..H12 row-wise

        protocol.comment(
            f"Setting up self-assembly for block {{block_idx + 1}}/{{total_blocks}} "
            f"(BM {{bm_source.well_name}} → SA well {{sa_dest.well_name}})"
        )

        pipette.pick_up_tip()

        # Pre-mix brick mix well: 10× at 10 µL
        pipette.mix(10, 10.0, bm_source)

        # 1 µL brick mix into SA destination
        pipette.aspirate(BM_VOL, bm_source.bottom(1.0))
        pipette.dispense(BM_VOL, sa_dest.bottom(1.0))

        # Template DNA
        remaining_temp = TEMP_VOL
        while remaining_temp > 0:
            vol = min(remaining_temp, 10.0)
            pipette.aspirate(vol, template_source.bottom(1.0))
            pipette.dispense(vol, sa_dest.bottom(1.0))
            remaining_temp -= vol

        # Buffer
        remaining_buf = BUFFER_VOL
        while remaining_buf > 0:
            vol = min(remaining_buf, 10.0)
            pipette.aspirate(vol, buffer_source.bottom(1.0))
            pipette.dispense(vol, sa_dest.bottom(1.0))
            remaining_buf -= vol

        total_added = BM_VOL + TEMP_VOL + BUFFER_VOL
        mix_v = min(10.0, total_added)
        pipette.mix(3, mix_v, sa_dest)

        pipette.drop_tip()

    protocol.comment("All self-assembly reactions have been set up in thermocycler plate.")

    # ---- STAGE 3: THERMOCYCLER PROGRAM ----
    protocol.comment(
        "Starting thermocycler program: "
        "95°C 5min, 65°C 30min, 50°C 30min, 37°C 30min, 25°C 30min, then hold at 25°C."
    )

    tc.close_lid()
    tc.execute_profile(
        steps=[
            {{"temperature": 95, "hold_time_minutes": 5}},
            {{"temperature": 65, "hold_time_minutes": 30}},
            {{"temperature": 50, "hold_time_minutes": 30}},
            {{"temperature": 37, "hold_time_minutes": 30}},
            {{"temperature": 25, "hold_time_minutes": 30}},
        ],
        repetitions=1,
        block_max_volume=RXN_TOTAL_VOL,
    )
    tc.set_block_temperature(25)
    tc.open_lid()

    protocol.comment("Self-assembly complete. Reactions are held at 25°C in the thermocycler.")

"""

    output_py.write_text(code, encoding="utf-8")
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

    output_dir = Path(r"D:\OT-2 output")
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