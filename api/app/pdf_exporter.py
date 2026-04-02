import io
import logging
from xml.sax.saxutils import escape

import requests
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import ExportBook

logger = logging.getLogger(__name__)

PAGE_WIDTH, PAGE_HEIGHT = A4
COVER_W = 2.8 * cm
COVER_H = 4.1 * cm


def _fetch_cover_image(cover_url: str | None) -> RLImage | None:
    """Scarica la copertina dal cover_url già disponibile nel risultato OPAC."""
    if not cover_url:
        return None

    try:
        response = requests.get(cover_url, timeout=8)
        if response.status_code != 200 or len(response.content) <= 500:
            return None

        img_buffer = io.BytesIO(response.content)
        Image.open(img_buffer).verify()
        img_buffer.seek(0)
        return RLImage(img_buffer, width=COVER_W, height=COVER_H)
    except Exception as error:
        logger.debug("copertina non scaricata | url=%s | error=%s", cover_url, error)
        return None


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def _cover_placeholder(styles_map: dict[str, ParagraphStyle]) -> Table:
    placeholder = Table(
        [[Paragraph("Nessuna<br/>copertina", styles_map["cover_placeholder"])]] ,
        colWidths=[COVER_W],
        rowHeights=[COVER_H],
    )
    placeholder.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return placeholder


def _format_availability(book: ExportBook) -> str:
    if book.available_copies and book.available_copies > 0:
        total = book.total_copies if book.total_copies is not None else "?"
        return f"Disponibile: {book.available_copies} copie su {total}"
    return "Attualmente non disponibile"


