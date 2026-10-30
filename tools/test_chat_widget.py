"""Static guards for the ChatKit widget (assets/chat.js). Run: python3 tools/test_chat_widget.py"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_aeo as ca  # noqa: E402

ROOT = ca.ROOT
js = (ROOT / "assets/chat.js").read_text(encoding="utf-8")
FORBIDDEN = [r"2[- ]hour", r"2-годин", r"\bFranke\b", r"\bWMF\b", r"retro", r"ретро", r"Viber", r"\bUSD\b", r"\bEUR\b",
             r"\$\d", r"₴", r"грн", r"\bUAH\b", r"specialty", r"Q-grader", r"Bellissima.{0,40}roaster"]
problems = [f"chat.js matches forbidden /{p}/" for p in FORBIDDEN if re.search(p, js, re.I)]
if "consent" not in js or "cb.checked" not in js:
    problems.append("consent gate missing")
if "submitChat" not in js:
    problems.append("must deliver via animaLead.submitChat")
for p in ca.all_html_pages():
    t = p.read_text(encoding="utf-8", errors="ignore")
    if ca.is_indexable(t) and 'id="sticky-cta"' in t:
        if "assets/chat.js" not in t or "assets/chat.css" not in t:
            problems.append(f"{p.relative_to(ROOT)}: sticky bar present but chat widget missing")
        if "assets/lead.js" not in t:
            problems.append(f"{p.relative_to(ROOT)}: chat needs lead.js")
for p in problems:
    print("FAIL", p)
print("chat widget guards:", "FAIL" if problems else "OK")
sys.exit(1 if problems else 0)
