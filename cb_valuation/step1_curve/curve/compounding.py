# -*- coding: utf-8 -*-
"""
curve/compounding.py — 복리 변환(FORMULA_REFERENCE §4, 한공회 §3.7.4.4)과 이표율 변환(§2).
  기간이자율 s(주기 m) → 연복리 z = (1+s)^m − 1 = expm1(m·log1p(s))      # BOOT!M, AB
  연복리 z → 연속복리 r_c = ln(1+z) = log1p(z)                            # BOOT!N, AC
  기간이자율 s(주기 m) → 연속복리 r_c = m·log1p(s)
  이표율: COUPON_CONV "nominal_div_m" c = y/m (역: y = c·m) | "effective_root" c = (1+y)^(1/m) − 1 (역: (1+c)^m − 1)
DF 는 annual_eff/continuous 에서만 만든다(per_period → exp() 금지: discount_factor 가 basis 를 검사). rv() 는 basis 라벨을 검증한다.
"""
from __future__ import annotations
import math

BASIS = ("nominal_m2", "nominal_m4", "per_period_m2", "per_period_m4", "annual_eff", "continuous", "per_step_simple")  # = Constants.BASIS


def rv(values, times, basis) -> dict:
    """RateVector — 모든 금리 배열의 공통 자료형(JSON 직렬화 가능). basis 는 Constants.BASIS 어휘만."""
    if basis not in BASIS:
        raise ValueError(f"basis '{basis}' ∉ BASIS")
    return {"values": list(values), "times": list(times), "basis": basis}


def pp_to_annual(s: float, m: int) -> float:
    return math.expm1(m * math.log1p(s))


def pp_to_cont(s: float, m: int) -> float:
    return m * math.log1p(s)


def annual_to_cont(z: float) -> float:
    return math.log1p(z)


def cont_to_annual(r: float) -> float:
    return math.expm1(r)


def cont_to_pp(r: float, m: int) -> float:
    return math.expm1(r / m)


def coupon_from_ytm(y: float, m: int, conv: str) -> float:
    if conv == "nominal_div_m":
        return y / m
    if conv == "effective_root":
        return math.expm1(math.log1p(y) / m)
    raise NotImplementedError(f"COUPON_CONV {conv} 미구현")


def ytm_from_coupon(c: float, m: int, conv: str) -> float:
    if conv == "nominal_div_m":
        return c * m
    if conv == "effective_root":
        return math.expm1(m * math.log1p(c))
    raise NotImplementedError(f"COUPON_CONV {conv} 미구현")


def discount_factor(rate: float, t: float, basis: str) -> float:
    if basis == "continuous":
        return math.exp(-rate * t)
    if basis == "annual_eff":
        return math.exp(-t * math.log1p(rate))
    raise ValueError(f"DF 는 annual_eff/continuous 에서만 계산한다(basis={basis}; 한공회 §3.7.4.4)")
