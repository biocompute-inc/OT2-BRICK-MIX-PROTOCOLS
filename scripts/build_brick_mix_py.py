import json
import argparse
from pathlib import Path
import re
from datetime import datetime, timezone

# ------------------------------------------------------------
#                TEXT → BINARY → MODIFIED BRICKS
# ------------------------------------------------------------
def ascii_to_binary(text: str) -> str:
    return ''.join(format(ord(c), '07b') for c in text)


def word_to_modified_bricks(text: str, max_bits: int = 36):
    bits = ascii_to_binary(text)
    bits = bits[:max_bits]

    bricks = []
    idx = 2
    for b in bits:
        if b == "1":
            bricks.append(idx)
        idx += 1

    return sorted([b for b in bricks if 2 <= b <= 37])


# ------------------------------------------------------------
#                      JSON HELPERS
# ------------------------------------------------------------
def find_labware_ids(pd_data):
    unmod_id = mod_id = mix_id = None
    for lw_id, lw in pd_data["labware"].items():
        name = lw.get("displayName", "").lower()
        if name == "unmod bricks":
            unmod_id = lw_id
        elif name == "mod bricks":
            mod_id = lw_id
        elif name == "brick mix":
            mix_id = lw_id
    return unmod_id, mod_id, mix_id


def update_brick_stock_volumes(pd_data, brick_stock):
    if brick_stock is None:
        return

    ingreds = pd_data.get("ingredients", {})
    ids = {
        id_
        for id_, v in ingreds.items()
        if v.get("displayName", "").lower() in ("mod bricks", "unmod bricks")
    }

    count = 0
    for lw, wells in pd_data.get("ingredLocations", {}).items():
        for wellname, ing in wells.items():
            for id_, rec in ing.items():
                if id_ in ids and isinstance(rec, dict) and "volume" in rec:
                    rec["volume"] = brick_stock
                    count += 1
    print(f"Updated BRICK STOCK to {brick_stock} µL in {count} locations.")


def force_brick_mix_labware_to_match_bricks(pd_data):
    """
    Overwrite 'brick mix' labwareDefURI so it matches
    the UNMOD/MOD bricks plate model.
    """
    labware = pd_data["labware"]
    unmod_key = None
    mix_key = None

    for key, info in labware.items():
        name = info.get("displayName", "").lower()
        if name == "unmod bricks":
            unmod_key = key
        elif name == "brick mix":
            mix_key = key

    if not unmod_key or not mix_key:
        print("WARNING: Could not find unmod or brick mix labware.")
        return

    uri = labware[unmod_key].get("labwareDefURI")
    if not uri:
        print("WARNING: UNMOD bricks have no labwareDefURI.")
        return

    labware[mix_key]["labwareDefURI"] = uri
    print(f"Brick mix labwareDefURI updated → {uri}")


# ------------------------------------------------------------
#               PYTHON SOURCE PATCHING (MOD/UNMOD)
# ------------------------------------------------------------
def patch_python_sources(src: str, modified_bricks: set[int]) -> str:
    """
    Replace well_plate_1[...] with well_plate_2[...] for MOD bricks.
    First 38 occurrences correspond to bricks 1..38.
    """

    pattern = r'source=\[well_plate_1\["([A-H][0-9]{1,2})"\]\]'
    matches = list(re.finditer(pattern, src))

    if len(matches) < 38:
        print(f"WARNING: Only found {len(matches)} source steps (expected 38).")

    new_src = src
    for i, m in enumerate(matches[:38], start=1):
        well = m.group(1)
        old = f'source=[well_plate_1["{well}"]]'
        if i in modified_bricks and i not in (1, 38):
            new = f'source=[well_plate_2["{well}"]]'
        else:
            new = old
        new_src = new_src.replace(old, new, 1)

    print("Python source patching complete.")
    return new_src


# ------------------------------------------------------------
#       STRIP TRIAL2 LABWARE FROM CUSTOM_LABWARE BLOCK
# ------------------------------------------------------------
def strip_trial2_from_custom_labware(py_source: str) -> str:
    """
    Remove the 'custom_beta/trial2_96_wellplate_100ul/1' entry entirely
    from the CUSTOM_LABWARE JSON so the final .py contains no TRIAL 2.
    """
    marker = 'CUSTOM_LABWARE = json.loads("""'
    try:
        start = py_source.index(marker) + len(marker)
    except ValueError:
        print("No CUSTOM_LABWARE block found; skipping TRIAL2 cleanup.")
        return py_source

    end = py_source.index('""")', start)
    json_text = py_source[start:end]

    try:
        labware_defs = json.loads(json_text)
    except json.JSONDecodeError:
        print("WARNING: Failed to parse CUSTOM_LABWARE JSON; leaving unchanged.")
        return py_source

    if "custom_beta/trial2_96_wellplate_100ul/1" in labware_defs:
        del labware_defs["custom_beta/trial2_96_wellplate_100ul/1"]
        print("Removed TRIAL2 labware definition.")
    else:
        print("No TRIAL2 labware definition found.")

    new_json_text = json.dumps(labware_defs, separators=(",", ":"))
    new_source = py_source[:start] + new_json_text + py_source[end:]
    return new_source


