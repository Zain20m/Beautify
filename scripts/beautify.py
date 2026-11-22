#!/usr/bin/env python3
"""Scope-aware Roblox/Luau beautifier for already-deobfuscated source.

This is a conservative source cleaner: it renames local bindings and parameters,
formats whitespace/indentation, and removes only narrowly proven tool noise.
It does not reconstruct missing VM logic or change runtime behavior intentionally.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

BANNER_RE = re.compile(
    r"^\s*--\s*(Deobfuscated by|Detected obfuscation|Local names are inferred|"
    r"NOTE:\s*reconstructed|DAILY DEOBF|BEHAVIOUR TRACE ONLY|run status:|"
    r"\d+\s+statements recorded|URLs requested:|anti-tamper trap|source:\s|"
    r"during the trace|Full devirtualization did not|The VM lifter did not|"
    r"Lines below are runtime probes|If protos\.json was written|"
    r"Beautified from deobfuscator|NOT SOURCE:|={5,}).*$", re.I
)
PURE_STMT_RE = re.compile(
    r"^\s*(?:bit32\.\w+\s*\([^;]*\)|"
    r"(?:type|typeof|tostring|tonumber)\s*\(\s*(?:\d+|true|false|nil|\"[^\"]*\"|'[^']*')\s*\)|"
    r"table\.pack\s*\([^;]*\))\s*;?\s*$"
)
EMPTY_DO_RE = re.compile(r"^\s*do\s*end\s*;?\s*$")

# Rename only local bindings with weak/generated names. The second group catches
# common decompiler leftovers which the old v#/tbl#/Arg# matcher missed.
GARBAGE_IDENT = re.compile(
    r"^(?:v\d*|V\d*|u\d+|U\d+|p\d+|P\d+|a\d+|A\d+|r\d+|R\d+|"
    r"t\d+|T\d+|t_\d+|T_\d+|f\d+|F\d+|fn\d+|FN\d+|tbl\d*|Tbl\d*|"
    r"arg|Arg\d+|arg\d+|ARG\d+|var_\d+|_l\d+|L_\d+|[A-Z]_\d+|loc\d+|"
    r"PROTO_\d+|STACK\d*|REGISTER\d*|R\d+|n\d*|flag\d*|thread\d*|"
    r"connection\d*|lib\d*|tween\d*|paragraph\d*|cFrame)$"
)

KEYWORDS = {
    "and", "break", "continue", "do", "else", "elseif", "end", "false",
    "for", "function", "if", "in", "local", "nil", "not", "or", "repeat",
    "return", "then", "true", "until", "while", "type",
}
RESERVED = KEYWORDS | {
    "game", "workspace", "script", "shared", "plugin", "Enum", "Axes", "Faces",
    "Color3", "Vector2", "Vector3", "CFrame", "UDim", "UDim2", "Rect", "Region3",
    "BrickColor", "Ray", "Instance", "task", "coroutine", "buffer", "bit32",
    "string", "table", "math", "utf8", "os", "debug", "ipairs", "pairs", "next",
    "pcall", "xpcall", "typeof", "tostring", "tonumber", "print", "warn", "error",
    "assert", "select", "unpack", "rawget", "rawset", "rawequal", "rawlen",
    "setmetatable", "getmetatable", "newproxy", "require", "tick", "time", "wait",
    "delay", "spawn", "getfenv", "setfenv", "loadstring", "load", "self", "_G",
}

SERVICE_NAMES = {
    "Players", "RunService", "ReplicatedStorage", "ReplicatedFirst", "ServerStorage",
    "ServerScriptService", "StarterGui", "StarterPack", "StarterPlayer", "UserInputService",
    "TweenService", "HttpService", "Debris", "Lighting", "CollectionService",
    "MarketplaceService", "TeleportService", "PathfindingService", "PhysicsService",
    "SoundService", "TextService", "Chat", "Teams", "Workspace", "DataStoreService",
    "MemoryStoreService", "MessagingService", "ProximityPromptService", "ContextActionService",
    "GuiService", "GroupService", "PolicyService", "VirtualInputManager",
}

CHILD_NAMES = {
    "HumanoidRootPart": "humanoidRootPart", "PlayerGui": "playerGui", "Remotes": "remotes",
    "Humanoid": "humanoid", "Hit": "hitRemote", "Sync": "syncRemote",
    "CombatEvent": "combatEvent", "DataFunction": "dataFunction", "Backpack": "backpack",
    "Character": "character", "leaderstats": "leaderstats", "Main": "mainFrame",
    "MainMenu": "mainMenu", "requests": "requestsFolder",
}


@dataclass
class Token:
    value: str
    kind: str
    start: int
    end: int
    line: int


@dataclass
class Binding:
    name: str
    token_index: int
    scope: "Scope"
    active_from: int
    role: str = "local"
    hint: str | None = None
    new_name: str | None = None
    refs: list[int] = field(default_factory=list)
    function_body: str = ""
    function_context: str = ""


@dataclass
class Scope:
    parent: "Scope | None"
    start: int
    end: int = 10**18
    bindings: list[Binding] = field(default_factory=list)
    label: str = "block"
    function_token: int | None = None
    function_end: int | None = None


@dataclass
class Block:
    kind: str
    parent_scope: Scope
    scope: Scope | None = None
    header_start: int = -1
    loop_names: list[tuple[str, int]] = field(default_factory=list)


def _long_bracket_end(source: str, start: int) -> int | None:
    m = re.match(r"\[(=*)\[", source[start:])
    if not m:
        return None
    closer = "]" + m.group(1) + "]"
    end = source.find(closer, start + len(m.group(0)))
    return len(source) if end < 0 else end + len(closer)


def lex(source: str) -> list[Token]:
    """Tokenize Lua/Luau without interpreting strings or comments as code."""
    out: list[Token] = []
    i, line, n = 0, 1, len(source)
    while i < n:
        ch = source[i]
        if ch in " \t\r\f\v":
            i += 1
            continue
        if ch == "\n":
            line += 1
            i += 1
            continue
        start, start_line = i, line
        if source.startswith("--", i):
            long_end = _long_bracket_end(source, i + 2)
            if long_end is not None:
                value = source[i:long_end]
                line += value.count("\n")
                i = long_end
            else:
                end = source.find("\n", i)
                i = n if end < 0 else end
                value = source[start:i]
            out.append(Token(value, "comment", start, i, start_line))
            continue
        if ch in "\"'":
            quote = ch
            i += 1
            while i < n:
                if source[i] == "\\":
                    i += 2
                    continue
                if source[i] == quote:
                    i += 1
                    break
                if source[i] == "\n":
                    line += 1
                i += 1
            out.append(Token(source[start:i], "string", start, i, start_line))
            continue
        long_end = _long_bracket_end(source, i)
        if long_end is not None:
            value = source[i:long_end]
            line += value.count("\n")
            i = long_end
            out.append(Token(value, "string", start, i, start_line))
            continue
        if ch.isalpha() or ch == "_":
            i += 1
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
            out.append(Token(source[start:i], "keyword" if source[start:i] in KEYWORDS else "ident", start, i, start_line))
            continue
        if ch.isdigit():
            i += 1
            while i < n and (source[i].isalnum() or source[i] in "._"):
                if source.startswith("..", i):
                    break
                i += 1
            out.append(Token(source[start:i], "number", start, i, start_line))
            continue
        op = next((x for x in ("...", "..=", "//", "==", "~=", "<=", ">=", "::", "..", "+=", "-=", "*=", "/=", "%=", "^=") if source.startswith(x, i)), None)
        if op:
            i += len(op)
            out.append(Token(op, "operator", start, i, start_line))
        else:
            i += 1
            out.append(Token(ch, "punct", start, i, start_line))
    return out


def significant(tokens: list[Token]) -> list[Token]:
    return [t for t in tokens if t.kind != "comment"]


def matching(tokens: list[Token], index: int, opening: str, closing: str) -> int:
    depth = 0
    for j in range(index, len(tokens)):
        if tokens[j].value == opening:
            depth += 1
        elif tokens[j].value == closing:
            depth -= 1
            if depth == 0:
                return j
    return -1


def _statement_end(tokens: list[Token], start: int) -> int:
    """Find the next statement boundary without swallowing a following block."""
    if start >= len(tokens):
        return start
    paren = bracket = brace = block = 0
    continuation = {
        "=", ",", ".", ":", "+", "-", "*", "/", "//", "%", "^", "..",
        "and", "or", "not", "return", "then", "do", "(", "{", "[",
    }
    statement_words = {"local", "function", "if", "for", "while", "repeat", "return", "break", "continue", "do"}
    last_line = tokens[start].line
    j = start
    while j < len(tokens):
        v = tokens[j].value
        if j > start and paren == bracket == brace == block == 0:
            previous = tokens[j - 1].value
            if previous == ";":
                return j
            if tokens[j].line > last_line and previous not in continuation and v not in {".", ":", ",", ")", "]", "}", "and", "or"}:
                return j
            if v in statement_words and tokens[j].line == last_line and previous not in continuation:
                return j
        if v == "(":
            paren += 1
        elif v == ")":
            paren = max(0, paren - 1)
        elif v == "[":
            bracket += 1
        elif v == "]":
            bracket = max(0, bracket - 1)
        elif v == "{":
            brace += 1
        elif v == "}":
            brace = max(0, brace - 1)
        elif v in ("function", "if", "repeat"):
            block += 1
        elif v == "do":
            if j == 0 or tokens[j - 1].value not in ("for", "while"):
                block += 1
        elif v in ("end", "until"):
            block = max(0, block - 1)
        last_line = max(last_line, tokens[j].line)
        j += 1
    return len(tokens)


def _parse_local_names(tokens: list[Token], i: int) -> tuple[list[int], int, bool]:
    """Return declared name-token indices, first token after lhs, and function-local flag."""
    if i + 2 < len(tokens) and tokens[i + 1].value == "function" and tokens[i + 2].kind == "ident":
        return [i + 2], i + 3, True
    names: list[int] = []
    j = i + 1
    while j < len(tokens):
        if tokens[j].kind != "ident":
            break
        names.append(j)
        j += 1
        if j < len(tokens) and tokens[j].value == ":":
            j += 1
            while j < len(tokens) and tokens[j].value not in (",", "=") and tokens[j].line == tokens[j - 1].line:
                j += 1
        if j < len(tokens) and tokens[j].value == ",":
            j += 1
            continue
        break
    return names, j, False


def _create_scope(parent: Scope, start: int, label: str) -> Scope:
    return Scope(parent=parent, start=start, label=label)


def find_function_end(tokens: list[Token], function_index: int, parameter_close: int | None = None) -> int | None:
    """Find a function's matching end, tolerating nested Luau blocks."""
    if parameter_close is None:
        p = function_index + 1
        while p < len(tokens) and tokens[p].value != "(":
            if tokens[p].value in ("end", "then", "do", ";"):
                return None
            p += 1
        if p >= len(tokens):
            return None
        parameter_close = matching(tokens, p, "(", ")")
    if parameter_close is None or parameter_close < 0:
        return None
    blocks = ["function"]
    j = parameter_close + 1
    while j < len(tokens):
        value = tokens[j].value
        if value == "function":
            blocks.append("function")
        elif value == "if":
            blocks.append("if")
        elif value in ("for", "while"):
            blocks.append("loop_wait")
        elif value == "do":
            if blocks and blocks[-1] == "loop_wait":
                blocks[-1] = "loop"
            else:
                blocks.append("do")
        elif value == "repeat":
            blocks.append("repeat")
        elif value == "until":
            if blocks and blocks[-1] == "repeat":
                blocks.pop()
        elif value == "end":
            if blocks:
                blocks.pop()
            if not blocks:
                return j
        j += 1
    return None


