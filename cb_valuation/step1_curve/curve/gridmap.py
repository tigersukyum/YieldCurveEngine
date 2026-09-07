# -*- coding: utf-8 -*-
"""
curve/gridmap.py — 부트스트랩 마디 → 트리 격자 매핑(FORMULA_REFERENCE §5.1, INTERPOLATION_METHODS §1·§5).
공간(INTERP_SPACE_GRID): spot_annual(변형 ①, 엑셀 BM MF_INTERPOL) / spot_continuous(②) / log_df(④: g = r_c·t, (0,0) 마디 포함).
외삽: EXTRAP_LEFT="flat"(첫 마디 앞 현물 평탄 = 첫 구간 선도 상수), EXTRAP_RIGHT="flat_forward"(g(t)=g_n+g'(t_n−)(t−t_n)) | "flat_spot".
입력은 RateVector(basis per_period_m{m}) — 라벨과 m 이 맞지 않으면 거부. 시간 비교 여유 eps_t = Constants.EPS_T. 판정은 하지 않고 사실만 돌려준다.
"""
from __future__ import annotations
import math
from . import interp as I
from . import compounding as K


class CurveOnGrid:
    def __init__(self, method: str, space: str, knot_t: list, spot_pp_rv: dict, m: int, extrap_left: str, extrap_right: str, eps_t: float):
        if extrap_left not in ("flat",) or extrap_right not in ("flat_forward", "flat_spot"):
            raise NotImplementedError(f"외삽 규칙 {extrap_left}/{extrap_right} 는 초안 미구현(EXCEL_REF 전용 규칙 포함)")
        if spot_pp_rv.get("basis") != f"per_period_m{m}":
            raise ValueError(f"spot_pp basis {spot_pp_rv.get('basis')} ≠ per_period_m{m}")
        self.method, self.space, self.m, self.eps = method, space, m, eps_t
        self.t = list(knot_t)
        spot_pp = spot_pp_rv["values"]
        self.rc = [K.pp_to_cont(s, m) for s in spot_pp]
        self.z = [K.pp_to_annual(s, m) for s in spot_pp]
        if space == "spot_annual":
            self.x, self.y = self.t, self.z
        elif space == "spot_continuous":
            self.x, self.y = self.t, self.rc
        elif space == "log_df":
            self.x, self.y = [0.0] + self.t, [0.0] + [r * t for r, t in zip(self.rc, self.t)]
        else:
            raise NotImplementedError(f"보간 공간 '{space}' 는 초안 미구현")
        self.f = I.make(method, self.x, self.y)
        self.extrap_right = extrap_right
        self.t_first, self.t_last = self.t[0], self.t[-1]

    def _rc_at(self, t: float):
        """연속복리 현물 r_c(t) 와 외삽 사실('left_flat' | 'right' | None)."""
        if t > self.t_last + self.eps:
            if self.extrap_right == "flat_spot":
                return self.rc[-1], "right"
            g_n = self.rc[-1] * self.t_last
            return (g_n + self._g_slope_left_limit() * (t - self.t_last)) / t, "right"
        if self.space == "log_df":
            if t <= 0.0:
                return self.f.deriv(0.0), None
            return self.f(t) / t, None
        if t < self.t_first - self.eps:
            return (self.rc[0] if self.space == "spot_continuous" else K.annual_to_cont(self.z[0])), "left_flat"
        v = self.f(t)
        return (v if self.space == "spot_continuous" else K.annual_to_cont(v)), None

    def _g_slope_left_limit(self) -> float:
        """g'(t_n−), g = r_c·t. spot 공간에서는 r_c + t·r_c'(t_n−) (참조 구현 _segment 이 끝점을 마지막 구간에 두므로 좌극한)."""
        tn = self.t_last
        if self.space == "log_df":
            return self.f.deriv(tn)
        d = self.f.deriv(tn)
        if self.space == "spot_annual":
            d = d / (1.0 + self.z[-1])  # dr_c/dt = dz/dt / (1+z)
        return self.rc[-1] + tn * d

    def at(self, t: float) -> dict:
        rc, flag = self._rc_at(t)
        z = K.cont_to_annual(rc)
        df = 1.0 if t <= 0.0 else math.exp(-rc * t)
        return {"t": t, "spot_cont": rc, "spot_annual": z, "df": df, "extrap": flag}

    def knot_roundtrip_err(self) -> float:
        return max(abs(self.f(x) - y) for x, y in zip(self.x, self.y))
