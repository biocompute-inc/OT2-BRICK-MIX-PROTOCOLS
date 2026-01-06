from pathlib import Path
import scripts.winUser.brickMixAndSAOT2

def test_cli_word_generates_file(tmp_path, monkeypatch):
    outdir = tmp_path / "out"
    outdir.mkdir()

    # Fake command line:
    # python brickmixAndSAOT2.py --word Epic --output demo --temp-vol 10 --outdir <tmp>
    monkeypatch.setattr(
        "sys.argv",
        [
            "brickmixAndSAOT2.py",
            "--word", "Epic",
            "--output", "demo.py",
            "--temp-vol", "10",
            "--outdir", str(outdir),
            "--brick-stock", "20",
            "--transfer-vol", "20",
        ],
    )

    scripts.winUser.brickMixAndSAOT2.main()

    out_file = outdir / "demo.py"
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    text = out_file.read_text(encoding="utf-8")
    assert "from opentrons import protocol_api" in text
    assert "BLOCKS = " in text
