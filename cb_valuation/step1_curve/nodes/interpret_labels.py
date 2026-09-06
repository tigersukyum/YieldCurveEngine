# -*- coding: utf-8 -*-
"""labels.*: LABEL_GRAMMAR 정규식 해석(io/label_regex). AI 경로(io/label_ai)는 초안에 없다 — AI_ENABLED=True 는 명시적으로 거부(러너 사전 게이트도 막는다)."""
from ..io.label_regex import interpret


def node_interpret_labels(s, C):
    if C.AI_ENABLED:
        raise NotImplementedError("AI 라벨 해석(io/label_ai.py)은 초안 미구현 — AI_ENABLED=False 로 실행")
    r = interpret(s.input.rows, C)
    s.labels.update(parsed=r["parsed"], rf_candidates=r["rf_candidates"], rd_candidates=r["rd_candidates"], unparsed_rows=r["unparsed_rows"])
