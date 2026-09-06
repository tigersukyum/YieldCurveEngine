# -*- coding: utf-8 -*-
"""
io/matrix_parser.py — 채권평가사 시가평가 기준수익률 매트릭스(KIS-NET 시트 붙여넣기/CSV/TSV) 파서 (FORMULA_REFERENCE §1).
레이아웃: 종류 | 구분 | 적용대상채권 | 3M … 50Y (%). 결측 '-' → None(절대 0 아님). 숫자 변환 실패는 parse_errors 로 남긴다(추정 금지).
"""
from __future__ import annotations
import csv, hashlib, io as _io


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
    for li, row in enumerate(lines[1:], start=2):  # row_index = 파일 행 번호(헤더 = 1) = KIS-NET 엑셀 행 번호
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
