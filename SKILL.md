---
name: beautify
description: Clean, semantically rename, and format already-deobfuscated Roblox Luau while preserving source behavior and reporting incomplete recovery.
license: MIT
metadata:
  version: "5.0"
  focus: roblox-luau-semantic-cleanup
---

# Beautify

Beautify turns recovered Roblox / Luau into readable source. It does not reverse a VM, invent missing logic, or guarantee runtime correctness.

## Workflow

```bash
python3 scripts/beautify.py input.lua -o clean.lua --report --formatter auto
```

Install StyLua for full Luau syntax-aware formatting:

```bash
pip install git+https://github.com/JohnnyMorganz/StyLua@v2.6.0
```

Use `--formatter auto` to prefer StyLua and fall back on malformed input, `--formatter stylua` to require parser validation, or `--formatter fallback` for best-effort formatting only.

## Whole-file semantic renaming

Do not stop after replacing a few obvious names. Process the entire source file from top to bottom:

1. Build a lexical binding map for locals, local functions, function parameters, and loop variables. Resolve each use to its declaration, so shadowed names are handled independently.
2. Keep meaningful source names. Identify both obfuscator names (`v12`, `tbl4`, `Arg2`, `_l173`, `fn3`) and weak names left by earlier Beautify passes (`handleEvent`, `sendRemoteEvent`, `value12`, `numericValue2`).
3. Name each local function from its complete body and nearby API usage. Look for the job it performs, not just the first API call. Examples: character refresh, player lookup, quest tracking, spectating, flight start/stop, raid management, UI updates, and task lifecycle.
4. Name callback parameters from the signal or callback role (`CharacterAdded` -> `character`, `InputBegan` -> `input`, `OnClientEvent` -> `action` / `payload`) and refine them from properties used in the body.
5. Name temporaries from their initializer, later assignments, constructors, member access, and surrounding function context. Examples: `Instance.new("BodyVelocity")` -> `bodyVelocity`; `FindFirstChildOfClass("Humanoid")` -> `humanoid`; a lookup in `raidDefinitions` -> `raidDefinition`.
6. Prefer action + target names for functions (`findLiveEntityByPrefix`, `startFlight`, `autoUseChestItems`) and role + type names for values (`targetPlayerName`, `rootPart`, `missionTask`).
7. Make replacements unique and avoid reserved words or collisions. Never rename member names after `.` or `:`, table keys, strings, comments, or unrelated scopes.
8. When the evidence is weak, use a neutral but readable fallback such as `localValue`, `item`, `state`, or `argument`. Do not guess names for unbound globals or missing upvalues.

Re-running Beautify should improve its own generic intermediate names, not leave `handleEvent` or `value12` as the final result when contextual evidence is available.

## Formatting

- Use StyLua's Luau parser/printer for complete-file formatting when available.
- Format statements, multiline expressions, tables, callbacks, method chains, operators, and control blocks consistently.
- Reuse an already-declared service local when it is lexically in scope. For example, after declaring `ReplicatedStorage`, use it instead of repeating `game:GetService("ReplicatedStorage")`.
- Keep the source order. Do not reorganize functions or callbacks if doing so could alter initialization order.
- If the input is malformed, use the fallback formatter and report the limitations. Do not claim that fallback output is parser-validated.

## Safe junk removal

Remove only code that is confidently inert:

- Recognized deobfuscator banners and metadata comments.
- Empty `do end` padding.
- Standalone pure constant expressions, such as `type(123)` or `bit32.bxor(12, 3)`.
- An unused generated local whose initializer is only a scalar literal or a literal-only table.

Keep calls with possible side effects, including `pcall`, `task.spawn`, remote calls, property writes, indexing through dynamic objects, and function calls inside `table.pack`. Keep unknown statements. Never delete code just because it looks unusual or contains a generated-looking token.

## Recovery diagnostics

- Report unmatched `end` / `until` tokens.
- Report unbound generated-looking identifiers without automatically renaming them; they may be globals or missing VM upvalues.
- Preserve explicit devirtualization markers such as `devirt: value ...`.
- If a sample is incomplete, say it is formatted partial output, not recovered source.

## Validation

```bash
python3 -m unittest discover -s tests -v
```

CI also runs StyLua against the example files. For real inputs, keep the original file and inspect the `--report` output, especially `remaining_garbage`, `unresolved_generated_identifiers`, `removed_junk_statements`, and parser diagnostics.

## Repository integration

After a deobfuscator succeeds, a bot may run Beautify before delivering the recovered Lua. Attach the whole output file for large results. If Beautify fails, deliver the original deobfuscator output when possible. Never turn a behavior trace or malformed partial result into a claimed successful deobfuscation.
