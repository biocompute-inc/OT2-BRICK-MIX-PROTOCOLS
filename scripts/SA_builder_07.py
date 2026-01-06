import argparse
from pathlib import Path


# ---------- FILE → BITS → 36-BIT BLOCKS ----------


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


def bitstring_to_blocks(bits: str, block_size: int = 36) -> list[str]:
    """
    Split a long bitstring into fixed-size blocks (36 bits).
    Last block is right-padded with '0' if needed.
    """
    if not bits:
        raise ValueError("No bits to encode (empty file).")
    blocks = [bits[i:i + block_size] for i in range(0, len(bits), block_size)]
    if len(blocks[-1]) < block_size:
        blocks[-1] = blocks[-1].ljust(block_size, "0")
    return blocks


# ---------- SA PROTOCOL GENERATION ONLY ----------


def build_sa_protocol(
    data_path: Path,
    blocks: list[str],
    output_py: Path,
    temp_vol: float,
) -> None:
    """
    Build a self-assembly-only OT-2 protocol.

    Assumptions:
      - Brick mixes are already prepared in slot 2 in a PCR rack
        (opentronspcrrack_96_wellplate_100ul) in sparse rows A,C,E,G,H:
          A1–A12, C1–C12, E1–E12, G1–G12, H1–H12 (max 60 blocks).
      - We only set up SA reactions:
          1 µL BM + TEMP_VOL template + BUFFER_VOL buffer = 20 µL total.
      - Template DNA in slot 5, A1 (same PCR-rack model).
      - Buffer (TAE/Mg2+) in slot 4, A1 (same rack).
      - ThermocyclerModuleV1 in slot 7, with a Nest 96-well PCR plate.
    """
    num_blocks = len(blocks)
    if num_blocks == 0:
        raise ValueError("No blocks to encode.")

    if num_blocks > 60:
        raise ValueError(
            f"SA builder currently assumes at most 60 blocks (one brick-mix rack), "
            f"but you have {num_blocks}. Split your file or use multiple runs."
        )

    RXN_TOTAL_VOL = 20.0
    BM_VOL = 1.0
    if temp_vol <= 0 or temp_vol >= RXN_TOTAL_VOL - BM_VOL:
        raise ValueError(
            f"temp-vol must be > 0 and < {RXN_TOTAL_VOL - BM_VOL}, got {temp_vol}"
        )
    buffer_vol = RXN_TOTAL_VOL - BM_VOL - temp_vol

    file_name = data_path.name

    code = f"""from opentrons import protocol_api

metadata = {{
    "protocolName": "SELF ASSEMBLY - MULTIBLOCK ({file_name})",
    "author": "Franci / auto-generated",
    "description": "Self-assembly for file '{file_name}' using pre-made brick mixes.",
}}

requirements = {{
    "robotType": "OT-2",
    "apiLevel": "2.15",
}}

BLOCK_SIZE = 36  # bits per block
BM_VOL = 1.0  # µL brick mix per SA reaction
TEMP_VOL = {temp_vol}  # µL template DNA
BUFFER_VOL = {buffer_vol}  # µL buffer (TAE/Mg2+)
RXN_TOTAL_VOL = {RXN_TOTAL_VOL}  # total reaction volume

# We only need to know how many blocks (= how many brick-mix wells).
NUM_BLOCKS = {num_blocks}

# Deck layout for SA ONLY:
#   slot 2: brick-mix destination plate from previous protocol
#   slot 5: TEMPLATE DNA (PCR rack, we use A1)
#   slot 4: BUFFER (PCR rack, we use A1)
#   slot 7: ThermocyclerModuleV1 with Nest 96-well PCR plate
#   tip racks: slots 1,3,6,9 (safe with thermocycler footprint)
TIP_SLOTS = ["1", "3", "6", "9"]
MIX_SLOT = "2"
TEMPLATE_SLOT = "5"
BUFFER_SLOT = "4"

TIP_RACK_NAME = "geb_96_tiprack_10ul"
BRICK_PLATE_NAME = "opentronspcrrack_96_wellplate_100ul"
DEST_PLATE_NAME = BRICK_PLATE_NAME
SA_PLATE_NAME = "nest_96_wellplate_100ul_pcr_full_skirt"


def run(protocol: protocol_api.ProtocolContext) -> None:
    \"\"\"Self-assembly only: assumes brick mixes already exist in slot 2.\"\"\"

    # ---- LABWARE & INSTRUMENTS ----
    tip_racks = [protocol.load_labware(TIP_RACK_NAME, slot) for slot in TIP_SLOTS]
    pipette = protocol.load_instrument("p10_single", mount="left", tip_racks=tip_racks)

    mix_plate = protocol.load_labware(
        DEST_PLATE_NAME, MIX_SLOT, "brick mix destination (pre-made)"
    )

    template_plate = protocol.load_labware(
        BRICK_PLATE_NAME, TEMPLATE_SLOT, "template DNA"
    )
    buffer_plate = protocol.load_labware(
        BRICK_PLATE_NAME, BUFFER_SLOT, "TAE/Mg2+ buffer"
    )

    tc = protocol.load_module("thermocyclerModuleV1", "7")
    sa_plate = tc.load_labware(SA_PLATE_NAME, label="self-assembly plate")
    tc.open_lid()

    # Template and buffer sources (A1 in each PCR rack)
    template_source = template_plate.wells()[0]  # A1
    buffer_source = buffer_plate.wells()[0]      # A1

    # ---- BRICK-MIX WELL MAPPING (MUST MATCH BRICK MIX PROTOCOL) ----
    # Destination rows used for brick mixes: A, C, E, G, H → indices [0, 2, 4, 6, 7]
    DEST_ROW_INDICES = [0, 2, 4, 6, 7]

    def bm_well_for_block(plate, block_index: int):
        \"\"\"Map block index 0..59 to A1–A12, C1–C12, E1–E12, G1–G12, H1–H12.\"\"\"
        rows = plate.rows()
        num_cols = len(rows[0])  # assume 12
        wells_per_row = num_cols
        max_blocks = wells_per_row * len(DEST_ROW_INDICES)  # 60

        if block_index < 0 or block_index >= max_blocks:
            raise RuntimeError(
                f"Block index {{block_index}} exceeds capacity of one brick-mix rack ({{max_blocks}} mixes)."
            )

        row_block = block_index // wells_per_row   # 0..4 → A,C,E,G,H
        col_idx = block_index % wells_per_row      # 0..11
        row_idx = DEST_ROW_INDICES[row_block]
        return rows[row_idx][col_idx]

    protocol.comment(
        f"Starting self-assembly for {{NUM_BLOCKS}} brick mixes from file '{file_name}'."
    )

    # ---- SETUP SA REACTIONS ----
    for block_idx in range(NUM_BLOCKS):
        bm_source = bm_well_for_block(mix_plate, block_index=block_idx)
        sa_dest = sa_plate.wells()[block_idx]  # A1..H12 row-wise (<=60 so it's safe)

        protocol.comment(
            f"SA block {{block_idx + 1}}/{{NUM_BLOCKS}}: "
            f"BM {{bm_source.well_name}} → SA well {{sa_dest.well_name}}"
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

    protocol.comment(
        "All self-assembly reactions have been set up in the thermocycler plate."
    )

    # ---- THERMOCYCLER PROGRAM ----
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

    protocol.comment(
        "Self-assembly complete. Reactions are held at 25°C in the thermocycler."
    )
"""

    output_py.write_text(code)
    print(f"Built SA-only protocol: {output_py}")
    print(f"  File: {file_name}")
    print(f"  Blocks: {num_blocks}")
    print(
        f"  SA: 1 µL BM + {temp_vol} µL template + {buffer_vol} µL buffer = {RXN_TOTAL_VOL} µL"
    )


