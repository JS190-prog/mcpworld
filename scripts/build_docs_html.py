from __future__ import annotations

import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    "terms-and-policy-map.md",
    "privacy-policy-outline.md",
    "business-disclosure.md",
    "consent-ui-plan.md",
    "local-agent-risk-notice.md",
    "data-retention-and-processing.md",
    "Auth_Legal_Addendum_Short.md",
    "MCP_SaaS_Webpage_Concept_Plan.md",
]


def inline_markdown(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def render_table(lines: list[str]) -> str:
    rows = []
    for index, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if index == 1 and all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        tag = "th" if index == 0 else "td"
        rows.append("<tr>" + "".join(f"<{tag}>{inline_markdown(cell)}</{tag}>" for cell in cells) + "</tr>")
    return "<div class=\"doc-table-wrap\"><table>" + "".join(rows) + "</table></div>"


def render_markdown(source: str) -> tuple[str, str]:
    title = "MCP World 문서"
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_lines: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append("<p>" + inline_markdown(" ".join(paragraph)) + "</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            blocks.append(render_table(table_lines))
            table_lines = []

    for raw_line in source.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                flush_paragraph()
                flush_list()
                flush_table()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            flush_table()
            continue
        if "|" in line and line.strip().startswith("|"):
            flush_paragraph()
            flush_list()
            table_lines.append(line)
            continue
        flush_table()
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(len(heading.group(1)), 4)
            text = heading.group(2).strip()
            if title == "MCP World 문서":
                title = re.sub(r"[*`]", "", text)
            blocks.append(f"<h{level}>{inline_markdown(text)}</h{level}>")
            continue
        item = re.match(r"^\s*[-*]\s+(.+)$", line)
        if item:
            flush_paragraph()
            list_items.append(inline_markdown(item.group(1).strip()))
            continue
        numbered = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if numbered:
            flush_paragraph()
            list_items.append(inline_markdown(numbered.group(1).strip()))
            continue
        paragraph.append(line.strip())

    flush_paragraph()
    flush_list()
    flush_table()
    if in_code:
        blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return title, "\n".join(blocks)


def build_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} | MCP World</title>
  <link rel="stylesheet" href="../styles.css">
</head>
<body class="doc-page">
  <header class="site-header">
    <nav class="nav" aria-label="문서 메뉴">
      <a class="brand" href="../index.html" aria-label="MCP World 홈">
        <span class="brand-mark">MW</span>
        <span>MCP World</span>
      </a>
      <div class="nav-actions">
        <a class="btn btn-ghost" href="../index.html">홈</a>
        <a class="btn btn-secondary" href="../dashboard.html">대시보드</a>
      </div>
    </nav>
  </header>
  <main class="section doc-shell">
    <article class="doc-content">
      {body}
    </article>
  </main>
</body>
</html>
"""


def main() -> None:
    docs_dir = ROOT / "docs"
    for name in DOCS:
        source_path = docs_dir / name
        title, body = render_markdown(source_path.read_text(encoding="utf-8-sig"))
        output_path = source_path.with_suffix(".html")
        output_path.write_text(build_page(title, body), encoding="utf-8", newline="\n")
        print(output_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
