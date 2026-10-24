#!/usr/bin/env python3
"""Build the submission files from the Markdown in this folder.

  python3 paper/build.py          # writes paper/submission/

  manuscript.docx     the anonymised review copy (Word, the journal's source format)
  title-page.docx     author details and the declarations that identify the author
  highlights.docx     the highlights, in their own file as Elsevier asks
  cover-letter.docx   the cover letter
  preprint.pdf        the full paper with the author line and the figures, for a preprint server
  *.html              the same documents as HTML, which the Word and PDF files are made from

The Word files are written directly (Office Open XML with real headings, tables and
bullets); the PDF is printed from the HTML by Google Chrome, headless, if it is
installed. Standard library only otherwise. The figures come from paper/figures/ (run
paper/figures.py first).
"""
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "submission"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 25mm 22mm; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 11pt; line-height: 1.45; color: #111; max-width: 170mm; margin: 0 auto; }
h1 { font-size: 17pt; line-height: 1.25; margin: 0 0 8pt; }
h2 { font-size: 13pt; margin: 20pt 0 6pt; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; }
p { margin: 0 0 8pt; text-align: left; }
table { border-collapse: collapse; margin: 6pt 0 12pt; font-size: 9.5pt; width: 100%; }
th, td { border-top: 1px solid #999; border-bottom: 1px solid #999; padding: 3pt 6pt; text-align: left; vertical-align: top; }
th { border-bottom: 1px solid #333; }
ul { margin: 0 0 8pt 18pt; padding: 0; }
li { margin: 0 0 3pt; }
figure { margin: 12pt 0 16pt; page-break-inside: avoid; }
figure img { width: 100%; height: auto; display: block; border: 1px solid #ddd; }
figcaption { font-size: 9.5pt; margin-top: 4pt; }
.author { margin: 0 0 14pt; }
.refs p { font-size: 9.5pt; padding-left: 18pt; text-indent: -18pt; }
a { color: inherit; text-decoration: none; }
"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(s):
    s = esc(s)
    return re.sub(r"(https?://[^\s)]+)", r'<a href="\1">\1</a>', s)


def md_blocks(text):
    """Split Markdown into blocks: ('h', level, text), ('p', text), ('table', rows), ('ul', items)."""
    blocks = []
    for raw in re.split(r"\n\s*\n", text.strip()):
        lines = [l for l in raw.split("\n") if not l.strip().startswith("<!--")]
        if not lines:
            continue
        first = lines[0]
        if first.startswith("#"):
            level = len(first) - len(first.lstrip("#"))
            blocks.append(("h", level, first[level:].strip()))
        elif first.startswith("|"):
            rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines if not re.match(r"^\|\s*-", l)]
            blocks.append(("table", rows))
        elif first.startswith("- "):
            blocks.append(("ul", [l[2:].strip() for l in lines]))
        else:
            blocks.append(("p", " ".join(l.strip() for l in lines)))
    return blocks


def html_of(blocks, figures_dir=None, title=None):
    out, in_refs = [], False
    for b in blocks:
        kind = b[0]
        if kind == "h":
            level, text = b[1], b[2]
            if level == 2 and text == "References":
                in_refs = True
                out.append('<div class="refs">')
            out.append(f"<h{level}>{inline(text)}</h{level}>")
        elif kind == "table":
            rows = b[1]
            head = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
            out.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
        elif kind == "ul":
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in b[1]) + "</ul>")
        else:
            text = b[1]
            m = re.match(r"Figure (\d)\. ", text)
            if m and figures_dir:
                out.append(f'<figure><img src="{figures_dir}/figure-{m.group(1)}.svg" alt="Figure {m.group(1)}">'
                           f"<figcaption>{inline(text)}</figcaption></figure>")
            elif text.startswith("Ismat Samadov,") or text.startswith("E-mail:"):
                out.append(f'<p class="author">{inline(text)}</p>')
            else:
                out.append(f"<p>{inline(text)}</p>")
    if in_refs:
        out.append("</div>")
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{esc(title or 'Document')}</title><style>{CSS}</style></head><body>\n" + "\n".join(out) + "\n</body></html>\n")


# ---------------------------------------------------------------- Word (Office Open XML)

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
</Relationships>"""


def _style(sid, name, size, bold=False, before=0, after=120, based="Normal", keep=False):
    return (f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{name}"/><w:basedOn w:val="{based}"/>'
            f'<w:qFormat/><w:pPr><w:spacing w:before="{before}" w:after="{after}"/>{"<w:keepNext/>" if keep else ""}</w:pPr>'
            f'<w:rPr>{"<w:b/>" if bold else ""}<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr></w:style>')


STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {W}>
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
<w:sz w:val="24"/><w:szCs w:val="24"/><w:lang w:val="en-GB"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="360" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
{_style("Title", "Title", 32, True, 0, 240)}
{_style("Heading1", "heading 1", 28, True, 360, 120, keep=True)}
{_style("Heading2", "heading 2", 26, True, 300, 120, keep=True)}
{_style("Heading3", "heading 3", 24, True, 240, 120, keep=True)}
{_style("Caption", "caption", 22, False, 0, 120)}
<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:qFormat/>
<w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr><w:spacing w:after="60"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Reference"><w:name w:val="Reference"/><w:basedOn w:val="Normal"/><w:qFormat/>
<w:pPr><w:ind w:left="567" w:hanging="567"/><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders>
<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>
<w:insideH w:val="single" w:sz="4" w:space="0" w:color="999999"/></w:tblBorders>
<w:tblCellMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
</w:styles>"""

