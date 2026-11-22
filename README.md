# Beautify

Clean already-deobfuscated Roblox / Luau into readable source.

The engine first performs conservative token- and scope-aware cleanup, then formats the complete file with StyLua's Luau parser when StyLua is installed. This gives consistent formatting for statements, expressions, tables, callbacks, chains, and control blocks. A fallback formatter remains available for malformed or incomplete decompiler output that cannot be parsed.

## What it does

- Renames scoped locals, function parameters, and loop variables such as `v12`, `tbl4`, `Arg2`, `_l173`, and `fn3`.
- Uses context from `GetService`, `LocalPlayer`, `WaitForChild`, `Instance.new`, event connections, and recognizable function bodies.
- Reuses declared service aliases, so repeated `game:GetService("ReplicatedStorage")` chains become `ReplicatedStorage` when that local is in scope.
- Infers a missing service alias only when a known Roblox service name is used as an otherwise-unbound identifier.
- Formats the whole Luau file, including multiline expressions, callbacks, tables, operators, method chains, and control blocks.
- Reuses declared services instead of repeating `game:GetService(...)` where the matching local is in scope.
- Falls back to a conservative best-effort formatter when incomplete decompiler output cannot be parsed.
- Removes only narrowly recognized deobfuscator banners and standalone pure-noise statements.
- Reports unbalanced blocks and unbound generated-looking names rather than silently deleting or guessing at them.

## CLI

```bash
python3 scripts/beautify.py input.lua -o clean.lua --report --formatter auto
```

Options:

- `--formatter auto`: use StyLua when installed; otherwise use the fallback formatter.
- `--formatter stylua`: require StyLua and the Luau parser. Fail instead of falling back.
- `--formatter fallback`: force the built-in formatter, useful for malformed decompiler output.
- `--no-semantic`: use neutral generated names instead of contextual names.
- `--report`: print rename counts, formatter used, parse errors, remaining generated names, and structural diagnostics.

## Full formatting engine

Install the pinned formatter with:

```bash
pip install git+https://github.com/JohnnyMorganz/StyLua@v2.6.0
```

The repository includes `.stylua.toml` for four-space Luau formatting. The engine uses StyLua's parser/printer for valid source, then applies the preferred one-call-per-line method-chain layout. The fallback is for broken or partial decompiler output and cannot guarantee valid syntax.

## Tests

Run the regression suite with:

```bash
python3 -m unittest discover -s tests -v
```

The tests cover shadowed locals, callback parameters, literal preservation, service alias reuse, full formatting, method-chain wrapping, table formatting, malformed input, and unresolved generated names.

## Limits

Beautify cleans recovered source. It is not a devirtualizer and cannot reconstruct missing VM expressions or repair failed decompilation. StyLua validates and formats syntactically valid Luau; fallback output is best-effort and may remain invalid when the original decompiler output is malformed. Unknown statements and suspicious fragments are preserved. When the structural report shows unmatched blocks, treat the result as incomplete and inspect the original deobfuscator output too.

## Skill

Agents load [SKILL.md](./SKILL.md). The AI rewrite guidance is in [AI_PROMPT.md](./AI_PROMPT.md), with examples under [examples/](./examples/).

## Discord / deobfuscation bots

After a deobfuscation engine successfully returns source text, a bot may pass the output through `scripts/beautify.py` before delivering it. Keep the original result as a fallback. Do not report a successful recovery when the engine produced only a behavior trace or malformed partial output.

## License

MIT
