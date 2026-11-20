# Strip list

## Always remove (tool noise)

- `-- Deobfuscated by …`
- `-- Detected obfuscation …`
- `-- Local names are inferred …`
- `-- NOTE: reconstructed …`
- `-- DAILY DEOBF …` / `-- BEHAVIOUR TRACE ONLY …`
- `-- run status:` / `-- N statements recorded`
- `-- anti-tamper trap functions disabled …`
- Standalone credit banners from deobfuscators

## Remove when clearly junk

- Expression statements that are pure and unused
- Locals never read
- Empty `do end`
- `if false then … end` opaque shells (unwrap if safe)

## Never remove just because it looks ugly

- `pcall` / `xpcall` around real work
- `task.spawn` / `task.defer` / `task.wait`
- Remote fires / invokes
- Instance property writes
- Any call you cannot prove pure
