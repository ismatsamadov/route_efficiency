#!/usr/bin/env python3
"""Check the manuscript against the journal's form and tidy its line wrapping.

  python3 paper/check.py              # counts and checks only
  python3 paper/check.py --wrap       # also re-wrap the prose at 88 characters

Reports the length of each highlight, the word counts (abstract; main text from the
Introduction to the Conclusions, with and without the tables; the whole with title,
keywords and figure captions), that every citation has a reference entry and every
entry is cited, and that figures and tables are first cited in order. Standard library only.
"""
import re
import sys
import textwrap
from pathlib import Path

PATH = Path(__file__).resolve().parent / "manuscript.md"
WIDTH = 88


def wrap(text):
    out, in_refs = [], False
    for line in text.split("\n"):
        if line.startswith("## References"):
            in_refs = True
        if in_refs or line.startswith(("|", "#", "- ", "<!--")) or not line.strip():
            out.append(line)
        else:
            out.extend(textwrap.wrap(line, width=WIDTH, break_long_words=False, break_on_hyphens=False))
    return "\n".join(out).rstrip("\n") + "\n"


def main():
    text = PATH.read_text(encoding="utf-8")
    if "--wrap" in sys.argv:
        text = wrap(text)
        PATH.write_text(text, encoding="utf-8")
    body, refs = text.split("## References")

    highlights = re.search(r"## Highlights\n\n(.*?)\n\n## Abstract", text, re.S).group(1)
    print("highlights (characters, at most 85):")
    for bullet in highlights.split("\n"):
        print(f"  {len(bullet[2:]):3d}  {bullet[2:]}")
    abstract = re.search(r"## Abstract\n\n(.*?)\n\nKeywords", text, re.S).group(1)
    print("abstract words:", len(abstract.split()))
    main_text = re.search(r"## 1\. Introduction(.*?)## Declarations", text, re.S).group(1)
    no_tables = " ".join(l for l in main_text.split("\n") if not l.startswith("|"))
    print("main text words, Introduction to Conclusions:", len(no_tables.split()),
          "without tables;", len(main_text.split()), "with table cells")
    captions = re.search(r"## Figures\n(.*?)$", body, re.S).group(1)
    title = len(text.split("\n")[0].lstrip("# ").split())
    keywords = len(re.search(r"Keywords:(.*?)\n", text).group(1).split())
    print("with title, abstract, keywords and figure captions:",
          title + len(abstract.split()) + keywords + len(no_tables.split()) + len(captions.split()))

    entries = [l for l in refs.split("\n") if l.strip()]
    keys = []
    for e in entries:
        m = re.match(r"(.+?) \((\d{4}[a-z]?)", e)
        keys.append((m.group(1), m.group(2)))
    cited = set()
    for m in re.finditer(r"\(([^()]*?\d{4}[a-z]?[^()]*)\)", body):
        for part in m.group(1).split(";"):
            name = re.sub(r",?\s*\d{4}[a-z]?.*$", "", part).strip()
            for year in re.findall(r"\d{4}[a-z]?", part):
                cited.add((name, year))
    for m in re.finditer(r"([A-Z][\w&\-\.' ]+?) \((\d{4}[a-z]?)\)", body):
        cited.add((m.group(1).strip(), m.group(2)))
    first_word = lambda n: n.replace(" et al.", "").split(",")[0].strip().split(" ")[0]
    never_cited = [f"{n} ({y})" for n, y in keys
                   if not any(y == cy and (n.split(",")[0].split(" &")[0].strip() in cn or cn.split(" ")[0] in n)
                              for cn, cy in cited)]
    no_entry = sorted(f"{cn} ({cy})" for cn, cy in cited
                      if not any(cy == y and first_word(cn) in n for n, y in keys)
                      and not re.match(r"(Houston|Barcelona|Dublin)", cn))
    print("reference entries:", len(entries))
    print("entries never cited:", never_cited or "none")
    print("citations without an entry:", no_entry or "none")
    figures = re.findall(r"Figure (\d)", body.split("## Figures")[0])
    tables = re.findall(r"Table (\d)", body)
    print("figures in order of first citation:", figures)
    print("tables in order of first citation:", tables)
    long_lines = [i + 1 for i, l in enumerate(body.split("\n")) if len(l) > WIDTH and not l.startswith(("|", "#", "<!--"))]
    print("prose lines over", WIDTH, "characters:", long_lines or "none")


if __name__ == "__main__":
    main()
