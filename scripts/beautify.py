#!/usr/bin/env python3
"""
Beautify deobfuscated Roblox / Luau source (mechanical pass).

  python3 scripts/beautify.py input.lua -o output.lua
  python3 scripts/beautify.py input.lua --aggressive -o output.lua

For semantic renames (v12 -> humanoid), use AI_PROMPT.md with an AI.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BANNER_RE = re.compile(
    r"^\s*--\s*("
    r"Deobfuscated by|"
    r"Detected obfuscation|"
    r"Local names are inferred|"
    r"NOTE:\s*reconstructed|"
    r"DAILY DEOBF|"
    r"BEHAVIOUR TRACE ONLY|"
    r"run status:|"
    r"\d+\s+statements recorded|"
    r"URLs requested:|"
    r"anti-tamper trap|"
    r"source:\s|"
    r"during the trace|"
    r"Full devirtualization did not|"
    r"The VM lifter did not|"
    r"Lines below are runtime probes|"
    r"If protos\.json was written|"
    r"={5,}"
    r").*$",
    re.I,
)

PURE_CALL_RE = re.compile(
    r"^\s*(bit32\.\w+|type|typeof|tostring|tonumber)\s*\([^)]*\)\s*;?\s*$"
)

GARBAGE_IDENT = re.compile(
    r"\b("
    r"v\d+|"
    r"u\d+|"
    r"p\d+|"
    r"a\d+|"
    r"r\d+|"
    r"t\d+|"
    r"f\d+|"
    r"fn\d+|"
    r"tbl\d*|"
    r"Arg\d+|"
    r"arg\d+|"
    r"var_\d+|"
    r"_l\d+|"
    r"L_\d+|"
    r"loc\d+"
    r")\b"
)

RESERVED = {
    "game", "workspace", "script", "shared", "plugin", "Enum", "Axes", "Faces",
    "Color3", "Vector2", "Vector3", "CFrame", "UDim", "UDim2", "Rect", "Region3",
    "BrickColor", "Ray", "Instance", "task", "coroutine", "buffer", "bit32",
    "string", "table", "math", "utf8", "os", "debug", "ipairs", "pairs", "next",
    "pcall", "xpcall", "type", "typeof", "tostring", "tonumber", "print", "warn",
    "error", "assert", "select", "unpack", "rawget", "rawset", "rawequal", "rawlen",
    "setmetatable", "getmetatable", "newproxy", "require", "tick", "time", "wait",
    "delay", "spawn", "getfenv", "setfenv", "loadstring", "load",
}


def strip_banners(text: str) -> str:
    out = []
    for line in text.splitlines():
        if BANNER_RE.match(line):
            continue
        out.append(line)
    return "\n".join(out)


def strip_pure_junk(text: str) -> str:
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if PURE_CALL_RE.match(stripped):
            continue
        if re.match(r"^do\s*end\s*;?$", stripped):
            continue
        out.append(line)
    return "\n".join(out)


def collapse_blank_lines(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def collect_idents(text: str) -> list[str]:
    found = []
    seen = set()
    for m in GARBAGE_IDENT.finditer(text):
        name = m.group(1)
        if name in RESERVED or name in seen:
            continue
        seen.add(name)
        found.append(name)
    return found


def build_rename_map(idents: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    counters = {
        "v": 0, "u": 0, "p": 0, "a": 0, "r": 0, "t": 0, "f": 0,
        "fn": 0, "tbl": 0, "arg": 0, "var": 0, "l": 0, "loc": 0, "other": 0,
    }

    def family(name: str) -> str:
        lower = name.lower()
        if lower.startswith("tbl"):
            return "tbl"
        if lower.startswith("arg"):
            return "arg"
        if lower.startswith("var"):
            return "var"
        if lower.startswith("fn"):
            return "fn"
        if lower.startswith("_l") or lower.startswith("l_"):
            return "l"
        if lower.startswith("loc"):
            return "loc"
        if name[0] in counters:
            return name[0]
        return "other"

    prefix_word = {
        "v": "value",
        "u": "upval",
        "p": "part",
        "a": "arg",
        "r": "reg",
        "t": "temp",
        "f": "fn",
        "fn": "handler",
        "tbl": "data",
        "arg": "param",
        "var": "state",
        "l": "local",
        "loc": "local",
        "other": "name",
    }

    for name in idents:
        fam = family(name)
        counters[fam] += 1
        n = counters[fam]
        word = prefix_word[fam]
        new = f"{word}{n}" if n > 1 or fam in ("v", "u", "r", "t", "other") else word
        base = new
        k = 1
        used = set(mapping.values()) | RESERVED
        while new in used:
            k += 1
            new = f"{base}_{k}"
        mapping[name] = new
    return mapping


def apply_renames(text: str, mapping: dict[str, str]) -> str:
    if not mapping:
        return text
    keys = sorted(mapping.keys(), key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in keys) + r")\b")

    def repl(m: re.Match) -> str:
        return mapping.get(m.group(1), m.group(1))

    return pattern.sub(repl, text)


def light_indent(text: str) -> str:
    lines = []
    for line in text.splitlines():
        i = 0
        spaces = 0
        while i < len(line):
            if line[i] == "\t":
                spaces += 4
                i += 1
            elif line[i] == " ":
                spaces += 1
                i += 1
            else:
                break
        lines.append(" " * spaces + line[i:])
    return "\n".join(lines)


def is_trace_only(text: str) -> bool:
    body = text.strip()
    if not body:
        return True
    if re.search(r"BEHAVIOUR TRACE ONLY|statements recorded", body, re.I):
        if body.count("function") <= 2 and "DescendantAdded" in body and "math_floor_precision" in body:
            return True
    return False


def beautify(text: str, aggressive: bool = False) -> str:
    if is_trace_only(text):
        return (
            "-- NOT SOURCE: behaviour / anti-tamper trace only\n"
            "-- No recoverable game logic in this input.\n"
        )

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = strip_banners(text)
    text = strip_pure_junk(text)
    text = light_indent(text)

    if aggressive:
        idents = collect_idents(text)
        mapping = build_rename_map(idents)
        text = apply_renames(text, mapping)

    text = collapse_blank_lines(text)
    if not text.startswith("-- Beautified"):
        text = "-- Beautified from deobfuscator output\n\n" + text
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description="Mechanical beautifier for deobfuscated Luau")
    ap.add_argument("input", type=Path, help="Input .lua / .luau file")
    ap.add_argument("-o", "--output", type=Path, help="Output path (default: stdout)")
    ap.add_argument(
        "--aggressive",
        action="store_true",
        help="Rename v1/tbl2/Arg3/_l9 style identifiers to valueN/dataN/paramN/...",
    )
    args = ap.parse_args()

    raw = args.input.read_text(encoding="utf-8", errors="replace")
    out = beautify(raw, aggressive=args.aggressive)

    if args.output:
        args.output.write_text(out, encoding="utf-8")
        print(f"wrote {args.output} ({len(out)} bytes)", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
