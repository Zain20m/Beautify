# Beautify

Clean and semantically rename already-deobfuscated Roblox / Luau.

Beautify builds a scope-aware binding map, improves generated and intermediate names from Roblox API usage and function behavior, removes only provably inert junk, then formats the whole file with StyLua when installed. A conservative fallback handles malformed or incomplete decompiler output.

## What it does

- Renames locals, local functions, callback parameters, and loop variables by lexical binding, so shadowed variables stay separate.
- Improves both obfuscator names (`v12`, `tbl4`, `Arg2`, `_l173`, `fn3`) and generic names from an earlier beautification pass (`handleEvent`, `sendRemoteEvent`, `value12`).
- Infers function names from their full body and API usage, and value names from constructors, assignments, properties, and callback roles.
- Reuses service aliases when the same service is requested again and the alias is in scope.
- Removes only recognized banners, empty `do end` padding, standalone pure constant calls, and unused generated locals initialized with literal-only values.
- Formats full Luau files, including expressions, callbacks, tables, method chains, operators, and control flow.
- Reports parser failures, unmatched blocks, unresolved generated globals/upvalues, and removed junk counts.

## CLI

```bash
python3 scripts/beautify.py input.lua -o clean.lua --report --formatter auto
```

Options:

- `--formatter auto`: use StyLua when installed; otherwise use the built-in fallback.
- `--formatter stylua`: require StyLua's Luau parser and fail if it rejects the source.
- `--formatter fallback`: force best-effort formatting for malformed output.
- `--no-semantic`: disable contextual naming and use neutral renames.
- `--report`: print rename counts, removed-junk counts, inferred service aliases, formatter details, and structural diagnostics.

## Full formatter

Install StyLua:

```bash
pip install git+https://github.com/JohnnyMorganz/StyLua@v2.6.0
```

The checked-in `.stylua.toml` selects four-space Luau formatting. StyLua parses and formats complete valid Luau. The fallback is only a best-effort option for malformed decompiler output.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Regression coverage includes lexical shadowing, callback parameters, semantic function naming, literal preservation, service alias reuse, full formatting, safe junk removal, and malformed-input diagnostics.

## Limits

Beautify is not a VM devirtualizer and cannot reconstruct missing expressions or function bodies. It does not guess names for unbound globals or missing upvalues. A fallback-formatted file with unmatched block tokens is still incomplete source.

## Skill and prompt

Agents load [SKILL.md](./SKILL.md). The deeper AI-assisted naming and formatting guidance is in [AI_PROMPT.md](./AI_PROMPT.md). Examples are under [examples/](./examples/).

## Bot integration

After a deobfuscator returns Lua text, a bot may run `scripts/beautify.py` before delivery. Preserve the original output as a fallback. Do not present behavior traces or malformed fragments as successfully recovered source.

## License

MIT
