# -*- coding: utf-8 -*-
"""
curve/interp.py — 보간 플러그인 등록표. 공식은 검증된 참조 구현(reference/interp_ref.py; scipy·SLATEC·MATLAB 대조)을 그대로 쓴다.
INTERP_TABLE(Constants) 의 method_id ↔ 생성자. 새 플러그인은 is_local 을 Constants.INTERP_TABLE 에 선언하고 knot 왕복 테스트를 추가한다.
ytm_curve(): 마디 YTM 의 단일 보간 경로(이표격자·헤드라인·증빙 표시 공용) — 마디 밖은 평탄(EXTRAP_LEFT="flat" 와 같은 규칙), 외삽 사실을 함께 돌려준다.
"""
from __future__ import annotations
from ..reference import interp_ref as R

INTERPOLATORS = {
    "linear": R.linear,
    "pchip": R.pchip,
    "natural_cubic": R.natural_cubic_spline,
}


def make(method: str, x, y):
    if method not in INTERPOLATORS:
        raise NotImplementedError(f"보간법 '{method}' 는 초안에 없음(INTERPOLATORS: {sorted(INTERPOLATORS)})")
    return INTERPOLATORS[method](x, y)


class YtmCurve:
    """마디 (t, ytm) 보간 + 평탄 외삽. at(t) → (값, 외삽 여부). knot_roundtrip_err() 는 마디 재현 오차."""
    def __init__(self, method: str, kt, ky, eps_t: float):
        self.kt, self.ky, self.eps = list(kt), list(ky), eps_t
        self.f = make(method, self.kt, self.ky)

    def at(self, t: float):
        if t < self.kt[0] - self.eps:
            return self.ky[0], True
        if t > self.kt[-1] + self.eps:
            return self.ky[-1], True
        return self.f(t), False

    def knot_roundtrip_err(self) -> float:
        return max(abs(self.f(x) - y) for x, y in zip(self.kt, self.ky))
