# -*- coding: utf-8 -*-
"""input.*: 원문(input.raw_text 는 러너가 넣음) → 파싱 결과. 숫자는 % 원문 유지, '-' → None."""
from ..io.matrix_parser import parse_matrix_text


def node_load_matrix(s, C):
    r = parse_matrix_text(s.input.raw_text or "", C)
    s.input.update(file_sha256=r["file_sha256"], header_labels=r["header_labels"], header_ok=r["header_ok"], rows=r["rows"],
                   parse_errors=r["parse_errors"], zero_value_cells=r["zero_value_cells"], n_rows=r["n_rows"])
