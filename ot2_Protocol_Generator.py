#!/usr/bin/env python3
"""
OT2-BRICK-MIX-PROTOCOLS: interactive menu runner

- Lets user choose which generator script/protocol to run
- Prompts for key args
- Executes the selected script via subprocess (so we don't have to refactor existing scripts)
"""

from __future__ import annotations

import os
import platform
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
WINUSER_DIR = SCRIPTS_DIR / "winUser"


@dataclass(frozen=True)
class MenuItem:
    key: str
    label: str
    script_path: Path
    notes: str = ""


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


def python_executable() -> str:
    # Use current interpreter to run scripts (more reliable than assuming python3/python).
    return sys.executable or "python"


def safe_int(prompt: str, default: Optional[int] = None) -> Optional[int]:
    while True:
        raw = input(f"{prompt}{' ['+str(default)+']' if default is not None else ''}: ").strip()
        if not raw and default is not None:
            return default
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            print("  Please enter an integer (or leave blank).")


def safe_float(prompt: str, default: Optional[float] = None) -> Optional[float]:
    while True:
        raw = input(f"{prompt}{' ['+str(default)+']' if default is not None else ''}: ").strip()
        if not raw and default is not None:
            return default
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            print("  Please enter a number (or leave blank).")


def safe_str(prompt: str, default: Optional[str] = None) -> Optional[str]:
    raw = input(f"{prompt}{' ['+default+']' if default else ''}: ").strip()
    if not raw:
        return default
    return raw


def safe_path(prompt: str, must_exist: bool = True) -> Optional[Path]:
    raw = input(f"{prompt} (leave blank to skip): ").strip()
    if not raw:
        return None
    p = Path(raw).expanduser()
    if must_exist and not p.exists():
        print(f"  Path not found: {p}")
        return None
    return p


def yes_no(prompt: str, default: bool = False) -> bool:
    d = "Y/n" if default else "y/N"
    raw = input(f"{prompt} [{d}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes", "true", "1")


def discover_menu_items() -> List[MenuItem]:
    """
    Curated menu + fallback discovery.
    If files move, you only need to update these paths.
    """
    items: List[MenuItem] = []
    print("Welcome to the OT-2 Protocol Generator Menu!")
    # Windows-friendly brickmix+SA entrypoint (per repo README note)
    win_bm_sa = WINUSER_DIR / "brickMixAndSAOT2.py"
    if win_bm_sa.exists():
        items.append(MenuItem(
            key="1",
            label="Brick Mix + Self-Assembly (Windows script: brickMixAndSAOT2.py)",
            script_path=win_bm_sa,
            notes="Recommended on Windows."
        ))

    # Linux/WSL-friendly brickmix+SA entrypoint
    linux_bm_sa = SCRIPTS_DIR / "BM_SA_builder.py"
    if linux_bm_sa.exists():
        items.append(MenuItem(
            key="2",
            label="Brick Mix + Self-Assembly (Linux/WSL script: BM_SA_builder.py)",
            script_path=linux_bm_sa,
            notes="Recommended on Linux/WSL."
        ))

    # Other generators (if present)
    for key, rel, label in [
        ("3", "sa_builder_07.py", "Self-Assembly only (sa_builder_07.py)"),
        ("4", "BRICK_MIX_38_TIMES.py", "Brick Mix only (BRICK_MIX_38_TIMES.py)"),
        ("5", "ASYM_PCR.py", "Asymmetric PCR builder (ASYM_PCR.py)"),
        ("6", "build_brick_mix_py.py", "Legacy Brick Mix generator (build_brick_mix_py.py)"),
        ("7", "watchdog.py", "Utility / monitoring (watchdog.py)"),
        ("8", "new_builder_07.py", "This is Brick Mix protocol")
    ]:
        p = SCRIPTS_DIR / rel
        if p.exists():
            items.append(MenuItem(key=key, label=label, script_path=p))

    # Fallback: discover any other .py scripts under scripts/ (not __init__.py)
    discovered = []
    if SCRIPTS_DIR.exists():
        for p in sorted(SCRIPTS_DIR.rglob("*.py")):
            if p.name == "__init__.py":
                continue
            if any(p == it.script_path for it in items):
                continue
            discovered.append(p)

    # Add discovered as "X1, X2..." at end
    base = 10
    for i, p in enumerate(discovered, start=1):
        items.append(MenuItem(
            key=f"{base+i}",
            label=f"Other: {p.relative_to(REPO_ROOT).as_posix()}",
            script_path=p,
            notes="Auto-discovered"
        ))

    return items


