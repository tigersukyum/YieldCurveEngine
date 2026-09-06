# -*- coding: utf-8 -*-
"""
curve/bootstrap.py — 모드 A(보간 후 폐형식 부트스트랩, FORMULA_REFERENCE §3.1; XL BOOT!H/I 동치형)와 par 재가격(§6).
  DF_n = (1 − c_n·Σ_{k<n} DF_k) / (1 + c_n),  spot_n(per period) = DF_n^(−1/n) − 1 = expm1(−ln DF_n / n)
  분모 1 − c_n·ΣDF ≤ DENOM_FLOOR → FAIL_DENOMINATOR ; DF 유효 범위 = DF_RANGE
누적합은 math.fsum. 모드 B(한공회 사례 1130 근찾기)는 초안 미구현(NotImplementedError).
"""
from __future__ import annotations
import math


def bootstrap_mode_a(coupons_pp: list, denom_floor: float, df_range=(0.0, 1.0)) -> dict:
    """coupons_pp[n-1] = c_n (기간 이표율, n=1..N). 반환: points, df, spot_pp, min_denominator, status."""
    dfs, spots, points = [], [], []
    min_den = None
    for n, c in enumerate(coupons_pp, start=1):
        if c is None or not math.isfinite(c):
            return {"status": "FAIL_DF_INVALID", "points": points, "df": dfs, "spot_pp": spots, "min_denominator": min_den}
        sum_prior = math.fsum(dfs)
        den = 1.0 - c * sum_prior
        min_den = den if min_den is None else min(min_den, den)
        if den <= denom_floor:
            return {"status": "FAIL_DENOMINATOR", "points": points, "df": dfs, "spot_pp": spots, "min_denominator": min_den}
        df = den / (1.0 + c)
        spot = math.expm1(-math.log(df) / n)
        dfs.append(df); spots.append(spot)
        points.append({"n": n, "c": c, "price_target": 1.0, "spot_pp": spot, "df": df, "denominator": den, "sum_df_prior": sum_prior})
    lo, hi = df_range
    ok = all(math.isfinite(d) and lo < d <= hi for d in dfs)
    return {"status": "OK" if ok else "FAIL_DF_INVALID", "points": points, "df": dfs, "spot_pp": spots, "min_denominator": min_den}


def par_reprice(coupons_pp: list, dfs: list, target: float = 1.0) -> list:
    """만기 n 마다 Σ_{k≤n} c_n·DF_k + DF_n − target (액면 1 기준)."""
    out = []
    for n, (c, df) in enumerate(zip(coupons_pp, dfs), start=1):
        price = c * math.fsum(dfs[:n]) + df
        out.append({"n": n, "price": price, "target": target, "residual": price - target})
    return out
