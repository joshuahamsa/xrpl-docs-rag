from __future__ import annotations

import re

from xrpl_rag.code_map.models import CodeRecord, SourceFile, make_record_id


INCLUDE_RE = re.compile(r"^\s*#include\s+[<\"]([^>\"]+)[>\"]")
NAMESPACE_RE = re.compile(r"^\s*namespace\s+([A-Za-z_]\w*)\s*\{")
CLASS_RE = re.compile(r"^\s*(class|struct)\s+([A-Za-z_]\w*)\b")
CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
CONTROL_WORDS = {
    "if",
    "for",
    "while",
    "switch",
    "return",
    "sizeof",
    "static_cast",
    "dynamic_cast",
    "reinterpret_cast",
    "const_cast",
    "catch",
}


class CppAnalyzer:
    language = "cpp"

    def analyze(
        self, source_file: SourceFile, max_code_chars: int = 12_000
    ) -> list[CodeRecord]:
        try:
            text = source_file.path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return []

        lines = text.splitlines()
        imports = _extract_imports(lines)
        namespace_by_line = _namespace_context(lines)
        class_records = _extract_classes(source_file, lines, imports, namespace_by_line)
        function_records = _extract_functions(
            source_file, lines, imports, namespace_by_line, max_code_chars
        )
        return class_records + function_records


def _extract_imports(lines: list[str]) -> list[str]:
    imports: list[str] = []
    for line in lines:
        match = INCLUDE_RE.match(line)
        if match:
            imports.append(match.group(1))
    return imports


def _namespace_context(lines: list[str]) -> dict[int, str]:
    namespaces: list[tuple[int, str]] = []
    context: dict[int, str] = {}
    depth = 0

    for line_number, line in enumerate(lines, start=1):
        while namespaces and depth < namespaces[-1][0]:
            namespaces.pop()

        match = NAMESPACE_RE.match(line)
        if match:
            namespaces.append((depth + 1, match.group(1)))

        context[line_number] = "::".join(name for _, name in namespaces)
        depth += _brace_delta(line)
        while namespaces and depth < namespaces[-1][0]:
            namespaces.pop()

    return context


def _extract_classes(
    source_file: SourceFile,
    lines: list[str],
    imports: list[str],
    namespace_by_line: dict[int, str],
) -> list[CodeRecord]:
    records: list[CodeRecord] = []
    for index, line in enumerate(lines):
        match = CLASS_RE.match(line)
        if not match:
            continue

        line_start = index + 1
        line_end = _find_class_end(lines, index)
        code = "\n".join(lines[index:line_end])
        kind, name = match.groups()
        namespace = namespace_by_line.get(line_start, "")
        qualified_name = _qualify(namespace, name)
        records.append(
            CodeRecord(
                record_id=make_record_id(
                    source_file.relative_path, kind, qualified_name, line_start, code
                ),
                kind=kind,
                language="cpp",
                name=name,
                qualified_name=qualified_name,
                file=source_file.relative_path,
                line_start=line_start,
                line_end=line_end,
                namespace=namespace,
                imports=list(imports),
                code=code,
            )
        )
    return records


def _find_class_end(lines: list[str], start_index: int) -> int:
    for index in range(start_index, len(lines)):
        if "};" in lines[index]:
            return index + 1
    return start_index + 1


def _extract_functions(
    source_file: SourceFile,
    lines: list[str],
    imports: list[str],
    namespace_by_line: dict[int, str],
    max_code_chars: int,
) -> list[CodeRecord]:
    records: list[CodeRecord] = []
    index = 0
    while index < len(lines):
        start = _function_start(lines, index)
        if start is None:
            index += 1
            continue

        signature, open_brace_index = start
        raw_name = _raw_function_name(signature)
        if not raw_name:
            index += 1
            continue

        end_index = _find_balanced_body_end(lines, open_brace_index)
        line_start = index + 1
        line_end = end_index + 1
        full_code = "\n".join(lines[index : end_index + 1])
        namespace = namespace_by_line.get(line_start, "")
        class_name = _class_name_from_raw_name(raw_name)
        name = raw_name.split("::")[-1]
        qualified_name = _qualify(namespace, raw_name)
        code = _truncate_code(full_code, max_code_chars)
        calls = _extract_calls(full_code, name)
        records.append(
            CodeRecord(
                record_id=make_record_id(
                    source_file.relative_path,
                    "function",
                    qualified_name,
                    line_start,
                    full_code,
                ),
                kind="function",
                language="cpp",
                name=name,
                qualified_name=qualified_name,
                file=source_file.relative_path,
                line_start=line_start,
                line_end=line_end,
                class_name=class_name,
                namespace=namespace,
                signature=signature,
                docstring=_preceding_docstring(lines, index),
                imports=list(imports),
                code=code,
                calls=calls,
            )
        )
        index = end_index + 1
    return records


