"""Cross-platform CLI entry — works regardless of clone folder name."""

from __future__ import annotations

import sys
import types
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent


def bootstrap_package() -> None:
    """Register batch_birthday when the repo is cloned as happy-birthday-batch."""
    if _REPO_ROOT.name == "batch_birthday":
        parent = str(_REPO_ROOT.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        return
    if "batch_birthday" in sys.modules:
        return
    pkg = types.ModuleType("batch_birthday")
    pkg.__path__ = [str(_REPO_ROOT)]
    init_py = _REPO_ROOT / "__init__.py"
    pkg.__file__ = str(init_py) if init_py.is_file() else str(_REPO_ROOT / "cli_entry.py")
    sys.modules["batch_birthday"] = pkg


def main() -> None:
    """Run the CelebrateVibes batch CLI."""
    bootstrap_package()
    from batch_birthday.__main__ import main as batch_main

    batch_main()


if __name__ == "__main__":
    main()
