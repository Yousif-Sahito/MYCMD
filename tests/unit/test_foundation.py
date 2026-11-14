"""Foundation contracts; these tests do not claim application functionality."""

import tomllib
import unittest
from pathlib import Path

import mycmd

ROOT = Path(__file__).resolve().parents[2]


class FoundationTests(unittest.TestCase):
    def test_package_version_matches_metadata(self) -> None:
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["project"]["version"], mycmd.__version__)

    def test_environment_template_has_no_active_secrets(self) -> None:
        values = dict(
            line.split("=", 1)
            for line in (ROOT / ".env.example").read_text().splitlines()
            if line and not line.startswith("#")
        )
        self.assertEqual(values["DATABASE_URL"], "")
        self.assertEqual(values["MYCMD_SECRET_KEY"], "")
        self.assertEqual(values["MYCMD_SYNC_ENABLED"], "false")

    def test_client_wheel_excludes_server(self) -> None:
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            config["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"], ["src/mycmd"]
        )
