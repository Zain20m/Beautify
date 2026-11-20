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

Use DailyDeobf's Luraph cleanup as the concrete reference, especially `luraph-v15-engine/tidy.py` (`strip_preamble` / `preamble_plan`) and the trace cleanup in `luraph-v15.1-engine/src/tidy.js`.

### v15-style preamble removal

Do not just delete the first N lines. Detect the generated probe preamble by its structure:

- Require the Luraph-style `Instance.new("Path2D")` signature near the beginning (DailyDeobf checks the first 60 lines).
- Starting at the first non-comment, non-blank statement, remove only the contiguous sequence of recognized generated setup statements.
- Recognize the known setup patterns: generated `ScreenGui` / `Frame` creation and layout, `Path2D` setup and calls, `ScreenGui:Destroy()`, generated connection disconnects, numeric-name `Folder` setup and `WaitForChild` checks, empty event callbacks for common instance events, and empty `task.spawn` / `task.defer` / `task.delay` callbacks.
- Stop at the first statement that does not match the probe patterns. Do not skip over an unknown statement to keep deleting later code.
- Preserve `GetService` bindings from the preamble only when the remaining script actually references them.
- Keep real code after the probe sequence. Never remove a whole file merely because it contains `Path2D`, `ScreenGui`, event connections, or task scheduling.

### Anti-tamper handling

- Prefer the engine's trap attribution over guessing from source text. DailyDeobf instruments VM closures, records the triggered function ID, skips that specific function, and reruns.
- If skipping a triggered function makes execution stop earlier, treat it as a possible script-owned crash/license check and retain the earlier run. Do not strip it as an environment probe.
- Remove trace trigger markers and generated probe annotations from the delivered readable output.
- Do not blindly remove all debug, integrity, licensing, authentication, or environment-check code. Only remove the recognizable generated preamble or code explicitly identified by the deobfuscation engine as a probe.
- When the result is still only a probe trace or hits an environment-compatibility failure before payload execution, label it as diagnostic/incomplete rather than presenting it as recovered source.

### v15.1 implementation distinction

DailyDeobf's v15.1 `src/tidy.js` has a narrower trace cleanup: it removes generated `--@` markers and trace annotations, then trims a preamble when it sees the known `Path2D:GetTangentOnCurveArcLength` or `ScreenGui:Destroy()` marker near the top. The separate `scripts/luau-cleaner.js` used on a v15.1 lifted candidate is a formatter with syntax validation and raw-output restoration; it is not the same Luraph-specific preamble remover.

Beautify should apply its own safe, structure-aware cleanup to successful recovered source, not claim the existing v15.1 formatter already strips every Luraph probe.
