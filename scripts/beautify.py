#!/usr/bin/env python3
"""Beautify deobfuscated Roblox / Luau (mechanical + light semantic)."""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

BANNER_RE = re.compile(
    r"^\s*--\s*("
    r"Deobfuscated by|Detected obfuscation|Local names are inferred|"
    r"NOTE:\s*reconstructed|DAILY DEOBF|BEHAVIOUR TRACE ONLY|"
    r"run status:|\d+\s+statements recorded|URLs requested:|"
    r"anti-tamper trap|source:\s|during the trace|"
    r"Full devirtualization did not|The VM lifter did not|"
    r"Lines below are runtime probes|If protos\.json was written|"
    r"Beautified from deobfuscator|NOT SOURCE:|={5,}"
    r").*$",
    re.I,
)
PURE_STMT_RE = re.compile(
    r"^\s*(?:"
    r"bit32\.\w+\s*\([^;]*\)|"
    r"(?:type|typeof|tostring|tonumber)\s*\(\s*(?:\d+|true|false|nil|\"[^\"]*\"|'[^']*')\s*\)|"
    r"table\.pack\s*\([^;]*\)"
    r")\s*;?\s*$"
)
EMPTY_DO_RE = re.compile(r"^\s*do\s*end\s*;?\s*$")
GARBAGE_IDENT = re.compile(
    r"\b(v\d+|u\d+|p\d+|a\d+|r\d+|t\d+|f\d+|fn\d+|tbl\d*|Arg\d+|arg\d+|var_\d+|_l\d+|L_\d+|loc\d+)\b"
)
RESERVED = {
    "game","workspace","script","shared","plugin","Enum","Axes","Faces","Color3","Vector2",
    "Vector3","CFrame","UDim","UDim2","Rect","Region3","BrickColor","Ray","Instance","task",
    "coroutine","buffer","bit32","string","table","math","utf8","os","debug","ipairs","pairs",
    "next","pcall","xpcall","type","typeof","tostring","tonumber","print","warn","error",
    "assert","select","unpack","rawget","rawset","rawequal","rawlen","setmetatable",
    "getmetatable","newproxy","require","tick","time","wait","delay","spawn","getfenv",
    "setfenv","loadstring","load","self","_G","and","or","not","if","then","else","elseif",
    "end","for","while","repeat","until","function","local","return","break","continue",
    "in","true","false","nil",
}
SERVICE_NAMES = {
    "Players","RunService","ReplicatedStorage","ReplicatedFirst","ServerStorage",
    "ServerScriptService","StarterGui","StarterPack","StarterPlayer","UserInputService",
    "TweenService","HttpService","Debris","Lighting","CollectionService","MarketplaceService",
    "TeleportService","PathfindingService","PhysicsService","SoundService","TextService",
    "Chat","Teams","Workspace","DataStoreService","MemoryStoreService","MessagingService",
    "ProximityPromptService","ContextActionService","GuiService","GroupService","PolicyService",
}

def strip_banners(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not BANNER_RE.match(l))

def strip_pure_junk(text: str) -> str:
    out = []
    for line in text.splitlines():
        if PURE_STMT_RE.match(line) or EMPTY_DO_RE.match(line):
            continue
        out.append(line)
    return "\n".join(out)

def unpack_minified(text: str) -> str:
    text = re.sub(r";\s*(?=(?:local|function|end|if|for|while|repeat|return|do|else|elseif)\b)", ";\n", text)
    text = re.sub(r";\s*(?=local\s+)", ";\n", text)
    text = re.sub(r"\)\s*(?=local\s+)", ")\n", text)
    text = re.sub(r"\bend\s*(?=local\s+)", "end\n", text)
    text = re.sub(r"\bend\s*(?=function\s+)", "end\n", text)
    text = re.sub(r"\)\s*(?=function\s+)", ")\n", text)
    return text

def collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

def light_indent(text: str) -> str:
    out, depth = [], 0
    dec_before = re.compile(r"^\s*(end|until|else|elseif)\b", re.I)
    for raw in text.splitlines():
        line = raw.replace("\t", "    ")
        stripped = line.lstrip()
        if not stripped:
            out.append("")
            continue
        if dec_before.match(stripped):
            depth = max(0, depth - 1)
        out.append("    " * depth + stripped)
        opens = len(re.findall(r"\b(function|then|do|repeat)\b", stripped, re.I))
        closes = len(re.findall(r"\b(end|until)\b", stripped, re.I))
        if re.match(r"else\b", stripped, re.I):
            opens += 1
        depth = max(0, depth + opens - closes)
    return "\n".join(out)

def collect_idents(text: str) -> list[str]:
    found, seen = [], set()
    for m in GARBAGE_IDENT.finditer(text):
        name = m.group(1)
        if name in RESERVED or name in seen:
            continue
        seen.add(name)
        found.append(name)
    return found

