# -*- coding: utf-8 -*-
"""rows.*: RF/RD 행 선택. (a) provenance.row_choice(사용자가 드롭다운으로 고른 행 번호; 앱 기본) 이 있으면 그 행, (b) 없으면 상품 정보(등급 + BLOCK_OF_ISSUANCE 블록,
BLOCK_FALLBACK 대체 시 사실 기록). ytm RateVector(nominal_m{m}), knot_tenors/missing/usable. 등급·블록은 labels.parsed 의 해석값을 기록한다."""
from ..curve.compounding import rv


def node_select_rows(s, C):
    inst, rc = s.provenance.instrument, s.provenance.row_choice
    by_idx = {r["row_index"]: r for r in s.input.rows}
    parsed = {p["row_index"]: p for p in s.labels.parsed}

    def row_dict(idx, **extra):
        r = by_idx.get(idx)
        if r is None:
            return None
        p = parsed.get(idx, {})
        d = {"row_index": idx, "label_raw": r["label_raw"], "block": p.get("block"), "rating": p.get("rating"), "kind": p.get("kind"),
             "notch": C.NOTCH_DEFAULT, "ytm_pct": r["ytm_pct"], "selected_by": None, "block_requested": None}
        d.update(extra)
        return d

    if rc.rf_row_index is not None:
        rf = row_dict(int(rc.rf_row_index), selected_by="row_choice")
    elif s.labels.rf_candidates:
        rf = row_dict(s.labels.rf_candidates[0]["row_index"], selected_by="label")
    else:
        rf = None
    fallback, reason = False, None
    if rc.rd_row_index is not None:
        rd = row_dict(int(rc.rd_row_index), selected_by="row_choice")
    else:
        want_block = C.BLOCK_OF_ISSUANCE.get(inst.issuance_type or "")
        cands = [p for p in s.labels.rd_candidates if inst.rating and p["rating"] == inst.rating]
        pick = next((p for p in cands if p["block"] == want_block), None)
        if pick is None and want_block in C.BLOCK_FALLBACK:
            alt = C.BLOCK_FALLBACK[want_block]
            pick = next((p for p in cands if p["block"] == alt), None)
            if pick is not None:
                fallback, reason = True, f"{want_block} {inst.rating} 미고시 → {alt} {inst.rating} 사용(BLOCK_FALLBACK)"
        rd = row_dict(pick["row_index"], selected_by="product", block_requested=want_block) if pick is not None else None
    s.rows.rf, s.rows.rd = rf, rd
    s.rows.rd_fallback_used, s.rows.rd_fallback_reason = fallback, reason
    s.rows.rating_consistency_ok = None if not (inst.prior_rating_basis and rd) else (inst.prior_rating_basis == rd["rating"])
    s.rows.block_consistency_ok = None if not (inst.prior_block_basis and rd) else (inst.prior_block_basis == rd["block"])
    for c, row in (("RF", rf), ("RD", rd)):
        m = C.RF_FREQ if c == "RF" else C.RD_FREQ
        s.rows.knot_tenors[c] = C.knot_tenors(c)
        if row is None:
            continue
        vals = [None if row["ytm_pct"][t] is None else row["ytm_pct"][t] * C.PCT_TO_DEC for t in C.TENOR_LABELS]
        s.rows.ytm[c] = rv(vals, [C.TENOR_YEARS[t] for t in C.TENOR_LABELS], f"nominal_m{m}")
        s.rows.missing_knots[c] = [t for t in s.rows.knot_tenors[c] if row["ytm_pct"][t] is None]
        s.rows.usable_knot_count[c] = len(s.rows.knot_tenors[c]) - len(s.rows.missing_knots[c])
