#!/usr/bin/env python3
"""
Normalize Aqua Delivery KB markdown:
  - Unified YAML frontmatter (title, area, tags, optional source)
  - Structure: ## Кратко / ## Пошагово where safe (skip if ## Кратко exists)

Run from repo root: python3 scripts/normalize_kb.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT_MARKER = " — База знаний Aqua Delivery"

AREA_BY_PREFIX: tuple[tuple[str, str], ...] = (
    ("01. CRM — Кабинет заказов", "crm"),
    ("02. Курьерское приложение", "courier"),
    ("03. Мобильное приложение", "mobile-app"),
    ("04. Система лояльности", "loyalty"),
    ("05. Маркировка", "marking"),
    ("06. Оплата и финансы", "payments"),
    ("07. Аналитика и отчёты", "analytics"),
    ("08. Сайт и виджеты", "site-widgets"),
    ("09. Интеграция с 1С", "1c"),
    ("10. МикроМаркет", "micromarket"),
    ("11. Партнёры и онбординг", "partners"),
    ("12. Регламенты и процессы", "processes"),
)


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\u0400-\u04FF]+", "-", s, flags=re.UNICODE)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:48] if len(s) > 48 else s


def area_from_relative(rel: Path) -> str:
    parts = rel.parts
    if not parts:
        return "general"
    top = parts[0]
    for prefix, code in AREA_BY_PREFIX:
        if top == prefix:
            return code
    return _slug(top.split(". ", 1)[-1] if ". " in top else top)


def tags_from_path(rel: Path) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for part in rel.parts[:-1]:
        label = part.split(". ", 1)[-1] if ". " in part else part
        t = _slug(label)
        if t and t not in seen:
            seen.add(t)
            tags.append(t)
    stem = rel.stem
    if stem:
        t = _slug(stem.replace("_", " "))
        if t and t not in seen:
            seen.add(t)
            tags.append(t)
    return tags[:12]


def clean_title_line(h1: str) -> str:
    line = h1.strip()
    if line.startswith("# "):
        line = line[2:].strip()
    if ROOT_MARKER in line:
        line = line.split(ROOT_MARKER)[0].strip()
    line = re.sub(r"\s*[│|]\s*CRM-система Aqua Delivery\s*$", "", line, flags=re.I)
    return line.strip() or "Инструкция"


def extract_h1(body: str) -> str | None:
    for line in body.splitlines():
        if line.startswith("# ") and not line.startswith("##"):
            return clean_title_line(line)
    return None


def _yaml_escape_double(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def yaml_double_quoted(s: str) -> str:
    return '"' + _yaml_escape_double(s) + '"'


def _strip_leading_orphan_dashes(body: str) -> str:
    """Убирает лишние «---» в начале тела (после некорректного парсинга или правок)."""
    lines = body.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    while i < len(lines) and lines[i].strip() == "---":
        i += 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    out = "\n".join(lines[i:])
    if body.endswith("\n"):
        out += "\n"
    return out


def parse_frontmatter(raw: str) -> tuple[dict[str, object], str]:
    if not raw.startswith("---"):
        return {}, raw
    m = re.match(r"^---\r?\n", raw)
    if not m:
        return {}, raw
    rest = raw[m.end() :]
    end_marker = "\n---"
    end_idx = rest.find(end_marker)
    if end_idx == -1:
        return {}, raw
    fm_block = rest[:end_idx]
    after_close = end_idx + len(end_marker)
    body = rest[after_close:]
    if body.startswith("\r"):
        body = body[1:]
    if body.startswith("\n"):
        body = body[1:]
    # После бага парсера или ручных правок тело могло начинаться с лишних ---
    body = _strip_leading_orphan_dashes(body)
    meta: dict[str, object] = {}
    lines = fm_block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("tags:"):
            tags: list[str] = []
            i += 1
            while i < len(lines) and lines[i].startswith("  - "):
                val = lines[i][4:].strip()
                if (val.startswith('"') and val.endswith('"')) or (
                    val.startswith("'") and val.endswith("'")
                ):
                    val = val[1:-1]
                tags.append(val)
                i += 1
            meta["tags"] = tags
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1].replace('\\"', '"').replace("\\\\", "\\")
            meta[key] = val
        i += 1
    return meta, body


def dump_frontmatter(meta: dict[str, object]) -> str:
    lines = ["---"]
    title = str(meta.get("title", "")).strip()
    lines.append(f"title: {yaml_double_quoted(title)}")
    lines.append(f"area: {meta['area']}")
    lines.append("tags:")
    for t in meta.get("tags") or []:
        lines.append(f"  - {yaml_double_quoted(str(t))}")
    src = meta.get("source")
    if src:
        lines.append(f"source: {yaml_double_quoted(str(src))}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def merge_tags(existing: list[str] | None, generated: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for t in (existing or []) + generated:
        t = str(t).strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:15]


def apply_structure(body: str) -> str:
    """Insert ## Кратко / ## Пошагово when missing (conservative)."""
    if "## Кратко" in body:
        return body

    lines = body.splitlines()
    h1_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# ") and not line.startswith("##"):
            h1_idx = i
            break
    if h1_idx is None:
        return body

    i = h1_idx + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return body

    first = lines[i]

    # Starts with ### role blocks — add short Кратко from H1
    if first.startswith("### "):
        summary_line = _auto_summary_line(lines[h1_idx])
        block = ["", "## Кратко", "", summary_line, ""]
        for off, ln in enumerate(block):
            lines.insert(i + off, ln)
        return "\n".join(lines) + ("\n" if body.endswith("\n") else "")

    # Starts with ## — already structured at level 2
    if first.startswith("## "):
        return body

    # Starts with numbered step — wrap whole tail in Пошагово (after optional Кратко)
    if re.match(r"^\d+\.\s", first):
        lines.insert(i, "## Пошагово")
        lines.insert(i, "")
        return "\n".join(lines) + ("\n" if body.endswith("\n") else "")

    # Paragraphs until ## / ### / numbered list → Кратко
    j = i
    prefix: list[str] = []
    while j < len(lines):
        line = lines[j]
        if line.startswith("## "):
            break
        if line.startswith("### "):
            break
        if re.match(r"^\d+\.\s", line):
            break
        prefix.append(line)
        j += 1

    if not prefix or not any(p.strip() for p in prefix):
        # Nothing to wrap as Кратко; numbered list may follow
        if j < len(lines) and re.match(r"^\d+\.\s", lines[j]):
            lines.insert(j, "## Пошагово")
            lines.insert(j, "")
        return "\n".join(lines) + ("\n" if body.endswith("\n") else "")

    # Insert ## Кратко before prefix; remove duplicate prefix lines from original positions
    head = lines[:i]
    tail = lines[j:]
    new_lines = head + ["## Кратко", ""] + prefix + [""] + tail

    # If next meaningful line is numbered list, insert ## Пошагово before it
    k = len(head) + 2 + len(prefix) + 1  # after blank following prefix
    # Recalculate: new_lines structure
    merged = "\n".join(new_lines)
    if merged.endswith("\n"):
        merged_ok = merged
    else:
        merged_ok = merged + "\n"

    lines2 = merged_ok.splitlines()
    # Find position after Кратко block (blank line after prefix)
    insert_at = None
    found_kratko = False
    for idx, ln in enumerate(lines2):
        if ln.strip() == "## Кратко":
            found_kratko = True
            continue
        if found_kratko and insert_at is None:
            # skip blank after ## Кратко then consume prefix until double newline then next
            pass
    # Simpler second pass on merged_ok
    return _ensure_poshagovo_after_kratko(merged_ok)