def attach_function_bodies(source: str, tokens: list[Token], bindings: list[Binding]) -> None:
    """Attach actual function bodies to local function bindings for semantic naming."""
    for binding in bindings:
        if binding.role != "local":
            continue
        candidates: list[int] = []
        i = binding.token_index
        if i > 0 and tokens[i - 1].value == "function":
            candidates.append(i - 1)
        j = i + 1
        while j < len(tokens) and tokens[j].line == tokens[i].line and tokens[j].value not in (";", "local", "return"):
            if tokens[j].value == "=" and j + 1 < len(tokens) and tokens[j + 1].value == "function":
                candidates.append(j + 1)
                break
            j += 1
        for ref in binding.refs:
            if ref + 2 < len(tokens) and tokens[ref + 1].value == "=" and tokens[ref + 2].value == "function":
                candidates.append(ref + 2)
                break
        for fn_index in candidates:
            p = fn_index + 1
            while p < len(tokens) and tokens[p].value != "(":
                p += 1
            if p >= len(tokens):
                continue
            close = matching(tokens, p, "(", ")")
            if close < 0:
                continue
            end = find_function_end(tokens, fn_index, close)
            if end is not None:
                binding.function_body = " ".join(t.value for t in tokens[close + 1:end])
                binding.function_context = _function_context(tokens, fn_index)
                break


