from pathlib import Path


def test_phase9_packaging_files_reference_gui_and_resources() -> None:
    root = Path(__file__).resolve().parents[2]
    spec = (root / "MYCMD_GUI.spec").read_text(encoding="utf-8")
    entry = (root / "scripts" / "mycmd_gui.py").read_text(encoding="utf-8")
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "mycmd_gui.py" in spec
    assert "gui/resources" in spec
    assert "console=False" in spec
    assert "from mycmd.gui.app import run" in entry
    assert "Build packaged GUI executable" in workflow
    assert "packaged-gui-" in workflow
