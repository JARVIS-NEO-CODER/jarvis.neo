from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assistant.py"
TARGET = ROOT / "core" / "legacy_memory.py"
IMPORT_LINE = "from core.legacy_memory import MemoryManager"


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    if IMPORT_LINE in source:
        print("MemoryManager already extracted")
        return 0

    tree = ast.parse(source, filename=str(SOURCE))
    node = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MemoryManager"), None)
    if node is None:
        raise SystemExit("MemoryManager class not found")
    if node.end_lineno is None:
        raise SystemExit("MemoryManager has no end line")

    lines = source.splitlines(keepends=True)
    start = node.lineno - 1
    end = node.end_lineno
    class_source = "".join(lines[start:end]).rstrip() + "\n"

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    module = (
        '"""Legacy SQLite memory adapter kept compatible with the historical assistant runtime."""\n'
        "from __future__ import annotations\n\n"
        "import datetime\n"
        "import time\n"
        "from pathlib import Path\n\n\n"
        + class_source
        + "\n\n__all__ = [\"MemoryManager\"]\n"
    )
    TARGET.write_text(module, encoding="utf-8")

    replacement = IMPORT_LINE + "\n"
    new_source = "".join(lines[:start]) + replacement + "".join(lines[end:])
    SOURCE.write_text(new_source, encoding="utf-8")

    print(f"Extracted MemoryManager: {TARGET}")
    print(f"Removed {end - start} lines from assistant.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
