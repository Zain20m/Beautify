# Beautify

Turn messy **deobfuscated** Roblox / Luau into clean, readable source.

Strips Luraph/deobf junk, kills `v1` / `tbl4` / `Arg4` / `_l173`, expands minified lines, renames from `GetService` / `LocalPlayer` / `WaitForChild` / `Connect`.

## Skill

Agents load [`SKILL.md`](./SKILL.md).

## AI (best quality)

1. Open [`AI_PROMPT.md`](./AI_PROMPT.md)
2. Paste into any AI with your deobfuscated script
3. Optional teaching pairs in [`examples/`](./examples/) (including **extreme** whole-file soup)

## CLI (fast)

```bash
python3 scripts/beautify.py input.lua -o clean.lua
```

Default pass:

- strip banners + pure junk
- unpack minified `;local` walls
- semantic rename (`Players`, `localPlayer`, `remotes`, `hitRemote`, `getHumanoidAndRoot`, `*Conn`)
- fallback rename for leftover garbage idents
- 4-space indent

```bash
python3 scripts/beautify.py input.lua --no-semantic -o clean.lua  # rename only, no usage hints
```

## Layout

```
SKILL.md
AI_PROMPT.md
scripts/beautify.py
rules/naming.md
rules/strip_list.md
examples/before.lua | after.lua
examples/before_extreme.lua | after_extreme.lua
```

## Discord / deobf bots

After every deobfuscation, pipe through `scripts/beautify.py` before sending to users.

## License

MIT
