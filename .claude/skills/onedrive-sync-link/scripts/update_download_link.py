#!/usr/bin/env python3
import argparse
import re
import sys


def update_anchor_href(html: str, label: str, new_url: str) -> str:
    label_pos = html.find(label)
    if label_pos == -1:
        raise ValueError(f"Cannot find button label: {label}")

    a_start = html.rfind("<a ", 0, label_pos)
    if a_start == -1:
        raise ValueError(f"Cannot find <a> before label: {label}")

    tag_end = html.find(">", a_start)
    if tag_end == -1:
        raise ValueError("Malformed HTML: missing closing '>' for <a> tag")

    opening_tag = html[a_start : tag_end + 1]

    href_pattern = re.compile(r'href\s*=\s*"[^"]*"')
    if href_pattern.search(opening_tag):
        new_opening_tag = href_pattern.sub(f'href="{new_url}"', opening_tag, count=1)
    else:
        new_opening_tag = opening_tag[:-1] + f' href="{new_url}">'

    return html[:a_start] + new_opening_tag + html[tag_end + 1 :]


def main() -> int:
    parser = argparse.ArgumentParser(description="Update download link in HTML anchor by button text")
    parser.add_argument("--file", required=True, help="HTML file path")
    parser.add_argument("--label", required=True, help="Anchor display text to locate")
    parser.add_argument("--url", required=True, help="New href URL")
    args = parser.parse_args()

    try:
        with open(args.file, "rb") as f:
            raw = f.read()
        html = raw.decode("utf-8")

        updated = update_anchor_href(html, args.label, args.url)

        with open(args.file, "wb") as f:
            f.write(updated.encode("utf-8"))

        print(f"Updated link in {args.file}")
        return 0
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
