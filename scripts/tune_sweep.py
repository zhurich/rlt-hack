"""Перебор параметров признаков: каждый вариант — отдельный прогон tune.py, по 5 параллельно.

Итог по каждому варианту — строка «подобранные веса» на периоде настройки и проверки.
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARIANTS = [
    "",
    "--top-lots 1000",
    "--top-lots 100",
    "--sim-power 4",
    "--sim-power 1",
    "--top-lots 1000 --sim-power 4",
    "--half-life 180",
    "--half-life 730",
    "--win-bonus 0",
    "--win-bonus 1.5",
]


def run(variant: str) -> tuple[str, str]:
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "tune.py"), *variant.split()],
        capture_output=True, text=True, encoding="utf-8", env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    return variant or "(по умолчанию)", out.stdout if out.returncode == 0 else out.stderr[-2000:]


with ThreadPoolExecutor(5) as pool:
    for variant, text in pool.map(run, VARIANTS):
        print(f"\n### {variant}")
        for line in text.splitlines():
            if line.startswith(("подобранные веса", "  релевантность", "  множители", "Traceback")) or "Error" in line:
                print(line)
