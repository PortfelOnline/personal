#!/usr/bin/env python3
"""
Parse Safari Cookies.binarycookies and extract Yandex/Dzen/Spark session cookies.
Writes Puppeteer-compatible JSON to .safari-cookies.json beside this script.
"""
import struct, sys, json, os

COOKIES_FILE = os.path.expanduser("~/Library/Cookies/Cookies.binarycookies")
OUTPUT_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".safari-cookies.json")
MAC_EPOCH_DELTA = 978307200  # seconds from Mac epoch (2001-01-01) to Unix epoch
TARGET_DOMAINS = {".yandex.ru",".yandex.com",".dzen.ru",".sso.dzen.ru",".passport.dzen.ru",".spark.ru",".spark-interfax.ru"}


def read_cstr(data, offset):
    end = data.index(b"\x00", offset)
    return data[offset:end].decode("utf-8", errors="replace")


def parse():
    with open(COOKIES_FILE, "rb") as fh:
        raw = fh.read()
    assert raw[:4] == b"cook", "Not a Cookies.binarycookies file"
    num_pages = struct.unpack_from(">I", raw, 4)[0]
    page_sizes = [struct.unpack_from(">I", raw, 8 + i*4)[0] for i in range(num_pages)]
    cookies, cursor = [], 8 + num_pages * 4
    for ps in page_sizes:
        page = raw[cursor:cursor+ps]; cursor += ps
        if page[:4] != b"\x00\x00\x01\x00": continue
        nc = struct.unpack_from("<I", page, 4)[0]
        offsets = [struct.unpack_from("<I", page, 8+i*4)[0] for i in range(nc)]
        for co in offsets:
            try:
                c = page[co:]
                flags   = struct.unpack_from("<I", c, 8)[0]
                dom_o   = struct.unpack_from("<I", c, 16)[0]
                name_o  = struct.unpack_from("<I", c, 20)[0]
                path_o  = struct.unpack_from("<I", c, 24)[0]
                val_o   = struct.unpack_from("<I", c, 28)[0]
                exp_mac = struct.unpack_from(">d", c, 40)[0]
                domain = read_cstr(c, dom_o)
                name   = read_cstr(c, name_o)
                path   = read_cstr(c, path_o)
                value  = read_cstr(c, val_o)
                if domain and not domain.startswith("."): domain = "." + domain
                cookies.append({
                    "name": name, "value": value, "domain": domain, "path": path,
                    "expires": int(exp_mac + MAC_EPOCH_DELTA),
                    "httpOnly": bool(flags & 4), "secure": bool(flags & 1), "sameSite": "Lax"
                })
            except Exception: pass
    return [c for c in cookies if any(c["domain"] == d or c["domain"].endswith(d.lstrip(".")) for d in TARGET_DOMAINS)]


if __name__ == "__main__":
    try:
        data = parse()
        with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print(f"OK {len(data)}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)
