# Beautify

Clean, semantically rename, and format already-deobfuscated Roblox / Luau.

Beautify uses a Tree-sitter Luau syntax tree for lexical-scope analysis when the AST dependencies are installed. It resolves local declarations, local functions, parameters, loop variables, nested blocks, and shadowed names by their bindings. It scores function-name suggestions from AST call/member/string evidence, formats valid source through StyLua, and retains a conservative fallback for incomplete decompiler output.

## What it does

- AST-backed binding resolution for locals, local functions, callback parameters, generic/numeric loop variables, nested blocks, and repeat scopes.
- Contextual naming for obfuscator names and earlier Beautify placeholders, using function bodies, AST calls/members, constructors, reference sites, and callback context.
- Confidence/evidence fields for semantic name suggestions, with neutral fallbacks when evidence is weak.
- Service alias reuse when the original local is visible and not shadowed.
- Safe junk removal limited to known banners, empty padding, standalone pure constants, and unused generated locals initialized only by literals.
- Whole-file formatting via StyLua for valid Luau; best-effort formatting for malformed or partially recovered output.
- Partial-function, syntax-node, unresolved generated-name, possible missing-upvalue/external-global, and devirtualization-marker diagnostics.

## Install

Install the AST and formatter dependencies:

```bash
python3 -m pip install -r requirements.txt
```

StyLua is pinned by the CI workflow. For local formatting, install StyLua 2.6.0 or newer and ensure `stylua` is on PATH.

## CLI

```bash
python3 scripts/beautify.py input.lua -o clean.lua --report --formatter auto
```

Options:

- `--formatter auto`: use StyLua when installed; otherwise use the built-in fallback.
- `--formatter stylua`: require StyLua's Luau parser and fail if it rejects the source.
- `--formatter fallback`: force best-effort formatting for damaged decompiler output.
- `--no-semantic`: disable contextual naming.
- `--report`: include rename counts, parser backend, AST scope count, syntax-error nodes, partial functions, possible missing upvalues, unresolved generated names, junk removals, and formatting details.

## Tests and fixtures

```bash
python3 -m unittest discover -s tests -v
```

The regression suite covers AST shadowing, loops and repeat scopes, typed/generic Luau, closure/string-pool patterns, representative register-style decompiler output, malformed function bodies, missing-upvalue placeholders, contextual names, service alias reuse, full formatting, and safe junk removal.

The files under `tests/fixtures/` are representative synthetic fixtures. They test parsing and recovery patterns; they are not claimed to be complete samples from every proprietary obfuscator.

## Recovery and safety limits

Beautify is not a VM devirtualizer. It cannot reconstruct missing bytecode, missing expressions, or lost function bodies. AST syntax errors are reported with source locations; functions containing errors are marked partial. Unbound generated-looking references inside functions are reported as possible missing upvalues or external globals. Beautify does not invent definitions for them.

The AST backend is preferred when installed. If it is missing or fails, the token-based scope tracker remains available and the report identifies the fallback backend.

## Repository

- `scripts/beautify.py`: CLI, semantic naming, cleanup, and formatting.
- `scripts/luau_ast.py`: Tree-sitter Luau scope and recovery analysis.
- `requirements.txt`: pinned AST dependencies.
- `SKILL.md`: agent skill and workflow.
- `AI_PROMPT.md`: full-file assisted-cleanup guidance.
- `rules/naming.md`: naming policy.
- `tests/`: regression suite and parser fixtures.

## Bot integration

After a deobfuscator produces Lua, a bot may run Beautify before delivery. Preserve the original deobfuscator output as a fallback. Label traces and partial output honestly; formatting a broken dump does not make missing source recoverable.

## License

MIT
