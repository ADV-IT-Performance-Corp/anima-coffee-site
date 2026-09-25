#!/usr/bin/env python3
"""Contract tests for tools/gen_okf_bundle.py — the OKF knowledge bundle
generator. Runs the real generator against an isolated tmp_path copy of the
real index.html/llms.txt (never the live working tree — repeated pytest
runs must not dirty the repo), then cross-checks every generated `resource`
URL against the REAL repo to confirm it traces to an actually-live page.

Usage: python3 -m pytest tools/test_gen_okf_bundle.py -v
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GEN_SCRIPT = REPO_ROOT / "tools" / "gen_okf_bundle.py"
BASE = "https://aeo.animacoffee.com.ua"
BUNDLE_LINE = f"- [OKF knowledge bundle]({BASE}/knowledge/index.md)"

REQUIRED_KEYS = {"type", "title", "description", "resource", "tags", "timestamp"}


def make_sandbox(tmp_path):
    """Copy only the inputs the generator reads into an isolated tree."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    shutil.copy(REPO_ROOT / "index.html", sandbox / "index.html")
    shutil.copy(REPO_ROOT / "llms.txt", sandbox / "llms.txt")
    return sandbox


def run_generator(root):
    result = subprocess.run(
        [sys.executable, str(GEN_SCRIPT), "--root", str(root)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    return result


def entity_pages(knowledge_dir):
    return sorted(
        p for p in knowledge_dir.glob("*.md") if p.name not in ("index.md", "log.md")
    )


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "missing YAML frontmatter block"
    fm = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.startswith((" ", "-")):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v.startswith('"') and v.endswith('"') and len(v) >= 2:
            v = v[1:-1]
        fm[k.strip()] = v
    return fm


def test_generator_produces_bundle_files(tmp_path):
    sandbox = make_sandbox(tmp_path)
    run_generator(sandbox)
    knowledge_dir = sandbox / "knowledge"
    assert (knowledge_dir / "index.md").exists()
    assert (knowledge_dir / "log.md").exists()
    pages = entity_pages(knowledge_dir)
    assert len(pages) >= 2, f"expected at least 2 entity pages, got {len(pages)}"


def test_entity_pages_have_required_frontmatter(tmp_path):
    sandbox = make_sandbox(tmp_path)
    run_generator(sandbox)
    pages = entity_pages(sandbox / "knowledge")
    assert pages, "no entity pages generated"
    for page in pages:
        text = page.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        missing = REQUIRED_KEYS - fm.keys()
        assert not missing, f"{page.name}: missing frontmatter keys {missing}"
        assert fm["resource"].startswith(f"{BASE}/"), (
            f"{page.name}: resource {fm['resource']!r} is not an absolute {BASE}/... URL"
        )


def test_entity_pages_trace_to_a_live_page(tmp_path):
    """The resource URL must map to a file that actually exists in the REAL
    repo (not the sandbox) — that's what "traces to a live page" means."""
    sandbox = make_sandbox(tmp_path)
    run_generator(sandbox)
    pages = entity_pages(sandbox / "knowledge")
    assert pages, "no entity pages generated"
    for page in pages:
        text = page.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        resource = fm["resource"]
        rel_path = resource[len(BASE):].lstrip("/")
        target = REPO_ROOT / rel_path
        assert target.exists(), (
            f"{page.name}: resource {resource!r} -> {target} does not exist in the repo"
        )


def test_llms_txt_has_bundle_link(tmp_path):
    sandbox = make_sandbox(tmp_path)
    run_generator(sandbox)
    content = (sandbox / "llms.txt").read_text(encoding="utf-8")
    assert BUNDLE_LINE in content


def test_llms_txt_edit_is_idempotent(tmp_path):
    sandbox = make_sandbox(tmp_path)
    run_generator(sandbox)
    first = (sandbox / "llms.txt").read_text(encoding="utf-8")
    run_generator(sandbox)
    second = (sandbox / "llms.txt").read_text(encoding="utf-8")
    assert first == second
    assert second.count(BUNDLE_LINE) == 1


def test_output_is_deterministic_across_runs(tmp_path):
    sandbox = make_sandbox(tmp_path)
    run_generator(sandbox)
    knowledge_dir = sandbox / "knowledge"
    pages_before = {p.name: p.read_bytes() for p in entity_pages(knowledge_dir)}
    index_before = (knowledge_dir / "index.md").read_bytes()

    run_generator(sandbox)
    pages_after = {p.name: p.read_bytes() for p in entity_pages(knowledge_dir)}
    index_after = (knowledge_dir / "index.md").read_bytes()

    assert pages_before == pages_after, "entity pages changed byte-for-byte across identical runs"
    assert index_before == index_after, "index.md changed byte-for-byte across identical runs"


def test_slugify_handles_type_lists_and_non_ascii():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import gen_okf_bundle as gen

    assert gen.type_label(["Organization", "LocalBusiness"]) == "Organization"
    assert gen.type_label("Organization") == "Organization"
    slug = gen.slugify("Кава")
    assert slug and re.fullmatch(r"[a-z0-9-]+", slug)
    assert gen.slugify(["Organization", "LocalBusiness"]) == "organization-localbusiness"


def test_yaml_str_escapes_newlines_and_quotes():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import gen_okf_bundle as gen

    out = gen.yaml_str('line one\nline "two"\ttabbed')
    assert "\n" not in out
    assert out == r'"line one\nline \"two\"\ttabbed"'


def test_live_repo_untouched_by_running_tests():
    """Guard against the exact defect the review caught: pytest runs must
    never dirty knowledge/log.md or any other file in the real repo."""
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", "knowledge/", "llms.txt"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert status.stdout.strip() == "", (
        f"running tests left the live repo dirty:\n{status.stdout}"
    )
