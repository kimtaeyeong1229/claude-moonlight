#!/usr/bin/env python3
"""Convert a paper's Korean markdown -> styled, Medium-like HTML with MathJax.

Usage:
    python3 build_paper.py <src.md> [out.html]

Math spans ($$...$$ and $...$) are protected with placeholders before markdown
conversion so the renderer can't mangle LaTeX, then restored for MathJax.
Tables are wrapped for horizontal scroll. Figures referenced as figures/*.png
work via relative paths.
"""
import re
import sys
import markdown

SRC = sys.argv[1] if len(sys.argv) > 1 else "paper.md"
OUT = sys.argv[2] if len(sys.argv) > 2 else SRC.rsplit(".", 1)[0] + ".html"

with open(SRC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
PAGE_TITLE = (m.group(1).strip() if m else "Paper") + " — 한국어"

# --- 1. Protect math spans ---
math_store = []

def stash(mo):
    math_store.append(mo.group(0))
    return f"@@MATH{len(math_store)-1}@@"

text = re.sub(r"\$\$.*?\$\$", stash, text, flags=re.DOTALL)
text = re.sub(r"(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$)", stash, text, flags=re.DOTALL)

# --- 2. Markdown -> HTML ---
html_body = markdown.markdown(
    text,
    extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
    output_format="html5",
)

# --- 3. Restore math ---
html_body = re.sub(r"@@MATH(\d+)@@", lambda mo: math_store[int(mo.group(1))], html_body)

# --- 4. Wrap tables for horizontal scroll ---
html_body = re.sub(r"(<table>.*?</table>)", r'<div class="table-wrap">\1</div>',
                   html_body, flags=re.DOTALL)

# --- 5. Page template ---
TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=Noto+Serif+KR:wght@400;600;700&display=swap" rel="stylesheet">
<script>
  window.MathJax = {
    tex: {
      inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
      displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
      tags: 'none'
    },
    options: { skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'] }
  };
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" id="MathJax-script" async></script>
<style>
  :root {
    --ink: #242424; --muted: #6b6b6b; --line: #e6e6e6;
    --accent: #1a8917; --boxbg: #fafafa; --maxw: 720px;
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  body {
    margin: 0; background: #fff; color: var(--ink);
    font-family: 'Noto Serif KR', Georgia, 'Times New Roman', serif;
    font-size: 20px; line-height: 1.85; word-break: keep-all; overflow-wrap: break-word;
  }
  .wrap { max-width: var(--maxw); margin: 0 auto; padding: 64px 24px 120px; }
  h1, h2, h3 {
    font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #111; line-height: 1.3; word-break: keep-all;
  }
  h1 { font-size: 2.1rem; font-weight: 900; text-align: center; margin: 0 0 .4em; letter-spacing: -0.01em; }
  .wrap > h3:first-of-type, h1 + h3 {
    text-align: center; font-weight: 500; font-size: 1.1rem; color: var(--muted); margin-top: 0;
  }
  h2 { font-size: 1.65rem; font-weight: 800; margin: 2.4em 0 .8em; padding-top: .4em; }
  h3 { font-size: 1.25rem; font-weight: 700; margin: 2em 0 .6em; }
  p { margin: 1.1em 0; text-align: left; }
  strong { font-weight: 700; color: #000; }
  a { color: var(--accent); text-decoration: none; border-bottom: 1px solid rgba(26,137,23,.4); }
  a:hover { border-bottom-color: var(--accent); }
  hr { border: none; border-top: 1px solid var(--line); margin: 3em auto; width: 60%; }
  ul, ol { margin: 1.1em 0; padding-left: 1.5em; }
  li { margin: .5em 0; }
  blockquote {
    margin: 1.6em 0; padding: 14px 22px; background: var(--boxbg);
    border-left: 4px solid var(--accent); border-radius: 0 8px 8px 0; color: #333;
  }
  blockquote p { margin: 0; }
  code {
    font-family: 'SFMono-Regular', Menlo, Consolas, monospace; background: #f2f2f2;
    padding: .08em .35em; border-radius: 4px; font-size: .86em; word-break: break-all;
  }
  .wrap p:has(> code:only-child) { text-align: center; }
  img {
    display: block; max-width: 100%; height: auto; margin: 2.4em auto .6em;
    border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 1px 14px rgba(0,0,0,.06);
    background: #fff; padding: 10px;
  }
  .figcaption {
    text-align: center; color: var(--muted); font-size: .92rem; line-height: 1.7;
    font-family: 'Noto Sans KR', sans-serif; margin: 0 auto 2.6em; max-width: 92%;
  }
  .boxtable { margin: 2.4em 0; border: 1px solid #d9d9d9; border-radius: 8px; overflow: hidden; background: #fff; }
  .boxtable-caption {
    text-align: center; color: var(--muted); font-size: .92rem; line-height: 1.7;
    font-family: 'Noto Sans KR', sans-serif; padding: 16px 20px; border-bottom: 1px solid var(--line); background: var(--boxbg);
  }
  .boxtable-body { padding: 20px 24px; font-size: .98rem; line-height: 1.9; }
  .boxtable-body p { margin: .55em 0; text-align: left; }
  .boxtable .prompt { color: #c0392b; font-weight: 600; }
  .boxtable .aha { color: #c0392b; }
  .table-wrap { overflow-x: auto; margin: 1.4em 0 2.6em; -webkit-overflow-scrolling: touch; }
  table { border-collapse: collapse; margin: 0 auto; font-family: 'Noto Sans KR', sans-serif; font-size: .9rem; min-width: 100%; }
  th, td { border: 1px solid var(--line); padding: 7px 12px; text-align: center; white-space: nowrap; }
  thead th { background: #2d2d2d; color: #fff; font-weight: 600; }
  tbody tr:nth-child(even) { background: #fafafa; }
  td:nth-child(2) { text-align: left; }
  table strong { color: var(--accent); }
  mjx-container[display="true"] { overflow-x: auto; overflow-y: hidden; max-width: 100%; padding: 6px 0; }
  @media (max-width: 600px) {
    body { font-size: 18px; } .wrap { padding: 40px 18px 90px; }
    h1 { font-size: 1.7rem; } h2 { font-size: 1.4rem; }
  }
</style>
</head>
<body>
<article class="wrap">
__BODY__
</article>
</body>
</html>
"""

out = TEMPLATE.replace("__TITLE__", PAGE_TITLE).replace("__BODY__", html_body)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(out)

print(f"Wrote {OUT} ({len(out):,} bytes); {len(math_store)} math spans protected.")
