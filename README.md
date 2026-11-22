# Beautify

Clean already-deobfuscated Roblox / Luau into readable source.

The default engine is a token-based, scope-aware cleanup pass. It expands many semicolon-packed and inline block statements, applies consistent indentation and spacing, and renames generated local variables without blindly replacing matching text in strings, comments, property names, or unrelated scopes.

## What it does

- Renames scoped locals, function parameters, and loop variables such as `v12`, `tbl4`, `Arg2`, `_l173`, and `fn3`.
- Uses context from `GetService`, `LocalPlayer`, `WaitForChild`, `Instance.new`, event connections, and recognizable function bodies.
- Infers a missing service alias only when a known Roblox service name is used as an otherwise-unbound identifier.
- Splits semicolon chains and common inline control blocks.
- Removes only narrowly recognized deobfuscator banners and standalone pure-noise statements.
- Reports unbalanced blocks rather than silently deleting unmatched `end` / `until` tokens.

## CLI

```bash
python3 scripts/beautify.py input.lua -o clean.lua --report
```

Options:

- `--no-semantic`: use neutral generated names instead of contextual names.
- `--report`: print rename counts, inferred service aliases, remaining generated-name count, and structural diagnostics.

## Tests

Run the regression suite with:

```bash
python3 -m unittest discover -s tests -v
```

The tests cover shadowed locals, callback parameters, strings/comments, member names, inline blocks, missing service aliases, malformed input, and trace-only output.

## Limits

Beautify cleans recovered source. It is not a devirtualizer, compiler, or full Luau parser. It cannot reconstruct missing VM expressions, repair a failed decompilation, or prove runtime behavior. Unknown statements and suspicious fragments are preserved. When the structural report shows unmatched blocks, treat the result as incomplete and inspect the original deobfuscator output too.

## Skill

Agents load [SKILL.md](./SKILL.md). The AI rewrite guidance is in [AI_PROMPT.md](./AI_PROMPT.md), with examples under [examples/](./examples/).

## Discord / deobfuscation bots

After a deobfuscation engine successfully returns source text, a bot may pass the output through `scripts/beautify.py` before delivering it. Keep the original result as a fallback. Do not report a successful recovery when the engine produced only a behavior trace or malformed partial output.

## License

MIT
