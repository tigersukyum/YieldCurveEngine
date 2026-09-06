# -*- coding: utf-8 -*-
"""conv.*: 기간 s(주기 m) → 연복리 expm1(m·log1p(s)) → 연속복리 m·log1p(s) (한공회 §3.7.4.4; BOOT!M/N). 왕복 검사."""
import math
from ..curve import compounding as K


def node_convert_compounding(s, C):
    worst, finite = 0.0, True
    for c in C.CURVE_IDS:
        m = C.RF_FREQ if c == "RF" else C.RD_FREQ
        spp = s.bootstrap.spot_pp[c]
        ann = [K.pp_to_annual(v, m) for v in spp["values"]]
        cont = [K.pp_to_cont(v, m) for v in spp["values"]]
        s.conv.spot_annual[c] = K.rv(ann, spp["times"], "annual_eff")
        s.conv.spot_cont[c] = K.rv(cont, spp["times"], "continuous")
        for v, a, r in zip(spp["values"], ann, cont):
            back = K.cont_to_pp(r, m)
            err = max(abs(back - v), abs(K.annual_to_cont(a) - r))
            finite = finite and math.isfinite(err)
            worst = max(worst, err)
    s.conv.roundtrip_max_err = worst if finite else float("nan")
    s.conv.all_finite = finite