def build_bindings(source: str, all_tokens: list[Token]) -> tuple[list[Token], list[Binding], dict[int, Binding], dict[int, Scope], list[str]]:
    """Build approximate lexical scopes and resolve local identifier references."""
    tokens = significant(all_tokens)
    root = Scope(None, 0, len(source) + 1, label="root")
    current = root
    stack: list[Block] = []
    token_scopes: dict[int, Scope] = {}
    decl_tokens: dict[int, Binding] = {}
    bindings: list[Binding] = []
    diagnostics: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        v = t.value
        if v == "end":
            if stack:
                block = stack.pop()
                if block.scope is not None:
                    block.scope.end = t.start
                current = block.parent_scope
            else:
                diagnostics.append(f"unmatched 'end' at line {t.line}")
            token_scopes[i] = current
            i += 1
            continue
        if v in ("else", "elseif"):
            if stack and stack[-1].kind == "if":
                block = stack[-1]
                if block.scope is not None:
                    block.scope.end = t.start
                current = block.parent_scope
                block.scope = None
                if v == "else":
                    new_scope = _create_scope(current, t.end, "else")
                    block.scope = new_scope
                    current = new_scope
            token_scopes[i] = current
            i += 1
            continue
        if v == "until":
            token_scopes[i] = current
            if stack and stack[-1].kind == "repeat":
                block = stack.pop()
                if block.scope is not None:
                    end_index = _statement_end(tokens, i + 1)
                    block.scope.end = tokens[end_index - 1].end if end_index > i + 1 else t.end
                current = block.parent_scope
            else:
                diagnostics.append(f"unmatched 'until' at line {t.line}")
            i += 1
            continue

        token_scopes[i] = current
        if v == "local":
            name_indices, lhs_end, local_function = _parse_local_names(tokens, i)
            if name_indices:
                if local_function:
                    active = tokens[name_indices[0]].start
                elif lhs_end < len(tokens) and tokens[lhs_end].value == "=":
                    next_index = _statement_end(tokens, lhs_end + 1)
                    active = tokens[next_index].start if next_index < len(tokens) else len(source) + 1
                else:
                    active = tokens[lhs_end - 1].end if lhs_end > i + 1 else t.end
                for ni in name_indices:
                    b = Binding(tokens[ni].value, ni, current, active, role="local")
                    current.bindings.append(b)
                    bindings.append(b)
                    decl_tokens[ni] = b
        elif v == "function":
            p = i + 1
            while p < len(tokens) and tokens[p].value != "(":
                if tokens[p].value in ("end", "then", "do", ";"):
                    break
                p += 1
            if p < len(tokens) and tokens[p].value == "(":
                close = matching(tokens, p, "(", ")")
                if close >= 0:
                    fn_scope = _create_scope(current, tokens[close].end, "function")
                    fn_scope.function_token = i
                    fn_scope.function_context = _function_context(tokens, i)
                    fn_end = find_function_end(tokens, i, close)
                    fn_scope.function_end = fn_end
                    stack.append(Block("function", current, fn_scope))
                    k = p + 1
                    while k < close:
                        if tokens[k].kind == "ident" and (k == p + 1 or tokens[k - 1].value == ","):
                            b = Binding(tokens[k].value, k, fn_scope, tokens[close].end, role="parameter")
                            fn_scope.bindings.append(b)
                            bindings.append(b)
                            decl_tokens[k] = b
                        k += 1
                    current = fn_scope
                    i = close + 1
                    continue
        elif v == "if":
            stack.append(Block("if", current))
        elif v in ("for", "while"):
            names: list[tuple[str, int]] = []
            if v == "for":
                j = i + 1
                while j < len(tokens) and tokens[j].value not in ("=", "in", "do"):
                    if tokens[j].kind == "ident" and (j == i + 1 or tokens[j - 1].value == ","):
                        names.append((tokens[j].value, j))
                    j += 1
            stack.append(Block("loop_wait", current, header_start=i, loop_names=names))
        elif v == "do":
            if stack and stack[-1].kind == "loop_wait":
                block = stack[-1]
                block.kind = "loop"
                loop_scope = _create_scope(current, t.end, "loop")
                block.scope = loop_scope
                for name, ni in block.loop_names:
                    b = Binding(name, ni, loop_scope, t.end, role="loop")
                    loop_scope.bindings.append(b)
                    bindings.append(b)
                    decl_tokens[ni] = b
                current = loop_scope
            else:
                scope = _create_scope(current, t.end, "do")
                stack.append(Block("do", current, scope))
                current = scope
        elif v == "then":
            if stack and stack[-1].kind == "if" and stack[-1].scope is None:
                scope = _create_scope(current, t.end, "if-branch")
                stack[-1].scope = scope
                current = scope
        elif v == "repeat":
            scope = _create_scope(current, t.end, "repeat")
            stack.append(Block("repeat", current, scope))
            current = scope
        i += 1

    for block in stack:
        if block.scope is not None and block.scope.end > len(source):
            diagnostics.append(f"unclosed '{block.kind}' block beginning near character {block.scope.start}")

    for i, tok in enumerate(tokens):
        if tok.kind != "ident" or i in decl_tokens:
            continue
        if i > 0 and tokens[i - 1].value in (".", ":"):
            continue
        if i + 1 < len(tokens) and tokens[i + 1].value == "=" and i > 0 and tokens[i - 1].value in ("{", ",", ";"):
            continue
        scope = token_scopes.get(i, root)
        found = None
        while scope is not None:
            for b in reversed(scope.bindings):
                if b.name == tok.value and tok.start >= b.active_from:
                    found = b
                    break
            if found:
                break
            scope = scope.parent
        if found:
            found.refs.append(i)
    attach_function_bodies(source, tokens, bindings)
    return tokens, bindings, decl_tokens, token_scopes, diagnostics


