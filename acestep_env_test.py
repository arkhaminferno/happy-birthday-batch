"""Tests for cross-platform bootstrap and ACE-Step discovery."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from batch_birthday.acestep_env import resolve_acestep_root


class TestAcestepEnv(unittest.TestCase):
    """ACE-Step root discovery."""

    def test_resolve_acestep_parent_on_mac_layout(self) -> None:
        """When nested in ACE-Step-1.5/batch_birthday, parent is ACE-Step root."""
        batch_root = Path(__file__).resolve().parent
        parent = batch_root.parent
        if (parent / "acestep").is_dir():
            self.assertEqual(resolve_acestep_root(), parent)

    def test_resolve_acestep_from_env(self) -> None:
        """ACESTEP_ROOT env overrides sibling search."""
        batch_root = Path(__file__).resolve().parent
        parent = batch_root.parent
        if not (parent / "acestep").is_dir():
            self.skipTest("not nested in ACE-Step checkout")
        with patch.dict("os.environ", {"ACESTEP_ROOT": str(parent)}):
            self.assertEqual(resolve_acestep_root(), parent)


class TestCliBootstrap(unittest.TestCase):
    """Flat clone folder name bootstrap."""

    def test_bootstrap_registers_package_for_flat_clone(self) -> None:
        """cli_entry can register batch_birthday when folder is not named batch_birthday."""
        import importlib.util

        batch_root = Path(__file__).resolve().parent
        spec = importlib.util.spec_from_file_location("cli_entry", batch_root / "cli_entry.py")
        assert spec and spec.loader
        cli_entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli_entry)

        fake_root = Path("/tmp/happy-birthday-batch")
        with patch.object(cli_entry, "_REPO_ROOT", fake_root):
            if "batch_birthday" in sys.modules:
                del sys.modules["batch_birthday"]
            cli_entry.bootstrap_package()
            self.assertIn("batch_birthday", sys.modules)
            pkg = sys.modules["batch_birthday"]
            self.assertIsInstance(pkg, types.ModuleType)
            self.assertEqual(pkg.__path__, [str(fake_root)])


if __name__ == "__main__":
    unittest.main()
