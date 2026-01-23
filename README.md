OT-2 Automation
# OT-2 Brick Mix Protocol Generator

## Repo Structure
```md
OT2-BRICK-MIX-PROTOCOLS/
│
├── scripts/ # Protocol builder scripts
│ ├── winUser
│     ├── brickMixAndSAOT2.py # Brick Mix + SA protocol generator (Windows/Linux)
│ ├── ASYM_PCR.py # Asymmetric PCR protocol builder
│ ├── BM_SA_builder.py # Legacy Brick Mix + SA builder
│ ├── BRICK_MIX_38_TIMES.py # Brick Mix-only protocol builder
│ ├── build_brick_mix_py.py # Legacy generator
│ ├── sa_builder_07.py # SA-only protocol builder
│ ├── watchdog.py # Utility / monitoring script
│ └── init.py
│
├── tests/ # Unit tests
│ ├── test_blocks.py
│ ├── test_cli.py
│ └── test_encoding.py
│
├── flow_brickmix_sa.png # Workflow diagram
├── README.md
└── .gitignore
```

## How it works

1. brickMixAndSAOY2.py, BM_SA_builder.py - The program is designed to convert input text or files into a binary representation, which is subsequently segmented into 36-bit blocks. Each block is then encoded using the Brick Mix protocol. Based on these encoded blocks, a self-assembly reaction is prepared and executed using a programmed thermocycler protocol.
      ![Brick Mix and Self-Assembly Flow](flow_brickmix_sa.png)
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
# if you're windows user
cd  OT2-BRICK-MIX-PROTOCOLS/scripts/winUser
# if you're linux/WSL user
cd OT2-BRICK-MIX-PROTOCOLS/scripts
```
--- 
## Note

- if you're a windows user, brickMixAndSAOT2.py is the script you should run
- if you're a linux/WSL user, BM_SA_builder.py is the script you should run
- if you're using python3 command and your system throws an error maybe use python, but please to have a python on your pc don't expect it to run without python
  
---
## Usage

```bash
python3 <script you want to run >.py --word <Literal/word > --transfer-vol <ul> --brick-stock <ul> --temp-vol <ul>
```
## Example

```bash
python3 brickMixAndSAOT2.py --word Epic --transfer-vol 2 --brick-stock 20 --temp-vol 10
```
```bash
python3 BM_SA_builder.py --word Epic --transfer-vol 2 --brick-stock 20 --temp-vol 10
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