def build_common_args() -> List[str]:
    """
    Prompts for a common set of args used by the brickmix/SA scripts in this repo.
    (Scripts that don't recognize some args will error; users can use 'Custom args' option if needed.)
    """
    args: List[str] = []

    # Choose word OR file
     # --- Explicit input mode selection ---
    print("\nInput type:")
    print("  [1] Text / literal (--word)")
    print("  [2] File path (--file)")
    mode = input("Choose 1 or 2 [1]: ").strip() or "1"

    if mode == "1":
        word = safe_str("Enter literal text to encode (--word)", default=None)
        if not word:
            print("  You must enter a non-empty --word.")
            return []
        args += ["--word", word]

    elif mode == "2":
        file_path = safe_path("Enter path to input file (--file)", must_exist=True)
        if not file_path:
            print("  You must provide a valid file path for --file.")
            return []
        args += ["--file", str(file_path)]

    else:
        print("  Invalid selection. Choose 1 or 2.")
        return []

    # Output controls
    outdir = safe_str("Output directory (--outdir)", default="output")
    if outdir:
        args += ["--outdir", outdir]

    output_name = safe_str("Output filename without extension (--output) [optional]", default=None)
    if output_name:
        args += ["--output", output_name]

    # Volumes / handling
    transfer_vol = safe_float("Transfer volume per brick µL (--transfer-vol)", default=2.0)
    if transfer_vol is not None:
        args += ["--transfer-vol", str(transfer_vol)]

    brick_stock = safe_float("Initial stock volume per brick well µL (--brick-stock)", default=20.0)
    if brick_stock is not None:
        args += ["--brick-stock", str(brick_stock)]

    # Mixing
    mix_times = safe_int("Pre-aspiration mixing cycles (--mix-times) [optional]", default=None)
    if mix_times is not None:
        args += ["--mix-times", str(mix_times)]

    mix_vol = safe_float("Mixing volume µL (--mix-vol) [optional]", default=None)
    if mix_vol is not None:
        args += ["--mix-vol", str(mix_vol)]

    asp_flow = safe_float("Aspirate flow rate µL/s (--asp-flow) [optional]", default=None)
    if asp_flow is not None:
        args += ["--asp-flow", str(asp_flow)]

    asp_depth = safe_float("Aspirate depth mm from bottom (--asp-depth) [optional]", default=None)
    if asp_depth is not None:
        args += ["--asp-depth", str(asp_depth)]

    # Encoding option
    if yes_no("Use 7-bit ASCII encoding? (--ascii7)", default=False):
        args += ["--ascii7"]

    # SA-specific: template volume
    temp_vol = safe_float("Template DNA volume per SA reaction µL (--temp-vol) [required for BM+SA]", default=None)
    if temp_vol is not None:
        args += ["--temp-vol", str(temp_vol)]
    else:
        # Some scripts require it; user can still proceed and script will complain if needed.
        pass

    return args


def build_custom_args() -> List[str]:
    raw = input("Enter any additional args exactly as you'd type them (or blank): ").strip()
    if not raw:
        return []
    return shlex.split(raw)


def run_script(script_path: Path, args: List[str]) -> int:
    cmd = [python_executable(), str(script_path)] + args
    print("\nRunning:\n  " + " ".join(shlex.quote(c) for c in cmd) + "\n")
    try:
        completed = subprocess.run(cmd, cwd=str(REPO_ROOT))
        return completed.returncode
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1


def main() -> int:
    if not SCRIPTS_DIR.exists():
        print(f"Error: scripts/ folder not found at {SCRIPTS_DIR}")
        return 2

    items = discover_menu_items()
    if not items:
        print("No runnable scripts found under scripts/.")
        return 2

    print("\n=== OT-2 Protocol Generator Menu ===")
    print(f"Repo: {REPO_ROOT}")
    print(f"Detected OS: {platform.system()} ({'Windows' if is_windows() else 'non-Windows'})\n")

    for it in items:
        note = f" — {it.notes}" if it.notes else ""
        print(f"[{it.key}] {it.label}{note}")
    print("[C] Run with custom args (you will choose a script, then type args)")
    print("[Q] Quit\n")

    choice = input("Select an option: ").strip()

    if not choice:
        return 0
    if choice.lower() == "q":
        return 0

    # Custom path: pick script then free-form args
    if choice.lower() == "c":
        print("\nPick a script to run:")
        for idx, it in enumerate(items, start=1):
            print(f"[{idx}] {it.script_path.relative_to(REPO_ROOT).as_posix()}")
        raw_idx = safe_int("Script number", default=1)
        if raw_idx is None or raw_idx < 1 or raw_idx > len(items):
            print("Invalid selection.")
            return 2
        script = items[raw_idx - 1].script_path
        args = build_custom_args()
        return run_script(script, args)

    # Normal path: menu item + guided prompts + optional extra args
    selected = next((it for it in items if it.key == choice), None)
    if not selected:
        print("Invalid selection.")
        return 2

    print(f"\nSelected: {selected.label}")
    # For non-brickmix scripts, guided prompts may be wrong; user can append extra args.
    args = build_common_args()
    if not args:
        return 2

    if yes_no("Add any extra args?", default=False):
        args += build_custom_args()

    return run_script(selected.script_path, args)


if __name__ == "__main__":
    raise SystemExit(main())
