---
name: beautify
description: AST-aware whole-file semantic renaming, formatting, and conservative cleanup for already-deobfuscated Roblox Luau.
license: MIT
metadata:
  version: "6.2"
  focus: roblox-luau-ast-cleanup
---

# Beautify

Beautify makes recovered Roblox / Luau readable while preserving source behavior. It is not a VM devirtualizer and must not invent missing code.

## Workflow

```bash
python3 -m pip install -r requirements.txt
python3 scripts/beautify.py input.lua -o clean.lua --report --formatter auto
```

- `--formatter auto`: use StyLua when installed; otherwise use fallback formatting.
- `--formatter stylua`: require StyLua and parser validation.
- `--formatter fallback`: use conservative best-effort formatting for damaged output.

## AST-backed scope analysis

When `tree-sitter` and `tree-sitter-luau` are available, `scripts/luau_ast.py` builds the binding model from the Luau syntax tree:

1. Resolve locals and local functions to their declarations.
2. Track function parameters, numeric/generic for-loop bindings, nested block scopes, and repeat-loop scopes.
3. Resolve references against the nearest active binding, preserving shadowed variables independently.
4. Exclude property/method names, table keys, type annotations, and declaration identifiers from reference renaming.
5. Collect function-local AST facts: calls, member names, strings, and control constructs.
6. Fall back to the token scanner when the AST package is missing or the AST adapter fails.

Do not describe the fallback scanner as AST validation. The report identifies the active backend.

## Semantic naming

Process the complete file, not just visible or top-level names.

- Keep meaningful names as written.
- Recognize numbered generated locals such as `s68` alongside `v1`, `t_1`, and `fn2`.
- Rename generated and weak intermediate names by binding, not global string replacement.
- Score function-name candidates from AST call/member/string evidence and the complete function body. Prefer action + target names only when evidence supports the behavior.
- Infer parameters from event/callback roles and their own reference sites.
- Infer temporaries from constructors, initializers, assignments, property access, and local usage neighborhoods.
- Record confidence/evidence when a contextual name is selected.
- Use neutral readable names when evidence is weak.
- Never rename unbound identifiers, globals, property names, method names, strings, comments, or table keys.

## Partial recovery and missing upvalues

- Report AST syntax-error nodes with line numbers and short excerpts.
- Mark functions whose bodies overlap parser errors as partially recovered.
- Report unbound generated-looking references inside function bodies as possible missing upvalues or external globals.
- Recognize common upvalue placeholders such as `UPVALUE_3` and `upvalue3`.
- Keep `devirt:` markers visible.
- Never synthesize placeholder assignments, guessed constants, or fake function bodies.

## Conservative cleanup

Remove only explicit tool banners, empty `do end` padding, standalone pure constant expressions, and unused generated locals with literal-only initializers.

Preserve calls with side effects, dynamic indexing, remotes, task scheduling, error handling, property writes, and unknown expressions. Preserve statement order.

## Formatting

Use StyLua's Luau parser/printer for valid source. Format expressions, callbacks, table constructors, method chains, operators, and control-flow blocks. Use the fallback formatter only for damaged or incomplete output and report that it was not parser-validated.

## Validation

```bash
python3 -m unittest discover -s tests -v
```

CI runs the regression suite, deterministic generated-input invariants, and example smoke tests on Python 3.10, 3.11, and 3.12.

The fixture corpus contains representative synthetic patterns for register-style output, string-pool/closures, typed Luau, and partial lifter output. Generated tests exercise nested scopes and output stability, but neither synthetic fixtures nor generated cases establish universal compatibility with every real-world obfuscator. Add sanitized real-world failures as regression fixtures.

## Output expectations

Return the complete source file. Include parser backend, rename/cleanup counts, partial-function details, unresolved-upvalue information, and devirtualization warnings when requested. Never claim that a partial dump is fully recovered.
