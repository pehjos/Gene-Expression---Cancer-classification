"""Edit the user's existing Word report while preserving unrelated manual changes."""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "output/docx/academic_report.docx"


def style_run(run, size=12, bold=False, italic=False):
    run.font.name = "Times New Roman"
    rpr = run._element.get_or_add_rPr()
    rpr.rFonts.set(qn("w:ascii"), "Times New Roman")
    rpr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    rpr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)


def replace_text(paragraph, old, new):
    if old not in paragraph.text:
        return False
    text = paragraph.text.replace(old, new)
    paragraph.clear()
    style_run(paragraph.add_run(text))
    return True


def set_title_field(paragraph, text, *, centered=False, bold=False, size=12, after=4):
    paragraph.clear()
    paragraph.style = "Normal"
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.left_indent = Inches(0.5) if not centered else None
    paragraph.paragraph_format.first_line_indent = None
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(after)
    style_run(paragraph.add_run(text), size=size, bold=bold)


def add_segments(paragraph, segments):
    paragraph.clear()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.left_indent = Inches(0.5)
    paragraph.paragraph_format.first_line_indent = Inches(-0.5)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    paragraph.paragraph_format.space_after = Pt(6)
    for text, italic in segments:
        style_run(paragraph.add_run(text), italic=italic)


def main():
    doc = Document(PATH)
    ps = doc.paragraphs

    # Reuse the existing blank title-page paragraphs so manually edited body content,
    # figures, tables, section breaks, and pagination remain untouched.
    title_fields = [
        (7, "Group Members", True, True, 12, 7),
        (8, "Name: ______________________________________________", False, False, 12, 2),
        (9, "Index Number: _______________________________________", False, False, 12, 7),
        (10, "Name: ______________________________________________", False, False, 12, 2),
        (11, "Index Number: _______________________________________", False, False, 12, 7),
        (12, "Course: _____________________________________________", False, False, 12, 3),
        (13, "Lecturer: ____________________________________________", False, False, 12, 3),
        (14, "Institution: __________________________________________", False, False, 12, 3),
        (15, "Submission date: _____________________________________", False, False, 12, 3),
    ]
    for index, text, centered, bold, size, after in title_fields:
        set_title_field(ps[index], text, centered=centered, bold=bold, size=size, after=after)
    for index in (16, 17):
        ps[index].clear()
        ps[index].style = "Normal"
    ps[17].add_run().add_break(WD_BREAK.PAGE)

    # Convert the existing numbered in-text citations to APA 7 author-date form.
    replacements = [
        ("tumour types [2].", "tumour types (The Cancer Genome Atlas Research Network, 2013)."),
        ("cancer types [2].", "cancer types (The Cancer Genome Atlas Research Network, 2013)."),
        ("Ambroise and McLachlan showed", "Ambroise and McLachlan (2002) showed"),
        ("gene-expression classification [3].", "gene-expression classification."),
        ("estimates [3].", "estimates (Ambroise & McLachlan, 2002)."),
        ("leakage [4].", "leakage (Scikit-learn developers, n.d.-a)."),
        ("variables [5].", "variables (Scikit-learn developers, n.d.-b)."),
        ("expression data [1].", "expression data (Fiorini, 2016)."),
        ("CC BY 4.0 [1].", "CC BY 4.0 (Fiorini, 2016)."),
    ]
    for paragraph in ps:
        for old, new in replacements:
            replace_text(paragraph, old, new)

    # Preserve the five existing reference paragraphs but replace their contents
    # with alphabetized APA 7 entries and the required hanging indentation.
    references = [
        [
            ("Ambroise, C., & McLachlan, G. J. (2002). Selection bias in gene extraction on the basis of microarray gene-expression data. ", False),
            ("Proceedings of the National Academy of Sciences, 99", True),
            ("(10), 6562-6566. https://doi.org/10.1073/pnas.102102699", False),
        ],
        [
            ("Fiorini, S. (2016). ", False),
            ("Gene expression cancer RNA-Seq", True),
            (" [Data set]. UCI Machine Learning Repository. https://doi.org/10.24432/C5R88H", False),
        ],
        [
            ("Scikit-learn developers. (n.d.-a). ", False),
            ("Common pitfalls and recommended practices", True),
            (". Scikit-learn. Retrieved September 23, 2026, from https://scikit-learn.org/stable/common_pitfalls.html", False),
        ],
        [
            ("Scikit-learn developers. (n.d.-b). ", False),
            ("Feature importances with a forest of trees", True),
            (". Scikit-learn. Retrieved September 23, 2026, from https://scikit-learn.org/stable/auto_examples/ensemble/plot_forest_importances.html", False),
        ],
        [
            ("The Cancer Genome Atlas Research Network. (2013). The Cancer Genome Atlas Pan-Cancer analysis project. ", False),
            ("Nature Genetics, 45", True),
            (", 1113-1120. https://doi.org/10.1038/ng.2764", False),
        ],
    ]
    ref_heading = next(i for i, p in enumerate(ps) if p.text.strip() == "References")
    ref_paragraphs = ps[ref_heading + 1: ref_heading + 6]
    if len(ref_paragraphs) != 5:
        raise RuntimeError("Expected five existing reference paragraphs.")
    for paragraph, segments in zip(ref_paragraphs, references):
        add_segments(paragraph, segments)

    doc.core_properties.subject = "Academic bioinformatics project report with APA 7th edition references"
    doc.save(PATH)
    print(PATH)


if __name__ == "__main__":
    main()
