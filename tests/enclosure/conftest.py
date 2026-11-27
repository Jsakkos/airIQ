"""Make enclosure/src importable (the generators are plain modules) and find solidcraft-cli."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "enclosure" / "src"))


@pytest.fixture(scope="session")
def cli():
    """solidcraft-cli's path; tests that need it skip where it is missing (CI has none)."""
    import encbuild
    path = encbuild.cli_path()
    if not path:
        pytest.skip("solidcraft-cli not found (install SolidCraft or set SOLIDCRAFT_CLI)")
    return path
