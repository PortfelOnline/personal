#!/usr/bin/env python3
"""
Parse Rankd SEO backlinks listing pages (pasted as text).
Usage: python3 rankd_parser.py  (reads from stdin or text files)
"""
import re
import json
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "rankd_platforms.json"


def parse_rankd_text(text: str) -> list[dict]:
    """Parse raw text pasted from Rankd listing pages."""
    platforms = []

    # Split by "Published in Backlinks" — each entry ends with this
    entries = re.split(r'\s*Published in Backlinks\s*', text)

    for entry in entries:
        entry = entry.strip()
        if not entry or "Details Website:" not in entry:
            continue

        # Extract website
        m = re.search(r'Website:\s*(https?://\S+)', entry)
        if not m:
            continue
        website = m.group(1).rstrip('/.,')

        # Extract DA
        m_da = re.search(r'DA:\s*(\d+)', entry)
        da = int(m_da.group(1)) if m_da else 0

        # Extract PA
        m_pa = re.search(r'PA:\s*(\d+)', entry)
        pa = int(m_pa.group(1)) if m_pa else 0

        # Extract Do-Follow
        m_df = re.search(r'Do-Follow:\s*(YES|NO)', entry, re.IGNORECASE)
        do_follow = m_df.group(1).upper() == "YES" if m_df else False

        # Extract name — first non-empty line before "Details"
        pre_details = entry.split("Details Website:")[0]
        name = ""
        for line in pre_details.split('\n'):
            line = line.strip()
            # Skip date lines and "by R-K-M" type lines
            if not line:
                continue
            if re.match(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', line):
                continue
            if re.match(r'\d{4}', line) or 'by ' in line.lower():
                continue
            if line in ('Home', 'Pricing', 'Backlink Database', 'My Profile', 'LOGOUT', 'Backlinks'):
                continue
            name = line
            break

        # Extract instructions
        instructions = ""
        m_inst = re.search(r'Instructions\s+(.*?)(?:\s*$|\s*Here\'s where)', entry, re.DOTALL)
        if m_inst:
            instructions = m_inst.group(1).strip()[:1000]

        # Detect link type
        text_lower = entry.lower()
        link_type = "profile"
        if "bookmark" in text_lower:
            link_type = "bookmark"
        elif "web 2.0" in text_lower or "blog" in text_lower or "post" in text_lower:
            link_type = "web2.0"
        elif "article" in text_lower or "guest post" in text_lower:
            link_type = "article"

        if name and website:
            platforms.append({
                "name": name,
                "website": website,
                "da": da,
                "pa": pa,
                "do_follow": do_follow,
                "type": link_type,
                "instructions": instructions,
            })

    return platforms


def main():
    # Read from stdin (paste multiple pages separated by newlines)
    import sys
    print("Paste Rankd listing page text (all pages), then press Ctrl+D (Mac/Linux) or Ctrl+Z (Windows):")
    text = sys.stdin.read()

    platforms = parse_rankd_text(text)

    # Merge with existing if any
    existing = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            for item in json.load(f):
                existing[item["website"]] = item

    for p in platforms:
        existing[p["website"]] = p

    all_platforms = list(existing.values())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_platforms, f, ensure_ascii=False, indent=2)

    do_follow = [p for p in all_platforms if p["do_follow"]]
    print(f"\n✅ Parsed {len(platforms)} from paste, total saved: {len(all_platforms)}")
    print(f"   Do-Follow: {len(do_follow)}, No-Follow: {len(all_platforms)-len(do_follow)}")

    top = sorted(do_follow, key=lambda x: x["da"], reverse=True)[:15]
    print("\nТоп Do-Follow по DA:")
    for p in top:
        print(f"  DA{p['da']:>3}  {p['name']:<30}  {p['website']}")


if __name__ == "__main__":
    main()