def _badge(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def _pill(text: str, style: ParagraphStyle) -> Table:
    pill = Table([[Paragraph(escape(text), style)]], hAlign="LEFT")
    pill.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return pill


def _build_badges(book: ExportBook, styles_map: dict[str, ParagraphStyle]) -> Table | None:
    badges = []

    if book.year:
        badges.append(_badge(f"Anno {book.year}", styles_map["badge_neutral"]))

    if book.material_type:
        badges.append(_badge(book.material_type.upper(), styles_map["badge_neutral"]))

    if book.score is not None:
        badges.append(_badge(f"score {book.score:.3f}", styles_map["badge_score"]))

    if not badges:
        return None

    badge_row = [*badges, ""]
    table = Table([badge_row], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _build_book_details(book: ExportBook, index: int, styles_map: dict[str, ParagraphStyle]):
    details = [
        _paragraph(f"{index}. {book.title}", styles_map["book_title"]),
        _paragraph(book.author or "Autore non disponibile", styles_map["author"]),
    ]

    badges = _build_badges(book, styles_map)
    if badges is not None:
        details.append(Spacer(1, 0.05 * cm))
        details.append(badges)

    meta_parts = [f"ID catalogo: {book.id}"]
    if not book.year:
        meta_parts.append("Anno non disponibile")
    details.append(_paragraph(" | ".join(meta_parts), styles_map["meta"]))
    details.append(_paragraph("Disponibilita", styles_map["section_label"]))
    details.append(_pill(_format_availability(book), styles_map["badge_availability"]))

    if book.summary:
        details.append(_paragraph("Abstract", styles_map["section_label"]))
        details.append(_paragraph(book.summary, styles_map["summary"]))

    details.append(
        Paragraph(
            f'<link href="{escape(book.source_url)}" color="#EA730B">Apri scheda OPAC</link>',
            styles_map["link"],
        )
    )
    return details


def generate_books_pdf(
    books: list[ExportBook],
    title: str = "Suggerimenti Libri",
    query: str = "",
) -> bytes:
    """
    Genera un PDF con la lista dei libri, copertine e informazioni.
    Restituisce i bytes del PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#2C3E50"),
        spaceAfter=0.3 * cm,
        alignment=TA_CENTER,
    )
    style_query = ParagraphStyle(
        "Query",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#7F8C8D"),
        spaceAfter=0.5 * cm,
        alignment=TA_CENTER,
        italics=True,
    )
    style_book_title = ParagraphStyle(
        "BookTitle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#2C3E50"),
        fontName="Helvetica-Bold",
        leading=14,
        spaceAfter=0.08 * cm,
    )
    style_author = ParagraphStyle(
        "Author",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=0.12 * cm,
    )
    style_meta = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=0.1 * cm,
    )
    style_availability = ParagraphStyle(
        "Availability",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#1D4ED8"),
        fontName="Helvetica-Bold",
        spaceAfter=0.12 * cm,
    )
    style_summary = ParagraphStyle(
        "Summary",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#111827"),
        spaceAfter=0.15 * cm,
    )
    style_section_label = ParagraphStyle(
        "SectionLabel",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#6B7280"),
        fontName="Helvetica-Bold",
        uppercase=True,
        spaceAfter=0.04 * cm,
    )
    style_link = ParagraphStyle(
        "Link",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#EA730B"),
        fontName="Helvetica-Bold",
        spaceBefore=0.05 * cm,
    )
    style_badge_neutral = ParagraphStyle(
        "BadgeNeutral",
        parent=styles["Normal"],
        fontSize=7.5,
        textColor=colors.HexColor("#4B5563"),
        backColor=colors.HexColor("#F3F4F6"),
        borderColor=colors.HexColor("#E5E7EB"),
        borderWidth=0.5,
        borderPadding=(2, 4, 2),
    )
    style_badge_score = ParagraphStyle(
        "BadgeScore",
        parent=styles["Normal"],
        fontSize=7.5,
        textColor=colors.HexColor("#374151"),
        backColor=colors.HexColor("#E5E7EB"),
        borderColor=colors.HexColor("#D1D5DB"),
        borderWidth=0.5,
        borderPadding=(2, 4, 2),
    )
    style_badge_availability = ParagraphStyle(
        "BadgeAvailability",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#1D4ED8"),
        backColor=colors.HexColor("#DBEAFE"),
        borderColor=colors.HexColor("#93C5FD"),
        borderWidth=0.5,
        borderPadding=(3, 5, 3),
        fontName="Helvetica-Bold",
    )
    style_cover_placeholder = ParagraphStyle(
        "CoverPlaceholder",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#6B7280"),
        alignment=TA_CENTER,
    )
    style_index = ParagraphStyle(
        "Index",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#BDC3C7"),
        alignment=TA_CENTER,
    )

    style_map = {
        "book_title": style_book_title,
        "author": style_author,
        "meta": style_meta,
        "availability": style_availability,
        "summary": style_summary,
        "section_label": style_section_label,
        "link": style_link,
        "badge_neutral": style_badge_neutral,
        "badge_score": style_badge_score,
        "badge_availability": style_badge_availability,
        "cover_placeholder": style_cover_placeholder,
    }

    story = []

    # --- Intestazione ---
    story.append(Paragraph(title, style_title))
    if query:
        story.append(Paragraph(f"Ricerca: <i>{query}</i>", style_query))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#BDC3C7")))
    story.append(Spacer(1, 0.4 * cm))

    # --- Righe libri ---
    for idx, book in enumerate(books, start=1):
        cover_cell = _fetch_cover_image(book.cover_url) or _cover_placeholder(style_map)
        info_content = _build_book_details(book, idx, style_map)

        row_data = [[cover_cell, info_content]]
        table = Table(
            row_data,
            colWidths=[COVER_W + 0.6 * cm, PAGE_WIDTH - 5 * cm - COVER_W],
        )
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1),
             [colors.HexColor("#F8F9FA") if idx % 2 == 0 else colors.white]),
            ("LINEBEFORE", (0, 0), (0, 0), 3, colors.HexColor("#EA730B")),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#E5E7EB")),
            ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ]))

        story.append(KeepTogether([table, Spacer(1, 0.3 * cm)]))

    # --- Footer ---
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#BDC3C7")))
    story.append(Paragraph(
        f"Totale: {len(books)} libri suggeriti — generato da AI Next Book",
        style_index,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()