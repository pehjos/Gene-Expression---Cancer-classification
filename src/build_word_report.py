"""Create a submission-ready Word report from the verified Markdown results."""
from pathlib import Path
import re
import json

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import (WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING,
                            WD_TAB_ALIGNMENT, WD_TAB_LEADER)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/academic_report.md"
OUTPUT = ROOT / "output/docx/academic_report_APA7.docx"
FIGURES = ROOT / "reports/figures"


def set_font(run, size=12, bold=False, italic=False):
    run.font.name = "Times New Roman"
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Times New Roman")
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=90, start=100, bottom=90, end=100):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color="D9D9D9", size="6"):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), size)
        tag.set(qn("w:color"), color)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    value = OxmlElement("w:t")
    value.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, separate, value, end])
    set_font(run, 10)


def configure_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal.font.size = Pt(12)
    pf = normal.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_after = Pt(6)

    for name, size, before, after in (
        ("Title", 18, 0, 12),
        ("Heading 1", 14, 12, 6),
        ("Heading 2", 12, 10, 4),
    ):
        style = doc.styles[name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        # Word's built-in Title style can carry a colored bottom border.
        # Academic submission formatting here uses typography and whitespace only.
        p_pr = style._element.get_or_add_pPr()
        p_bdr = p_pr.find(qn("w:pBdr"))
        if p_bdr is not None:
            p_pr.remove(p_bdr)


def add_title_page(doc, title):
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run(title), 18, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run("Academic Bioinformatics Project Report"), 14, bold=True)
    doc.add_paragraph()
    members_path = ROOT / "reports/group_members.json"
    members = json.loads(members_path.read_text(encoding="utf-8")) if members_path.exists() else []
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(6)
    set_font(p.add_run("Group Members"), 12, bold=True)
    if members:
        for member in members:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(3)
            set_font(p.add_run(f"{member['name']}  -  {member['index_number']}"), 12)
    else:
        for _ in range(2):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(3)
            set_font(p.add_run("____________________________  -  ________________"), 12)
    doc.add_paragraph()
    details = [
        ("Course", "________________________________________"),
        ("Lecturer", "________________________________________"),
        ("Institution", "________________________________________"),
    ]
    for label, value in details:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.2)
        p.paragraph_format.right_indent = Inches(0.2)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(1.8), WD_TAB_ALIGNMENT.LEFT)
        set_font(p.add_run(label), 12, bold=True)
        set_font(p.add_run(f"\t{value}"), 12)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run("Dataset: UCI Gene Expression Cancer RNA-Seq (ID 401)"), 12)
    set_font(p.add_run("\nSubmission date: ____________________"), 12)
    doc.add_page_break()


def add_contents(doc, headings):
    p = doc.add_paragraph(style="Heading 1")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run("Table of Contents"), 14, bold=True)
    page_map = {
        "Abstract": 3, "Introduction": 3, "Problem statement": 3,
        "Aim and objectives": 3, "Literature background": 4,
        "Dataset description": 4, "Methodology": 5,
        "Feature processing and model specifications": 5,
        "Metrics and visualization protocol": 6, "Results": 6,
        "Discussion": 10, "Limitations": 11, "Conclusion": 11,
        "Reproducibility and saved artifacts": 12, "References": 12,
    }
    for heading in headings:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.2)
        p.paragraph_format.right_indent = Inches(0.2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.tab_stops.add_tab_stop(
            Inches(6.1), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS
        )
        set_font(p.add_run(f"{heading}\t{page_map[heading]}"), 12)
    doc.add_page_break()


def add_body_paragraph(doc, text, references=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if references else WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    if references:
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.first_line_indent = Inches(-0.3)
    set_font(p.add_run(text), 12)
    return p


def add_caption(doc, text, keep_next=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.keep_with_next = keep_next
    set_font(p.add_run(text), 11, bold=True)


def add_markdown_table(doc, rows):
    headers = rows[0]
    body = rows[2:]
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for j, value in enumerate(headers):
        cell = table.rows[0].cells[j]
        set_cell_shading(cell, "1F4E78")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.0
        set_font(p.add_run(value), 10, bold=True)
        p.runs[-1].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_margins(cell)
    for i, values in enumerate(body):
        cells = table.add_row().cells
        for j, value in enumerate(values):
            cell = cells[j]
            if i % 2:
                set_cell_shading(cell, "EAF2F8")
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(0)
            set_font(p.add_run(value), 10)
            set_cell_margins(cell)
    set_table_borders(table)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def build():
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    title = lines[0].removeprefix("# ").strip()
    headings = [line[3:].strip() for line in lines if line.startswith("## ")]
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(0.85)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.different_first_page_header_footer = True
    configure_styles(doc)
    add_page_number(section.footer.paragraphs[0])
    add_title_page(doc, title)
    add_contents(doc, headings)

    i = 1
    current_section = ""
    pending_table_caption = None
    while i < len(lines):
        line = lines[i].strip()
        if not line or (i == 2 and line.startswith("Academic bioinformatics project")):
            i += 1
            continue
        if line.startswith("## "):
            current_section = line[3:].strip()
            p = doc.add_paragraph(style="Heading 1")
            set_font(p.add_run(current_section), 14, bold=True)
            i += 1
            continue
        if line.startswith("### "):
            pending_table_caption = line[4:].strip()
            i += 1
            continue
        image_match = re.fullmatch(r"!\[(.+?)\]\((.+?)\)", line)
        if image_match:
            caption, relative = image_match.groups()
            path = ROOT / "reports" / relative
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True
            width = Inches(5.9 if "top_genes" not in relative else 5.3)
            p.add_run().add_picture(str(path), width=width)
            picture = doc.inline_shapes[-1]
            picture._inline.docPr.set("descr", caption)
            picture._inline.docPr.set("title", caption.split(".", 1)[0])
            add_caption(doc, caption)
            i += 1
            continue
        if line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append([cell.strip() for cell in lines[i].strip().strip("|").split("|")])
                i += 1
            if pending_table_caption:
                add_caption(doc, pending_table_caption, keep_next=True)
                pending_table_caption = None
            add_markdown_table(doc, table_lines)
            continue
        add_body_paragraph(doc, line, references=current_section == "References")
        i += 1

    # Apply first-line indentation to ordinary body paragraphs, excluding headings,
    # captions, title matter, table cells and references.
    for p in doc.paragraphs:
        if p.style.name == "Normal" and p.text and p.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY:
            p.paragraph_format.first_line_indent = Inches(0.3)

    props = doc.core_properties
    props.title = title
    props.subject = "Academic bioinformatics machine-learning project using UCI dataset 401"
    props.keywords = "bioinformatics, gene expression, cancer classification, machine learning"
    props.author = "Student"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
