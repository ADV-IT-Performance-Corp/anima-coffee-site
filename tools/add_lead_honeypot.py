#!/usr/bin/env python3
"""DC-3 — idempotently add the lead-form honeypot input and the EN/UA consent
line to every `form.lead-form` on the site.

Safe to re-run: a file that already carries both markers is left untouched,
and each marker is added independently if only one is missing (so a partial
prior run still converges).

Usage:
    python3 tools/add_lead_honeypot.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

HP_MARK = 'name="company_url"'
CONSENT_MARK = 'class="lf-consent"'

SUBMIT_RE = re.compile(r'^([ \t]*)<button type="submit" class="btn btn-primary lf-submit">', re.M)
STATUS_RE = re.compile(r'^([ \t]*)<p class="lf-status" role="status" aria-live="polite"></p>', re.M)

EN_CONSENT = (
    "By submitting this form you agree to be contacted about your request and to our "
    '<a href="{href}">privacy policy</a>.'
)
UK_CONSENT = (
    "Надсилаючи форму, ви погоджуєтесь, що ми звʼяжемося з вами щодо запиту, та з нашою "
    '<a href="{href}">політикою конфіденційності</a>.'
)


def is_uk(rel_path: str) -> bool:
    return rel_path == "ua" or rel_path.startswith("ua/")


def privacy_href(rel_path: str) -> str:
    """Relative link to this locale's privacy.html, from rel_path's directory."""
    sub = rel_path[3:] if is_uk(rel_path) else rel_path
    depth = sub.count("/")
    return "../" * depth + "privacy.html"


def add_honeypot(text: str) -> tuple[str, bool]:
    if HP_MARK in text:
        return text, False

    def sub(m: re.Match) -> str:
        indent = m.group(1)
        return (
            f'{indent}<input type="text" name="company_url" class="lf-hp" '
            f'tabindex="-1" autocomplete="off" aria-hidden="true">\n'
            f'{indent}<button type="submit" class="btn btn-primary lf-submit">'
        )

    new_text, n = SUBMIT_RE.subn(sub, text)
    return (new_text, True) if n else (text, False)


def add_consent(text: str, rel_path: str) -> tuple[str, bool]:
    if CONSENT_MARK in text:
        return text, False

    href = privacy_href(rel_path)
    line = (UK_CONSENT if is_uk(rel_path) else EN_CONSENT).format(href=href)

    def sub(m: re.Match) -> str:
        indent = m.group(1)
        return (
            f'{indent}<p class="lf-consent">{line}</p>\n'
            f'{indent}<p class="lf-status" role="status" aria-live="polite"></p>'
        )

    new_text, n = STATUS_RE.subn(sub, text)
    return (new_text, True) if n else (text, False)


def process(path: pathlib.Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    if 'class="lead-form"' not in text:
        return False

    text, hp_changed = add_honeypot(text)
    text, consent_changed = add_consent(text, rel)

    if hp_changed or consent_changed:
        path.write_text(text, encoding="utf-8")
    return hp_changed or consent_changed


def main() -> None:
    touched = 0
    for path in sorted(ROOT.rglob("*.html")):
        if ".git" in path.parts:
            continue
        if process(path):
            touched += 1
    print(f"updated {touched} file(s)")


if __name__ == "__main__":
    main()
