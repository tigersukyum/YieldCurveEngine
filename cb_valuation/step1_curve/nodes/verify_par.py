# -*- coding: utf-8 -*-
"""par_check.*: 만기별 Σ c_n·DF_k + DF_n − 1 (FORMULA_REFERENCE §6), PAR_FACE 환산 병기. 미사용 knot 잔차는 초안에서 계산하지 않는다(None)."""
import math
from ..curve.bootstrap import par_reprice


def node_verify_par(s, C):
    worst, finite = 0.0, True
    for c in C.CURVE_IDS:
        rows = par_reprice(s.interp.par_coupon_on_grid[c]["values"], s.bootstrap.df[c], 1.0)
        times = s.grid.boot_times[c]
        out = []
        for r in rows:
            r = dict(r, curve=c, t=times[r["n"] - 1], residual_x_face=r["residual"] * C.PAR_FACE)
            out.append(r)
            finite = finite and math.isfinite(r["residual"])
            worst = max(worst, abs(r["residual"])) if math.isfinite(r["residual"]) else worst
        s.par_check.per_maturity[c] = out
    s.par_check.max_abs_err = worst if finite else float("nan")
    s.par_check.all_finite = finite
    s.par_check.unused_knot_max_abs_err = None
