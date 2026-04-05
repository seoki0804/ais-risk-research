#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from PIL import Image as PILImage


ROOT = Path("/Users/seoki/Desktop/research")
OUTPUT_ROOT = ROOT / "outputs" / "presentation_deck_outline_61day_2026-03-13"
WORKBENCH = OUTPUT_ROOT / "workbenches" / "presentation_workbench_main_61day"
GENERATED = WORKBENCH / "generated_assets"

HOUSTON = OUTPUT_ROOT / "conference_print_assets_61day" / "figure1_holdout_compare_houston.png"
SCENARIO = OUTPUT_ROOT / "conference_print_assets_61day" / "figure2_scenario_aware_contour_compare.png"
REGIONAL = OUTPUT_ROOT / "conference_print_assets_61day" / "figure3_regional_failure_mode_schematic.png"
NOLA = GENERATED / "nola_holdout.png"
SEATTLE = GENERATED / "seattle_holdout.png"

OUT_8 = WORKBENCH / "presentation_8slide_production_draft_61day.pdf"
OUT_3 = WORKBENCH / "presentation_3minute_production_draft_61day.pdf"

PAGE_W = 13.333 * 72
PAGE_H = 7.5 * 72

BG = colors.HexColor("#f4f1e8")
INK = colors.HexColor("#1d2b2a")
SUB = colors.HexColor("#5a645f")
ACCENT = colors.HexColor("#225c55")
ACCENT_2 = colors.HexColor("#b98847")
WHITE = colors.white
LINE = colors.HexColor("#d0cbbf")
TABLE_HEAD = colors.HexColor("#e1e8e5")

FONT = "Helvetica"


def ensure_assets() -> None:
    missing = [p for p in [HOUSTON, SCENARIO, REGIONAL, NOLA, SEATTLE] if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing assets: {missing}")


def register_font() -> None:
    global FONT
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            pdfmetrics.registerFont(TTFont("DeckUnicode", str(candidate)))
            FONT = "DeckUnicode"
            return


def inch(value: float) -> float:
    return value * 72


def para_style(
    *,
    size: float = 18,
    color=INK,
    align=TA_LEFT,
    leading: float | None = None,
    left_indent: float = 0,
    first_line_indent: float = 0,
) -> ParagraphStyle:
    return ParagraphStyle(
        "deck-style",
        fontName=FONT,
        fontSize=size,
        leading=leading or size * 1.28,
        textColor=color,
        alignment=align,
        leftIndent=left_indent,
        firstLineIndent=first_line_indent,
        spaceAfter=0,
        spaceBefore=0,
    )


def rich_text(text: str) -> str:
    return escape(text).replace("\n", "<br/>")


def draw_paragraph(
    c: canvas.Canvas,
    x: float,
    y_top: float,
    w: float,
    text: str,
    *,
    size: float = 18,
    color=INK,
    align=TA_LEFT,
    leading: float | None = None,
    left_indent: float = 0,
    first_line_indent: float = 0,
) -> float:
    paragraph = Paragraph(
        rich_text(text),
        para_style(
            size=size,
            color=color,
            align=align,
            leading=leading,
            left_indent=left_indent,
            first_line_indent=first_line_indent,
        ),
    )
    _, height = paragraph.wrap(w, PAGE_H)
    paragraph.drawOn(c, x, PAGE_H - y_top - height)
    return height


def draw_bullets(
    c: canvas.Canvas,
    x: float,
    y_top: float,
    w: float,
    bullets: list[str],
    *,
    size: float = 18,
    color=INK,
    gap: float = 6,
) -> float:
    current_y = y_top
    total = 0.0
    for bullet in bullets:
        height = draw_paragraph(
            c,
            x,
            current_y,
            w,
            f"• {bullet}",
            size=size,
            color=color,
            left_indent=10,
            first_line_indent=-10,
            leading=size * 1.35,
        )
        current_y += height + gap
        total += height + gap
    return total


def draw_background(c: canvas.Canvas) -> None:
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)


