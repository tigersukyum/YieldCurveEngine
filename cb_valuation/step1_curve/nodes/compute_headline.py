# -*- coding: utf-8 -*-
"""headline.*: HEADLINE_RULE 잔여만기 T 의 YTM(단위: 소수; 증빙은 %), 진단표(HEADLINE_DEFS), 보고서 값과 HEADLINE_ROUND_DIGITS 자리 ROUND_HALF_UP 비교.
interp_linear_ytm 은 curve.interp.YtmCurve(linear, 공시 전 테너) — 이표격자·증빙과 같은 보간 경로. nearest_tenor 동률은 작은 t 우선."""
from decimal import Decimal, ROUND_HALF_UP
from ..curve.gridmap import CurveOnGrid
from ..curve.interp import YtmCurve


def _ytm_points(row, C):
    return sorted((C.TENOR_YEARS[t], v * C.PCT_TO_DEC) for t, v in row["ytm_pct"].items() if v is not None)


def _by_rule(pts, T, rule, C):
    if not pts:
        return None
    if rule == "interp_linear_ytm":
        return YtmCurve("linear", [p[0] for p in pts], [p[1] for p in pts], C.EPS_T).at(T)[0]
    if rule == "ceil_tenor":
        return next((y for t, y in pts if t >= T - C.EPS_T), pts[-1][1])
    if rule == "nearest_tenor":
        return min(pts, key=lambda p: (abs(p[0] - T), p[0]))[1]
    return None


def _round_pct(x, digits):
    return Decimal(str(x)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)


def node_compute_headline(s, C):
    s.headline.rule = C.HEADLINE_RULE
    rh = s.provenance.instrument.reported_headline
    s.headline.reported_rf, s.headline.reported_rd = rh.rf_pct, rh.rd_pct
    T = s.grid.maturity_years  # 상품 만기일이 있을 때만(커브 전용 실행은 None)
    if T is None:
        s.headline.candidates = []
        s.headline.rf_ytm_remaining = s.headline.rd_ytm_remaining = s.headline.rf_spot_remaining_annual = s.headline.rd_spot_remaining_annual = None
        s.headline.rating_applied = s.rows.rd["rating"] if s.rows.rd else None
        s.headline.block_applied = s.rows.rd["block"] if s.rows.rd else None
        s.headline.match_ok = None
        return
    vals, cands = {}, []
    for rule in C.HEADLINE_DEFS:
        row = {"def": rule}
        for c in C.CURVE_IDS:
            r = s.rows[c.lower()]
            if rule in ("interp_linear_ytm", "ceil_tenor", "nearest_tenor"):
                v = _by_rule(_ytm_points(r, C), T, rule, C)
            else:
                m = C.RF_FREQ if c == "RF" else C.RD_FREQ
                cg = CurveOnGrid(C.INTERP_METHOD, C.INTERP_SPACE_GRID, s.grid.boot_times[c], s.bootstrap.spot_pp[c], m, C.EXTRAP_LEFT, C.EXTRAP_RIGHT, C.EPS_T)
                p = cg.at(T)
                v = p["spot_annual"] if rule == "spot_annual_at_T" else p["spot_cont"]
            row[f"{c.lower()}_pct"] = None if v is None else v * 100.0
            vals[(rule, c)] = v
        cands.append(row)
    s.headline.candidates = cands
    s.headline.rf_ytm_remaining, s.headline.rd_ytm_remaining = vals[(C.HEADLINE_RULE, "RF")], vals[(C.HEADLINE_RULE, "RD")]
    s.headline.rf_spot_remaining_annual, s.headline.rd_spot_remaining_annual = vals[("spot_annual_at_T", "RF")], vals[("spot_annual_at_T", "RD")]
    s.headline.rating_applied = s.rows.rd["rating"] if s.rows.rd else None
    s.headline.block_applied = s.rows.rd["block"] if s.rows.rd else None
    if rh.rf_pct is None and rh.rd_pct is None:
        s.headline.match_ok = None
        return
    ok = True
    for rep, comp in ((rh.rf_pct, s.headline.rf_ytm_remaining), (rh.rd_pct, s.headline.rd_ytm_remaining)):
        if rep is None:
            continue
        if comp is None:
            ok = False; continue
        ok = ok and _round_pct(comp * 100.0, C.HEADLINE_ROUND_DIGITS) == _round_pct(rep, C.HEADLINE_ROUND_DIGITS)
    s.headline.match_ok = ok
