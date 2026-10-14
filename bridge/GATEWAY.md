# How to run commands (headless agents)

You cannot run arbitrary shell commands. Use the **gateway** with ONE fixed command (replace N with your agent number, e.g. `gemini-1`):

1. Write the file `bridge/gw/<agent>.json` (with your file-writing tool) containing ONE request.
2. From the project root run exactly: `python -I tools/gw.py <agent>`
3. The result is printed and also saved in `bridge/gw/<agent>.out`.

Requests (JSON):
- Verify your scope: `{"op":"check","prefixes":["core","network"]}` -> must end with `ERRORS in scope [...]: 0`
- Ask / report to the orchestrator: `{"op":"post","to":"claude","task":"T001","text":"short message"}`
- Read replies: `{"op":"inbox"}`
- Search code (regex, read-only): `{"op":"grep","pattern":"someRegex","path":"src","max":200}`
- Commit your work: `{"op":"commit","task":"T001","message":"ported core","paths":["src/main/java/..."]}`
  (only paths allowed by `commit_allow` in singularity.json are accepted)
- See your changes: `{"op":"diffstat"}`

Reading files, listing, searching and editing files: use your built-in file tools (no shell needed).
Everything else (build tools, git, other scripts) is not available to you - the orchestrator runs those.
