#!/usr/bin/env python3
"""Check local links and #anchors in every .html file under a folder.

Usage: python check_links.py [root]    (root defaults to the current directory)

Prints each broken link as "file: link (reason)" and exits 1 if any are
broken, 0 otherwise. Uses only the standard library and never touches the
network: links with a URL scheme (http:, mailto:, ...) or starting with "//"
are ignored.
"""

import os
import sys
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

SKIP_DIRS = {".git", ".venv"}


class _PageParser(HTMLParser):
    """Collects href/src values and the anchor targets (ids, <a name>) of a page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value is None:
                continue
            if name in ("href", "src"):
                self.links.append(value.strip())
            elif name == "id" or (name == "name" and tag == "a"):
                self.anchors.add(value)

    handle_startendtag = handle_starttag


def _parse(path):
    parser = _PageParser()
    with open(path, encoding="utf-8", errors="replace") as f:
        parser.feed(f.read())
    parser.close()
    return parser


def _html_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.lower().endswith(".html"):
                yield os.path.join(dirpath, name)


def _is_external(link):
    return link.startswith("//") or bool(urlsplit(link).scheme)


def check(root="."):
    """Return a list of (file, link, reason) tuples for every broken link under root.

    file is relative to root.
    """
    root = os.path.abspath(root)
    cache = {}

    def page(path):
        if path not in cache:
            cache[path] = _parse(path)
        return cache[path]

    problems = []
    for html_file in _html_files(root):
        rel_file = os.path.relpath(html_file, root)
        for link in page(html_file).links:
            if not link or _is_external(link):
                continue
            parts = urlsplit(link)
            path = unquote(parts.path)
            fragment = unquote(parts.fragment)

            if not path:
                target = html_file  # "#anchor" or "?query" on the same page
            else:
                if path.startswith("/"):
                    target = os.path.join(root, path.lstrip("/"))
                else:
                    target = os.path.join(os.path.dirname(html_file), path)
                target = os.path.normpath(target)
                if os.path.isdir(target):
                    index = os.path.join(target, "index.html")
                    if not os.path.isfile(index):
                        problems.append((rel_file, link, "folder has no index.html"))
                        continue
                    target = index
                elif not os.path.isfile(target):
                    problems.append((rel_file, link, "file not found"))
                    continue

            if fragment and target.lower().endswith(".html"):
                if fragment not in page(target).anchors:
                    problems.append((rel_file, link, "anchor not found"))
    return problems


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) > 1:
        print("usage: check_links.py [root]", file=sys.stderr)
        return 2
    root = argv[0] if argv else "."
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    problems = check(root)
    for file, link, reason in problems:
        print(f"{file}: {link} ({reason})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
