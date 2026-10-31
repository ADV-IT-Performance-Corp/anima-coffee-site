# AGENTS.md — aeo.animacoffee.com.ua

Facts, copy rules and forbidden claims live in `CLAUDE.md` (ground truth — read it first).
This file only says HOW to work. It applies to Claude Code, Codex and any other agent.

## Toolchain (upstream, do not fork)

- **gstack** — skills in `~/.claude/skills/gstack` (https://github.com/garrytan/gstack; its AGENTS.md lists the skills).
- **gbrain** — memory and search (https://github.com/garrytan/gbrain, `INSTALL_FOR_AGENTS.md`). Install only
  `bun install -g github:garrytan/gbrain#latest-stable`, then `gbrain setup claude-code`.
  Never `npm install -g gbrain` (an unrelated package).
- One-command setup on a Windows PC: `scripts/setup_claude_autonomy.ps1` in the ADV-Strategy-Core repo.
- Tool not installed (cloud session, fresh PC)? Say so in one line and continue with plain tools. Do not stall.

## Working rules

1. **Recall first.** Before non-trivial work run `gbrain query "<topic>"` (or the `mcp__gbrain__query` tool). Prefer it to
   grep for "what did we decide / where is X". Grep stays right for exact strings.
2. **Use gstack skills, do not hand-roll:** `/investigate` for bugs, `/review` before merge, `/qa` or `/browse` to check the
   live page, `/ship` to open the PR, `/land-and-deploy` to merge and verify, `/cso` for security, `/context-save` at the end.
3. **Verify before claiming done:** render the page (`/browse` or Playwright), confirm JSON-LD parses, keep `llms.txt` and
   `sitemap.xml` consistent, and grep the diff for the forbidden claims listed in `CLAUDE.md`.
4. **Do not ask permission for routine work** (git, gh, node, python, file edits, tests). Ask only about paid runs, key
   rotation, anything in Anima's GCP, or missing access.
5. **Merge = deploy** (GitHub Pages from `main`). Work on a `claude/*` branch, open a PR, merge after local checks pass.
   Never push to `main`, never force-push, never read `.env` or secrets.
6. Save durable facts to gbrain (the `remember` tool) when you learn them.