def draw_header(c: canvas.Canvas, title: str, key: str) -> None:
    draw_paragraph(c, inch(0.55), inch(0.30), inch(9.6), title, size=28, color=INK)
    c.setFillColor(ACCENT)
    c.setStrokeColor(ACCENT)
    c.roundRect(inch(10.72), PAGE_H - inch(0.28) - inch(0.42), inch(1.9), inch(0.42), 8, stroke=1, fill=1)
    draw_paragraph(c, inch(10.72), inch(0.335), inch(1.9), key, size=14, color=WHITE, align=TA_CENTER)
    c.setFillColor(LINE)
    c.setStrokeColor(LINE)
    c.rect(inch(0.55), PAGE_H - inch(0.82) - inch(0.02), inch(12.2), inch(0.02), stroke=0, fill=1)


def draw_callout(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str, body: str, fill) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(fill)
    c.roundRect(inch(x), PAGE_H - inch(y) - inch(h), inch(w), inch(h), 10, stroke=1, fill=1)
    draw_paragraph(c, inch(x) + 10, inch(y) + 8, inch(w) - 20, title, size=15, color=WHITE)
    draw_paragraph(c, inch(x) + 10, inch(y) + 30, inch(w) - 20, body, size=12.5, color=WHITE, leading=16)


def draw_table(
    c: canvas.Canvas,
    x: float,
    y: float,
    col_widths: list[float],
    data: list[list[str]],
    *,
    font_size: float = 14,
) -> None:
    widths = [inch(value) for value in col_widths]
    table = Table(data, colWidths=widths)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEAD),
                ("BACKGROUND", (0, 1), (-1, -1), WHITE),
                ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                ("GRID", (0, 0), (-1, -1), 0.6, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    _, height = table.wrap(PAGE_W, PAGE_H)
    table.drawOn(c, inch(x), PAGE_H - inch(y) - height)


def draw_pipeline_box(c: canvas.Canvas, x: float, y: float, w: float, h: float, text: str, fill) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(fill)
    c.roundRect(inch(x), PAGE_H - inch(y) - inch(h), inch(w), inch(h), 8, stroke=1, fill=1)
    draw_paragraph(c, inch(x) + 8, inch(y) + 14, inch(w) - 16, text, size=14.5, color=WHITE, align=TA_CENTER)


def draw_image(c: canvas.Canvas, path: Path, x: float, y: float, w: float, h: float | None = None) -> None:
    img = ImageReader(str(path))
    iw, ih = PILImage.open(path).size
    target_w = inch(w)
    target_h = inch(h) if h is not None else target_w * (ih / iw)
    if h is not None:
        scale = min(target_w / iw, target_h / ih)
        draw_w = iw * scale
        draw_h = ih * scale
    else:
        draw_w = target_w
        draw_h = target_h
    x_pt = inch(x) + max(0, (target_w - draw_w) / 2)
    y_pt = PAGE_H - inch(y) - (h is not None and inch(h) or draw_h) + max(0, ((h is not None and inch(h) or draw_h) - draw_h) / 2)
    c.drawImage(img, x_pt, y_pt, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")


def start_slide(c: canvas.Canvas, title: str, key: str) -> None:
    draw_background(c)
    draw_header(c, title, key)


def slide_problem(c: canvas.Canvas) -> None:
    start_slide(c, "왜 공간 표현인가", "Problem")
    draw_paragraph(c, inch(0.7), inch(1.2), inch(11.7), "문제는 위험 계산 부족이 아니라 위험 공간 표현 부족이다.", size=25, color=ACCENT)
    draw_bullets(
        c,
        inch(0.9),
        inch(2.05),
        inch(6.1),
        [
            "기존 AIS 분석은 pairwise 숫자 판단에 강하다.",
            "실제 의사결정은 \"내 배 주변 어디가 더 위험한가\"라는 공간 질문에 가깝다.",
            "본 프로젝트는 pairwise risk를 spatial field로 바꾼다.",
        ],
        size=19,
    )
    draw_callout(c, 7.6, 2.0, 4.7, 2.5, "Bridge Question", "Not just whether another vessel is risky,\nbut which surrounding area becomes more risky\nfor the own ship.", ACCENT)
    draw_paragraph(c, inch(7.7), inch(5.0), inch(4.5), "Pairwise risk -> own-ship-centric spatial field", size=18, color=ACCENT_2)


def slide_method(c: canvas.Canvas) -> None:
    start_slide(c, "제안 구조", "Method")
    draw_paragraph(c, inch(0.7), inch(1.15), inch(11.5), "pairwise relation을 공간 representation으로 재구성한다.", size=24, color=ACCENT)
    draw_bullets(c, inch(0.8), inch(2.0), inch(3.6), ["trajectory reconstruction", "pairwise severity estimation", "heatmap + contour generation"], size=18)
    steps = ["Curate AIS", "Reconstruct Tracks", "Estimate Pairwise Risk", "Generate Heatmap & Contour"]
    for i, text in enumerate(steps):
        draw_pipeline_box(c, 4.7 + i * 2.0, 2.4, 1.75, 1.1, text, ACCENT if i % 2 == 0 else ACCENT_2)
    draw_paragraph(c, inch(4.9), inch(4.1), inch(6.9), "도메인 파이프라인 위에 설명 가능한 위험 표현을 고정하고, 모델은 severity layer에만 얹는다.", size=17, color=SUB)


def slide_pipeline(c: canvas.Canvas) -> None:
    start_slide(c, "구현 파이프라인", "Pipeline")
    draw_paragraph(c, inch(0.7), inch(1.15), inch(11.6), "도메인 파이프라인 위에 모델이 올라간다.", size=24, color=ACCENT)
    labels = ["focus", "tracks", "pairwise", "scenario shift", "threshold tuning"]
    xs = [0.8, 3.0, 5.2, 7.6, 10.0]
    for i, (x, label) in enumerate(zip(xs, labels)):
        draw_pipeline_box(c, x, 2.4, 2.0, 1.15, label, ACCENT if i % 2 == 0 else ACCENT_2)
    draw_paragraph(c, inch(0.9), inch(4.25), inch(11.2), "NOAA 수집부터 contour 비교까지 반복 가능한 구조를 만들었다.", size=18, color=SUB)
    draw_paragraph(c, inch(0.9), inch(5.15), inch(11.4), "focus -> tracks -> pairwise -> scenario shift -> threshold tuning", size=20, color=INK, align=TA_CENTER)


def slide_validation(c: canvas.Canvas) -> None:
    start_slide(c, "검증 설계", "Validation")
    draw_paragraph(c, inch(0.7), inch(1.1), inch(11.7), "single split이 아니라 split + LOO + repeat를 함께 봤다.", size=24, color=ACCENT)
    draw_table(
        c,
        0.8,
        2.0,
        [2.1, 2.5],
        [
            ["항목", "값"],
            ["기간", "61일"],
            ["해역", "Houston / NOLA / Seattle"],
            ["own_mmsi", "15"],
            ["pairwise rows", "67,892"],
        ],
        font_size=14,
    )
    draw_callout(c, 6.5, 2.0, 2.0, 1.1, "Benchmark", "timestamp split", ACCENT)
    draw_callout(c, 8.8, 2.0, 2.0, 1.1, "LOO", "own-ship holdout", ACCENT_2)
    draw_callout(c, 7.65, 3.45, 2.0, 1.1, "Repeat", "case repeat", ACCENT)
    draw_paragraph(c, inch(6.1), inch(5.1), inch(5.8), "benchmark + own-ship LOO + case repeat", size=19, color=INK, align=TA_CENTER)


def slide_model_results(c: canvas.Canvas) -> None:
    start_slide(c, "모델 결과", "Results")
    draw_paragraph(c, inch(0.7), inch(1.05), inch(11.7), "주력 모델은 hgbt, 설명 가능한 비교군은 logreg다.", size=24, color=ACCENT)
    draw_table(
        c,
        0.75,
        1.95,
        [1.6, 2.0, 1.4, 2.2],
        [
            ["Model", "Benchmark F1", "ECE", "LOO F1 mean"],
            ["hgbt", "0.9453", "0.0187", "0.9241"],
            ["logreg", "0.8750", "0.0644", "0.8953"],
        ],
        font_size=15,
    )
    draw_callout(c, 9.2, 2.0, 3.1, 1.15, "Primary", "hgbt", ACCENT)
    draw_callout(c, 9.2, 3.35, 3.1, 1.15, "Comparator", "logreg", ACCENT_2)
    draw_bullets(
        c,
        inch(0.95),
        inch(4.95),
        inch(10.8),
        [
            "모델 layer에서는 hgbt가 가장 안정적이었다.",
            "설명 가능성은 logreg comparator로 보완했다.",
        ],
        size=17,
        color=SUB,
    )


def slide_threshold(c: canvas.Canvas) -> None:
    start_slide(c, "Threshold 결과", "Threshold")
    draw_paragraph(c, inch(0.7), inch(1.05), inch(11.7), "single best value 대신 shortlist가 더 정직했다.", size=24, color=ACCENT)
    draw_table(
        c,
        0.75,
        1.95,
        [2.2, 2.1],
        [
            ["항목", "값"],
            ["majority profile", "s0p30_w0p55"],
            ["majority ratio", "0.1803"],
            ["mean top-k Jaccard", "0.1388"],
        ],
        font_size=14,
    )
    draw_callout(c, 5.8, 1.95, 2.1, 1.0, "default", "s0p30_w0p55", ACCENT)
    draw_callout(c, 8.05, 1.95, 2.1, 1.0, "balanced", "s0p30_w0p65", ACCENT_2)
    draw_callout(c, 10.3, 1.95, 2.1, 1.0, "tight", "s0p35_w0p65", ACCENT)
    draw_image(c, SCENARIO, 5.8, 3.0, 6.0)
    draw_paragraph(c, inch(0.85), inch(4.7), inch(4.2), "unstable -> shortlist 운영", size=21, color=ACCENT_2)


def slide_visual(c: canvas.Canvas) -> None:
    start_slide(c, "Holdout Figure", "Visual")
    draw_paragraph(c, inch(0.7), inch(1.0), inch(11.8), "shortlist는 위험 방향보다 contour 민감도를 조정한다.", size=24, color=ACCENT)
    draw_image(c, HOUSTON, 0.7, 1.75, 7.1)
    draw_image(c, NOLA, 8.15, 1.95, 2.2)
    draw_image(c, SEATTLE, 10.5, 1.95, 2.2)
    draw_bullets(
        c,
        inch(8.1),
        inch(4.65),
        inch(4.6),
        [
            "default -> balanced: warning area 축소",
            "balanced -> tight: caution area 추가 축소",
            "dominant sector는 대체로 유지",
        ],
        size=15,
    )


def slide_close(c: canvas.Canvas, *, include_regional: bool) -> None:
    start_slide(c, "기여와 한계", "Close")
    draw_paragraph(c, inch(0.7), inch(1.0), inch(11.8), "강점은 과장 없는 AIS-only decision-support framing이다.", size=24, color=ACCENT)
    draw_callout(c, 0.8, 1.95, 5.7, 2.7 if not include_regional else 3.0, "기여", "spatial field\nscenario-aware contour\nregional failure-mode reporting", ACCENT)
    draw_callout(c, 6.8, 1.95, 5.7, 2.7 if not include_regional else 3.0, "비주장", "autonomy\nlegal safety boundary\nsingle optimum threshold", ACCENT_2)
    draw_paragraph(c, inch(1.0), inch(5.0 if not include_regional else 5.45), inch(11.2), "Conclusion: explainable spatial decision support", size=22, color=INK, align=TA_CENTER)
    if include_regional:
        draw_image(c, REGIONAL, 3.75, 6.0, 5.7)


def build_8_slide_pdf(out_path: Path) -> None:
    c = canvas.Canvas(str(out_path), pagesize=(PAGE_W, PAGE_H))
    slides = [
        slide_problem,
        slide_method,
        slide_pipeline,
        slide_validation,
        slide_model_results,
        slide_threshold,
        slide_visual,
    ]
    for slide_fn in slides:
        slide_fn(c)
        c.showPage()
    slide_close(c, include_regional=True)
    c.save()


def build_3_min_pdf(out_path: Path) -> None:
    c = canvas.Canvas(str(out_path), pagesize=(PAGE_W, PAGE_H))
    slides = [
        slide_problem,
        lambda canvas_obj: (slide_method(canvas_obj)),
        slide_model_results,
        slide_threshold,
        slide_visual,
    ]
    for slide_fn in slides:
        slide_fn(c)
        c.showPage()
    slide_close(c, include_regional=False)
    c.save()


def main() -> None:
    ensure_assets()
    register_font()
    build_8_slide_pdf(OUT_8)
    build_3_min_pdf(OUT_3)
    print(OUT_8)
    print(OUT_3)


if __name__ == "__main__":
    main()
