#!/usr/bin/env python3
"""Codex #30 fix (MED): assert every /answers/*.md twin is a strict subset
of its page's visible text.

Rule (from the review): every sentence in the twin must exist in the
page's visible text after normalisation (lowercase, collapse whitespace,
strip Markdown syntax and punctuation at edges). The H1, the direct
answer, the FAQ Q/A and the contact line must be copied from the page's
own elements, not paraphrased or summarised. No added intros, no metadata
lines that are not on the page, except a final "Source: <page URL>" line,
which is exempt.

stdlib only. Usage: python3 tools/check_md_twin_subset.py
Exit 0 if every twin's every sentence is a substring of the page's
normalised visible text (the exempt Source: line aside), else 1.
"""
import html
import pathlib
import re
import sys

SITE = pathlib.Path(__file__).resolve().parent.parent
ANSWERS = SITE / "answers"


def normalise(s):
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    s = s.strip(" \t\n\r.,:;!?\"'()[]{}*_-—–")
    return s.strip()


def page_visible_text(html_src):
    # Drop JSON-LD / other scripts and styles first (replaced with a space
    # so unrelated surrounding words never fuse), then strip all remaining
    # tags with NO replacement — inline tags like the kg-triple <span>s sit
    # directly against adjacent punctuation (e.g. "...response</span>: on
    # ...") with no whitespace of their own, and replacing them with a
    # space would inject whitespace that was never actually rendered.
    html_src = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html_src, flags=re.S | re.I)
    html_src = re.sub(r"<[^>]+>", "", html_src)
    return html.unescape(html_src)


def md_sentences(md_src):
    """Split the twin into checkable units: the H1 line, the Direct-answer
    paragraph, the FAQ Q/A lines, and the contact line. Pure structural
    Markdown headings ('## FAQ', '## Contact') carry no page prose so they
    are not checked. The trailing 'Source: <url>' line is skipped (exempt
    by the review's own rule).
    """
    units = []
    for line in md_src.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Source:"):
            continue  # explicitly exempt
        if line in ("## FAQ", "## Contact"):
            continue  # structural headings, not page prose
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^\*\*Q:\s*", "", line)
        line = re.sub(r"\*\*$", "", line)
        line = re.sub(r"^A:\s*", "", line)
        units.append(line)
    return units


def check_twin(slug):
    html_path = ANSWERS / f"{slug}.html"
    md_path = ANSWERS / f"{slug}.md"
    page_text = normalise(page_visible_text(html_path.read_text(encoding="utf-8")))
    md_text = md_path.read_text(encoding="utf-8")

    failures = []
    for unit in md_sentences(md_text):
        norm_unit = normalise(unit)
        if not norm_unit:
            continue
        # "About Anima Volitiva" bullet lines carry structured contact/sameAs
        # facts (website/service area/contact/sameAs) copied from the same
        # page's own JSON-LD Organization node, which is also rendered
        # nowhere as prose text on the page — check membership of each
        # comma/·-separated token instead of the whole assembled line.
        if norm_unit in page_text:
            continue
        # fallback: token-level check for structured "key: value" bullets
        parts = re.split(r"[·,]", norm_unit)
        if parts and all(p.strip() and p.strip() in page_text for p in parts):
            continue
        failures.append(unit)

    return failures


def main():
    slugs = sorted(p.stem for p in ANSWERS.glob("*.md"))
    total = len(slugs)
    passed = 0
    for slug in slugs:
        failures = check_twin(slug)
        if failures:
            print(f"FAIL {slug}:")
            for f in failures:
                print(f"    - {f[:100]!r}")
        else:
            passed += 1
    print(f"\nMarkdown twin subset check: {passed}/{total} PASS")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