def _function_start(lines: list[str], index: int) -> tuple[str, int] | None:
    line = lines[index]
    stripped = line.strip()
    if not _can_start_signature(stripped):
        return None

    signature_lines: list[str] = []
    for cursor in range(index, min(len(lines), index + 12)):
        current = lines[cursor].strip()
        if not current:
            break
        signature_lines.append(current)
        signature = " ".join(part.replace("{", " ").strip() for part in signature_lines)
        if current.endswith(";"):
            return None
        if "{" in current:
            if _looks_like_function_signature(signature):
                return _normalize_space(signature), cursor
            return None
    return None


def _can_start_signature(stripped: str) -> bool:
    if not stripped or stripped.startswith(("#", "//", "/*", "*")):
        return False
    if stripped.startswith(("class ", "struct ", "enum ", "namespace ")):
        return False
    if stripped.split("(", 1)[0].strip() in CONTROL_WORDS:
        return False
    return "(" in stripped or re.search(r"\b[A-Za-z_]\w*(?:::[A-Za-z_]\w*)?\s*$", stripped)


def _looks_like_function_signature(signature: str) -> bool:
    signature = signature.strip()
    if not ("(" in signature and ")" in signature):
        return False
    prefix = signature.split("(", 1)[0].strip()
    if not prefix:
        return False
    raw_name = prefix.split()[-1].strip("*&")
    if raw_name in CONTROL_WORDS:
        return False
    if raw_name in {"class", "struct", "enum", "namespace"}:
        return False
    return bool(re.fullmatch(r"~?[A-Za-z_]\w*(?:::[~A-Za-z_]\w*)*", raw_name))


def _raw_function_name(signature: str) -> str:
    prefix = signature.split("(", 1)[0].strip()
    if not prefix:
        return ""
    return prefix.split()[-1].strip("*&")


def _find_balanced_body_end(lines: list[str], open_brace_index: int) -> int:
    depth = 0
    seen_open = False
    for index in range(open_brace_index, len(lines)):
        line = lines[index]
        depth += line.count("{")
        if "{" in line:
            seen_open = True
        depth -= line.count("}")
        if seen_open and depth <= 0:
            return index
    return open_brace_index


def _class_name_from_raw_name(raw_name: str) -> str:
    parts = raw_name.split("::")
    return parts[-2] if len(parts) > 1 else ""


def _extract_calls(code: str, function_name: str) -> list[str]:
    calls: list[str] = []
    seen: set[str] = set()
    for match in CALL_RE.finditer(_strip_comments_and_strings(code)):
        name = match.group(1)
        if name == function_name or name in CONTROL_WORDS:
            continue
        if name not in seen:
            seen.add(name)
            calls.append(name)
    return calls


def _strip_comments_and_strings(code: str) -> str:
    code = re.sub(r"//.*", "", code)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
    code = re.sub(r"'(?:\\.|[^'\\])*'", "''", code)
    return code


def _preceding_docstring(lines: list[str], function_index: int) -> str:
    cursor = function_index - 1
    while cursor >= 0 and not lines[cursor].strip():
        cursor -= 1
    if cursor < 0:
        return ""

    stripped = lines[cursor].strip()
    if stripped.startswith("//"):
        comments: list[str] = []
        while cursor >= 0 and lines[cursor].strip().startswith("//"):
            comments.append(lines[cursor].strip().removeprefix("//").strip())
            cursor -= 1
        return "\n".join(reversed(comments)).strip()

    if stripped.endswith("*/"):
        comments: list[str] = []
        while cursor >= 0:
            line = lines[cursor].strip()
            comments.append(line)
            if line.startswith("/*"):
                break
            cursor -= 1
        return _clean_block_comment("\n".join(reversed(comments)))

    return ""


def _clean_block_comment(comment: str) -> str:
    comment = re.sub(r"^/\*", "", comment.strip())
    comment = re.sub(r"\*/$", "", comment.strip())
    lines = [line.strip().lstrip("*").strip() for line in comment.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _truncate_code(code: str, max_code_chars: int) -> str:
    marker = "[truncated]"
    if len(code) <= max_code_chars:
        return code
    if max_code_chars <= len(marker):
        return marker[:max_code_chars]
    return code[: max_code_chars - len(marker)].rstrip() + marker


def _qualify(namespace: str, name: str) -> str:
    return f"{namespace}::{name}" if namespace else name


def _brace_delta(line: str) -> int:
    cleaned = _strip_comments_and_strings(line)
    return cleaned.count("{") - cleaned.count("}")


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
