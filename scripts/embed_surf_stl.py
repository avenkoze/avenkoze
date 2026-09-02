#!/usr/bin/env python3
"""Synchronize the generated ASCII STL with the profile README."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
MODEL = ROOT / "assets" / "surf-signal-001.stl"
START = "<!-- SURF_STL:START -->"
END = "<!-- SURF_STL:END -->"


def main() -> None:
    readme = README.read_text(encoding="utf-8")
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise SystemExit("README must contain exactly one surf STL marker pair")

    before, remainder = readme.split(START, 1)
    _, after = remainder.split(END, 1)
    model = MODEL.read_text(encoding="utf-8").rstrip()
    embedded = f"{START}\n```stl\n{model}\n```\n{END}"
    README.write_text(before + embedded + after, encoding="utf-8", newline="\n")
    print(f"embedded {MODEL.name} into {README.name}")


if __name__ == "__main__":
    main()