def semantic_hints(text: str) -> dict[str, str]:
    hints: dict[str, str] = {}
    for m in re.finditer(
        r"\blocal\s+([A-Za-z_]\w*)\s*=\s*game\s*:\s*GetService\s*\(\s*[\"'](\w+)[\"']\s*\)", text
    ):
        var, svc = m.group(1), m.group(2)
        if GARBAGE_IDENT.fullmatch(var) and svc in SERVICE_NAMES:
            hints[var] = svc
    for m in re.finditer(
        r"\blocal\s+([A-Za-z_]\w*)\s*=\s*[A-Za-z_]\w*\s*\.\s*LocalPlayer\b", text
    ):
        if GARBAGE_IDENT.fullmatch(m.group(1)):
            hints[m.group(1)] = "localPlayer"
    special = {
        "HumanoidRootPart": "rootPart", "PlayerGui": "playerGui", "Remotes": "remotes",
        "Humanoid": "humanoid", "Hit": "hitRemote", "Sync": "syncRemote",
        "CombatEvent": "combatEvent", "DataFunction": "dataFunction",
    }
    for m in re.finditer(
        r"\blocal\s+([A-Za-z_]\w*)\s*=\s*[^;\n]+:(?:WaitForChild|FindFirstChild|FindFirstChildOfClass)\s*\(\s*[\"'](\w+)[\"']",
        text,
    ):
        var, child = m.group(1), m.group(2)
        if GARBAGE_IDENT.fullmatch(var):
            hints[var] = special.get(child, child[0].lower() + child[1:])
    for m in re.finditer(r"\b(?:local\s+)?function\s+([A-Za-z_]\w*)\s*\(", text):
        var = m.group(1)
        if not GARBAGE_IDENT.fullmatch(var):
            continue
        window = text[m.end() : m.end() + 500]
        if "FireServer" in window or "InvokeServer" in window:
            hints.setdefault(var, "fireRemote")
        elif "WalkSpeed" in window or "JumpPower" in window:
            hints.setdefault(var, "applyStats")
        elif "FindFirstChildOfClass" in window and "Humanoid" in window:
            hints.setdefault(var, "getHumanoidAndRoot")
        elif "KeyCode" in window or "UserInputType" in window:
            hints.setdefault(var, "onInputBegan")
    for m in re.finditer(
        r"\blocal\s+([A-Za-z_]\w*)\s*=\s*[^;\n]+\.(\w+)\s*:\s*Connect\s*\(", text
    ):
        var, ev = m.group(1), m.group(2)
        if GARBAGE_IDENT.fullmatch(var):
            hints[var] = ev[0].lower() + ev[1:] + "Conn"
    return hints

def build_rename_map(idents: list[str], hints: dict[str, str] | None = None) -> dict[str, str]:
    hints = hints or {}
    mapping: dict[str, str] = {}
    used = set(RESERVED)
    for name in idents:
        if name in hints:
            base, cand, n = hints[name], hints[name], 2
            while cand in used:
                cand = f"{base}{n}"
                n += 1
            mapping[name] = cand
            used.add(cand)
    counters = {k: 0 for k in ("v","u","p","a","r","t","f","fn","tbl","arg","var","l","loc","other")}
    prefix_word = {
        "v":"value","u":"upval","p":"part","a":"arg","r":"reg","t":"temp","f":"fn",
        "fn":"handler","tbl":"data","arg":"param","var":"state","l":"node","loc":"node","other":"name",
    }
    def family(name: str) -> str:
        lower = name.lower()
        for p in ("tbl","arg","var","fn","loc"):
            if lower.startswith(p):
                return p
        if lower.startswith("_l") or lower.startswith("l_"):
            return "l"
        return name[0] if name[0] in counters else "other"
    for name in idents:
        if name in mapping:
            continue
        fam = family(name)
        counters[fam] += 1
        n = counters[fam]
        word = prefix_word[fam]
        new = f"{word}{n}" if n > 1 or fam in ("v","u","r","t","other","l","loc") else word
        base, k = new, 1
        while new in used:
            k += 1
            new = f"{base}_{k}"
        mapping[name] = new
        used.add(new)
    return mapping

def apply_renames(text: str, mapping: dict[str, str]) -> str:
    if not mapping:
        return text
    keys = sorted(mapping.keys(), key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in keys) + r")\b")
    return pattern.sub(lambda m: mapping.get(m.group(1), m.group(1)), text)

def space_operators(text: str) -> str:
    text = re.sub(r"(local\s+[A-Za-z_]\w*)\s*=\s*", r"\1 = ", text)
    text = re.sub(r",\s*", ", ", text)
    return text

def is_trace_only(text: str) -> bool:
    body = text.strip()
    if not body:
        return True
    if re.search(r"BEHAVIOUR TRACE ONLY|statements recorded", body, re.I):
        if body.count("function") <= 2 and "DescendantAdded" in body and "math_floor_precision" in body:
            return True
    return False

def beautify(text: str, aggressive: bool = True, semantic: bool = True) -> str:
    if is_trace_only(text):
        return (
            "-- NOT SOURCE: behaviour / anti-tamper trace only\n"
            "-- No recoverable game logic in this input.\n"
        )
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = strip_banners(text)
    text = unpack_minified(text)
    text = strip_pure_junk(text)
    text = space_operators(text)
    if aggressive or semantic:
        idents = collect_idents(text)
        hints = semantic_hints(text) if semantic else {}
        mapping = build_rename_map(idents, hints)
        text = apply_renames(text, mapping)
    text = light_indent(text)
    text = collapse_blank_lines(text)
    if not text.startswith("-- Beautified"):
        text = "-- Beautified from deobfuscator output\n\n" + text
    return text

def main() -> int:
    ap = argparse.ArgumentParser(description="Beautify deobfuscated Roblox Luau")
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--no-semantic", action="store_true")
    args = ap.parse_args()
    raw = args.input.read_text(encoding="utf-8", errors="replace")
    out = beautify(raw, aggressive=True, semantic=not args.no_semantic)
    if args.output:
        args.output.write_text(out, encoding="utf-8")
        print(f"wrote {args.output} ({len(out)} bytes)", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
