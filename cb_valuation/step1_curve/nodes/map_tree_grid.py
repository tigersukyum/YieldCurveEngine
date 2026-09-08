# -*- coding: utf-8 -*-
"""tree.*: 같은 보간 함수(INTERP_METHOD × INTERP_SPACE_GRID)로 부트스트랩 마디 → 트리 격자. DF=exp(−r_c t). 유한·범위(DF_RANGE)·단조(TOL_DF_MONOTONE) 사실,
격자 보간체의 마디 왕복 오차, 외삽 스텝 사실만 기록. 실제 사용한 method/space 는 보간체 객체에서 읽는다. ytm_on_grid 는 표시용(INTERP_METHOD_PRE, 검토자 r11)."""
import math
from ..curve.gridmap import CurveOnGrid
from ..curve.interp import YtmCurve
from ..curve.compounding import rv


def node_map_tree_grid(s, C):
    if C.TREE_FWD_RULE == "piecewise_quarter_step" and (C.INTERP_METHOD, C.INTERP_SPACE_GRID) != ("linear", "log_df"):
        raise NotImplementedError("piecewise_quarter_step 은 INTERP_METHOD=linear × INTERP_SPACE_GRID=log_df(분기 DF 사이 선도 일정)로만 구현됨")
    times = s.grid.tree.times
    finite, range_ok, mono, worst_rt = True, True, True, 0.0
    lo, hi = C.DF_RANGE
    for c in C.CURVE_IDS:
        m = C.RF_FREQ if c == "RF" else C.RD_FREQ
        cg = CurveOnGrid(C.INTERP_METHOD, C.INTERP_SPACE_GRID, s.grid.boot_times[c], s.bootstrap.spot_pp[c], m, C.EXTRAP_LEFT, C.EXTRAP_RIGHT, C.EPS_T)
        pts = [cg.at(t) for t in times]
        s.tree.spot_annual_on_grid[c] = rv([p["spot_annual"] for p in pts], times, "annual_eff")
        s.tree.spot_cont_on_grid[c] = rv([p["spot_cont"] for p in pts], times, "continuous")
        dfs = [p["df"] for p in pts]
        s.tree.df_spot_on_grid[c] = dfs
        s.tree.extrap_left_flat_steps[c] = [i for i, p in enumerate(pts) if p["extrap"] == "left_flat"]
        s.tree.extrap_left_origin_steps[c] = []
        s.tree.extrap_right_steps[c] = [i for i, p in enumerate(pts) if p["extrap"] == "right"]
        finite = finite and all(math.isfinite(d) for d in dfs) and all(math.isfinite(p["spot_cont"]) for p in pts)
        range_ok = range_ok and all(lo < d <= hi for d in dfs)
        mono = mono and all(dfs[i] <= dfs[i - 1] + C.TOL_DF_MONOTONE for i in range(1, len(dfs)))
        rt = cg.knot_roundtrip_err()
        worst_rt = max(worst_rt, rt) if math.isfinite(rt) else float("nan")
        knots = s.grid.knots[c]
        yc = YtmCurve(C.INTERP_METHOD_PRE, [k["t"] for k in knots], [k["ytm"] for k in knots], C.EPS_T)
        s.tree.ytm_on_grid[c] = rv([yc.at(t)[0] for t in times], times, f"nominal_m{m}")
        # 표시용 현물(검토자 row12): 분기 연복리 현물의 선형보간(첫 마디 앞 평탄) — DEFAULT 에서는 spot_annual_on_grid 와 같다
        cg_disp = CurveOnGrid("linear", "spot_annual", s.grid.boot_times[c], s.bootstrap.spot_pp[c], m, "flat", C.EXTRAP_RIGHT, C.EPS_T)
        s.tree.spot_annual_interp_on_grid[c] = rv([cg_disp.at(t)["spot_annual"] for t in times], times, "annual_eff")
        s.tree.interp_method_used, s.tree.interp_space_used = cg.method, cg.space
    s.tree.df_finite, s.tree.df_range_ok, s.tree.df_monotone_ok = finite, range_ok, mono
    s.tree.knot_roundtrip_max_err = worst_rt
    s.tree.excel_zero_used = False
