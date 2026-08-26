from __future__ import annotations

import ast
import inspect
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import yaml


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class ParsedPage:
    source_path: str
    title: str
    url: str
    text: str
    headings: list[str]
    source_name: str = "xrpl-docs"


def parse_markdown_file(path: Path, repo_root: Path) -> ParsedPage:
    raw = path.read_text(encoding="utf-8")
    metadata, body = _split_frontmatter(raw)
    text = _clean_mdx_lines(body)
    headings = _extract_headings(text)
    source_path = path.relative_to(repo_root).as_posix()
    title = _title_for_page(metadata, headings, path)

    return ParsedPage(
        source_path=source_path,
        title=title,
        url=derive_docs_url(source_path),
        text=text.strip(),
        headings=headings,
    )


def parse_document_file(
    path: Path,
    repo_root: Path,
    url_base: str = "https://xrpl.org/docs/",
    source_url_base: str | None = None,
    source_name: str = "xrpl-docs",
    prefix_source_path: bool | None = None,
) -> ParsedPage:
    suffix = path.suffix.lower()
    should_prefix = (
        source_name != "xrpl-docs"
        if prefix_source_path is None
        else prefix_source_path
    )

    if suffix in {".md", ".mdx"}:
        page = parse_markdown_file(path, repo_root)
        if source_name == "xrpl-docs" and not should_prefix:
            return page
        return _with_source(
            page,
            source_name=source_name,
            source_path=_source_path(path, repo_root, source_name, should_prefix),
            url=derive_source_url(path.relative_to(repo_root).as_posix(), url_base),
        )
    if suffix == ".rst":
        return _parse_rst_file(path, repo_root, url_base, source_name, should_prefix)
    if suffix == ".html":
        return _parse_html_file(path, repo_root, url_base, source_name, should_prefix)
    if suffix == ".py":
        return _parse_python_file(
            path,
            repo_root,
            source_url_base or url_base,
            source_name,
            should_prefix,
        )
    raise ValueError(f"Unsupported docs file type: {path.suffix}")


def derive_docs_url(source_path: str) -> str:
    path = source_path
    if path.startswith("docs/"):
        path = path.removeprefix("docs/")
    path = re.sub(r"\.mdx?$", "", path)
    path = re.sub(r"/index$", "", path)
    return f"https://xrpl.org/docs/{path.strip('/')}"


def derive_source_url(source_path: str, url_base: str) -> str:
    path = source_path
    if path.startswith("docs/"):
        path = path.removeprefix("docs/")
    path = re.sub(r"\.mdx?$", "", path)
    path = re.sub(r"\.rst$", ".html", path)
    path = re.sub(r"/index$", "", path)
    return f"{url_base.rstrip('/')}/{path.strip('/')}"


def _parse_rst_file(
    path: Path,
    repo_root: Path,
    url_base: str,
    source_name: str,
    prefix_source_path: bool,
) -> ParsedPage:
    raw = path.read_text(encoding="utf-8")
    text = _clean_rst_text(raw)
    headings = _extract_rst_headings(raw)
    title = headings[0] if headings else path.stem
    relative_path = path.relative_to(repo_root).as_posix()
    return ParsedPage(
        source_path=_source_path(path, repo_root, source_name, prefix_source_path),
        title=title,
        url=derive_source_url(relative_path, url_base),
        text=text.strip(),
        headings=headings,
        source_name=source_name,
    )


def _parse_html_file(
    path: Path,
    repo_root: Path,
    url_base: str,
    source_name: str,
    prefix_source_path: bool,
) -> ParsedPage:
    parser = _DocsHTMLParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    relative_path = path.relative_to(repo_root).as_posix()
    title = parser.title()
    return ParsedPage(
        source_path=_source_path(path, repo_root, source_name, prefix_source_path),
        title=title or path.stem,
        url=derive_source_url(relative_path, url_base),
        text=parser.text().strip(),
        headings=parser.headings,
        source_name=source_name,
    )


def _parse_python_file(
    path: Path,
    repo_root: Path,
    url_base: str,
    source_name: str,
    prefix_source_path: bool,
) -> ParsedPage:
    raw = path.read_text(encoding="utf-8")
    tree = ast.parse(raw)
    relative_path = path.relative_to(repo_root).as_posix()
    module_name = _module_name(relative_path)
    headings = [module_name]
    lines = [f"# {module_name}"]
    module_doc = ast.get_docstring(tree)
    if module_doc:
        lines.extend(["", inspect.cleandoc(module_doc)])

    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            _append_python_object(lines, headings, node)

    return ParsedPage(
        source_path=_source_path(path, repo_root, source_name, prefix_source_path),
        title=module_name,
        url=derive_source_url(relative_path, url_base),
        text="\n".join(lines).strip(),
        headings=headings,
        source_name=source_name,
    )


def _with_source(
    page: ParsedPage, source_name: str, source_path: str, url: str
) -> ParsedPage:
    return ParsedPage(
        source_path=source_path,
        title=page.title,
        url=url,
        text=page.text,
        headings=page.headings,
        source_name=source_name,
    )


