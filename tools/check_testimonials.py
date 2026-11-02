#!/usr/bin/env python3
"""Verify that NO customer testimonials are published anywhere on the site.

Policy (owner decision, 2026-11-02): named customer quotes and the
#testimonials section were removed because the owner has not confirmed them
for publication. This gate keeps them out. It fails if any tracked text file
the site serves or ships contains:

1. a testimonial block: `<figure class="testi...">`, a `class="testi"` /
   `id="testimonials"` element, a `#testimonials` anchor/link, or a
   "Customer testimonials" heading;
2. a `Review` / `AggregateRating` JSON-LD node (self-serving reviews);
3. any of the previously published named customer personas (see
   NAMED_PERSONAS);
4. a real custdev-interview respondent name (loaded at run time from
   `$ANIMA_CUSTDEV_NAMES_FILE`, default
   `~/work/anima-private/custdev-names.txt`, one name/transliteration per
   line, private, never committed). If that file is absent the name check
   prints a SKIP line and passes - all other checks still run.

To publish testimonials again the owner must confirm them in writing; this
gate and CLAUDE.md "MUST NOT appear" must be updated in the same change.

stdlib only. Usage: python3 tools/check_testimonials.py
Exit 0 if everything passes, else 1 (prints every failure found).
"""
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
THIS = pathlib.Path(__file__).resolve()

DEFAULT_NAMES_FILE = pathlib.Path("~/work/anima-private/custdev-names.txt").expanduser()

# Files the scan covers: every tracked text file the site serves or ships.
SCAN_PATTERNS = (
    re.compile(r"\.html$"),
    re.compile(r"\.md$"),
    re.compile(r"\.txt$"),
    re.compile(r"\.json$"),
    re.compile(r"\.js$"),
    re.compile(r"^delivery/"),
    re.compile(r"^release/"),
    re.compile(r"^docs/"),
    re.compile(r"^tools/"),
    re.compile(r"^tests/"),
)

# Structural markers of a testimonial block / review markup.
BLOCK_MARKERS = [
    (re.compile(r'<figure[^>]*class="[^"]*\btesti\b'), 'testimonial <figure class="testi">'),
    (re.compile(r'class="[^"]*\btesti(?:monials?)?\b'), 'testimonial CSS class'),
    (re.compile(r'id="testimonials"'), 'id="testimonials" section'),
    (re.compile(r'#testimonials'), '#testimonials link'),
    (re.compile(r'^#{1,6}\s*Customer testimonials', re.M | re.I), '"Customer testimonials" heading'),
    (re.compile(r'"@type"\s*:\s*"(?:Review|AggregateRating)"'), 'Review/AggregateRating JSON-LD'),
]

# Previously published named personas. Matched case-insensitively.
NAMED_PERSONAS = [
    "Maryna Dzhura", "Марина Джура", "Myata", "М'ята",
    "Diana Shevchenko", "Діана Шевченко",
    "Diana Samoukina", "Діана Самоукіна", "LUX CAFE",
    "Oleksii, grocery", "Олексій, власники",
    "Lesya, ", "Леся, М-н", "Леся (М-н",
    "Bohuslav",
    "Богуслав",
]

# Files that legitimately name the markers/personas: this checker and its test.
SELF_EXEMPT = {
    "tools/check_testimonials.py",
    "tools/test_check_testimonials.py",
}


def tracked_files(root: pathlib.Path):
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    files = []
    for rel in out.splitlines():
        rel = rel.strip()
        if rel and any(p.search(rel) for p in SCAN_PATTERNS):
            files.append(rel)
    return files


def load_custdev_names(path=None):
    """Load real custdev respondent names from a private, untracked file.

    Returns None if the file doesn't exist (caller must print SKIP and treat
    the name check as passed), else a list of non-empty, non-comment lines.
    """
    if path is not None:
        names_path = pathlib.Path(path).expanduser()
    else:
        names_path = pathlib.Path(os.environ.get("ANIMA_CUSTDEV_NAMES_FILE", str(DEFAULT_NAMES_FILE))).expanduser()
    if not names_path.exists():
        return None
    lines = []
    for line in names_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def scan_text(rel: str, text: str):
    """Return a list of error strings for one file. Pure function (no I/O) so
    it can be unit tested against synthetic fixtures."""
    errors = []
    for pat, label in BLOCK_MARKERS:
        if pat.search(text):
            errors.append(f"{rel}: contains {label} - testimonials are not approved for publication")
    low = text.lower()
    for name in NAMED_PERSONAS:
        if name.lower() in low:
            errors.append(f"{rel}: contains previously published named persona {name.strip(' ,')!r}")
    return errors


def scan_names(rel: str, text: str, custdev_names):
    low = text.lower()
    hits = sorted({n for n in custdev_names if n.lower() in low})
    if hits:
        return [f"{rel}: contains {len(hits)} real custdev respondent name(s) - must be removed"]
    return []


def main():
    errors = []
    custdev_names = load_custdev_names()
    if custdev_names is None:
        print("SKIP name-check (no private list)")

    scanned = 0
    for rel in tracked_files(ROOT):
        fpath = ROOT / rel
        if not fpath.exists():
            continue  # deleted in the working tree, not yet committed
        try:
            text = fpath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        if rel not in SELF_EXEMPT:
            errors.extend(scan_text(rel, text))
        if custdev_names:
            errors.extend(scan_names(rel, text, custdev_names))

    for e in errors:
        print(f"FAIL {e}")
    print(f"\nTestimonials check: {scanned} file(s) scanned, {len(errors)} failure(s) (no testimonials may be published)")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