# ------------------------------------------------------------
#             PATCH PYTHON METADATA AT TOP OF FILE
# ------------------------------------------------------------
def patch_python_metadata(py_src: str, word: str) -> str:
    """
    Update the metadata = { ... } block at top of file.
    Updates protocolName, created, lastModified timestamps.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    pattern = re.compile(
        r'metadata\s*=\s*\{[^}]*\}',
        re.DOTALL
    )

    def repl(match):
        return (
            "metadata = {\n"
            f'    "protocolName": "BRICK MIX - {word.upper()}",\n'
            f'    "created": "{now}",\n'
            f'    "lastModified": "{now}",\n'
            '    "protocolDesigner": "Python-Builder"\n'
            "}"
        )

    return pattern.sub(repl, py_src, count=1)


# ------------------------------------------------------------
#                    JSON PATCHING
# ------------------------------------------------------------
def extract_pd_json_from_py(path: Path):
    src = path.read_text()
    marker = 'DESIGNER_APPLICATION = """'
    start = src.index(marker) + len(marker)
    end = src.index('"""', start)
    return src, start, end, src[start:end]


def patch_pd_json(
    json_text,
    word,
    modified_bricks,
    transfer_vol,
    mix_times,
    mix_vol,
    asp_flow,
    asp_depth,
    brick_stock,
):
    # Fix residual PD references to old TRIAL2 URI
    json_text = json_text.replace(
        "custom_beta/trial2_96_wellplate_100ul/1",
        "custom_beta/opentronspcrrack_96_wellplate_100ul/1",
    )

    proto = json.loads(json_text)

    if "designerApplication" in proto:
        pd_data = proto["designerApplication"]["data"]
    else:
        pd_data = proto

    # Update protocol name inside JSON metadata
    proto.setdefault("metadata", {})
    proto["metadata"]["protocolName"] = f"BRICK MIX - {word.upper()}"
    if "designerApplication" in proto:
        proto["designerApplication"]["data"].setdefault("metadata", {})
        proto["designerApplication"]["data"]["metadata"]["protocolName"] = (
            f"BRICK MIX - {word.upper()}"
        )
    # Patch PD's internal timestamps so PD UI shows correct values
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if "designerApplication" in proto:
       md = proto["designerApplication"]["data"].setdefault("metadata", {})
       md["created"] = now
       md["lastUpdated"] = now
       md["lastModified"] = now

    update_brick_stock_volumes(pd_data, brick_stock)
    force_brick_mix_labware_to_match_bricks(pd_data)

    unmod_id, mod_id, mix_id = find_labware_ids(pd_data)

    saved = pd_data["savedStepForms"]
    ordered = pd_data["orderedStepIds"]
    step_index = 0

    for sid in ordered:
        step = saved.get(sid)
        if not step or step.get("stepType") != "moveLiquid":
            continue

        step_index += 1
        if step_index > 38:
            break

        if step_index in (1, 38):
            step["aspirate_labware"] = unmod_id
        elif step_index in modified_bricks:
            step["aspirate_labware"] = mod_id
        else:
            step["aspirate_labware"] = unmod_id

        if transfer_vol is not None:
            step["volume"] = str(transfer_vol)

        if mix_times is not None:
            if mix_times > 0:
                step["aspirate_mix_checkbox"] = True
                step["aspirate_mix_times"] = str(mix_times)
                step["aspirate_mix_volume"] = str(mix_vol or transfer_vol)
            else:
                step["aspirate_mix_checkbox"] = False
                step["aspirate_mix_times"] = ""

        if asp_flow is not None:
            step["aspirate_flowRate"] = str(asp_flow)

        if asp_depth is not None:
            step["aspirate_mmFromBottom"] = str(asp_depth)

    return json.dumps(proto, separators=(",", ":"))


# ------------------------------------------------------------
#               BUILD FINAL PROTOCOL (.py)
# ------------------------------------------------------------

def build_new_py(
    template_py,
    output_py,
    word,
    transfer_vol,
    mix_times,
    mix_vol,
    asp_flow,
    asp_depth,
    brick_stock,
):
    path = Path(template_py)
    src, start, end, json_text = extract_pd_json_from_py(path)

    modified = set(word_to_modified_bricks(word))
    print(f"Modified bricks (2–37) for '{word}': {sorted(modified)}")

    new_json = patch_pd_json(
        json_text,
        word,
        modified,
        transfer_vol,
        mix_times,
        mix_vol,
        asp_flow,
        asp_depth,
        brick_stock,
    )

    new_src = src[:start] + new_json + src[end:]
    new_src = patch_python_sources(new_src, modified)
    new_src = strip_trial2_from_custom_labware(new_src)
    new_src = patch_python_metadata(new_src, word)

    Path(output_py).write_text(new_src)
    print(f"Protocol written → {output_py}")


# ------------------------------------------------------------
#                          CLI
# ------------------------------------------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--word", "-w", required=True)
    p.add_argument("--template", "-t", default="BRICK_MIX_38_TIMES.py")
    p.add_argument("--output", "-o", default=None)

    p.add_argument("--transfer-vol", type=float, default=None)
    p.add_argument("--pre-mix", type=int, default=None)
    p.add_argument("--mix-vol", type=float, default=None)
    p.add_argument("--asp-flow", type=float, default=None)
    p.add_argument("--asp-depth", type=float, default=None)
    p.add_argument("--brick-stock", type=float, default=None)

    args = p.parse_args()

    out = args.output or f"BRICK MIX PROTOCOLS/BRICK_MIX_{args.word.upper()}.py"

    build_new_py(
        template_py=args.template,
        output_py=out,
        word=args.word,
        transfer_vol=args.transfer_vol,
        mix_times=args.pre_mix,
        mix_vol=args.mix_vol,
        asp_flow=args.asp_flow,
        asp_depth=args.asp_depth,
        brick_stock=args.brick_stock,
    )


if __name__ == "__main__":
    main()
