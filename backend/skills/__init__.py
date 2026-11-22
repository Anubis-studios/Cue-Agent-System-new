"""Agent skills library (agentic-awesome-skills style).

Skills are small prompt-template modules that register themselves into the
shared tool registry via :func:`backend.tools.register_tool` with
``source="skill"``.  Importing this package auto-discovers every module in
``backend/skills/library/``; user-provided skill directories can be loaded on
top via :func:`load_user_skills`.
"""

import importlib
import logging
import pkgutil
from pathlib import Path

logger = logging.getLogger(__name__)

BUILTIN_PACKAGE = "backend.skills.library"


def load_builtin_skills() -> list[str]:
    """Import every module in the bundled skills library."""
    loaded: list[str] = []
    package = importlib.import_module(BUILTIN_PACKAGE)
    for mod in pkgutil.iter_modules(package.__path__):
        if mod.name.startswith("_"):
            continue
        try:
            importlib.import_module(f"{BUILTIN_PACKAGE}.{mod.name}")
            loaded.append(mod.name)
        except Exception as exc:  # noqa: BLE001 - one bad skill shouldn't break boot
            logger.warning("Failed to load skill %s: %s", mod.name, exc)
    return loaded


def load_user_skills(directory: str | Path) -> list[str]:
    """Load extra skill modules from an arbitrary user directory."""
    directory = Path(directory).expanduser()
    loaded: list[str] = []
    if not directory.is_dir():
        return loaded
    import sys

    sys.path.insert(0, str(directory.parent))
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            importlib.import_module(path.stem)
            loaded.append(path.stem)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load user skill %s: %s", path.name, exc)
    return loaded
