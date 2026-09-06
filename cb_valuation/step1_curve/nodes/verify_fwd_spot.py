# -*- coding: utf-8 -*-
"""fwd_spot_check.*: Π DF_fwd = DF_spot (감사인 Q11) — 로그 공간 게이트 + 곱 절대차 병기 + 예시 1건(RF 마지막 격자점)."""
import math
from ..curve.forward import fwd_spot_check


def node_verify_fwd_spot(s, C):
    times = s.grid.tree.times
    worst_log, worst_prod, finite, sample, rows = 0.0, 0.0, True, None, {}
    for c in C.CURVE_IDS:
        r = fwd_spot_check(times, s.tree.df_spot_on_grid[c], s.fwd.cont_on_grid[c]["values"], s.grid.tree.dt)
        finite = finite and math.isfinite(r["max_abs_err_log"]) and math.isfinite(r["max_abs_err_prod"])
        worst_log, worst_prod = max(worst_log, r["max_abs_err_log"]), max(worst_prod, r["max_abs_err_prod"])
        rows[c] = r["rows"]
        if c == "RF" and r["sample"]:
            sample = dict(r["sample"], curve=c)
    s.fwd_spot_check.max_abs_err_log = worst_log if finite else float("nan")
    s.fwd_spot_check.max_abs_err_prod = worst_prod if finite else float("nan")
    s.fwd_spot_check.all_finite = finite
    s.fwd_spot_check.sample = sample
    s.fwd_spot_check.rows = rows  # 증빙 FWD_SPOT_CHECK 시트 원천(전 격자점)
