"""System diagnostics for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import os
import platform
import shutil
from typing import Any


class SystemDiagnostics:
    @staticmethod
    def snapshot() -> dict[str, Any]:
        disk = shutil.disk_usage(os.path.abspath(os.sep))
        return {
            "success": True,
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "memory": SystemDiagnostics._memory(),
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
            },
        }

    @staticmethod
    def _memory() -> dict[str, Any]:
        try:
            import psutil
            vm = psutil.virtual_memory()
            return {"total": vm.total, "used": vm.used, "available": vm.available, "percent": vm.percent}
        except ImportError:
            return {"available": None, "percent": None}


__all__ = ["SystemDiagnostics"]
