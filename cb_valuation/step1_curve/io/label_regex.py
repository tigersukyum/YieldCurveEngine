# -*- coding: utf-8 -*-
"""
io/label_regex.py — 행 라벨 해석의 기본 경로(Constants.LABEL_GRAMMAR 정규식). AI 는 쓰지 않는다(io/label_ai.py 는 초안 미구현).
블록(공모무보증/사모무보증) 라벨은 KIS-NET 병합 셀 특성상 블록 중간 행에 한 번만 나타나므로, 회사채 행을 등급 서열(Constants.RATING_ORDER)이
다시 시작하는 지점에서 블록으로 나누고 그 블록 안에 나타난 라벨을 블록 전체에 부여한다. 부호 없는 등급(AA)은 "0"(AA0) 으로 정규화한다.
"""
from __future__ import annotations
import re


def _rank(rating: str, order: list) -> int:
    r = rating if rating in order else (rating + "0" if rating + "0" in order else None)
    return order.index(r) if r is not None else len(order)  # 미서열 등급은 마지막


def interpret(rows: list, C) -> dict:
    rf_re = re.compile(C.LABEL_GRAMMAR["RF"]); rd_re = re.compile(C.LABEL_GRAMMAR["RD"]); blk_re = re.compile(C.LABEL_GRAMMAR["BLOCK"])
    parsed, unparsed = [], []
    for r in rows:
        label = r["label_raw"]
        if not label:
            unparsed.append(r["row_index"]); continue
        kind, rating = None, None
        if rf_re.search(label):
            kind = "RF"
        else:
            m = rd_re.search(label)
            if m:
                kind, rating = "RD", m.group(1)
                if rating not in C.RATING_ORDER and rating + "0" in C.RATING_ORDER:
                    rating = rating + "0"
        blk_src = " ".join(x for x in (r.get("group_raw", ""), r.get("kind_raw", ""), label) if x)
        mb = blk_re.search(blk_src)
        parsed.append({"row_index": r["row_index"], "kind": kind, "rating": rating, "block": (mb.group(0).replace(" ", "") if mb else None), "parser": "regex", "label_raw": label})
    run, runs, prev_rank = [], [], -1
    for p in parsed:
        if p["kind"] != "RD":
            if run: runs.append(run); run = []
            prev_rank = -1; continue
        rank = _rank(p["rating"], C.RATING_ORDER)
        if run and rank <= prev_rank:
            runs.append(run); run = []
        run.append(p); prev_rank = rank
    if run: runs.append(run)
    for grp in runs:
        blocks = {p["block"] for p in grp if p["block"]}
        blk = sorted(blocks)[0] if blocks else None
        for p in grp:
            p["block"] = blk
    return {"parsed": parsed, "rf_candidates": [p for p in parsed if p["kind"] == "RF"], "rd_candidates": [p for p in parsed if p["kind"] == "RD"], "unparsed_rows": unparsed}