# ---------- CLI ----------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build a self-assembly-only OT-2 protocol that uses pre-made brick mixes."
        )
    )
    parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="Path to the SAME data file used for brick-mix generation.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output .py protocol filename (default: SA_<FILENAME>.py).",
    )
    parser.add_argument(
        "--ascii7",
        action="store_true",
        help=(
            "Interpret the file as text and encode each character as 7-bit ASCII. "
            "Must match the choice you used for brick-mix generation."
        ),
    )
    parser.add_argument(
        "--temp-vol",
        type=float,
        required=True,
        help="Template DNA volume per reaction in µL (1 µL BM + temp + buffer = 20 µL total).",
    )

    args = parser.parse_args()

    data_path = Path(args.file).resolve()
    if not data_path.is_file():
        raise SystemExit(f"Input file not found: {data_path}")

    bits = file_to_bitstring(data_path, ascii7=args.ascii7)
    blocks = bitstring_to_blocks(bits, block_size=36)

    if args.output:
        filename = args.output
    else:
        stem = data_path.name.replace(" ", "_")
        filename = f"SA_{stem}.py"

    output_dir = Path(
        r"/mnt/c/Users/franc/Desktop/OT-2_protocols/BRICK MIX PROTOCOLS"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_py = (output_dir / filename).resolve()

    build_sa_protocol(
        data_path=data_path,
        blocks=blocks,
        output_py=output_py,
        temp_vol=args.temp_vol,
    )


if __name__ == "__main__":
    main()
