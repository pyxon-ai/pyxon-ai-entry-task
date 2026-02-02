"""Run all benchmarks and print summary metrics."""

import os
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    env = os.environ.copy()
    env["CHROMA_PATH"] = env.get("CHROMA_PATH", str(root / "data" / "chroma_bench"))
    env["SQLITE_PATH"] = env.get("SQLITE_PATH", str(root / "data" / "bench.db"))
    (root / "data").mkdir(exist_ok=True)
    (root / "data" / "chroma_bench").mkdir(exist_ok=True)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "benchmarks", "-v", "--tb=short", "-q"],
        env=env,
        cwd=root,
    )
    print("\nBenchmark run finished. Exit code:", result.returncode)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