def infer_missing_services(
    source: str, tokens: list[Token], bindings: list[Binding],
    decl_tokens: dict[int, Binding], token_scopes: dict[int, Scope],
) -> tuple[str, list[str]]:
    """Add GetService aliases only for bare, otherwise-unbound Roblox service names."""
    missing: list[str] = []
    seen: set[str] = set()
    for i, tok in enumerate(tokens):
        if tok.kind != "ident" or tok.value not in SERVICE_NAMES or i in decl_tokens:
            continue
        if i > 0 and tokens[i - 1].value in (".", ":"):
            continue
        if i + 1 < len(tokens) and tokens[i + 1].value == "=" and i > 0 and tokens[i - 1].value in ("{", ",", ";"):
            continue
        scope = token_scopes.get(i)
        resolved = False
        while scope is not None:
            if any(b.name == tok.value and tok.start >= b.active_from for b in reversed(scope.bindings)):
                resolved = True
                break
            scope = scope.parent
        if not resolved and tok.value not in seen:
            seen.add(tok.value)
            missing.append(tok.value)
    if not missing:
        return source, []
    first_code = tokens[0].start if tokens else len(source)
    prefix, body = source[:first_code], source[first_code:]
    aliases = "\n".join(f'local {name} = game:GetService("{name}")' for name in missing)
    spacer = "" if not prefix or prefix.endswith("\n") else "\n"
    # Keep inferred aliases adjacent to service declarations already at the top.
    return prefix + spacer + aliases + "\n" + body, missing


def _token_slice(source: str, tokens: list[Token], start_index: int, end_index: int) -> str:
    if start_index >= end_index or start_index >= len(tokens):
        return ""
    end_index = min(end_index, len(tokens))
    return source[tokens[start_index].start:tokens[end_index - 1].end]


def _function_context(tokens: list[Token], index: int) -> str:
    vals = [t.value for t in tokens[max(0, index - 12):index]]
    for event in ("CharacterAdded", "PlayerAdded", "InputBegan", "InputChanged", "OnClientEvent", "Heartbeat", "RenderStepped", "Stepped", "ChildAdded", "DescendantAdded", "MouseButton1Click", "MouseButton1Down", "MouseEnter", "MouseLeave"):
        if event in vals:
            return event
    return ""


