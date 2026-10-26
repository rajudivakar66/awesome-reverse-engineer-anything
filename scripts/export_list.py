#!/usr/bin/env python3
"""Export the entries of this list as JSON or CSV.

Each entry in the README becomes one record:

  name       the link text
  url        the link target
  repo       owner/name when the link is a GitHub repository, else empty
  section    the ## heading the entry sits under
  subsection the ### heading under it, else empty
  tags       every documented tag on the line, e.g. ["REA (partial)"]
  is_case    true for entries under the case sections
  license    true when the line states a license, or says there is none
  text       the line without its leading bullet

Line parsing is shared with validate_list.py.

    python3 scripts/export_list.py                       # JSON to stdout
    python3 scripts/export_list.py --format csv -o list.csv
    python3 scripts/export_list.py --lang zh --cases-only
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_list import (  # noqa: E402
    BULLET,
    CASE_SECTIONS,
    EN_README,
    HEADING,
    ROOT,
    ZH_README,
    Entry,
    attach_metadata,
    parse_file,
    read,
)

FIELDS = ["name", "url", "repo", "section", "subsection", "tags", "is_case", "license", "text"]


def top_sections(path: Path) -> dict[int, str]:
    """The ## heading in force on each line.

    parse_file records only the nearest heading, which for the community
    cases is a ### subsection such as "Games and reconstructions".
    """
    current, by_line = "(top)", {}
    for line_no, raw in enumerate(read(path).splitlines(), start=1):
        heading = HEADING.match(raw)
        if heading and len(heading.group(1)) == 2:
            current = heading.group(2).strip()
        by_line[line_no] = current
    return by_line


def record(entry: Entry, section: str) -> dict:
    bullet = BULLET.match(entry.text)
    return {
        "name": entry.name,
        "url": entry.url,
        "repo": entry.repo or "",
        "section": section,
        "subsection": entry.section if entry.section != section else "",
        "tags": entry.tags,
        "is_case": section.lower() in CASE_SECTIONS,
        "license": entry.has_license,
        "text": (bullet.group(1) if bullet else entry.text).strip(),
    }


def collect(readme: str, cases_only: bool) -> list[dict]:
    path = ROOT / readme
    entries, _ = parse_file(path)
    attach_metadata(entries)
    sections = top_sections(path)
    # Table rows repeat entries listed elsewhere ("Most shared"), so only
    # bullets are exported.
    records = [record(e, sections[e.line_no]) for e in entries if BULLET.match(e.text)]
    if cases_only:
        records = [r for r in records if r["is_case"]]
    return records


def write_csv(records: list[dict], out) -> None:
    writer = csv.DictWriter(out, fieldnames=FIELDS)
    writer.writeheader()
    for row in records:
        writer.writerow({**row, "tags": "; ".join(row["tags"])})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--lang", choices=["en", "zh"], default="en")
    parser.add_argument("--cases-only", action="store_true", help="only entries under case sections")
    parser.add_argument("-o", "--output", help="write to this file instead of stdout")
    args = parser.parse_args()

    records = collect(EN_README if args.lang == "en" else ZH_README, args.cases_only)

    out = open(args.output, "w", encoding="utf-8", newline="") if args.output else sys.stdout
    try:
        if args.format == "json":
            json.dump(records, out, ensure_ascii=False, indent=2)
            out.write("\n")
        else:
            write_csv(records, out)
    finally:
        if args.output:
            out.close()

    if args.output:
        print(f"wrote {len(records)} entries to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
