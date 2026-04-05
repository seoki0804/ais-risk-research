#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import markdown


ROOT = Path("/Users/seoki/Desktop/research")
CSS = """
body {
  margin: 0;
  background: #f5f7fb;
  color: #132238;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
main {
  max-width: 980px;
  margin: 32px auto 64px;
  padding: 40px 48px;
  background: #ffffff;
  border: 1px solid #d9e3f0;
  border-radius: 20px;
  box-shadow: 0 16px 40px rgba(19, 34, 56, 0.08);
}
h1, h2, h3 {
  color: #0d1b2a;
  line-height: 1.2;
}
h1 { font-size: 2.2rem; margin-top: 0; }
h2 { margin-top: 2rem; font-size: 1.4rem; }
h3 { margin-top: 1.4rem; font-size: 1.1rem; }
p, li {
  font-size: 1rem;
  line-height: 1.65;
}
code {
  background: #eef3f9;
  padding: 0.12rem 0.35rem;
  border-radius: 6px;
}
pre code {
  display: block;
  padding: 1rem;
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0 1.4rem;
}
th, td {
  border: 1px solid #d9e3f0;
  padding: 0.7rem 0.8rem;
  text-align: left;
  vertical-align: top;
}
th { background: #eef3f9; }
img {
  max-width: 100%;
  height: auto;
  border: 1px solid #d9e3f0;
  border-radius: 14px;
  background: #ffffff;
}
a { color: #0f5dbb; text-decoration: none; }
a:hover { text-decoration: underline; }
blockquote {
  margin: 1rem 0;
  padding: 0.8rem 1rem;
  border-left: 4px solid #8ab4f8;
  background: #f7faff;
}
"""


def render_markdown(input_path: Path, output_path: Path) -> None:
    text = input_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "toc"],
        output_format="html5",
    )
    html = f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{input_path.stem} preview</title>
    <style>{CSS}</style>
  </head>
  <body>
    <main>
      {html_body}
    </main>
  </body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")


def main() -> None:
    render_markdown(ROOT / "README.md", ROOT / "README.rendered.html")
    render_markdown(ROOT / "PORTFOLIO_PUBLIC_PAGE.md", ROOT / "PORTFOLIO_PUBLIC_PAGE.rendered.html")
    print(ROOT / "README.rendered.html")
    print(ROOT / "PORTFOLIO_PUBLIC_PAGE.rendered.html")


if __name__ == "__main__":
    main()