def infer_binding_names(source: str, tokens: list[Token], bindings: list[Binding], decl_tokens: dict[int, Binding]) -> None:
    """Use initialization, member access, and callback context for conservative names."""
    value_tokens = [t.value for t in tokens]
    for b in bindings:
        if not GARBAGE_IDENT.fullmatch(b.name):
            continue
        i = b.token_index
        init = ""
        if b.role == "local":
            j = i + 1
            while j < len(tokens) and tokens[j].line == tokens[i].line and tokens[j].value not in ("=", ";"):
                j += 1
            if j < len(tokens) and tokens[j].value == "=":
                end = _statement_end(tokens, j + 1)
                init = _token_slice(source, tokens, j + 1, end)
        init_low = init.lower()
        hint: str | None = None

        service = re.search(r"GetService\s*\(\s*['\"]([A-Za-z0-9_]+)['\"]", init)
        if service and service.group(1) in SERVICE_NAMES:
            hint = service.group(1)
        elif ".LocalPlayer" in init:
            hint = "localPlayer"
        elif "loadstring" in init_low and "fluent" in init_low:
            if "savemanager" in init_low:
                hint = "saveManager"
            elif "interfacemanager" in init_low:
                hint = "interfaceManager"
            else:
                hint = "fluentLibrary"
        else:
            inst = re.search(r"Instance\s*\.\s*new\s*\(\s*['\"]([A-Za-z0-9_]+)['\"]", init)
            if inst:
                hint = inst.group(1)[0].lower() + inst.group(1)[1:]

        if hint is None:
            child = re.search(r"(?:WaitForChild|FindFirstChild)\s*\(\s*['\"]([^'\"]+)['\"]", init)
            if child:
                raw = child.group(1)
                hint = CHILD_NAMES.get(raw, raw[:1].lower() + raw[1:])
        if hint is None:
            event = re.search(r"\.([A-Za-z_][A-Za-z0-9_]*)\s*:\s*Connect\s*\(", init)
            if event:
                ev = event.group(1)
                hint = ev[0].lower() + ev[1:] + "Conn"

        ref_texts = [tokens[r].value for r in b.refs]
        local_context = " ".join(value_tokens[max(0, i - 10):min(len(tokens), i + 40)])
        assignment_rhs: list[str] = []
        for ref in b.refs:
            if ref + 1 < len(tokens) and tokens[ref + 1].value == "=":
                rhs_end = _statement_end(tokens, ref + 2)
                assignment_rhs.append(_token_slice(source, tokens, ref + 2, rhs_end))
        assignment_context = " ".join(assignment_rhs)
        if hint is None and b.role == "parameter":
            ctx = b.scope.function_context or _function_context(tokens, i)
            if b.scope.function_token is not None and b.scope.function_end is not None:
                function_tokens = tokens[b.scope.function_token:b.scope.function_end + 1]
                around = " ".join(t.value for t in function_tokens)
            else:
                around = " ".join(" ".join(value_tokens[max(0, r - 3):min(len(tokens), r + 12)]) for r in b.refs)
            if ctx == "CharacterAdded": hint = "character"
            elif ctx == "PlayerAdded": hint = "player"
            elif ctx in ("InputBegan", "InputChanged"): hint = "input"
            elif ctx == "OnClientEvent": hint = "action" if not ref_texts else "payload"
            elif ctx in ("Heartbeat", "RenderStepped", "Stepped"): hint = "deltaTime"
            elif ctx in ("ChildAdded", "DescendantAdded"): hint = "child"
            elif "KeyCode" in around or "UserInputType" in around: hint = "input"
            elif "string . sub" in around or (". Name" in around and "sub" in around): hint = "namePrefix"
            elif "Health" in around or "WalkSpeed" in around or "JumpPower" in around: hint = "humanoid"
            elif "HumanoidRootPart" in around or "FindFirstChild" in around: hint = "character"
            elif "Character" in around and "UserId" in around: hint = "player"
            elif b.name.lower() == "arg": hint = "argument"
            else: hint = "value"
        if hint is None and b.role == "local":
            if "task.spawn" in init or "task.defer" in init or "task.delay" in init:
                hint = "workerTask"
            elif init.strip() == "{}":
                hint = "state"
            elif init.startswith(('"', "'")):
                hint = "textValue"
            elif re.search(r"\btrue\b|\bfalse\b", init):
                hint = "isEnabled"
            elif any(tokens[r - 2].value == "WalkSpeed" for r in b.refs if r >= 2):
                hint = "walkSpeedValue"
            elif any(tokens[r - 2].value == "JumpPower" for r in b.refs if r >= 2):
                hint = "jumpPowerValue"
            elif "Stats" in local_context and "SelectedStat" in local_context:
                hint = "statNameMap"
            elif "Options" in local_context and "Value" in local_context:
                hint = "optionValue"
            elif "FireServer" in local_context:
                hint = "remoteArgument"
            elif "return" in local_context and "Health" in local_context:
                hint = "isAlive"
            else:
                hint = "value"

        all_expr = init + " " + assignment_context
        all_low = all_expr.lower()
        if b.name.lower().startswith("connection"):
            event = re.search(r"\.([A-Za-z_][A-Za-z0-9_]*)\s*:\s*Connect\s*\(", all_expr)
            hint = event.group(1)[0].lower() + event.group(1)[1:] + "Conn" if event else "eventConnection"
        if b.name.lower().startswith("thread"):
            if "autostoryline" in all_low: hint = "storylineTask"
            elif "automission" in all_low: hint = "missionTask"
            elif "automeditation" in all_low: hint = "meditationTask"
            elif "autofarmplayer" in all_low: hint = "playerFarmTask"
            elif "autoraid" in all_low: hint = "raidTask"
            elif "autoskill" in all_low: hint = "skillTask"
            elif "autoworkout" in all_low: hint = "workoutTask"
            elif "task.spawn" in all_low: hint = "backgroundTask"
        if b.name.lower().startswith("paragraph") and "addparagraph" in all_low:
            title = re.search(r"Title\s*=\s*['\"]([^'\"]+)", all_expr)
            if title:
                title_name = re.sub(r"[^A-Za-z0-9]+", " ", title.group(1)).strip().title().replace(" ", "")
                hint = title_name[:1].lower() + title_name[1:] + "Paragraph"
            else:
                hint = "statusParagraph"
        if b.name.lower().startswith("tbl"):
            if "AddTab" in all_expr: hint = "uiTabs"
            elif "npcName" in all_expr and "bossName" in all_expr: hint = "raidDefinitions"
            elif "StrengthStat" in all_expr or "DestructivePowerStat" in all_expr: hint = "statNameMap"
            elif "Storyline" in all_expr and "function" not in all_expr: hint = "questNames"
            elif "Dioraid" in all_expr or "Jotaro" in all_expr: hint = "raidDefinitions"
            elif "!code" in all_expr: hint = "redeemCodes"
            elif all_expr.strip() == "{}" or (".main" in assignment_context): hint = "taskHandles"
            elif "function" in all_expr and "autostoryline" in all_expr: hint = "automationChecks"
            elif "FireServer" in assignment_context and "trackquest" in all_low: hint = "questNameArguments"
        if b.name.lower().startswith("flag"):
            if "MouseButton1Click" in assignment_context or "MouseButton1Click" in local_context: hint = "toggleGuiEnabled"
            elif "Joined PvP Mission Queue" in all_expr or "Mission Complete" in all_expr: hint = "isInMissionQueue"
            elif "BodyVelocity" in all_expr or "BodyGyro" in all_expr or "bodyVelocity" in local_context: hint = "isFlightEnabled"
            elif "RetryRaidMode" in all_expr: hint = "retryRaidEnabled"
            elif "prestige" in all_low or "Prestige" in local_context: hint = "isPrestigeActive"
        if b.name == "n" and "FlySpeed" in assignment_context + local_context: hint = "flightSpeed"
        if b.name == "n2" or "StatAmountInput" in assignment_context + local_context: hint = "statUpgradeAmount"
        if b.name.lower() == "cframe": hint = "savedCFrame"

        if b.role == "local" and re.fullmatch(r"(?:fn\d+|f\d+|_l\d+|tween\d*)", b.name, re.I):
            body_context = b.function_body or " ".join(value_tokens[i:min(len(tokens), i + 35)])
            body_low = body_context.lower()
            if "tweenservice" in body_low or ("color3" in body_low and "backgroundcolor3" in body_low):
                hint = "updateButtonAppearance"
            elif "characteradded" in body_low and "wait" in body_low and "humanoidrootpart" in body_low:
                hint = "refreshCharacterReferences"
            elif "findfirstchildofclass" in body_low and "humanoid" in body_low and "health" in body_low:
                hint = "isCharacterAlive"
            elif "getplayers" in body_low and "name" in body_low and "table" in body_low:
                hint = "getPlayerNames"
            elif "getdescendants" in body_low and "proximityprompt" in body_low and "fireproximityprompt" in body_low:
                hint = "activateNpcPrompts"
            elif "questbrick" in body_low and "cframe" in body_low and "effects" in body_low:
                hint = "processQuestEffects"
            elif "trackedquest" in body_low and "farmquest" in body_low:
                hint = "isTrackedQuestComplete"
            elif "trackquest" in body_low and "fireserver" in body_low:
                hint = "setTrackedQuest"
            elif "getchildren" in body_low and "humanoid" in body_low and "string" in body_low and "name" in body_low:
                hint = "findLivingTarget"
            elif "farmquestconfig" in body_low and "trackedquest" in body_low:
                hint = "runQuestHandler"
            elif "task.cancel" in body_low and "getgenv" in body_low:
                hint = "stopAutomation"
            elif "task.spawn" in body_low and "getgenv" in body_low:
                hint = "startAutomation"
            elif "getdescendants" in body_low and "proximityprompt" in body_low:
                hint = "findNpcPrompts"
            elif "invokeserver" in body_low:
                hint = "invokeRemoteFunction"
            elif "fireserver" in body_low:
                hint = "sendRemoteEvent"
            elif b.function_context:
                hint = "on" + b.function_context[0].upper() + b.function_context[1:]
            elif "callback" in body_low and "return" in body_low:
                hint = "checkCallback"
            else:
                hint = "handleEvent"
        if b.name.lower().startswith("thread") and hint in (None, "value", "workerTask"):
            hint = "backgroundTask"
        if b.name.lower().startswith("connection") and hint in (None, "value"):
            hint = "eventConnection"
        if b.name.lower().startswith("flag") and hint in (None, "value", "isEnabled"):
            hint = "isFeatureEnabled"
        if b.name.lower().startswith("n") and hint == "value":
            hint = "numericValue"
        if b.name.lower().startswith("lib") and hint in (None, "value"):
            hint = "library"
        b.hint = hint or "value"


