#!/usr/bin/env python3
"""
Fetch Instagram media permalinks and update strategy_dashboard DB.

Usage:
  python3 scripts/ig_sync_links.py --token YOUR_ACCESS_TOKEN --ig-id YOUR_IG_ACCOUNT_ID

Options:
  --token    Instagram / Facebook page access token (long-lived preferred)
  --ig-id    Instagram Business Account ID (numeric, e.g. 17841400000000000)
  --dry-run  Print matches but do not update the DB
  --list     Only list IG media (no DB update)
"""

import argparse
import json
import os
import sys

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import pymysql
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

DB_URL = os.environ.get("DATABASE_URL", "mysql://root@localhost:3306/strategy_dashboard")


def parse_db_url(url: str):
    """Parse mysql://user:pass@host:port/db"""
    url = url.replace("mysql://", "")
    user_pass, rest = (url.split("@", 1) if "@" in url else ("root", url))
    if ":" in user_pass:
        user, password = user_pass.split(":", 1)
    else:
        user, password = user_pass, ""
    host_port, db = rest.split("/", 1) if "/" in rest else (rest, "strategy_dashboard")
    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host, port = host_port, 3306
    return dict(host=host, port=port, user=user, password=password, database=db)


def ig_media(ig_id: str, token: str, limit: int = 100):
    """Fetch all published media from Instagram business account."""
    if not HAS_REQUESTS:
        print("requests not installed. Run: pip3 install requests", file=sys.stderr)
        sys.exit(1)
    results = []
    url = f"https://graph.facebook.com/v21.0/{ig_id}/media"
    params = {"fields": "id,permalink,timestamp,caption,media_type", "limit": limit, "access_token": token}
    while url:
        r = requests.get(url, params=params, verify=False, timeout=20)
        if not r.ok:
            print(f"[IG API error] {r.status_code}: {r.text}", file=sys.stderr)
            break
        data = r.json()
        results.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}  # next URL already has all params
    return results


def get_db_posts(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, metaPostId, postUrl, platform FROM contentPosts "
            "WHERE platform='instagram' AND status='published'"
        )
        return cur.fetchall()


def update_post_url(conn, post_id: int, post_url: str):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE contentPosts SET postUrl=%s WHERE id=%s",
            (post_url, post_id),
        )
    conn.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True, help="Facebook/Instagram access token")
    parser.add_argument("--ig-id", required=True, help="Instagram Business Account ID")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to DB")
    parser.add_argument("--list", action="store_true", help="Just list IG media and exit")
    args = parser.parse_args()

    print(f"Fetching IG media for account {args.ig_id}...")
    media = ig_media(args.ig_id, args.token)
    print(f"Found {len(media)} media items on Instagram\n")

    if args.list or not media:
        for m in media:
            print(f"  [{m['id']}] {m.get('timestamp','')} {m.get('media_type','')} → {m.get('permalink','')}")
            if m.get("caption"):
                print(f"          caption: {m['caption'][:80]}")
        return

    if not HAS_MYSQL:
        print("pymysql not installed. Run: pip3 install pymysql", file=sys.stderr)
        print("\nIG media JSON (copy to use manually):")
        print(json.dumps([{"id": m["id"], "permalink": m.get("permalink"), "ts": m.get("timestamp")} for m in media], indent=2))
        return

    db_params = parse_db_url(DB_URL)
    conn = pymysql.connect(**db_params, cursorclass=pymysql.cursors.DictCursor)

    try:
        db_posts = get_db_posts(conn)
        print(f"DB has {len(db_posts)} published Instagram posts\n")

        # Build map: metaPostId → permalink from IG
        ig_map = {m["id"]: m.get("permalink", "") for m in media if m.get("permalink")}

        matched = 0
        for post in db_posts:
            if post["postUrl"]:
                print(f"  [skip] #{post['id']} '{post['title'][:50]}' — already has URL")
                continue

            meta_id = post.get("metaPostId")
            if meta_id and meta_id in ig_map:
                permalink = ig_map[meta_id]
                print(f"  [match] #{post['id']} '{post['title'][:50]}' → {permalink}")
                if not args.dry_run:
                    update_post_url(conn, post["id"], permalink)
                matched += 1
            else:
                print(f"  [no match] #{post['id']} '{post['title'][:50]}' (metaPostId={meta_id})")
                # Show closest IG media by listing all (for manual matching)
                for m in media[:5]:
                    print(f"             candidate: {m['id']} {m.get('timestamp','')} {m.get('permalink','')}")

        print(f"\nDone. {matched} post(s) updated{'(dry run)' if args.dry_run else ''}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
