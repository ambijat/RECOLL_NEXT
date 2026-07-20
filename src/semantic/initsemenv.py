#!/usr/bin/env python3
"""Create an offline-safe Python environment for Recoll Next development."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def venv_interpreter(venv_path: Path, platform_name: str = os.name) -> Path:
    if platform_name == "nt":
        return venv_path / "Scripts" / "python.exe"
    python3 = venv_path / "bin" / "python3"
    return python3 if python3.exists() else venv_path / "bin" / "python"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "venv_path",
        nargs="?",
        default=str(REPOSITORY_ROOT / ".venv"),
        help="environment directory (default: repository .venv)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="run the dependency-free semantic test suite after creation",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    target = Path(args.venv_path).expanduser().resolve()
    if target.exists() and not target.is_dir():
        print(f"Environment target is not a directory: {target}", file=sys.stderr)
        return 2

    # The supported subsystem uses the standard library. In particular, bootstrap
    # must not install Chroma, contact a package index, or pull Ollama models.
    venv.EnvBuilder(with_pip=False, clear=False).create(target)
    interpreter = venv_interpreter(target)
    if not interpreter.is_file():
        print(f"Environment interpreter was not created: {interpreter}", file=sys.stderr)
        return 1

    print(f"Created local environment: {target}")
    print(f"Python: {interpreter}")
    print("No packages or models were downloaded.")
    if args.verify:
        command = [
            str(interpreter),
            "-W",
            "error::ResourceWarning",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/semantic",
        ]
        return subprocess.run(command, cwd=REPOSITORY_ROOT, check=False).returncode
    print(
        "Next: run the semantic tests, then provision Recoll and Ollama separately "
        "under operator control."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