def rename_bindings(source: str, tokens: list[Token], bindings: list[Binding], decl_tokens: dict[int, Binding]) -> tuple[str, dict[str, int]]:
    infer_binding_names(source, tokens, bindings, decl_tokens)
    used = set(RESERVED) | {b.name for b in bindings if not GARBAGE_IDENT.fullmatch(b.name)}
    renamed: dict[str, int] = {}
    replacements: list[tuple[int, int, str]] = []
    for b in bindings:
        if not GARBAGE_IDENT.fullmatch(b.name):
            continue
        base = b.hint or "value"
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}{suffix}"
            suffix += 1
        b.new_name = candidate
        used.add(candidate)
        renamed[b.name] = renamed.get(b.name, 0) + 1
        decl_tok = tokens[b.token_index]
        replacements.append((decl_tok.start, decl_tok.end, candidate))
        for ri in b.refs:
            ref = tokens[ri]
            replacements.append((ref.start, ref.end, candidate))
    for start, end, new in sorted(replacements, reverse=True):
        source = source[:start] + new + source[end:]
    return source, renamed


def strip_banners(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if not BANNER_RE.match(line))


def strip_pure_junk(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if not PURE_STMT_RE.match(line) and not EMPTY_DO_RE.match(line))


def split_semicolons(source: str) -> str:
    """Expand statement separators; retain table semicolons as commas."""
    tokens = lex(source)
    depth = 0
    replacements: list[tuple[int, int, str]] = []
    for index, tok in enumerate(tokens):
        if tok.value == "{":
            depth += 1
        elif tok.value == "}":
            depth = max(0, depth - 1)
        elif tok.value == ";":
            following = source[tok.end:tok.end + 1]
            if depth > 0:
                next_token = tokens[index + 1].value if index + 1 < len(tokens) else ""
                replacement = "" if next_token == "}" else ","
            else:
                replacement = "" if following in ("\n", "\r") else "\n"
            replacements.append((tok.start, tok.end, replacement))
    for start, end, replacement in reversed(replacements):
        source = source[:start] + replacement + source[end:]
    return source


def split_control_blocks(source: str) -> str:
    """Expand inline block statements without touching text inside strings/comments."""
    tokens = lex(source)
    insertions: set[int] = set()
    for index, tok in enumerate(tokens):
        if tok.kind != "keyword":
            continue
        value = tok.value
        line_start = source.rfind("\n", 0, tok.start) + 1
        has_code_before = bool(source[line_start:tok.start].strip())
        if value in ("local", "if", "for", "while", "repeat", "return", "end", "else", "elseif", "until") and has_code_before:
            previous = tokens[index - 1].value if index > 0 else ""
            already_after_opener = previous in ("then", "do", "else", "repeat", ";")
            if not already_after_opener and (value != "local" or (index > 0 and previous not in ("local", "function"))):
                insertions.add(tok.start)
        if value in ("then", "do", "else", "repeat"):
            line_end = source.find("\n", tok.end)
            if line_end < 0:
                line_end = len(source)
            if source[tok.end:line_end].strip():
                insertions.add(tok.end)
    for position in sorted(insertions, reverse=True):
        if position > 0 and source[position - 1] != "\n":
            source = source[:position] + "\n" + source[position:]
    return source


def normalize_spacing(source: str) -> str:
    """Normalize punctuation and binary operators without touching strings/comments."""
    tokens = lex(source)
    edits: dict[int, str] = {}
    binary_ops = {
        "=", "==", "~=", "<", ">", "<=", ">=", "+", "-", "*", "/", "//",
        "%", "^", "..", "+=", "-=", "*=", "/=", "%=", "^=",
    }
    unary_predecessors = {
        "", "(", "[", "{", ",", ";", "=", "==", "~=", "<", ">", "<=", ">=",
        "+", "-", "*", "/", "//", "%", "^", "..", "and", "or", "not",
        "then", "do", "return", "local", "in",
    }
    for index, tok in enumerate(tokens):
        previous = tokens[index - 1].value if index else ""
        if tok.value == ",":
            if tok.end < len(source) and source[tok.end] not in " \t\r\n":
                edits[tok.end] = " "
            continue
        if tok.value not in binary_ops and tok.value not in ("and", "or"):
            continue
        if tok.value in ("+", "-") and previous in unary_predecessors:
            continue
        if tok.start > 0 and source[tok.start - 1] not in " \t\r\n":
            edits[tok.start] = " "
        if tok.end < len(source) and source[tok.end] not in " \t\r\n":
            edits[tok.end] = " "
    for position, value in sorted(edits.items(), reverse=True):
        source = source[:position] + value + source[position:]
    return source


def _line_block_delta(line: str) -> tuple[int, int]:
    """Return leading outdent and net block depth using lexical tokens only."""
    toks = lex(line)
    words = [t.value for t in toks if t.kind == "keyword"]
    leading = 1 if words and words[0] in ("end", "until", "else", "elseif") else 0
    opens = sum(1 for x in words if x in ("function", "then", "do", "repeat", "else"))
    closes = sum(1 for x in words if x in ("end", "until", "elseif", "else"))
    return leading, opens - closes


