#!/usr/bin/env python3
"""W3a.5 — verify testimonials integrity across the site.

Checks, over every `<figure class="testi">` on index.html, ua/index.html,
about.html and ua/about.html:

1. The original-language (Ukrainian) quote text — whether it's the page's
   primary blockquote (UA pages) or the one inside a `<details class="t-orig">`
   toggle (EN pages, "Translated from Ukrainian" pattern) — exists verbatim
   in `delivery/testimonials-provenance.md`.
2. No quote text (Ukrainian or English) or figcaption attribution contains a
   forbidden-claim signature (mirrors tools/check_webmcp.py's list).
3. No figcaption tagged as sourced from the 2025 customer-development
   interviews (marked "2025 customer survey" / "опитування клієнтів, 2025")
   contains a real interviewee's surname from that corpus — the brief
   requires anonymous-only attribution (role + business type + city) for
   interview-derived quotes.

Separately, a repo-wide name check (4) scans every tracked text file the site
serves or ships (`*.html`, `*.md`, `llms.txt`, `assets/*.js`, `delivery/*`,
`tools/*`, `tests/*`) for any real custdev-interview respondent name. This
repo must never contain a real interviewee name in any tracked file, not just
the testimonial pages. The name list itself must never be committed: it is
loaded at run time from `$ANIMA_CUSTDEV_NAMES_FILE` (default
`~/work/anima-private/custdev-names.txt`, one name/transliteration per line,
private, not part of this repo). If that file is absent, the name check
prints a SKIP line and passes — all other checks still run.

stdlib only. Usage: python3 tools/check_testimonials.py
Exit 0 if everything passes, else 1 (prints every failure found).
"""
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROVENANCE = ROOT / "delivery" / "testimonials-provenance.md"

PAGES = [
    ROOT / "index.html",
    ROOT / "ua" / "index.html",
    ROOT / "about.html",
    ROOT / "ua" / "about.html",
]

DEFAULT_NAMES_FILE = pathlib.Path("~/work/anima-private/custdev-names.txt").expanduser()

# Files the name check scans: every tracked text file the site serves or
# ships. Matched against `git ls-files` output (tracked files only).
NAME_SCAN_PATTERNS = (
    re.compile(r"\.html$"),
    re.compile(r"\.md$"),
    re.compile(r"^llms\.txt$"),
    re.compile(r"^assets/.*\.js$"),
    re.compile(r"^delivery/"),
    re.compile(r"^tools/"),
    re.compile(r"^tests/"),
)

# Mirrors tools/check_webmcp.py's FORBIDDEN_SIGNATURES, scoped to strings
# that could plausibly leak into customer-quote copy.
FORBIDDEN_SIGNATURES = [
    "free first month",
    "first month free",
    "перший місяць оренди безкоштовно",
    "retro-bonus",
    "ретро-бонус",
    "1,300+",
    "1300+",
    "1,500+",
    "94%",
    "2-hour response",
    "2 hour response",
    "реагування 2 години",
    "2-hour sla",
    "2-hour emergency",
    "flat-rate monthly",
    "flat rate monthly",
    "swiss-grade",
    "swiss machines",
    "franke",
    "wmf",
]

INTERVIEW_MARKERS = ("2025 customer survey", "опитування клієнтів, 2025")

