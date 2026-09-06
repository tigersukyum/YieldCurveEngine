# -*- coding: utf-8 -*-
"""grid.*: 사용 마디(knots), 1/m 부트스트랩 격자(boot_times), 잔여만기(DAYCOUNT), 트리 격자(TREE_GRID), 이벤트일 매핑."""
from datetime import date
import math


def year_fraction(d0: str, d1: str, daycount: str) -> float:
    a, b = date.fromisoformat(d0), date.fromisoformat(d1)
    if daycount == "ACT/365":
        return (b - a).days / 365.0
    if daycount == "30/360":  # US 30/360 = 엑셀 YEARFRAC(…,0) 근사(월말 규칙 제외)
        return ((b.year - a.year) * 360 + (b.month - a.month) * 30 + (min(b.day, 30) - min(a.day, 30))) / 360.0
    raise NotImplementedError(f"DAYCOUNT {daycount} 초안 미구현")


def node_build_grid(s, C):
    s.grid.horizon_years = C.CURVE_HORIZON_Y
    inst = s.provenance.instrument
    T = None
    if inst.maturity_date and s.provenance.valuation_date:
        T = year_fraction(s.provenance.valuation_date, inst.maturity_date, C.DAYCOUNT)
    s.grid.remaining_years = T
    for c in C.CURVE_IDS:
        m = C.RF_FREQ if c == "RF" else C.RD_FREQ
        ytm = s.rows.ytm[c]
        vals = dict(zip(C.TENOR_LABELS, ytm["values"])) if ytm else {}
        s.grid.knots[c] = [{"tenor": lab, "t": C.TENOR_YEARS[lab], "ytm": vals[lab]} for lab in s.rows.knot_tenors[c] if vals.get(lab) is not None]
        n_boot = int(round(C.CURVE_HORIZON_Y * m))
        s.grid.boot_times[c] = [round(k / m, C.T_ROUND_DIGITS) for k in range(1, n_boot + 1)]
        s.grid.unused_tenors[c] = [lab for lab in C.TENOR_LABELS if lab not in s.rows.knot_tenors[c] and vals.get(lab) is not None]
    if T is not None and math.isfinite(T) and T > 0:
        g = C.TREE_GRID
        if g["mode"] in ("report", "excel"):
            N = int(g["N"]); dt = T / N
        elif g["mode"] == "weekly":
            dt = g["dt_weekly"]; N = int(math.ceil(T / dt - C.EPS_T))
        else:
            raise NotImplementedError(f"TREE_GRID mode {g['mode']} 초안 미구현")
        times = [round(i * dt, C.T_ROUND_DIGITS) for i in range(N + 1)]
        times[-1] = round(T, C.T_ROUND_DIGITS) if g["mode"] != "weekly" else times[-1]
        events = []
        for ev in inst.event_dates or []:
            d = ev.get("date") if isinstance(ev, dict) else ev
            if not d:
                continue
            te = year_fraction(s.provenance.valuation_date, d, C.DAYCOUNT)
            events.append({"label": (ev.get("label") if isinstance(ev, dict) else None), "date": d, "t": te, "step": int(round(te / dt))})
        s.grid.tree.update(N=N, T=T, dt_mode=g["mode"], dt=[round(times[i] - times[i - 1], C.T_ROUND_DIGITS) for i in range(1, N + 1)],
                           times=times, daycount=C.DAYCOUNT, event_times=events)
