#!/usr/bin/env python3
"""
Parse Rankd table format (copy-paste from the full list page).
Format: number  Name  DA  Yes/No  Type (multi-line type possible)
"""
import re, json, sys
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "rankd_platforms.json"

def parse_table(text: str) -> list[dict]:
    platforms = []

    # Normalize: collapse multiple spaces/tabs to single tab
    # Lines look like: "36\tMicrosoft\t100\tYes\tProfile link"
    # But may have multi-line types like "Web 2.0\nArticle Submission"

    lines = text.splitlines()
    # Filter to lines that start with a number (entries)
    # Each entry: number, name, DA, Yes/No, type(s)
    # Type can span multiple lines until next numbered entry

    entries = []
    current = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match: "240    Apple    100    No    Comment"
        # or:    "78    Google Sites    98    Yes    Web 2.0"
        m = re.match(r'^(\d+)\s{2,}(.+?)\s{2,}(\d+)\s{2,}(Yes|No)\s{2,}(.*)', line, re.IGNORECASE)
        if not m:
            # Could be continuation of type from previous entry
            if current is not None and line and not re.match(r'^\d+\s', line):
                # Append to type if it looks like a type descriptor
                if re.match(r'^(Web 2\.0|Article|Social|Profile|Forum|URL|Business|Other|Bookmark|Comment)', line, re.IGNORECASE):
                    current['type'] = (current['type'] + ' / ' + line).strip(' /')
            continue

        if current is not None:
            entries.append(current)

        num, name, da, do_follow_str, type_str = m.groups()
        current = {
            'num': int(num),
            'name': name.strip(),
            'da': int(da),
            'do_follow': do_follow_str.lower() == 'yes',
            'type': type_str.strip(),
            'website': '',
            'pa': 0,
            'instructions': '',
        }

    if current is not None:
        entries.append(current)

    return entries


def main():
    text = sys.stdin.read()
    entries = parse_table(text)

    # Load existing
    existing = {}
    if OUTPUT_FILE.exists():
        for item in json.loads(OUTPUT_FILE.read_text()):
            existing[item['name'].lower()] = item

    added = 0
    for e in entries:
        key = e['name'].lower()
        if key not in existing:
            existing[key] = e
            added += 1
        else:
            # Update DA/do_follow/type from table (more authoritative)
            existing[key].update({
                'da': e['da'],
                'do_follow': e['do_follow'],
                'type': e['type'] or existing[key].get('type', ''),
                'num': e['num'],
            })

    all_platforms = sorted(existing.values(), key=lambda x: x.get('da', 0), reverse=True)
    OUTPUT_FILE.write_text(json.dumps(all_platforms, ensure_ascii=False, indent=2))

    do_follow = [p for p in all_platforms if p['do_follow']]
    print(f"\n✅ Parsed {len(entries)} from table, {added} new. Total saved: {len(all_platforms)}")
    print(f"   Do-Follow: {len(do_follow)}, No-Follow: {len(all_platforms)-len(do_follow)}")
    print("\nТоп-20 Do-Follow по DA:")
    for p in do_follow[:20]:
        name = p['name']
        print(f"  DA{p['da']:>3}  {name:<30}  {p.get('type','')[:35]}")


if __name__ == "__main__":
    main()