NUMBERING = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering {W}>
<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="singleLevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="&#8226;"/><w:lvlJc w:val="left"/>
<w:pPr><w:ind w:left="567" w:hanging="283"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/></w:rPr></w:lvl>
</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>"""


HEADING_SIZE = {"Title": 32, "Heading1": 28, "Heading2": 26, "Heading3": 24}


def _run(text, bold=False, size=None):
    rpr = ("<w:b/>" if bold else "") + (f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>' if size else "")
    return f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def _para(text, style=None):
    """Headings carry their size and weight on the run too, so they survive a reader that ignores styles."""
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}{_run(text, style in HEADING_SIZE, HEADING_SIZE.get(style))}</w:p>"


def _table(rows):
    cols = max(len(r) for r in rows)
    width = 9400 // cols
    grid = "".join(f'<w:gridCol w:w="{width}"/>' for _ in range(cols))
    out = [f'<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    for i, row in enumerate(rows):
        cells = "".join(f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>'
                        f'<w:p><w:pPr><w:spacing w:after="40" w:line="240" w:lineRule="auto"/></w:pPr>'
                        f'<w:r><w:rPr>{"<w:b/>" if i == 0 else ""}<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
                        f'<w:t xml:space="preserve">{esc(c)}</w:t></w:r></w:p></w:tc>' for c in row + [""] * (cols - len(row)))
        out.append(f"<w:tr>{'<w:trPr><w:tblHeader/></w:trPr>' if i == 0 else ''}{cells}</w:tr>")
    out.append("</w:tbl><w:p/>")
    return "".join(out)


def docx_of(blocks, path):
    body, in_refs = [], False
    for b in blocks:
        kind = b[0]
        if kind == "h":
            level, text = b[1], b[2]
            in_refs = in_refs or (level == 2 and text == "References")
            body.append(_para(text, "Title" if level == 1 else f"Heading{level - 1}"))
        elif kind == "table":
            body.append(_table(b[1]))
        elif kind == "ul":
            body.extend(_para(item, "ListBullet") for item in b[1])
        else:
            text = b[1]
            style = "Reference" if in_refs else "Caption" if re.match(r"(Figure|Table) \d\. ", text) else None
            body.append(_para(text, style))
    sect = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418" w:header="709" w:footer="709" w:gutter="0"/></w:sectPr>')
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {W}><w:body>'
                + "".join(body) + sect + "</w:body></w:document>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/numbering.xml", NUMBERING)
        z.writestr("word/document.xml", document)


def to_pdf(html_path, pdf_path):
    if not Path(CHROME).exists():
        print(f"  (Google Chrome not found; {pdf_path.name} not written)")
        return
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=10000",
                    f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()],
                   check=True, capture_output=True)


def preprint_blocks(manuscript, title_page):
    """The manuscript with the author line and the identifying declarations put back."""
    title = next(b for b in manuscript if b[0] == "h" and b[1] == 1)
    author = [b for b in title_page if b[0] == "p" and (b[1].startswith("Ismat Samadov,"))]
    decl = {b[1].split(":")[0]: b[1] for b in title_page if b[0] == "p" and ":" in b[1]}
    out = [title] + author
    skip = False
    for b in manuscript:
        if b[0] == "h" and b[1] == 1:
            continue
        if b[0] == "h" and b[1] == 2 and b[2] == "Highlights":
            skip = True
            continue
        if b[0] == "h" and b[1] == 2 and b[2] == "Abstract":
            skip = False
        if skip:
            continue
        if b[0] == "p" and b[1].startswith("Data and code availability:"):
            out.append(("p", decl["Data and code availability"]))
            continue
        if b[0] == "p" and b[1].startswith("Ethics:"):
            out.append(b)
            for key in ("Competing interests", "Funding", "Author contributions"):
                if key in decl:
                    out.append(("p", decl[key]))
            continue
        out.append(b)
    return out


def main():
    OUT.mkdir(exist_ok=True)
    manuscript = md_blocks((HERE / "manuscript.md").read_text(encoding="utf-8"))
    title_page = md_blocks((HERE / "title-page.md").read_text(encoding="utf-8"))
    cover = md_blocks((HERE / "cover-letter.md").read_text(encoding="utf-8")) if (HERE / "cover-letter.md").exists() else None
    highlights = [b for b in manuscript if b[0] == "ul"][:1]
    title = next(b[2] for b in manuscript if b[0] == "h" and b[1] == 1)
    docs = {
        "manuscript": (manuscript, title),
        "title-page": (title_page, "Title page"),
        "highlights": ([("h", 2, "Highlights")] + highlights, "Highlights"),
    }
    if cover:
        docs["cover-letter"] = (cover, "Cover letter")
    for name, (blocks, doc_title) in docs.items():
        (OUT / f"{name}.html").write_text(html_of(blocks, title=doc_title), encoding="utf-8")
        docx_of(blocks, OUT / f"{name}.docx")
        print(f"  {name}.html, {name}.docx")
    figures = HERE / "figures"
    (OUT / "figures").mkdir(exist_ok=True)
    for f in figures.glob("figure-*.svg"):
        shutil.copy(f, OUT / "figures" / f.name)
    pre = OUT / "preprint.html"
    pre.write_text(html_of(preprint_blocks(manuscript, title_page), figures_dir="figures", title=title), encoding="utf-8")
    to_pdf(pre, OUT / "preprint.pdf")
    print("  preprint.html, preprint.pdf")


if __name__ == "__main__":
    sys.exit(main())
