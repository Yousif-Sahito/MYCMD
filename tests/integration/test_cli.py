import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
BOXES = {
    chr(codepoint)
    for codepoint in (
        0x2500,
        0x2502,
        0x250C,
        0x2510,
        0x2514,
        0x2518,
        0x251C,
        0x2524,
        0x252C,
        0x2534,
        0x253C,
        0x2550,
        0x2551,
        0x2554,
        0x2557,
        0x255A,
        0x255D,
        0x2560,
        0x2563,
        0x2566,
        0x2569,
        0x256C,
        0x2574,
        0x2575,
        0x2576,
        0x2577,
    )
}


def run_cli(
    data_dir: Path, *args: str, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["MYCMD_DATA_DIR"] = str(data_dir)
    env["NO_COLOR"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "mycmd", *args],
        cwd=ROOT,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(
    "args",
    [
        ("--help",),
        ("projects", "--help"),
        ("skills", "--help"),
        ("education", "--help"),
        ("certificates", "--help"),
        ("milestones", "--help"),
    ],
)
def test_help_is_plain_and_borderless(tmp_path, args):
    result = run_cli(tmp_path, *args)
    assert result.returncode == 0
    assert not (BOXES & set(result.stdout))
    assert "\x1b[" not in result.stdout
    assert "Options:" in result.stdout
    assert "Commands:" in result.stdout if args == ("--help",) else True


def test_command_groups_registered(tmp_path):
    result = run_cli(tmp_path, "--help")
    assert result.returncode == 0
    for name in (
        "status",
        "search",
        "projects",
        "skills",
        "education",
        "certificates",
        "milestones",
    ):
        assert name in result.stdout


def test_real_crud_validation_and_process_persistence(tmp_path):
    added = run_cli(tmp_path, "projects", "add", input_text="demo\nDemo project\nactive\n")
    assert added.returncode == 0, added.stderr
    listed = run_cli(tmp_path, "projects", "list")
    assert listed.returncode == 0 and "demo" in listed.stdout
    record_id = listed.stdout.splitlines()[1].split()[0]
    shown = run_cli(tmp_path, "projects", "show", record_id)
    assert shown.returncode == 0 and "Demo project" in shown.stdout
    invalid = run_cli(tmp_path, "projects", "show", "not-a-uuid")
    assert invalid.returncode != 0 and invalid.stderr.startswith("Error:")
    invalid_record = run_cli(tmp_path, "projects", "edit", record_id, "status", "bogus")
    assert invalid_record.returncode != 0 and "Error:" in invalid_record.stderr


def test_redirect_output_is_plain_text(tmp_path):
    output_file = tmp_path / "help.txt"
    result = run_cli(tmp_path, "--help")
    output_file.write_text(result.stdout, encoding="utf-8")
    text = output_file.read_text(encoding="utf-8")
    assert text.startswith("Usage:")
    assert not (BOXES & set(text))
    assert "\x1b" not in text


def test_invalid_data_directory_has_plain_error(tmp_path):
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("occupied", encoding="utf-8")
    result = run_cli(file_path, "status")
    assert result.returncode != 0
    assert result.stderr.startswith("Error:")
    assert "Traceback" not in result.stderr
    assert "\x1b[" not in result.stderr


def test_backup_create_verify_and_restore_workflows(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    added = run_cli(root, "projects", "add", input_text="backup-project\nBackup project\nactive\n")
    assert added.returncode == 0, added.stderr

    backup = tmp_path / "snapshot.sqlite3"
    created = run_cli(root, "backup", "create", "--output", str(backup))
    assert created.returncode == 0, created.stderr
    verified = run_cli(root, "backup", "verify", str(backup))
    assert verified.returncode == 0, verified.stderr

    dry_run = run_cli(root, "backup", "restore", str(backup), "--dry-run")
    assert dry_run.returncode == 0, dry_run.stderr
