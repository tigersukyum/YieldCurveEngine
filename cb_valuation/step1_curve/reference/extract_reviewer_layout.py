# -*- coding: utf-8 -*-
"""
extract_reviewer_layout.py — 개발 도구(1회 실행): 내부 검토자 통합문서(REV 8521, ref/ 커밋 제외)의 Rf_dc/Rd_dc 시트에서
**서식·배치만**(글꼴·채우기·테두리·맞춤·숫자서식의 행별 런, 행 높이·개요 수준·thick 플래그, 열 폭, 틀 고정, 탭 색, B열 라벨·마커 문자열, 테마 XML)
을 뽑아 io/reviewer_dc_layout.json 과 io/reviewer_theme1.xml 로 저장한다. **숫자 값(금리표)은 기록하지 않는다** — 고객 데이터는 자원 파일에 들어가지 않는다.
사용: python cb_valuation/step1_curve/reference/extract_reviewer_layout.py <원본 xlsx 경로>
런타임(io/reviewer_sheet.py)은 이 JSON 만 읽는다. 원본 셀 서식이 바뀌면 다시 실행한다(2026-09-08 추출, openpyxl 3.1.5).
"""
from __future__ import annotations
import json, os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
IO_DIR = os.path.join(os.path.dirname(HERE), "io")
SHEETS = {"Rf_dc": (39, 524), "Rd_dc": (53, 524)}  # (마지막 행, 마지막 열=TD)


def _color(c):
    if c is None:
        return None
    if c.type == "rgb":
        return {"rgb": c.rgb}
    if c.type == "theme":
        return {"theme": c.theme, "tint": round(c.tint, 6)}
    if c.type == "indexed":
        return {"indexed": c.indexed}
    return None


def _style(font, fill, border, align, nf):
    return {
        "font": [font.name, float(font.size) if font.size else None, bool(font.bold), bool(font.italic), _color(font.color)],
        "fill": [fill.patternType, _color(fill.fgColor) if fill.patternType else None, _color(fill.bgColor) if fill.patternType else None],
        "border": [[getattr(border, side).style, _color(getattr(border, side).color)] if getattr(border, side).style else None
                   for side in ("left", "right", "top", "bottom")],
        "align": [align.horizontal, align.vertical, float(align.indent or 0), bool(align.wrap_text)],
        "nf": nf,
    }


def _col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26); s = chr(65 + r) + s
    return s


def extract(path: str) -> dict:
    from openpyxl import load_workbook
    wb = load_workbook(path)
    out = {"source_note": "REV 8521 Rf_dc/Rd_dc 서식만(값 없음)", "sheets": {}}
    for name, (maxr, maxc) in SHEETS.items():
        ws = wb[name]
        styles, index = [], {}

        def sid(st):
            k = json.dumps(st, sort_keys=True, ensure_ascii=False)
            if k not in index:
                index[k] = len(styles); styles.append(st)
            return index[k]

        rows = {}
        for r in range(1, maxr + 1):
            runs, prev, start = [], None, None
            for c in range(1, maxc + 1):
                cell = ws.cell(r, c)
                s = sid(_style(cell.font, cell.fill, cell.border, cell.alignment, cell.number_format)) if cell.has_style else -1
                if s != prev:
                    if prev is not None:
                        runs.append([start, c - 1, prev])
                    prev, start = s, c
            runs.append([start, maxc, prev])
            rd = ws.row_dimensions[r]
            row_style = None
            if rd.customFormat:
                row_style = sid(_style(rd.font, rd.fill, rd.border, rd.alignment, rd.number_format))
            rows[str(r)] = {"h": rd.height, "row_style": row_style, "thickTop": bool(rd.thickTop), "thickBot": bool(rd.thickBot),
                            "outline": int(rd.outlineLevel or 0), "runs": runs}
        sv = ws.sheet_view
        texts = {}
        for r in range(1, maxr + 1):
            for c in range(2, maxc + 1):
                v = ws.cell(r, c).value
                if isinstance(v, str) and not v.startswith("="):
                    texts[f"{_col(c)}{r}"] = v
        out["sheets"][name] = {
            "styles": styles, "rows": rows,
            "col_widths": {k: v.width for k, v in ws.column_dimensions.items() if v.width and v.customWidth and k in ("A", "B")},
            "default_col_width": ws.sheet_format.defaultColWidth, "default_row_height": ws.sheet_format.defaultRowHeight,
            "freeze_panes": str(ws.freeze_panes), "show_grid_lines": bool(sv.showGridLines), "zoom": sv.zoomScaleNormal,
            "tab_color": _color(ws.sheet_properties.tabColor),
            "texts": texts,  # B열 라벨 + 마커 문자열(테너/분기 라벨) — 배치 텍스트일 뿐 금리 값 아님
        }
    with zipfile.ZipFile(path) as z:
        theme = z.read("xl/theme/theme1.xml")
    return out, theme


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    layout, theme = extract(argv[1])
    os.makedirs(IO_DIR, exist_ok=True)
    jp = os.path.join(IO_DIR, "reviewer_dc_layout.json")
    with open(jp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(layout, fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(IO_DIR, "reviewer_theme1.xml"), "wb") as fh:
        fh.write(theme)
    for name, sh in layout["sheets"].items():
        print(name, "styles", len(sh["styles"]), "rows", len(sh["rows"]), "texts", len(sh["texts"]))
    print("written", jp, os.path.getsize(jp), "bytes; theme", len(theme), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
