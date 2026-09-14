#!/usr/bin/env python3
"""
NASA APOD Data Fetcher
Fetches Astronomy Picture of the Day (APOD) entries from science.nasa.gov
using the provided base URL and API key.

Usage:
  python fetch_nasa_apod.py                     # Fetches latest 10 items and saves to nasa_apod_data.json
  python fetch_nasa_apod.py --count 20          # Fetches 20 items
  python fetch_nasa_apod.py --date 2026-09-14   # Fetches item for specific date
  python fetch_nasa_apod.py --search "Earth"    # Searches APOD feed
  python fetch_nasa_apod.py --download-images   # Also downloads image files to ./nasa_images/
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic"
API_KEY = "mrcH27uIs4gX9tPYIeBl0GFD62p49pMxmlas7vlq4"
OUTPUT_JSON = Path("nasa_apod_data.json")
DOWNLOAD_DIR = Path("nasa_images")


def strip_html(text: str) -> str:
    """Remove HTML markup for clean terminal viewing."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"&nbsp;", " ", clean)
    clean = re.sub(r"&#8211;", "-", clean)
    clean = re.sub(r"&#8217;", "'", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def make_request(url: str) -> tuple[int, dict, any]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-API-KEY": API_KEY,
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        status = resp.status
        headers_dict = dict(resp.getheaders())
        body = resp.read().decode("utf-8")
        data = json.loads(body)
        return status, headers_dict, data


def normalize_item(item: dict) -> dict:
    explanation_html = item.get("explanation", "")
    explanation_clean = strip_html(explanation_html)
    img_url = item.get("hdurl") or item.get("url") or ""

    return {
        "date": item.get("date", ""),
        "post_id": item.get("post_id"),
        "title": item.get("title", ""),
        "media_type": item.get("media_type", "image"),
        "image_url": img_url,
        "hdurl": item.get("hdurl", ""),
        "url": item.get("url", ""),
        "explanation": explanation_clean,
        "explanation_html": explanation_html,
        "credit": strip_html(item.get("credit", "")),
        "copyright": strip_html(item.get("copyright", "")),
        "permalink": item.get("permalink", ""),
        "alt": item.get("alt", ""),
    }


def fetch_apod_feed(count: int = 10, page: int = 1, search: str = None) -> list:
    params = {
        "per_page": min(max(1, count), 100),
        "page": max(1, page),
    }
    if search:
        params["search"] = search
    if API_KEY:
        params["api_key"] = API_KEY

    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}?{query}"
    print(f"[*] Requesting APOD feed from: {url}")

    status, headers, data = make_request(url)
    print(f"[+] HTTP Status: {status}")

    items = []
    if isinstance(data, list):
        items = [normalize_item(i) for i in data]
    elif isinstance(data, dict):
        items = [normalize_item(data)]
    return items


def fetch_apod_date(date_str: str) -> dict:
    clean = date_str.strip().replace("/", "-")
    code = clean
    if "-" in clean:
        try:
            dt = datetime.strptime(clean, "%Y-%m-%d")
            code = dt.strftime("%y%m%d")
        except ValueError:
            pass

    url = f"{BASE_URL}/{code}"
    if API_KEY:
        url += f"?api_key={urllib.parse.quote(API_KEY)}"

    print(f"[*] Requesting APOD for date [{date_str} / {code}] from: {url}")
    status, headers, data = make_request(url)
    print(f"[+] HTTP Status: {status}")

    if isinstance(data, list) and len(data) > 0:
        data = data[0]
    return normalize_item(data)


def download_image(img_url: str, dest_path: Path):
    if not img_url:
        return
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    req = urllib.request.Request(img_url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(resp.read())


def main():
    parser = argparse.ArgumentParser(description="Fetch NASA APOD data")
    parser.add_argument("--count", type=int, default=10, help="Number of items to fetch (default: 10)")
    parser.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    parser.add_argument("--date", type=str, default=None, help="Fetch specific date (e.g. 2026-09-14 or 260914)")
    parser.add_argument("--search", type=str, default=None, help="Search query (e.g. Earth, Nebula)")
    parser.add_argument("--download-images", action="store_true", help="Download images to ./nasa_images/")
    parser.add_argument("--output", type=str, default="nasa_apod_data.json", help="Output JSON file name")
    args = parser.parse_args()

    print("=" * 65)
    print(" SatQuery AI — NASA APOD Data Ingestion")
    print(f" Base URL: {BASE_URL}")
    print(f" API Key : {API_KEY[:8]}...{API_KEY[-4:]}")
    print("=" * 65)

    try:
        if args.date:
            item = fetch_apod_date(args.date)
            items = [item]
        else:
            items = fetch_apod_feed(count=args.count, page=args.page, search=args.search)

        print(f"\n[+] Successfully retrieved {len(items)} APOD entries.")

        # Save to JSON
        out_file = Path(args.output)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        print(f"[+] Saved structured data to: {out_file.resolve()}")

        # Display items
        print("\n" + "-" * 65)
        for idx, it in enumerate(items, 1):
            print(f"[{idx}] {it['date']} | {it['title']}")
            print(f"    Type     : {it['media_type']}")
            print(f"    HD URL   : {it['hdurl']}")
            print(f"    Webpage  : {it['permalink']}")
            if it.get('credit'):
                print(f"    Credit   : {it['credit']}")
            exp = it.get("explanation", "")
            snippet = (exp[:160] + "...") if len(exp) > 160 else exp
            print(f"    Summary  : {snippet}")
            print("-" * 65)

        # Image download if requested
        if args.download_images:
            print(f"\n[*] Downloading {len(items)} images to '{DOWNLOAD_DIR}'...")
            DOWNLOAD_DIR.mkdir(exist_ok=True)
            for idx, it in enumerate(items, 1):
                url = it.get("hdurl") or it.get("url")
                if not url or it.get("media_type") != "image":
                    continue
                ext = ".jpg"
                if ".png" in url:
                    ext = ".png"
                img_name = f"{it['date']}_{re.sub(r'[^a-zA-Z0-9]', '_', it['title'][:25])}{ext}"
                dest = DOWNLOAD_DIR / img_name
                print(f"    [{idx}/{len(items)}] Saving {dest.name} ...")
                download_image(url, dest)
            print("[+] Image downloads complete!")

    except Exception as e:
        print(f"[-] Error fetching data: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
