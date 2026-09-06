# -*- coding: utf-8 -*-
"""interp.*: 모드 A — 마디 YTM 을 이표 격자로 보간(INTERP_METHOD_PRE, INTERP_SPACE_PRE='ytm', XL BOOT!G/V 재현)해 ytm_on_coupon_grid 와 기간 이표율
par_coupon_on_grid(COUPON_CONV) 를 만든다. 트리 격자용 method/space_grid 는 기록만 하고 map_tree_grid 가 쓴다. 마디 왕복 오차·외삽 사용 사실 기록.
지원하지 않는 규칙(모드 B, SPACE_PRE≠ytm, 좌측 외삽≠flat)은 러너 사전 게이트가 막고 여기서는 방어적으로 거부한다."""
import math
from ..curve.interp import YtmCurve
from ..curve.compounding import rv, coupon_from_ytm


def node_interpolate(s, C):
    s.interp.update(method=C.INTERP_METHOD, method_pre=C.INTERP_METHOD_PRE, space_pre=C.INTERP_SPACE_PRE, space_grid=C.INTERP_SPACE_GRID,
                    extrap_left=C.EXTRAP_LEFT, extrap_right=C.EXTRAP_RIGHT, is_local=C.INTERP_TABLE[C.INTERP_METHOD][0])
    if C.BOOTSTRAP_MODE != "interpolate_then_bootstrap" or C.INTERP_SPACE_PRE != "ytm" or C.EXTRAP_LEFT != "flat":
        raise NotImplementedError(f"초안 미구현: BOOTSTRAP_MODE={C.BOOTSTRAP_MODE}, INTERP_SPACE_PRE={C.INTERP_SPACE_PRE}, EXTRAP_LEFT={C.EXTRAP_LEFT}")
    pcg, errs, ext_used, finite = {}, [], False, True
    for c in C.CURVE_IDS:
        m = C.RF_FREQ if c == "RF" else C.RD_FREQ
        knots = s.grid.knots[c]
        yc = YtmCurve(C.INTERP_METHOD_PRE, [k["t"] for k in knots], [k["ytm"] for k in knots], C.EPS_T)
        ytms, coupons, ext = [], [], []
        for t in s.grid.boot_times[c]:
            y, extrap = yc.at(t)
            if extrap:
                ext.append(t)
            ytms.append(y); coupons.append(coupon_from_ytm(y, m, C.COUPON_CONV))
        s.interp.ytm_on_coupon_grid[c] = rv(ytms, s.grid.boot_times[c], f"nominal_m{m}")
        pcg[c] = rv(coupons, s.grid.boot_times[c], f"per_period_m{m}")
        errs.append(yc.knot_roundtrip_err())
        s.interp.extrapolated_points[c] = ext
        ext_used = ext_used or bool(ext)
        finite = finite and all(math.isfinite(v) for v in coupons)
    s.interp.par_coupon_on_grid = pcg
    s.interp.knot_roundtrip_max_err = max(errs)
    s.interp.all_finite = finite
    s.interp.coupon_grid_extrap_used = ext_used
