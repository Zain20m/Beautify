---
name: beautify
description: Clean already-deobfuscated Roblox Luau using scope-aware renaming, conservative junk removal, formatting, and structural diagnostics.
license: MIT
metadata:
  version: "3.0"
  focus: roblox-luau-deobf-cleanup
---

# Beautify

Beautify makes recovered Roblox / Luau easier to read. It does not reverse a VM, invent missing logic, or certify that a deobfuscated file runs.

## When to use

- After a deobfuscator has produced Lua / Luau source.
- Files containing generated names such as `v1`, `tbl4`, `Arg3`, `_l173`, `fn2`, or `t_1`.
- Semicolon-packed or inline control-flow statements.
- Decompiled output with tool banners or obvious standalone noise.

Do not present a probe-only trace as recovered source.

## Workflow

Run the mechanical beautifier first:

```bash
python3 scripts/beautify.py input.lua -o clean.lua --report
```

Then inspect the report and output. Keep the original deobfuscator output unchanged as a fallback.

## What the engine does

1. Tokenizes source while distinguishing identifiers, strings, long-bracket strings, and comments.
2. Tracks approximate lexical scopes for locals, function parameters, and loop variables.
3. Renames generated identifiers by binding, so shadowed variables are not globally replaced together.
4. Uses nearby API and function context to suggest names such as `Players`, `localPlayer`, `humanoid`, `rootPart`, `inputBeganConn`, or `activateNpcPrompts`.
5. Infers known Roblox service aliases only when a bare service identifier is otherwise unbound.
6. Expands semicolon chains and common inline blocks, normalizes assignment / comma spacing, and applies indentation.
7. Removes only narrowly recognized tool banners, pure constant-expression noise, and empty `do end` padding.
8. Reports unmatched `end` / `until` tokens and remaining generated-name patterns.

The scope tracker is intentionally conservative and is not a complete Luau AST or compiler.

## Naming rules

- Preserve meaningful names already present.
- Rename only weak/generated local bindings, parameters, and loop variables.
- Never rename text inside strings or comments.
- Never rename member names after `.` or `:`, or literal table keys.
- Prefer clear camelCase locals, event names ending in `Conn`, and known service names.
- When meaning is unclear, use neutral names such as `value`, `item`, `state`, or `argument`.
- Make generated replacements unique within the file to avoid accidental collisions.

## Cleanup safety

Delete a statement only when it is confidently a recognized deobfuscator banner or a standalone expression known to be pure and constant. When unsure, keep it.

Do not strip arbitrary `pcall`, remote calls, task scheduling, property assignments, authentication, integrity checks, or licensing logic. Do not reorder services, callbacks, or user statements because ordering may matter.

Never delete unmatched block tokens to make the output look valid. Report them and preserve the source fragment. If the deobfuscator emitted an expression marker such as `devirt: value ...`, keep it visible as an unresolved recovery artifact.

## Validation

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

For a user sample:

1. Keep the original file.
2. Run Beautify with `--report`.
3. Check string and comment preservation.
4. Review all structural diagnostics and devirtualization markers.
5. Use a Luau parser / formatter separately when one is available.
6. Do not claim successful syntax validation unless a parser actually accepted the file.

## Discord / bot integration

When integrated into a deobfuscation bot, run Beautify after the engine successfully produces Lua output and before sending the result. Attach the complete cleaned file for large outputs. If beautification fails, deliver the original recovered output where possible and explain that cleanup failed. Keep this optional for non-Discord integrations.

If the engine only produced anti-tamper probes, behavior traces, or incomplete output, label it as diagnostic / incomplete rather than recovered source.

## Luraph / anti-tamper handling

- Strip only explicit deobfuscator banners and known metadata comments.
- Do not delete code merely because it mentions `Path2D`, `ScreenGui`, events, task scheduling, URLs, debugging, or Luraph.
- Do not blindly remove script-owned integrity, licensing, authentication, or environment checks.
- Treat version-specific generated preambles as a separate, evidence-based cleanup step. Stop at the first unknown statement; never skip over it and continue deleting later code.
- Preserve the input if a cleanup step causes structural validation to worsen.

## Repository layout

- `scripts/beautify.py`: CLI engine
- `tests/test_beautify.py`: regression suite
- `AI_PROMPT.md`: prompt for a deeper assisted rewrite
- `rules/`: naming and strip guidance
- `examples/`: before / after examples