def indent_source(source: str) -> str:
    out: list[str] = []
    depth = 0
    table_depth = 0
    for raw in source.splitlines():
        text = raw.strip()
        if not text:
            out.append("")
            continue
        leading, delta = _line_block_delta(text)
        toks = lex(text)
        symbols = [t.value for t in toks if t.kind == "punct"]
        closes_table = 1 if symbols and symbols[0] == "}" else 0
        chain_indent = 1 if text.startswith((".", ":")) else 0
        out.append("    " * max(0, depth - leading + table_depth - closes_table + chain_indent) + text)
        depth = max(0, depth + delta)
        table_depth = max(0, table_depth + symbols.count("{") - symbols.count("}"))
    return "\n".join(out)



def _scope_distance(scope: Scope | None, ancestor: Scope) -> int | None:
    distance = 0
    current = scope
    while current is not None:
        if current is ancestor:
            return distance
        current = current.parent
        distance += 1
    return None


def canonicalize_service_calls(source: str) -> tuple[str, int]:
    """Reuse an in-scope GetService local instead of repeating game:GetService()."""
    tokens, bindings, _, token_scopes, _ = build_bindings(source, lex(source))
    service_bindings: list[tuple[Binding, str]] = []
    for binding in bindings:
        i = binding.token_index
        if binding.role != "local" or i + 7 >= len(tokens):
            continue
        seq = tokens[i:i + 8]
        if [t.value for t in seq[1:7]] != ["=", "game", ":", "GetService", "(", seq[6].value]:
            continue
        if seq[6].kind != "string" or seq[7].value != ")":
            continue
        service_name = seq[6].value[1:-1]
        if service_name in SERVICE_NAMES:
            service_bindings.append((binding, service_name))
    if not service_bindings:
        return source, 0

    replacements: list[tuple[int, int, str]] = []
    for i in range(len(tokens) - 6):
        seq = tokens[i:i + 7]
        if [t.value for t in seq[:6]] != ["game", ":", "GetService", "(", seq[4].value, ")"]:
            continue
        if seq[4].kind != "string":
            continue
        service_name = seq[4].value[1:-1]
        if service_name not in SERVICE_NAMES:
            continue
        scope = token_scopes.get(i)
        visible = []
        for binding, bound_service in service_bindings:
            if bound_service != service_name or tokens[i].start < binding.active_from:
                continue
            distance = _scope_distance(scope, binding.scope)
            if distance is None or tokens[i].start >= binding.scope.end:
                continue
            visible_names = []
            for candidate in bindings:
                if candidate.name != binding.name or tokens[i].start < candidate.active_from:
                    continue
                candidate_distance = _scope_distance(scope, candidate.scope)
                if candidate_distance is not None and tokens[i].start < candidate.scope.end:
                    visible_names.append((candidate_distance, -candidate.active_from, candidate))
            if visible_names:
                nearest = min(visible_names, key=lambda item: (item[0], item[1]))[2]
                if nearest is not binding:
                    continue
            visible.append((distance, -binding.active_from, binding))
        if visible:
            binding = min(visible, key=lambda item: (item[0], item[1]))[2]
            replacements.append((seq[0].start, seq[5].end, binding.name))
    for start, end, replacement in sorted(replacements, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source, len(replacements)


def add_top_level_section_spacing(source: str) -> str:
    """Separate top-level helper functions while preserving source order."""
    out: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        is_top_level_function = bool(re.match(r"^(?:local\s+)?function\b", stripped)) and not line[:1].isspace()
        if is_top_level_function and out and out[-1].strip():
            out.append("")
        out.append(line.rstrip())
    return "\n".join(out)


def find_unresolved_generated_identifiers(source: str) -> list[str]:
    """Find generated-looking bare identifiers with no local declaration."""
    tokens = significant(lex(source))
    _, _, declarations, _, _ = build_bindings(source, lex(source))
    unresolved: set[str] = set()
    for index, tok in enumerate(tokens):
        if tok.kind != "ident" or not GARBAGE_IDENT.fullmatch(tok.value):
            continue
        if index in declarations:
            continue
        if index > 0 and tokens[index - 1].value in (".", ":"):
            continue
        unresolved.add(tok.value)
    return sorted(unresolved, key=str.lower)


def split_chained_calls(source: str, indent_width: int = 4) -> tuple[str, int]:
    """Put each continuation in a method/property chain on its own indented line."""
    tokens = significant(lex(source))
    insertions: list[tuple[int, str]] = []
    for index in range(1, len(tokens)):
        token = tokens[index]
        previous = tokens[index - 1]
        if token.value not in (".", ":") or previous.value not in (")", "]", "}"):
            continue
        between = source[previous.end:token.start]
        if "\n" in between or "\r" in between:
            continue
        line_start = source.rfind("\n", 0, token.start) + 1
        leading = re.match(r"[ \t]*", source[line_start:token.start]).group(0)
        insertions.append((token.start, "\n" + leading + (" " * indent_width)))
    for position, text in reversed(insertions):
        source = source[:position] + text + source[position:]
    return source, len(insertions)


def split_table_fields(source: str) -> tuple[str, int]:
    """Move table fields onto separate lines while leaving call-argument commas alone."""
    tokens = significant(lex(source))
    paren_depth = bracket_depth = 0
    table_stack: list[tuple[int, int]] = []
    insertions: list[tuple[int, str]] = []
    for token in tokens:
        value = token.value
        if value == "(":
            paren_depth += 1
        elif value == ")":
            paren_depth = max(0, paren_depth - 1)
        elif value == "[":
            bracket_depth += 1
        elif value == "]":
            bracket_depth = max(0, bracket_depth - 1)
        elif value == "{":
            table_stack.append((paren_depth, bracket_depth))
        elif value == "}" and table_stack:
            table_stack.pop()
        elif value == "," and table_stack:
            table_paren, table_bracket = table_stack[-1]
            if paren_depth == table_paren and bracket_depth == table_bracket:
                following = source[token.end:token.end + 1]
                if following not in ("\n", "\r"):
                    insertions.append((token.end, "\n"))
    for position, text in reversed(insertions):
        source = source[:position] + text + source[position:]
    return source, len(insertions)


def find_stylua() -> str | None:
    """Resolve StyLua from STYLUA_BIN or PATH."""
    configured = os.environ.get("STYLUA_BIN")
    if configured:
        return configured if Path(configured).is_file() else None
    return shutil.which("stylua")


def format_with_stylua(source: str, timeout: int = 45) -> tuple[str | None, str | None]:
    """Format and parse the complete source with StyLua's Luau parser."""
    binary = find_stylua()
    if not binary:
        return None, "StyLua is not installed or was not found on PATH"
    config_path = Path(__file__).resolve().parents[1] / ".stylua.toml"
    command = [binary, "--syntax", "Luau", "--verify", "--stdin-filepath", "beautified.luau"]
    if config_path.is_file():
        command.extend(["--config-path", str(config_path)])
    command.append("-")
    try:
        completed = subprocess.run(
            command,
            input=source,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"StyLua could not run: {exc}"
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "StyLua rejected the input").strip()
        return None, message[:700]
    return completed.stdout, None

def collapse_blank_lines(source: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", source).strip() + "\n"


def is_trace_only(source: str) -> bool:
    body = source.strip()
    if not body:
        return True
    if re.search(r"BEHAVIOUR TRACE ONLY|statements recorded", body, re.I):
        if body.count("function") <= 2 and "DescendantAdded" in body and "math_floor_precision" in body:
            return True
    return False


def beautify(
    source: str,
    aggressive: bool = True,
    semantic: bool = True,
    return_report: bool = False,
    formatter: str = "auto",
):
    if formatter not in ("auto", "stylua", "fallback"):
        raise ValueError("formatter must be 'auto', 'stylua', or 'fallback'")
    if is_trace_only(source):
        out = "-- NOT SOURCE: behaviour / anti-tamper trace only\n-- No recoverable game logic in this input.\n"
        report = {
            "renamed_bindings": 0,
            "diagnostics": [],
            "formatter_used": "none",
            "formatter_warning": None,
        }
        return (out, report) if return_report else out

    source = source.replace("\r\n", "\n").replace("\r", "\n")
    source = strip_banners(source)
    source = split_semicolons(source)
    source = split_control_blocks(source)
    source = normalize_spacing(source)
    source = strip_pure_junk(source)

    rename_stats: dict[str, int] = {}
    diagnostics: list[str] = []
    inferred_services: list[str] = []
    canonicalized_service_calls = 0
    if aggressive or semantic:
        tokens, bindings, decl_tokens, token_scopes, diagnostics = build_bindings(source, lex(source))
        source, inferred_services = infer_missing_services(source, tokens, bindings, decl_tokens, token_scopes)
        if inferred_services:
            tokens, bindings, decl_tokens, _, refreshed_diagnostics = build_bindings(source, lex(source))
            diagnostics = refreshed_diagnostics
        if semantic:
            source, rename_stats = rename_bindings(source, tokens, bindings, decl_tokens)
        else:
            for binding in bindings:
                if GARBAGE_IDENT.fullmatch(binding.name):
                    binding.hint = "value"
            source, rename_stats = rename_bindings(source, tokens, bindings, decl_tokens)
        source, canonicalized_service_calls = canonicalize_service_calls(source)

    unresolved_generated = find_unresolved_generated_identifiers(source)
    if unresolved_generated:
        diagnostics.append("unbound generated-looking identifiers retained: " + ", ".join(unresolved_generated))

    formatter_used = "fallback"
    formatter_warning = None
    if formatter in ("auto", "stylua"):
        formatted, formatter_error = format_with_stylua(source)
        if formatted is not None:
            source = formatted
            formatter_used = "stylua"
            # StyLua parsed and verified the result, so token-based block warnings
            # from the conservative fallback scanner are no longer authoritative.
            diagnostics = [
                item for item in diagnostics
                if item.startswith("unbound generated-looking identifiers retained:")
            ]
        elif formatter == "stylua":
            raise RuntimeError(formatter_error or "StyLua formatting failed")
        else:
            formatter_warning = formatter_error

    chain_breaks = 0
    table_breaks = 0
    if formatter_used == "fallback":
        source, table_breaks = split_table_fields(source)
        source, chain_breaks = split_chained_calls(source)
        source = indent_source(source)
        source = add_top_level_section_spacing(source)
    else:
        source, chain_breaks = split_chained_calls(source)
        source = add_top_level_section_spacing(source)
    source = collapse_blank_lines(source)

    if not source.startswith("-- Beautified"):
        source = "-- Beautified from deobfuscator output\n\n" + source
    if diagnostics:
        notes = "\n".join("-- Beautifier note: " + item for item in diagnostics)
        source = source.replace(
            "-- Beautified from deobfuscator output\n",
            "-- Beautified from deobfuscator output\n" + notes + "\n",
        )

    remaining_garbage = sum(
        1 for token in significant(lex(source))
        if token.kind == "ident" and GARBAGE_IDENT.fullmatch(token.value)
    )
    report = {
        "renamed_bindings": sum(rename_stats.values()),
        "renamed_names": len(rename_stats),
        "inferred_services": inferred_services,
        "canonicalized_service_calls": canonicalized_service_calls,
        "chain_breaks": chain_breaks,
        "table_field_breaks": table_breaks,
        "unresolved_generated_identifiers": unresolved_generated,
        "diagnostics": diagnostics,
        "remaining_garbage": remaining_garbage,
        "formatter_used": formatter_used,
        "formatter_warning": formatter_warning,
        "ast_formatted": formatter_used == "stylua",
    }
    return (source, report) if return_report else source


def main() -> int:
    parser = argparse.ArgumentParser(description="Scope-aware Roblox Luau beautifier")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--no-semantic", action="store_true")
    parser.add_argument("--report", action="store_true", help="print rename and structural diagnostics")
    parser.add_argument(
        "--formatter",
        choices=("auto", "stylua", "fallback"),
        default="auto",
        help="auto uses StyLua when installed; fallback handles malformed/incomplete decompiler output",
    )
    args = parser.parse_args()
    raw = args.input.read_text(encoding="utf-8", errors="replace")
    try:
        out, report = beautify(
            raw,
            aggressive=True,
            semantic=not args.no_semantic,
            return_report=True,
            formatter=args.formatter,
        )
    except RuntimeError as exc:
        print(f"formatting failed: {exc}", file=sys.stderr)
        return 2
    if args.output:
        args.output.write_text(out, encoding="utf-8")
        print(f"wrote {args.output} ({len(out)} bytes)", file=sys.stderr)
    else:
        sys.stdout.write(out)
    if args.report:
        print(report, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