def _source_path(
    path: Path, repo_root: Path, source_name: str, prefix_source_path: bool
) -> str:
    relative_path = path.relative_to(repo_root).as_posix()
    if not prefix_source_path:
        return relative_path
    return f"{source_name}:{relative_path}"


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw

    parsed = yaml.safe_load(match.group(1)) or {}
    if not isinstance(parsed, dict):
        parsed = {}
    return parsed, raw[match.end() :]


def _clean_mdx_lines(text: str) -> str:
    cleaned: list[str] = []
    in_code_block = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            cleaned.append(line)
            continue
        if not in_code_block and _is_mdx_only_line(stripped):
            continue
        cleaned.append(line)

    return "\n".join(cleaned)


def _is_mdx_only_line(stripped: str) -> bool:
    if not stripped:
        return False
    if stripped.startswith(("import ", "export ")):
        return True
    return bool(re.fullmatch(r"</?[A-Z][A-Za-z0-9_.:-]*(\s+[^>]*)?/?>", stripped))


def _extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    in_code_block = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        match = HEADING_RE.match(stripped)
        if match:
            headings.append(_clean_heading(match.group(2)))
    return headings


def _extract_rst_headings(text: str) -> list[str]:
    headings: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines[:-1]):
        title = line.strip()
        underline = lines[index + 1].strip()
        if title and _is_rst_heading_underline(underline, len(title)):
            headings.append(_clean_heading(title))
    return headings


def _clean_rst_text(text: str) -> str:
    cleaned: list[str] = []
    lines = text.splitlines()
    skip_directive_options = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        previous_line = lines[index - 1].strip() if index > 0 else ""
        if _is_rst_heading_underline(stripped, len(previous_line)):
            continue
        if stripped and _is_rst_heading_underline(next_line, len(stripped)):
            cleaned.append(f"{'#' * _rst_heading_level(next_line)} {stripped}")
            skip_directive_options = False
            continue
        if stripped.startswith(".. "):
            skip_directive_options = True
            continue
        if skip_directive_options and line.startswith("   :"):
            continue
        skip_directive_options = False
        cleaned.append(_clean_rst_inline_markup(line))

    return "\n".join(cleaned)


def _is_rst_heading_underline(text: str, title_length: int) -> bool:
    if title_length <= 0 or len(text) < title_length:
        return False
    return bool(re.fullmatch(r"([=\-~^\"'#*+`])\1*", text))


def _clean_rst_inline_markup(text: str) -> str:
    text = re.sub(r"``([^`]+)``", r"`\1`", text)
    text = re.sub(r"`([^`<]+?)\s*<[^>]+>`_", r"\1", text)
    return text


def _rst_heading_level(underline: str) -> int:
    levels = {"=": 1, "-": 2, "~": 3, "^": 4, '"': 5}
    return levels.get(underline[:1], 6)


def _module_name(relative_path: str) -> str:
    return re.sub(r"\.py$", "", relative_path).replace("/", ".")


def _append_python_object(
    lines: list[str],
    headings: list[str],
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
    parent: str | None = None,
) -> None:
    name = f"{parent}.{node.name}" if parent else node.name
    if node.name.startswith("_"):
        return

    headings.append(name)
    level = "###" if parent else "##"
    lines.extend(["", f"{level} {name}", "", _python_signature(node)])
    docstring = ast.get_docstring(node)
    if docstring:
        lines.extend(["", inspect.cleandoc(docstring)])

    if isinstance(node, ast.ClassDef):
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _append_python_object(lines, headings, child, parent=node.name)


def _python_signature(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    if isinstance(node, ast.ClassDef):
        bases = ", ".join(ast.unparse(base) for base in node.bases)
        return f"class {node.name}({bases})" if bases else f"class {node.name}"

    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix} {node.name}({ast.unparse(node.args)}){returns}"


def _title_for_page(metadata: dict[str, Any], headings: list[str], path: Path) -> str:
    title = metadata.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    if headings:
        return headings[0]
    return path.stem


def _clean_heading(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().strip("#")).strip()


class _DocsHTMLParser(HTMLParser):
    _SKIP_TAGS = {"button", "footer", "header", "nav", "script", "style"}
    _BLOCK_TAGS = {
        "article",
        "blockquote",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
        "ol",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._title_parts: list[str] = []
        self._heading_parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self._in_heading = False
        self.headings: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._in_heading = True
            self._heading_parts = []
            self._parts.append(f"\n{'#' * int(tag[1])} ")
            return
        if tag == "br":
            self._parts.append("\n")
        elif tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            heading = _clean_heading("".join(self._heading_parts))
            if heading:
                self.headings.append(heading)
            self._in_heading = False
            self._heading_parts = []
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
            return
        if self._in_heading:
            self._heading_parts.append(data)
        self._parts.append(data)

    def title(self) -> str:
        if self.headings:
            return self.headings[0]
        title = _clean_heading("".join(self._title_parts))
        return re.sub(r"\s+\|\s+xrpl$", "", title).strip()

    def text(self) -> str:
        return _normalize_html_text("".join(self._parts))


def _normalize_html_text(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    compacted: list[str] = []
    previous_blank = True
    for line in lines:
        if not line:
            if not previous_blank:
                compacted.append("")
            previous_blank = True
            continue
        compacted.append(line)
        previous_blank = False
    return "\n".join(compacted).strip()