def _auto_summary_line(h1_line: str) -> str:
    title = clean_title_line(h1_line)
    return (
        f"Кратко: пошаговый порядок действий по теме «{title}» "
        f"для ролей, указанных ниже."
    )


def _ensure_poshagovo_after_kratko(body: str) -> str:
    if "## Пошагово" in body:
        return body
    lines = body.splitlines()
    for idx, ln in enumerate(lines):
        if ln.strip() != "## Кратко":
            continue
        j = idx + 1
        while j < len(lines):
            if re.match(r"^\d+\.\s", lines[j]):
                # Не вставлять между ### и списком шагов
                k = j - 1
                while k >= 0 and lines[k].strip() == "":
                    k -= 1
                if k >= 0 and lines[k].startswith("### "):
                    break
                lines.insert(j, "")
                lines.insert(j, "## Пошагово")
                break
            j += 1
        break
    out = "\n".join(lines)
    if body.endswith("\n"):
        out += "\n"
    return out


def process_file(path: Path, root: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    meta_old, body = parse_frontmatter(raw)

    rel = path.relative_to(root)
    area = area_from_relative(rel)
    gen_tags = tags_from_path(rel)
    title = extract_h1(body) or meta_old.get("title") or path.stem.replace("-", " ").replace("_", " ")
    title = str(title).strip()

    meta_new: dict[str, object] = {
        "title": title,
        "area": area,
        "tags": merge_tags(
            meta_old.get("tags") if isinstance(meta_old.get("tags"), list) else None,
            gen_tags,
        ),
    }
    src = meta_old.get("source")
    if src:
        meta_new["source"] = src

    body2 = apply_structure(body)
    out = dump_frontmatter(meta_new) + body2
    if raw != out:
        path.write_text(out, encoding="utf-8")
        return True
    return False


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    changed = 0
    for md in sorted(root.rglob("*.md")):
        if "scripts" in md.parts and md.parent.name == "scripts":
            continue
        if process_file(md, root):
            changed += 1
            print(md.relative_to(root))
    print(f"Updated {changed} file(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
