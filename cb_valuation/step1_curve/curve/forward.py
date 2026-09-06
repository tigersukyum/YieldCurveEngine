# -*- coding: utf-8 -*-
"""
curve/forward.py — 트리 격자 선도금리(FORMULA_REFERENCE §5; XL BM C-FWD/DF).
  f_i = (ln DF_{i−1} − ln DF_i) / dt_i        (연속복리, basis continuous)
  df_step_i = exp(−f_i·dt_i)  [감사인 Q8 ③]     F_i = expm1(f_i·dt_i) (basis per_step_simple)
  df_step_alt_i = (1+f_i)^(−dt_i) [① XL BM F열: 연속선도를 연복리처럼 넣은 값 — ③ 과의 차이 ≈ f²dt/2]   F_annual_i = expm1(f_i) (annual_eff)
  growth_step_i = 1+F_i (검토자 Rf_dc r33 FORMULA I), growth_cum_prev_k = Π_{j<k}(1+F_j) (r34 FORMULA II -CUMM, 첫 열 1),
  df_backward_k = Π_{j≥k} df_step_j (r38 MODEL CHECK 역방향 PV), spot_per_step_i = (1+z_i)^{dt_i} − 1 (r32)
  검증: |Σ_{k≤i}(−f_k dt_k) − ln DF_i| (로그) 와 |Π df_step − DF_i| (곱)  — 감사인 Q11
"""
from __future__ import annotations
import math


def forwards_from_df(times: list, dfs: list, dt: list, spot_annual: list, bp_per_unit: float) -> dict:
    """times[0]=0, dfs[0]=1, dt[i-1] = times[i]−times[i−1](격자 원천 그대로). 반환 리스트 길이 N(스텝 1..N)."""
    N = len(times) - 1
    f, df_step, df_alt, F, F_ann, df_cum, g_step, g_prev, spot_step = [], [], [], [], [], [], [], [], []
    cum = 1.0
    for i in range(1, N + 1):
        h = dt[i - 1]
        fi = (math.log(dfs[i - 1]) - math.log(dfs[i])) / h
        Fi = math.expm1(fi * h)
        step = math.exp(-fi * h)
        g_prev.append(1.0 / cum)  # Π_{j<i}(1+F_j) = 1/DF_cum(t_{i−1}), 첫 열 1
        cum *= step
        f.append(fi); df_step.append(step); F.append(Fi); df_alt.append(math.exp(-h * math.log1p(fi)))
        F_ann.append(math.expm1(fi)); df_cum.append(cum); g_step.append(1.0 + Fi)
        spot_step.append(math.expm1(h * math.log1p(spot_annual[i])))
    back, acc = [0.0] * N, 1.0
    for i in range(N - 1, -1, -1):
        acc *= df_step[i]; back[i] = acc
    neg = sum(1 for v in f if v < 0.0)
    jump = max((abs(f[i] - f[i - 1]) for i in range(1, len(f))), default=0.0) * bp_per_unit
    return {"f": f, "df_step": df_step, "df_step_alt": df_alt, "F": F, "F_annual": F_ann, "df_cum": df_cum,
            "growth_step": g_step, "growth_cum_prev": g_prev, "df_backward": back, "spot_per_step": spot_step,
            "negative_count": neg, "max_jump_bp": jump}


def boot_grid_forwards(dfs: list, m: int) -> dict:
    """부트스트랩 격자 기간 선도 F_n = DF_{n−1}/DF_n − 1 (DF_0=1; 검토자 r26) 과 연환산 (1+F_n)^m − 1 (r27)."""
    pp = [1.0 / dfs[0] - 1.0] + [dfs[i - 1] / dfs[i] - 1.0 for i in range(1, len(dfs))]
    return {"pp": pp, "annual": [math.expm1(m * math.log1p(v)) for v in pp]}


def fwd_spot_check(times: list, dfs: list, f: list, dt: list) -> dict:
    """로그 공간·곱 공간 잔차(전 격자점) + 마지막 격자점 예시."""
    log_err, prod_err, rows = [], [], []
    acc, prod = 0.0, 1.0
    for i in range(1, len(times)):
        acc += -f[i - 1] * dt[i - 1]
        prod *= math.exp(-f[i - 1] * dt[i - 1])
        le, pe = abs(acc - math.log(dfs[i])), abs(prod - dfs[i])
        log_err.append(le); prod_err.append(pe)
        rows.append({"step": i, "t": times[i], "prod_df_fwd": prod, "df_spot": dfs[i], "diff_log": acc - math.log(dfs[i]), "diff_prod": prod - dfs[i]})
    return {"max_abs_err_log": max(log_err, default=float("nan")), "max_abs_err_prod": max(prod_err, default=float("nan")),
            "rows": rows, "sample": rows[-1] if rows else None}


def tenor_forward_table(knot_t: list, rc: list) -> list:
    """테너 간 연속복리 선도 f(t_a,t_b) = (r_b t_b − r_a t_a)/(t_b − t_a) (감사인 Q10-1)."""
    out = []
    prev_t, prev_r = 0.0, None
    for t, r in zip(knot_t, rc):
        fwd = r if prev_r is None else (r * t - prev_r * prev_t) / (t - prev_t)
        out.append({"t_from": prev_t, "t_to": t, "fwd_cont": fwd, "fwd_annual": math.expm1(fwd)})
        prev_t, prev_r = t, r
    return out
