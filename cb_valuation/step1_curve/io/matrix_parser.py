# -*- coding: utf-8 -*-
"""
io/matrix_parser.py — 채권평가사 시가평가 기준수익률 매트릭스 파서 (FORMULA_REFERENCE §1).
입력 형식: 붙여넣기/CSV/TSV 텍스트, 또는 xlsx 파일(첫 시트 또는 'KIS-NET' 시트 → CSV 텍스트로 변환: read_matrix_bytes/read_matrix_file).
레이아웃: 종류 | 구분 | 적용대상채권 | 3M … 50Y (%). 결측 '-' → None(절대 0 아님). 숫자 변환 실패는 parse_errors 로 남긴다(추정 금지).
preview() 는 화면 드롭다운용 행 요약(행 번호·라벨·해석 결과)이며 판단을 하지 않는다.
"""
from __future__ import annotations
import csv, hashlib, io as _io, os


def parse_matrix_text(text: str, C) -> dict:
    raw = text.lstrip("﻿")
    sample = raw[:2000]
    delim = "\t" if sample.count("\t") >= sample.count(",") else ","
    reader = csv.reader(_io.StringIO(raw), delimiter=delim)
    lines = [row for row in reader]
    lines = [r for r in lines if any(c.strip() for c in r)]
    out = {"header_labels": [], "header_ok": False, "rows": [], "parse_errors": [], "zero_value_cells": [], "n_rows": 0,
           "file_sha256": "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()}
    if not lines:
        return out
    header = [c.strip() for c in lines[0]]
    out["header_labels"] = header
    tenor_cols = header[3:3 + len(C.TENOR_LABELS)]
    out["header_ok"] = [t.upper() for t in tenor_cols] == [t.upper() for t in C.TENOR_LABELS] and len(header) >= 3 + len(C.TENOR_LABELS)
    for li, row in enumerate(lines[1:], start=2):  # row_index = 파일 행 번호(헤더 = 1) = 평가사 엑셀 행 번호
        cells = [c.strip() for c in row] + [""] * (3 + len(C.TENOR_LABELS) - len(row))
        kind, group, label = cells[0], cells[1], cells[2]
        ytm = {}
        for j, ten in enumerate(C.TENOR_LABELS):
            tok = cells[3 + j]
            if tok in C.MISSING_TOKENS:
                ytm[ten] = None
                continue
            try:
                v = float(tok.replace(",", ""))
            except ValueError:
                out["parse_errors"].append(f"row {li} {ten}: 숫자 아님 '{tok}'")
                ytm[ten] = None
                continue
            if v == 0.0:
                out["zero_value_cells"].append((li, ten))
            ytm[ten] = v
        out["rows"].append({"row_index": li, "kind_raw": kind, "group_raw": group, "label_raw": label, "block": group if "무보증" in group else None, "ytm_pct": ytm})
    out["n_rows"] = len(out["rows"])
    return out


def _decode_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-16"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _xlsx_to_csv_text(data: bytes, prefer_sheet: str = "KIS-NET") -> str:
    from openpyxl import load_workbook  # 선언 의존성(pyproject)
    wb = load_workbook(_io.BytesIO(data), data_only=True, read_only=True)
    ws = wb[prefer_sheet] if prefer_sheet in wb.sheetnames else wb[wb.sheetnames[0]]
    buf = _io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    for row in ws.iter_rows(values_only=True):
        if row is None or all(v is None or str(v).strip() == "" for v in row):
            continue
        w.writerow(["" if v is None else (f"{v:.10g}" if isinstance(v, float) else str(v)) for v in row])
    return buf.getvalue()


def read_matrix_bytes(name: str, data: bytes) -> str:
    """업로드/파일 바이트 → 매트릭스 텍스트(CSV/TSV). xlsx/xlsm 은 첫 시트(또는 'KIS-NET' 시트)를 CSV 로 바꾼다."""
    ext = os.path.splitext(name or "")[1].lower()
    if ext in (".xlsx", ".xlsm"):
        return _xlsx_to_csv_text(data)
    if ext == ".xls":
        raise ValueError(".xls(구형)는 지원하지 않습니다 — 엑셀에서 .xlsx 또는 CSV 로 저장해 주세요")
    return _decode_text(data)


def read_matrix_file(path: str) -> str:
    with open(path, "rb") as fh:
        return read_matrix_bytes(os.path.basename(path), fh.read())


def preview(text: str, C) -> dict:
    """화면 드롭다운용 요약: 행 번호·원문 라벨·해석(kind/rating/block)·값 개수. 판단 없음(라벨 해석은 io/label_regex 와 같은 함수)."""
    from .label_regex import interpret
    r = parse_matrix_text(text, C)
    lab = interpret(r["rows"], C)
    parsed = {p["row_index"]: p for p in lab["parsed"]}
    rows = []
    for row in r["rows"]:
        p = parsed.get(row["row_index"], {})
        rows.append({"row_index": row["row_index"], "kind_raw": row["kind_raw"], "group_raw": row["group_raw"], "label": row["label_raw"],
                     "kind": p.get("kind"), "rating": p.get("rating"), "block": p.get("block"),
                     "n_values": sum(1 for v in row["ytm_pct"].values() if v is not None)})
    return {"header_ok": r["header_ok"], "header_labels": r["header_labels"], "n_rows": r["n_rows"], "parse_errors": r["parse_errors"],
            "rows": rows, "rf_candidates": [p["row_index"] for p in lab["rf_candidates"]], "rd_candidates": [p["row_index"] for p in lab["rd_candidates"]]}
