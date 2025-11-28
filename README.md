OT-2 Automation
# OT-2 Brick Mix Protocol Generator



##Repo Structure

OT-2_protocols/
│
├── build_brick_mix_py.py        # Protocol builder
├── BRICK_MIX_38_TIMES.py        # Template protocol
├── BRICK MIX PROTOCOLS/         # Output folder
│   └── BRICK_MIX_<WORD>.py
└── README.md

In the OT-2_protocols folder, create a subfolder called "BRICK MIX PRTOCOLS" to store all the output files

## How it works

1. Edit BRICK_MIX_38_TIMES.py only when template needs changes.
2. Run build_brick_mix_py.py to generate a custom protocol for any word.
3. The builder:
   - Converts ASCII text → binary → modified brick positions (2–37)
   - Patches PD JSON inside the template
   - Fixes labware models
   - Applies custom volumes & mixing settings
   - Updates timestamps + metadata
   - Writes final protocol inside `BRICK MIX PROTOCOLS/`

##How to use this?

- Move to the folder:

cd ot2-brick-mix-protocols

- Run the script:

python3 build_brick_mix_py.py --word HELLO --brick-stock 20 --transfer-vol 2

Optional args:
- --word                       ---> Word to encode (required)
- --brick-stock <µL>           ---> Volume of each brick in stock plate
- --transfer-vol <µL>          ---> Volume dispensed for each brick
- --pre-mix <times>            ---> Number of pre-aspiration mixing cycles
- --mix-vol <µL>               ---> Volume used for mixing
- --asp-flow <µL/s>            ---> Aspirate flow rate
- --asp-depth <mm>             ---> Aspirate depth (mm from bottom)



## Output

Generated protocols appear in:

- BRICK MIX PROTOCOLS/

These `.py` files can be directly imported to Opentrons App.

---

# Files

- `BRICK_MIX_38_TIMES.py` — template protocol with embedded PD JSON
- `build_brick_mix_py.py` — generator script
