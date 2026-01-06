OT-2 Automation
# OT-2 Brick Mix Protocol Generator

## Repo Structure

OT2-BRICK-MIX-PROTOCOLS/
│
├── scripts #Protocol Builder python scripts
|  └──winUser  
|     └── brickMixAndSAOT2.py # Brick Mix and SA Protocol Builder for people using Windows
|  └── ASYM_PCR.py # Asym PCR Protocol Builder for people using Linux/WSL
|  └── BM_SA_builder.py # Brick Mix and SA Protocol Builder for people using Linux/WSL
|  └── BRICK_MIX_38_TIMES.py # Brick Mix protocol Builder
|  └── build_brick_mix_py.py
|  └── SA_builder_07.py 
|  └── watchdog.py
├── tests # Unit test written for winUsers
|     └── test_blocks.py
|     └── test_cli.py
|     └── test_encoding.py
└── README.md
└── flow_brickmix_sa.png
└── .gitignore


## How it works

1. brickMixAndSAOY2.py, BM_SA_builder.py - The program is designed to convert input text or files into a binary representation, which is subsequently segmented into 36-bit blocks. Each block is then encoded using the Brick Mix protocol. Based on these encoded blocks, a self-assembly reaction is prepared and executed using a programmed thermocycler protocol.
      ![Brick Mix and Self-Assembly Flow](flow%20Brickmix%20and%20SA.png)
2. ASYM_PCR.py
3. watchdog.py 
---

## Requirements

- **Python** (tested on Python 3.14)
- Opentrons API **2.15** (for generated protocols)
- `pytest` (optional, for tests)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/biocompute-inc/OT2-BRICK-MIX-PROTOCOLS.git
cd OT2-BRICK-MIX-PROTOCOLS

```
--- 

## Usage

```bash
   python3 <script you want to run >.py --word <Literal/word > --transfer-vol <ul> --brick-stock <ul> --temp-vol <ul>
```
   ## Example

   ```bash
      python3 brickMixAndSAOT2.py --word Epic --transfer-vol 2 --brick-stock 20 --temp-vol 10
   ```
      ## Output 
      ./output/BRICK_MIX_Epic.py

   ## Custom output filename
   ```bash
      python3 brickMixAndSAOT2.py --word Epic --output demo  --transfer-vol 2 --brick-stock 20 --temp-vol 10
   ```
      ## Output
      ./output/demo.py

   ## Custom output directory
   ```bash
      python3 brickMixAndSAOT2.py --word Epic --outdir results  --transfer-vol 2 --brick-stock 20 --temp-vol 10
   ```
      ## Output
      ./results/BRICK_MIX_Epic.py

Optional args:
| Argument         | Description                                        |
| ---------------- | -------------------------------------------------- |
| `--word`         | Literal word/string to encode                      |
| `--file`         | Path to input file to encode                       |
| `--output`       | Output protocol filename (optional)                |
| `--outdir`       | Output directory (default: `./output`)             |
| `--transfer-vol` | Transfer volume per brick (µL)                     |
| `--brick-stock`  | Initial stock volume per brick well (µL)           |
| `--mix-times`    | Pre-aspiration mixing cycles                       |
| `--mix-vol`      | Mixing volume (µL)                                 |
| `--asp-flow`     | Aspirate flow rate (µL/s)                          |
| `--asp-depth`    | Aspirate depth from bottom (mm)                    |
| `--ascii7`       | Use 7-bit ASCII encoding                           |
| `--temp-vol`     | Template DNA volume per SA reaction (**required**) |

## Running Tests
- if you wish to run test, You have to install "pytest"
```bash
   python -m pip install pytest
```
- once you have installed pytest 
```bash
   python -m pytest 
   #For Verbose output use the below one
   python -m pytest -v tests
```

## Notes
- Cross-platform (Windows / macOS / Linux)
- No hard-coded local paths
- Output directories are created automatically
- Designed for reproducible, testable OT-2 automation

