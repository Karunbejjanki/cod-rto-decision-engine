import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "founder_memo.md"
OUTPUT = ROOT / "docs" / "founder_memo.pdf"


def register_font() -> tuple[str, str]:
    options = [
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
    ]
    for regular, bold in options:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("MemoSans", str(regular)))
            pdfmetrics.registerFont(TTFont("MemoSans-Bold", str(bold)))
            pdfmetrics.registerFontFamily("MemoSans", normal="MemoSans", bold="MemoSans-Bold", italic="MemoSans", boldItalic="MemoSans-Bold")
            return "MemoSans", "MemoSans-Bold"
    raise RuntimeError("Install Arial or DejaVu Sans to render the rupee symbol in the memo PDF.")


def inline_markup(text: str) -> str:
    safe = html.escape(text, quote=False)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
    safe = re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', safe)
    return safe


def build_pdf() -> Path:
    regular, bold = register_font()
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("MemoTitle", parent=base["Title"], fontName=bold, fontSize=17, leading=20, textColor=colors.HexColor("#173f32"), alignment=TA_CENTER, spaceAfter=8),
        "heading": ParagraphStyle("MemoHeading", parent=base["Heading2"], fontName=bold, fontSize=11, leading=13, textColor=colors.HexColor("#176b52"), spaceBefore=7, spaceAfter=3),
        "body": ParagraphStyle("MemoBody", parent=base["BodyText"], fontName=regular, fontSize=8.7, leading=11.2, textColor=colors.HexColor("#24312b"), spaceAfter=4),
        "meta": ParagraphStyle("MemoMeta", parent=base["BodyText"], fontName=regular, fontSize=8.5, leading=10.5, textColor=colors.HexColor("#52625a"), spaceAfter=1),
        "bullet": ParagraphStyle("MemoBullet", parent=base["BodyText"], fontName=regular, fontSize=8.5, leading=10.8, textColor=colors.HexColor("#24312b"), spaceAfter=2),
    }
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter, rightMargin=42, leftMargin=42, topMargin=36, bottomMargin=34,
        title="Founder Memo: COD RTO Decision Pilot", author="COD RTO Decision Engine",
    )
    story = []
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    paragraph_lines: list[str] = []
    bullet_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            story.append(Paragraph(inline_markup(" ".join(paragraph_lines)), styles["body"]))
            paragraph_lines.clear()

    def flush_bullets() -> None:
        if bullet_lines:
            items = [ListItem(Paragraph(inline_markup(item), styles["bullet"]), leftIndent=9) for item in bullet_lines]
            story.append(ListFlowable(items, bulletType="bullet", start="square", leftIndent=11, bulletFontName=regular, bulletFontSize=5, bulletColor=colors.HexColor("#176b52")))
            story.append(Spacer(1, 2))
            bullet_lines.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_bullets()
        elif stripped.startswith("# "):
            flush_paragraph()
            flush_bullets()
            story.append(Paragraph(inline_markup(stripped[2:]), styles["title"]))
            story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#9ab9a8"), spaceAfter=6))
        elif stripped.startswith("## "):
            flush_paragraph()
            flush_bullets()
            story.append(Paragraph(inline_markup(stripped[3:]), styles["heading"]))
        elif stripped.startswith("- "):
            flush_paragraph()
            bullet_lines.append(stripped[2:])
        else:
            flush_bullets()
            target_style = styles["meta"] if stripped.startswith("**To:**") or stripped.startswith("**Date:**") or stripped.startswith("**Subject:**") else styles["body"]
            if target_style == styles["meta"]:
                flush_paragraph()
                story.append(Paragraph(inline_markup(stripped), target_style))
            else:
                paragraph_lines.append(stripped)
    flush_paragraph()
    flush_bullets()

    def footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont(regular, 7)
        canvas.setFillColor(colors.HexColor("#68766f"))
        canvas.drawString(42, 19, "Internal decision pilot · modeled estimates, not booked savings")
        canvas.drawRightString(letter[0] - 42, 19, f"{document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUTPUT


if __name__ == "__main__":
    print(build_pdf())