FIGURE_RE = re.compile(r'<figure class="testi">(.*?)</figure>', re.S)
FIGCAPTION_RE = re.compile(r"<figcaption>(.*?)</figcaption>", re.S)
UK_QUOTE_RE = re.compile(r'<blockquote lang="uk"><p>(.*?)</p></blockquote>', re.S)
EN_QUOTE_RE = re.compile(r'<blockquote lang="en"><p>(.*?)</p></blockquote>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(s: str) -> str:
    return TAG_RE.sub("", s).strip()


def forbidden_hits(text: str):
    low = text.lower()
    return [s for s in FORBIDDEN_SIGNATURES if s.lower() in low]


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


def scan_page(rel: str, text: str, provenance_text: str, custdev_names=None):
    """Check one page's testimonial figures. Returns (errors, figures_checked).

    Pure function of its inputs (no filesystem access) so it can be unit
    tested directly against synthetic HTML fixtures — see
    tools/test_check_testimonials.py. custdev_names is None to skip the
    interview-name check (no private list available) or a list of names.
    """
    errors = []
    figures_checked = 0

    page_figures = FIGURE_RE.findall(text)
    if not page_figures:
        errors.append(f"{rel}: no <figure class=\"testi\"> testimonials found on this page")

    for fig_html in page_figures:
        figures_checked += 1

        caption_m = FIGCAPTION_RE.search(fig_html)
        caption = strip_tags(caption_m.group(1)) if caption_m else ""

        uk_quotes = UK_QUOTE_RE.findall(fig_html)
        en_quotes = EN_QUOTE_RE.findall(fig_html)

        if not uk_quotes:
            errors.append(f"{rel}: testimonial has no Ukrainian (original-language) quote: {caption}")
        else:
            uk_quote = strip_tags(uk_quotes[0])
            if not uk_quote:
                errors.append(f"{rel}: testimonial has an empty Ukrainian quote: {caption}")
            elif uk_quote not in provenance_text:
                errors.append(f"{rel}: quote not found verbatim in provenance file ({caption}): {uk_quote[:70]}...")
            hits = forbidden_hits(uk_quote)
            if hits:
                errors.append(f"{rel}: quote contains forbidden claim(s) {hits} ({caption})")

        for en_quote_html in en_quotes:
            en_quote = strip_tags(en_quote_html)
            if not en_quote:
                errors.append(f"{rel}: testimonial has an empty English quote: {caption}")
            hits = forbidden_hits(en_quote)
            if hits:
                errors.append(f"{rel}: EN translation contains forbidden claim(s) {hits} ({caption})")

        hits = forbidden_hits(caption)
        if hits:
            errors.append(f"{rel}: figcaption contains forbidden claim(s) {hits}: {caption}")

        if custdev_names and any(marker in caption for marker in INTERVIEW_MARKERS):
            haystack = " ".join([caption] + [strip_tags(q) for q in uk_quotes] + [strip_tags(q) for q in en_quotes]).lower()
            name_hits = [n for n in custdev_names if n.lower() in haystack]
            if name_hits:
                errors.append(f"{rel}: interview-derived quote carries a real interviewee name ({caption})")

    return errors, figures_checked


def tracked_files_for_name_scan(root: pathlib.Path):
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    files = []
    for rel in out.splitlines():
        rel = rel.strip()
        if rel and any(p.search(rel) for p in NAME_SCAN_PATTERNS):
            files.append(rel)
    return files


def scan_repo_for_names(root: pathlib.Path, custdev_names):
    """Scan every tracked text file the site serves or ships for a real
    custdev-interview respondent name. Returns a list of error strings.
    """
    errors = []
    for rel in tracked_files_for_name_scan(root):
        fpath = root / rel
        try:
            text = fpath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        low = text.lower()
        name_hits = sorted({n for n in custdev_names if n.lower() in low})
        if name_hits:
            errors.append(f"{rel}: contains {len(name_hits)} real custdev respondent name(s) — must be removed")
    return errors


def main():
    errors = []

    if not PROVENANCE.exists():
        print("FAIL delivery/testimonials-provenance.md is missing")
        sys.exit(1)
    provenance_text = PROVENANCE.read_text(encoding="utf-8")

    custdev_names = load_custdev_names()
    if custdev_names is None:
        print("SKIP name-check (no private list)")
    else:
        errors.extend(scan_repo_for_names(ROOT, custdev_names))

    figures_checked = 0
    for page in PAGES:
        if not page.exists():
            errors.append(f"{page.relative_to(ROOT).as_posix()}: expected page is missing")
            continue
        rel = page.relative_to(ROOT).as_posix()
        text = page.read_text(encoding="utf-8")

        page_errors, page_figures_checked = scan_page(rel, text, provenance_text, custdev_names)
        errors.extend(page_errors)
        figures_checked += page_figures_checked

    for e in errors:
        print(f"FAIL {e}")
    print(f"\nTestimonials check: {figures_checked} testimonial(s) scanned across {len(PAGES)} page(s), {len(errors)} failure(s)")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
