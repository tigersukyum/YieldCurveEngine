# -*- coding: utf-8 -*-
"""fwd.*: f_i=(lnDF_{i−1}−lnDF_i)/dt (BM C-FWD), df_step=exp(−f dt)[③], df_step_alt=(1+f)^(−dt)[① XL BM F열], F=expm1(f dt), 연환산,
spot_per_step·growth_step·growth_cum_prev·df_backward(검토자 Rf_dc r32~r38), 부트스트랩 격자 선도(r26·r27), 음수·점프(BP_PER_UNIT), 테너간 선도표.
dt 는 grid.tree.dt 하나만 쓴다(원천 단일). TREE_FWD_RULE=piecewise_quarter_step 은 map_tree_grid 의 log-linear DF 로 이미 반영되어 같은 식을 쓴다; NODE_DISCOUNT_CONV=1_discrete_fwd 면 1/(1+F) 가 주 할인계수."""
import math
from ..curve.forward import forwards_from_df, tenor_forward_table, boot_grid_forwards
from ..curve.compounding import rv


def node_compute_forward(s, C):
    if C.NODE_DISCOUNT_CONV not in ("3_continuous_fwd", "1_discrete_fwd"):
        raise NotImplementedError(f"NODE_DISCOUNT_CONV={C.NODE_DISCOUNT_CONV} 미구현")
    times, dt = s.grid.tree.times, s.grid.tree.dt
    finite = True
    for c in C.CURVE_IDS:
        m = C.RF_FREQ if c == "RF" else C.RD_FREQ
        r = forwards_from_df(times, s.tree.df_spot_on_grid[c], dt, s.tree.spot_annual_on_grid[c]["values"], C.BP_PER_UNIT)
        st = times[1:]
        s.fwd.cont_on_grid[c] = rv(r["f"], st, "continuous")
        s.fwd.disc_per_step[c] = rv(r["F"], st, "per_step_simple")
        s.fwd.disc_annual_eff[c] = rv(r["F_annual"], st, "annual_eff")
        s.fwd.spot_per_step[c] = rv(r["spot_per_step"], st, "per_step_simple")
        if C.NODE_DISCOUNT_CONV == "1_discrete_fwd":  # ① 1/(1+F) 가 주 할인계수(검토자 PVF OF FORWARD RATE), ③ exp(−f dt) 는 병기
            step1 = [1.0 / (1.0 + F) for F in r["F"]]
            cum, dcum = 1.0, []
            for d in step1:
                cum *= d; dcum.append(cum)
            back, acc = [0.0] * len(step1), 1.0
            for i in range(len(step1) - 1, -1, -1):
                acc *= step1[i]; back[i] = acc
            s.fwd.df_step[c], s.fwd.df_step_alt[c], s.fwd.df_cum[c] = step1, r["df_step"], dcum
            r["growth_cum_prev"] = [1.0] + [1.0 / d for d in dcum[:-1]]; r["df_backward"] = back
        else:
            s.fwd.df_step[c], s.fwd.df_step_alt[c], s.fwd.df_cum[c] = r["df_step"], r["df_step_alt"], r["df_cum"]
        s.fwd.growth_step[c], s.fwd.growth_cum_prev[c], s.fwd.df_backward[c] = r["growth_step"], r["growth_cum_prev"], r["df_backward"]
        s.fwd.negative_count[c], s.fwd.max_jump_bp[c] = r["negative_count"], r["max_jump_bp"]
        finite = finite and all(math.isfinite(v) for v in r["f"])
        bg = boot_grid_forwards(s.bootstrap.df[c], m)
        bt = s.grid.boot_times[c]
        s.fwd.boot_fwd_pp[c] = rv(bg["pp"], bt, f"per_period_m{m}")
        s.fwd.boot_fwd_annual[c] = rv(bg["annual"], bt, "annual_eff")
        cont = dict(zip([round(t, C.T_ROUND_DIGITS) for t in s.conv.spot_cont[c]["times"]], s.conv.spot_cont[c]["values"]))
        kt = [k["t"] for k in s.grid.knots[c] if round(k["t"], C.T_ROUND_DIGITS) in cont]
        s.fwd.tenor_table[c] = tenor_forward_table(kt, [cont[round(t, C.T_ROUND_DIGITS)] for t in kt])
    s.fwd.all_finite = finite
    s.fwd.rule = C.TREE_FWD_RULE
    s.fwd.node_discount_conv = C.NODE_DISCOUNT_CONV
    s.fwd.node_discount_reason = C.CONVENTION_REASONS["NODE_DISCOUNT_CONV"]
