# Beautify

Turn messy **deobfuscated** Roblox / Luau into clean, readable source.

Built for output from Luraph, IronBrew, generic VM lifts, and Discord deobf bots — strip tool junk, kill `tbl4` / `Arg4` / `_l173` names, keep real behaviour.

## Quick start (AI)

1. Open [`AI_PROMPT.md`](./AI_PROMPT.md).
2. Copy the full prompt into ChatGPT / Claude / Grok / Cursor.
3. Paste your deobfuscated `.lua` / `.luau` under it.
4. Get clean Roblox-style Luau back.

That path is the main product. The Python CLI is optional automation for the mechanical steps.

## Quick start (CLI)

```bash
python3 scripts/beautify.py input.lua -o output.lua
python3 scripts/beautify.py input.lua --aggressive -o output.lua
```

What the CLI does:

- strips deobfuscator / Luraph tool banners
- removes obvious pure junk statements
- renames common garbage identifiers (`v1`, `tbl2`, `Arg3`, `_l10`, …) to stable readable locals
- normalizes blank lines and light indentation

What the CLI does **not** do (use the AI prompt for these):

- deep semantic renames (`v12` → `humanoid` from context)
- control-flow redesign
- recovering missing logic from traces

## Layout

```
AI_PROMPT.md          ← paste this into any AI (primary workflow)
README.md
rules/
  naming.md           ← rename conventions
  strip_list.md       ← what to delete vs keep
scripts/
  beautify.py         ← mechanical cleaner
examples/
  before.lua
  after.lua
```

## Tips for best results

1. Run **CLI first**, then **AI prompt** on the result.
2. If the file is only `-- N statements recorded` / `DescendantAdded` probes, it is **not source** — do not force a fake script.
3. Keep executor dumps and real lifted bodies; do not mix in harness-only fingerprints as gameplay.
4. After AI rename, skim remotes and `GetService` names — those are the highest-value reads.

## For Discord / deobf bots

After every successful deobfuscation:

1. Pipe through `scripts/beautify.py`.
2. Optionally run the AI prompt for semantic names.
3. Ship the cleaned file to the user — never ship raw `tbl4` soup when avoidable.

## License

MIT — use in bots, tools, and private pipelines.
