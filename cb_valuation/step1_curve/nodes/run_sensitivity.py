# -*- coding: utf-8 -*-
"""sensitivity.*: 교차 (보간법 × 공간; SENSITIVITY_COMBOS) DF 상대차표 + FREQ_SENSITIVITY_SET(RF 분기 부트스트랩: m 별 마디 집합 재구성·같은 이표율 규칙) 현물 차이. 주 커브는 바꾸지 않는다."""
import math
from ..curve.gridmap import CurveOnGrid
from ..curve.interp import YtmCurve
from ..curve.bootstrap import bootstrap_mode_a
from ..curve.compounding import pp_to_annual, coupon_from_ytm, rv


def _knots_for_m(s, C, c, m):
    """주기 m 의 이표 격자(1/m 배수)에 놓이는 공시 테너만(Constants.knot_tenors 와 같은 규칙, m 만 바꿈)."""
    ytm = s.rows.ytm[c]; vals = dict(zip(C.TENOR_LABELS, ytm["values"]))
    out = []
    for lab in C.TENOR_LABELS:
        t = C.TENOR_YEARS[lab]
        if t > C.CURVE_HORIZON_Y + C.EPS_T or abs(t * m - round(t * m)) > C.EPS_T or vals.get(lab) is None:
            continue
        out.append((t, vals[lab]))
    return out


def node_run_sensitivity(s, C):
    times = s.grid.tree.times
    table, worst = [], 0.0
    for method, space in C.SENSITIVITY_COMBOS:
        if (method, space) == (C.INTERP_METHOD, C.INTERP_SPACE_GRID):
            continue
        for c in C.CURVE_IDS:
            m = C.RF_FREQ if c == "RF" else C.RD_FREQ
            try:
                cg = CurveOnGrid(method, space, s.grid.boot_times[c], s.bootstrap.spot_pp[c], m, C.EXTRAP_LEFT, C.EXTRAP_RIGHT, C.EPS_T)
            except NotImplementedError as e:
                table.append({"method": method, "space": space, "curve": c, "max_rel_df_diff": None, "note": str(e)}); continue
            main = s.tree.df_spot_on_grid[c]
            rel = max(abs(cg.at(t)["df"] / d - 1.0) for t, d in zip(times[1:], main[1:]))
            table.append({"method": method, "space": space, "curve": c, "max_rel_df_diff": rel})
            worst = max(worst, rel) if math.isfinite(rel) else worst
    s.sensitivity.table = table
    s.sensitivity.max_rel_df_diff = worst
    freq_alt = {}
    for c, alts in C.FREQ_SENSITIVITY_SET.items():
        m0 = C.RF_FREQ if c == "RF" else C.RD_FREQ
        for m in alts:
            if m == m0:
                continue
            knots = _knots_for_m(s, C, c, m)
            if len(knots) < 2:
                freq_alt[c] = {"m": m, "status": "TOO_FEW_KNOTS"}; continue
            yc = YtmCurve(C.INTERP_METHOD_PRE, [k[0] for k in knots], [k[1] for k in knots], C.EPS_T)
            bt = [round(k / m, C.T_ROUND_DIGITS) for k in range(1, int(round(C.CURVE_HORIZON_Y * m)) + 1)]
            coupons = [coupon_from_ytm(yc.at(t)[0], m, C.COUPON_CONV) for t in bt]
            res = bootstrap_mode_a(coupons, C.DENOM_FLOOR, tuple(C.DF_RANGE))
            if res["status"] != "OK":
                freq_alt[c] = {"m": m, "status": res["status"]}; continue
            alt = dict(zip(bt, [pp_to_annual(v, m) for v in res["spot_pp"]]))
            base = dict(zip(s.conv.spot_annual[c]["times"], s.conv.spot_annual[c]["values"]))
            common = [t for t in base if t in alt]
            diff_bp = max(abs(alt[t] - base[t]) for t in common) * C.BP_PER_UNIT if common else None
            freq_alt[c] = {"m": m, "knots": len(knots), "max_spot_annual_diff_bp": diff_bp, "n_common": len(common)}
    s.sensitivity.freq_alt = freq_alt
    s.sensitivity.excel_recon = None
