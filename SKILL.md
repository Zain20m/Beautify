---
name: beautify
description: Clean deobfuscated Roblox Luau into readable source. Strip Luraph/deobf junk, kill v1 tbl4 Arg4 _l173 names, expand minified lines, rename from GetService LocalPlayer WaitForChild usage. Use when the user says beautify, clean deobfuscated, readable lua, rename tbl/Arg/v locals, or post-process Luraph/IronBrew/Discord deobf output.
license: MIT
metadata:
  version: "2.0"
  focus: roblox-luau-deobf-cleanup
---

# Beautify

Turn messy **deobfuscated** Roblox / Luau into clean, readable scripts. Do not invent game logic.

## When to use

- After Luraph / IronBrew / generic VM deobfuscation
- File full of `v1`, `tbl4`, `Arg3`, `_l173`, `fn2`
- Minified one-line walls of locals
- Tool banners (`Deobfuscated by`, `statements recorded`, `BEHAVIOUR TRACE ONLY`)

## Workflow

1. If input is **only** anti-tamper probes / behaviour trace (DescendantAdded spam + `math_floor_precision`, no real payload), say so and stop. Do not fake a script.
2. Prefer running `scripts/beautify.py` first for mechanical cleanup.
3. Then apply the semantic pass in this skill (or paste `AI_PROMPT.md` into an AI) for human names.

```bash
python3 scripts/beautify.py input.lua -o clean.lua
```

## Mechanical rules (CLI + agent)

**Always strip**

- Deobfuscator banners and status comments
- Pure junk statements (`bit32.*` on constants, `type(123)`, empty `do end`)

**Always expand**

- Minified `;local` / `;function` chains onto separate lines
- Indent with 4 spaces using simple keyword depth

**Rename (mandatory on full beautify)**

| Pattern | Prefer |
|---------|--------|
| `game:GetService("Players")` binding | `Players` (same for other services) |
| `*.LocalPlayer` | `localPlayer` |
| `WaitForChild("Remotes")` etc. | camelCase / known map (`remotes`, `hitRemote`, `rootPart`) |
| Function body uses FireServer | `fireRemote` / better from context |
| Function body uses Humanoid + root | `getHumanoidAndRoot` / `setupCharacter` |
| `:Connect` result local | `characterAddedConn`, `inputBeganConn`, ... |
| Leftover `v#` `tbl#` `Arg#` `_l#` | neutral `valueN` / `dataN` / `paramN` / `nodeN` — never leave garbage |

## Agent semantic pass (after CLI)

Walk top to bottom:

1. Group services at top, then state, then helpers, then connections.
2. Rename **every** remaining garbage ident from usage — not just three.
3. Prefer `local function name()` forms.
4. Keep `pcall` / `task.spawn` / remotes / property writes.
5. Self-check zero `tbl#` / `Arg#` / `_l#` / bare `v#` left.

Full AI paste prompt lives in `AI_PROMPT.md`. Extreme teaching pair: `examples/before_extreme.lua` → `examples/after_extreme.lua`.

## Hard limits

- Never invent missing logic or recover source from a probe-only trace.
- Never claim behaviour changed for the better without preserving semantics.
- When unsure whether a statement is junk, keep it.

## Repo layout

- `scripts/beautify.py` — default aggressive + semantic mechanical pass
- `AI_PROMPT.md` — copy into any AI for full rewrite
- `rules/naming.md`, `rules/strip_list.md`
- `examples/` — medium + extreme before/after

## Output validation

- Check the actual deobfuscated samples, not just a hand-picked example. Include different obfuscator versions and difficult outputs where available.
- Separate deobfuscation failures from readability problems. Beautify can clean recovered Luau, but it cannot reconstruct source that the deobfuscator failed to recover.
- Compare the script before and after cleanup. Preserve behavior, side effects, control flow, and all statements whose purpose is uncertain.
- Test changes against the sample set and check for regressions in other supported versions. Keep fixes focused; do not rewrite unrelated engines or add unnecessary features.
- If an input is incomplete or only a behavior trace, clearly label that limitation instead of presenting it as recovered source.

## Automatic Discord post-deobfuscation cleanup

When this skill is integrated into a Discord deobfuscation bot or workflow, run Beautify automatically after a deobfuscation engine successfully produces Lua output and before sending the result to the user.

1. Pass the completed deobfuscated Lua output through the Beautify workflow.
2. Send the cleaned result as the normal Discord result, using the existing preview format where applicable.
3. Attach the complete cleaned Lua file when the output is too large for a Discord message.
4. If beautification fails, preserve and deliver the original deobfuscated output when possible, and clearly indicate that cleanup failed. Do not silently discard successful deobfuscation output.
5. If the engine only produced a behavior trace, anti-tamper probes, or incomplete output, do not present it as a successfully recovered script.
6. Keep this automatic cleanup optional for non-Discord integrations, and do not change the underlying deobfuscation engine or recovered script behavior.

This section describes the integration behavior. The bot or application must actually call the Beautify script/module; adding this instruction alone does not implement the integration.


## Luraph bootstrap and anti-tamper cleanup

Clean recognizable Luraph-generated probe scaffolding from the beginning of successfully recovered output. Use structure-aware matching rather than deleting an arbitrary number of lines.

### Remove generated preamble

- Look for the characteristic generated `Instance.new("Path2D")` probe near the beginning of the file. Treat it as a strong signature only when it appears as part of the expected preamble structure.
- Starting at the first non-comment, non-blank statement, remove only the contiguous sequence of recognized generated probe statements.
- Recognize generated `ScreenGui` / `Frame` creation and layout, `Path2D` setup and calls, `ScreenGui:Destroy()`, generated connection disconnects, numeric-name `Folder` setup and `WaitForChild` checks, empty event callbacks for common instance events, and empty `task.spawn` / `task.defer` / `task.delay` callbacks.
- Stop at the first statement that does not match a known probe pattern. Never jump over an unknown statement and continue deleting later code.
- Preserve service bindings from the removed preamble only when the remaining script actually references them.
- Remove generated attribution, promotional links, status comments, support-ticket text, and debug-library notices when they are comments or other clearly non-functional boilerplate.
- Do not delete code merely because it mentions `Path2D`, `ScreenGui`, events, task scheduling, debugging, URLs, or Luraph.

### Handle anti-tamper probes carefully

- Prefer explicit deobfuscator trap-attribution metadata when available. If a specific generated probe function is identified, remove only that probe from the final recovered source.
- When testing a suspected trap, compare execution with and without that specific function. If skipping it causes the script to stop earlier, treat it as a possible script-owned crash, licensing, or integrity check and retain the original behavior.
- Remove generated trace markers and probe-only annotations from the normal recovered-source output.
- Do not blindly remove user-authored debug logic, integrity checks, licensing, authentication, or environment checks. Only remove code confidently identified as generated anti-tamper/environment probing.
- If the output contains only probes, or execution failed before reaching the payload, label it as diagnostic/incomplete. Never present a probe trace as recovered source.

### Keep version-specific cleanup distinct

- For trace-style output, remove known generated markers and annotations, then trim the recognized preamble using the structural rules above.
- For lifted source, run formatting and semantic cleanup separately. Validate the cleaned file with a Luau parser when available.
- Keep a copy of the original output. If cleanup causes a syntax or structural validation failure, restore the original instead of delivering damaged code.
- Do not assume a formatter alone removes the Luraph preamble or anti-tamper scaffolding.
