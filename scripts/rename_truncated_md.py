#!/usr/bin/env python3
"""
Переименовать .md с обрезанными именами: новое имя = slug от поля title в frontmatter.

Запуск из корня репозитория:
  python3 scripts/rename_truncated_md.py           # dry-run
  python3 scripts/rename_truncated_md.py --apply   # выполнить (git mv при наличии git)
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_title_from_frontmatter(raw: str) -> str | None:
    """Минимальный разбор YAML frontmatter: только поле title."""
    if not raw.startswith("---"):
        return None
    rest = raw[3:]
    if rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\n"):
        rest = rest[1:]
    end_marker = "\n---"
    end_idx = rest.find(end_marker)
    if end_idx == -1:
        return None
    fm_block = rest[:end_idx]
    for line in fm_block.splitlines():
        line = line.strip()
        if not line.startswith("title:"):
            continue
        val = line[len("title:") :].strip()
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            return val[1:-1].replace('\\"', '"').replace("\\'", "'")
        return val
    return None

BAD_SUFFIXES = (
    "-си",
    "-клие",
    "-прил",
    "-интеграци",
    "-доку",
    "-каби",
    "-ск",
    "-сис",
    "-об",
    "-н",
    "-на-то",
    "-штучные-то",
)


def stem_from_title(title: str, max_len: int = 130) -> str:
    s = title.strip().lower()
    s = re.sub(r"[^\w\u0400-\u04FF]+", "-", s, flags=re.UNICODE)
    s = re.sub(r"-+", "-", s).strip("-")
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s


def needs_rename(path: Path) -> bool:
    name = path.name
    if "│" in name or "|" in name:
        return True
    if "онлайн-о" in path.stem:
        return True
    stem = path.stem
    for b in BAD_SUFFIXES:
        if stem.endswith(b):
            return True
    if stem.endswith("-з") and not stem.endswith("-заказ"):
        return True
    return False


def _git_mv(old: Path, new: Path) -> None:
    try:
        subprocess.run(
            ["git", "mv", str(old), str(new)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        shutil.move(str(old), str(new))


def main() -> int:
    apply = "--apply" in sys.argv
    planned: list[tuple[Path, Path]] = []

    for path in sorted(ROOT.rglob("*.md")):
        if path.parent == ROOT / "scripts":
            continue
        if not needs_rename(path):
            continue
        raw = path.read_text(encoding="utf-8")
        title = read_title_from_frontmatter(raw)
        if not title:
            print(f"skip (нет title): {path.relative_to(ROOT)}", file=sys.stderr)
            continue
        new_stem = stem_from_title(str(title))
        new_path = path.with_name(new_stem + ".md")
        if new_path.resolve() == path.resolve():
            continue
        if new_path.exists():
            print(f"collision: {path} -> {new_path}", file=sys.stderr)
            continue
        planned.append((path, new_path))

    for old, new in planned:
        rel_o = old.relative_to(ROOT)
        rel_n = new.relative_to(ROOT)
        if apply:
            _git_mv(old, new)
            print(f"{rel_o} -> {rel_n}")
        else:
            print(f"{rel_o} -> {rel_n}")

    if not planned:
        print("Нет файлов для переименования.", file=sys.stderr)
    elif not apply:
        print(
            f"\nDry-run: {len(planned)} файл(ов). Для выполнения: "
            "python3 scripts/rename_truncated_md.py --apply",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
