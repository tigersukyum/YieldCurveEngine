# -*- coding: utf-8 -*-
"""rows.*: RF=국고채 첫 후보, RD=요청 등급·블록(BLOCK_OF_ISSUANCE; BLOCK_FALLBACK 대체 시 사실 기록), ytm RateVector(nominal_m{m}), knot_tenors/missing/usable."""
from ..curve.compounding import rv


def node_select_rows(s, C):
    inst = s.provenance.instrument
    by_idx = {r["row_index"]: r for r in s.input.rows}
    rf = None
    if s.labels.rf_candidates:
        r = by_idx[s.labels.rf_candidates[0]["row_index"]]
        rf = {"row_index": r["row_index"], "label_raw": r["label_raw"], "block": None, "rating": None, "notch": C.NOTCH_DEFAULT, "ytm_pct": r["ytm_pct"]}
    want_block = C.BLOCK_OF_ISSUANCE.get(inst.issuance_type or "")
    cands = [p for p in s.labels.rd_candidates if p["rating"] == inst.rating]
    pick = next((p for p in cands if p["block"] == want_block), None)
    fallback, reason = False, None
    if pick is None and want_block in C.BLOCK_FALLBACK:
        alt = C.BLOCK_FALLBACK[want_block]
        pick = next((p for p in cands if p["block"] == alt), None)
        if pick is not None:
            fallback, reason = True, f"{want_block} {inst.rating} 미고시 → {alt} {inst.rating} 사용(BLOCK_FALLBACK)"
    rd = None
    if pick is not None:
        r = by_idx[pick["row_index"]]
        rd = {"row_index": r["row_index"], "label_raw": r["label_raw"], "block": pick["block"], "block_requested": want_block,
              "rating": inst.rating, "notch": C.NOTCH_DEFAULT, "ytm_pct": r["ytm_pct"]}
    s.rows.rf, s.rows.rd = rf, rd
    s.rows.rd_fallback_used, s.rows.rd_fallback_reason = fallback, reason
    s.rows.rating_consistency_ok = None if not inst.prior_rating_basis else (inst.prior_rating_basis == inst.rating)
    s.rows.block_consistency_ok = None if (not inst.prior_block_basis or rd is None) else (inst.prior_block_basis == rd["block"])
    for c, row in (("RF", rf), ("RD", rd)):
        m = C.RF_FREQ if c == "RF" else C.RD_FREQ
        s.rows.knot_tenors[c] = C.knot_tenors(c)
        if row is None:
            continue
        vals = [None if row["ytm_pct"][t] is None else row["ytm_pct"][t] * C.PCT_TO_DEC for t in C.TENOR_LABELS]
        s.rows.ytm[c] = rv(vals, [C.TENOR_YEARS[t] for t in C.TENOR_LABELS], f"nominal_m{m}")
        s.rows.missing_knots[c] = [t for t in s.rows.knot_tenors[c] if row["ytm_pct"][t] is None]
        s.rows.usable_knot_count[c] = len(s.rows.knot_tenors[c]) - len(s.rows.missing_knots[c])
