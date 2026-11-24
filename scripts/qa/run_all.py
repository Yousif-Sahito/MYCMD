"""Execute release gates, preserving command output and machine-readable results.

Use --local before pushing; this never claims cross-platform CI verification.
The default release mode requires --ci-run and checks that run against HEAD.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class Result:
    stage: str
    status: str
    mandatory: bool
    command: list[str]
    exit_code: int | None
    seconds: float
    detail: str


def execute(stage: str, command: list[str], output: Path, *, timeout: int = 600) -> Result:
    start = time.monotonic()
    log = output / f"{stage}.log"
    try:
        with log.open("w", encoding="utf-8") as stream:
            process = subprocess.run(
                command, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout, check=False
            )
        return Result(
            stage,
            "PASS" if process.returncode == 0 else "FAIL",
            True,
            command,
            process.returncode,
            time.monotonic() - start,
            str(log),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"\n{type(error).__name__}: {error}\n")
        return Result(stage, "BLOCKED", True, command, None, time.monotonic() - start, str(log))


def ci_result(run: str | None, output: Path, local: bool) -> Result:
    command = [
        "gh",
        "run",
        "view",
        run or "",
        "--repo",
        "Yousif-Sahito/MYCMD",
        "--json",
        "headSha,status,conclusion,jobs,url",
    ]
    if not run:
        return Result(
            "P-cross-platform-ci",
            "NOT RUN",
            not local,
            [],
            None,
            0,
            "No run supplied. Local results do not establish Windows/Ubuntu CI.",
        )
    result = execute("P-cross-platform-ci", command, output)
    result.mandatory = not local
    if result.status != "PASS":
        return result
    try:
        evidence = json.loads(Path(result.detail).read_text(encoding="utf-8"))
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        jobs = evidence["jobs"]
        platforms = [
            any(platform in job["name"] and job["conclusion"] == "success" for job in jobs)
            for platform in ("windows", "ubuntu")
        ]
        valid = (
            evidence["headSha"] == head
            and evidence["status"] == "completed"
            and evidence["conclusion"] == "success"
            and all(platforms)
        )
        result.status = "PASS" if valid else "BLOCKED"
        result.detail += "; exact HEAD and successful Windows/Ubuntu jobs required"
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        result.status = "BLOCKED"
        result.detail += f"; invalid CI evidence: {error}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".tools/phase4-qa"))
    parser.add_argument("--uv", default=shutil.which("uv") or "uv")
    parser.add_argument("--ci-run")
    parser.add_argument("--local", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    pytest = [python, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    stages = [
        ("A-lock", [args.uv, "lock", "--check"]),
        ("A-dependencies", [args.uv, "pip", "check", "--python", python]),
        (
            "B-format",
            [python, "-m", "ruff", "format", "--check", "src", "server", "tests", "scripts"],
        ),
        ("C-lint", [python, "-m", "ruff", "check", "src", "server", "tests", "scripts"]),
        ("D-types", [python, "-m", "mypy", "--strict"]),
        ("E-unit", pytest + ["tests/unit"]),
        ("F-database", pytest + ["tests/integration/test_storage.py"]),
        ("G-cli", pytest + ["tests/integration/test_cli.py"]),
        ("H-terminal", pytest + ["tests/integration/test_terminal.py"]),
        ("I-gui", pytest + ["tests/gui"]),
        ("J-accessibility", pytest + ["tests/gui", "-k", "accessibility"]),
        ("K-security", pytest + ["tests/gui", "-k", "security"]),
        ("K-full-suite", pytest + ["tests"]),
        ("L-build", [args.uv, "build", "--out-dir", str(output / "dist")]),
        ("P-frontend-deps", [npm, "ci", "--prefix", "apps/portfolio"]),
        ("Q-frontend-types", [npm, "run", "typecheck", "--prefix", "apps/portfolio"]),
        ("R-frontend-lint", [npm, "run", "lint", "--prefix", "apps/portfolio"]),
        ("S-frontend-unit", [npm, "test", "--prefix", "apps/portfolio"]),
        ("T-frontend-build", [npm, "run", "build", "--prefix", "apps/portfolio"]),
        ("U-frontend-browser", [npm, "run", "e2e:install", "--prefix", "apps/portfolio"]),
        ("U-frontend-e2e", [npm, "run", "e2e", "--prefix", "apps/portfolio"]),
    ]
    results = []
    for stage, command in stages:
        print(f"Running {stage}", flush=True)
        is_test = command[:3] == pytest[:3]
        junit = output / f"{stage}.xml"
        if is_test:
            command = command + ["--basetemp", str(output / f"{stage}-tmp")]
            command = command + [f"--junitxml={junit}"]
        result = execute(stage, command, output)
        if is_test and result.status == "PASS":
            try:
                cases = list(ET.parse(junit).iter("testcase"))
                skipped = sum(case.find("skipped") is not None for case in cases)
                result.detail += f"; {len(cases)} cases, {skipped} skipped"
                if len(cases) == skipped:
                    result.status = "SKIPPED"
            except (OSError, ET.ParseError) as error:
                result.status = "BLOCKED"
                result.detail += f"; cannot validate test evidence: {error}"
        results.append(result)
        print(f"{stage}: {results[-1].status}", flush=True)
    wheels = list((output / "dist").glob("*.whl"))
    if results[-1].status == "PASS" and len(wheels) == 1:
        for stage, script in (
            ("M-wheel", "scripts/qa/check_gui_wheel.py"),
            ("N-installed", "scripts/qa/check_installed_gui.py"),
        ):
            results.append(execute(stage, [python, script, str(wheels[0])], output))
    else:
        for stage in ("M-wheel", "N-installed"):
            results.append(
                Result(
                    stage,
                    "BLOCKED",
                    True,
                    [],
                    None,
                    0,
                    "A successful build producing exactly one wheel is required",
                )
            )
    results.append(execute("O-git-hygiene", ["git", "diff", "--check"], output))
    results.append(ci_result(args.ci_run, output, args.local))
    success = all(item.status == "PASS" for item in results if item.mandatory)
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "local" if args.local else "release",
        "result": "PASS" if success else "FAIL",
        "results": [asdict(item) for item in results],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Phase 4 executed quality gates",
        "",
        f"Scope: {report['scope']}",
        f"Result: {report['result']}",
        "",
        "| Stage | Status | Exit | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| {item.stage} | {item.status} | {item.exit_code} | {item.detail} |" for item in results
    )
    lines += [
        "",
        "Offscreen GUI results do not establish visible desktop appearance.",
        "Ubuntu evidence does not establish direct Kali Linux verification.",
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
