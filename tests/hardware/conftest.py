"""Make tools/hw importable (the checkers are plain scripts, not a package)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "hw"))
