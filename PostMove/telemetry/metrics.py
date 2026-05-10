from __future__ import annotations

import psutil


class RuntimeMetrics:
    @staticmethod
    def snapshot() -> dict:
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": psutil.virtual_memory().percent,
            "process_count": len(psutil.pids()),
        }
