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

Follow the behavior already used by DailyDeobf's Luraph pipeline. This is more than deleting a few banner lines.

- Remove the Luraph/deobfuscator preamble by default so the delivered file starts with recovered script logic. Keep-preamble behavior should remain an explicit diagnostic option, not the normal Discord result.
- Remove known generated notices and promotional text, including Luraph links, attribution banners, and messages such as "The debug library is required on Luau platforms. Please open a support ticket."
- Respect the engine's anti-tamper isolation and trap-attribution results. When the engine identifies an anti-tamper trap function and successfully reruns without that trap, exclude that proven probe-only function from the final recovered payload.
- Remove only Luraph environment/anti-tamper probe code that the engine has identified as generated or proven unrelated to the payload. Do not use broad text matching or delete code just because it references `debug`, `Path2D`, `ChildAdded`, `DescendantRemoving`, `HttpService`, or other Roblox APIs.
- Preserve actual payload code, required initialization, runtime dependencies, and user-authored checks. Some environment values can participate in Luraph's decryption key, so do not strip probes before the engine has finished recovery.
- If the result is only a probe/anti-tamper shell or an environment-compatibility failure, label it as incomplete/probe-only. Do not pretend it is the recovered script.
- Keep the cleanup after successful deobfuscation and before the Discord result is sent. If cleanup cannot confidently distinguish generated probes from payload logic, keep the code and report the limitation.
