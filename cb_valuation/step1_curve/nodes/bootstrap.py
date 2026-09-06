# -*- coding: utf-8 -*-
"""bootstrap.*: 모드 A 폐형식(curve/bootstrap.bootstrap_mode_a; DENOM_FLOOR·DF_RANGE). PRICE_MODE='par' 만 초안 지원."""
from ..curve.bootstrap import bootstrap_mode_a
from ..curve.compounding import rv


def node_bootstrap(s, C):
    s.bootstrap.mode, s.bootstrap.price_mode = C.BOOTSTRAP_MODE, C.PRICE_MODE
    if C.PRICE_MODE != "par":
        raise NotImplementedError("PRICE_MODE kicpa_conventional 은 초안 미구현")
    for c in C.CURVE_IDS:
        m = C.RF_FREQ if c == "RF" else C.RD_FREQ
        coupons = s.interp.par_coupon_on_grid[c]["values"]
        times = s.grid.boot_times[c]
        res = bootstrap_mode_a(coupons, C.DENOM_FLOOR, tuple(C.DF_RANGE))
        s.bootstrap.points[c] = [dict(p, t=times[p["n"] - 1]) for p in res["points"]]
        s.bootstrap.df[c] = res["df"]
        s.bootstrap.spot_pp[c] = rv(res["spot_pp"], times[:len(res["spot_pp"])], f"per_period_m{m}")
        s.bootstrap.min_denominator[c] = res["min_denominator"]
        s.bootstrap.status[c] = res["status"]
        s.bootstrap.df_valid[c] = res["status"] == "OK" and len(res["df"]) == len(times)
        if res["status"] != "OK":
            s.bootstrap.errors.append(f"{c}: {res['status']} at n={len(res['df']) + 1}")
