# -*- coding: utf-8 -*-
"""
curve_demo.py -- application demo on the KICPA 사례 1130 data (2023-05-03, KIS).

Pipeline per method M in {linear, pchip}:
  1. interpolate the par YTM curve with M onto the bootstrap grid
  2. bootstrap par bonds sequentially (coupon dates counted back from maturity every 1/m
     years; a short first period pays a prorated simple coupon c * stub_length)
  3. continuous spot r_c(T) = -ln DF(T) / T on the bootstrap grid
  4. interpolate r_c with M onto the quarterly grid 0.25 .. 10Y
  5. continuous forwards f_i = (r_i t_i - r_{i-1} t_{i-1}) / (t_i - t_{i-1}), (t_0, r_0 t_0) = (0, 0)
  6. flags: negative forwards, sign changes of delta f, max |delta f|
  7. par verification: reprice every knot par bond with the bootstrapped DFs
"""
import math
import os
import sys
from bisect import bisect_right

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from interp_ref import pchip, linear, natural_cubic_spline, loglinear_df  # noqa: E402

TENORS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0, 50.0]
GOV_YTM = [v / 100 for v in [3.250, 3.285, 3.310, 3.350, 3.380, 3.365, 3.315, 3.270, 3.280, 3.257,
                             3.340, 3.317, 3.330, 3.360, 3.357, 3.352]]
CORP_T = TENORS[:12]
CORP_YTM = [v / 100 for v in [3.675, 3.745, 3.815, 3.863, 3.938, 3.970, 3.998, 4.032, 4.048, 4.225,
                              4.529, 5.094]]
KICPA_GOV_ZERO = {0.25: 0.032898, 0.5: 0.03312, 0.75: 0.033424, 1.0: 0.033786, 1.5: 0.034095,
                  2.0: 0.033936, 2.5: 0.03341, 3.0: 0.032936, 4.0: 0.033051, 5.0: 0.032805,
                  7.0: 0.033734, 10.0: 0.033452, 20.0: 0.034003, 50.0: 0.033793}
KICPA_GOV_DF = {10.0: 0.719607, 50.0: 0.18981}
HORIZON = 10.0
METHODS = [("linear", linear), ("pchip", pchip)]


# ----------------------------------------------------------------------------- utilities
def grid(step, horizon=HORIZON):
    return [round(k * step, 8) for k in range(1, int(round(horizon / step)) + 1)]


def cashflows(T, m, c):
    """[(t, amount)] for a par bond: coupons every 1/m counted back from T, prorated stub first."""
    step = 1.0 / m
    times = []
    t = T
    while t > 1e-9:
        times.append(round(t, 8))
        t -= step
    times.reverse()
    cfs = []
    prev = 0.0
    for i, ti in enumerate(times):
        amt = c * (ti - prev)
        if i == len(times) - 1:
            amt += 1.0
        cfs.append((ti, amt))
        prev = ti
    return cfs


def bootstrap_par(grid_t, ytm_fn, m):
    DF = {}
    out = []
    for T in grid_t:
        c = ytm_fn(T)
        cfs = cashflows(T, m, c)
        pv = 0.0
        for t, a in cfs[:-1]:
            if t not in DF:
                raise KeyError("DF(%r) needed for T=%r is not on the bootstrap grid" % (t, T))
            pv += a * DF[t]
        tl, al = cfs[-1]
        DF[tl] = (1.0 - pv) / al
        out.append(DF[tl])
    return out, DF


def price_bond(T, m, c, df_of):
    return sum(a * df_of(t) for t, a in cashflows(T, m, c))


def cont_spot(t, df):
    return -math.log(df) / t


def forwards(ts, rs):
    f = []
    prev_t, prev_rt = 0.0, 0.0
    for t, r in zip(ts, rs):
        f.append((r * t - prev_rt) / (t - prev_t))
        prev_t, prev_rt = t, r * t
    return f


def flags(f, tol=1e-12):
    """(negative forward count, sign changes of delta f ignoring |delta f| < tol, max |delta f|)."""
    neg = sum(1 for v in f if v < 0)
    d = [f[i] - f[i - 1] for i in range(1, len(f))]
    signs = [s for s in (((v > tol) - (v < -tol)) for v in d) if s != 0]
    changes = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i - 1])
    return neg, changes, (max(abs(v) for v in d) if d else 0.0)


def annual_zero(T, df):
    return df ** (-1.0 / T) - 1.0


# ----------------------------------------------------------------------------- pipeline
def run_curve(label, kT, kY, m, boot_step):
    print("\n" + "=" * 100)
    print("%s  (m=%d, bootstrap grid step=%.2f, YTM knots up to %gY)" % (label, m, boot_step, kT[-1]))
    print("=" * 100)
    res = {}
    qgrid = grid(0.25)
    bgrid = grid(boot_step)
    for mname, ctor in METHODS:
        ytm = ctor(kT, kY)
        dfs, DFd = bootstrap_par(bgrid, ytm, m)
        rb = [cont_spot(t, d) for t, d in zip(bgrid, dfs)]
        rq = ctor(bgrid, rb)(qgrid) if boot_step != 0.25 else rb
        dfq = [math.exp(-r * t) for r, t in zip(rq, qgrid)]
        fq = forwards(qgrid, rq)
        neg, chg, mxd = flags(fq)
        dfq_d = dict(zip(qgrid, dfq))

        def df_of(t, _d=dfq_d):
            return _d[round(t, 8)]

        on_err, off_err = 0.0, 0.0
        on_n, off_n = 0, 0
        for T, c in zip(kT, kY):
            if T > HORIZON:
                continue
            e = abs(price_bond(T, m, c, df_of) - 1.0)
            if round(T, 8) in DFd:
                on_err, on_n = max(on_err, e), on_n + 1
            else:
                off_err, off_n = max(off_err, e), off_n + 1
        res[mname] = dict(rq=rq, dfq=dfq, fq=fq, neg=neg, chg=chg, mxd=mxd, on_err=on_err, on_n=on_n,
                          off_err=off_err, off_n=off_n, DFd=DFd, dfq_d=dfq_d)
        print("[%s] ytm-interp -> bootstrap(%d pts) -> spot-interp -> quarterly(%d pts)" % (mname, len(bgrid), len(qgrid)))
        print("   forwards: negative=%d, sign changes of delta f=%d, max|delta f|=%.2f bp, min f=%.4f%%, max f=%.4f%%"
              % (neg, chg, mxd * 1e4, min(fq) * 100, max(fq) * 100))
        print("   par verification (knots <= 10Y): on-grid knots n=%d max|P-1|=%.2e ; off-grid knots n=%d max|P-1|=%.2e"
              % (on_n, on_err, off_n, off_err))
        ext = " (0.25Y point is EXTRAPOLATED below first bootstrap node %.2f)" % bgrid[0] if bgrid[0] > 0.25 else ""
        print("   quarterly spot r_c(0.25)=%.5f%%%s" % (rq[0] * 100, ext))
    return qgrid, res


def kicpa_compare(label, res):
    print("-- KICPA published 국채 zero (annual comp.) vs %s" % label)
    print("   %-6s %-10s" % ("T", "KICPA") + "".join("%-22s" % ("%s(diff bp)" % m) for m, _ in METHODS))
    worst = {m: 0.0 for m, _ in METHODS}
    for T in sorted(KICPA_GOV_ZERO):
        if T > HORIZON:
            continue
        row = "   %-6g %-10.6f" % (T, KICPA_GOV_ZERO[T])
        for m, _ in METHODS:
            z = annual_zero(T, res[m]["dfq_d"][round(T, 8)])
            diff = (z - KICPA_GOV_ZERO[T]) * 1e4
            worst[m] = max(worst[m], abs(diff))
            row += "%-22s" % ("%.6f (%+.2f)" % (z, diff))
        print(row)
    for m, _ in METHODS:
        d10 = res[m]["dfq_d"][10.0]
        print("   DF(10Y): KICPA %.6f  %s %.6f (diff %.2e)" % (KICPA_GOV_DF[10.0], m, d10, d10 - KICPA_GOV_DF[10.0]))
    print("   max |diff| bp: " + ", ".join("%s %.2f" % (m, worst[m]) for m in worst))
    return worst


# ----------------------------------------------------------------------------- knot-only bootstrap (KICPA variants)
def bootstrap_knots(kT, kY, m, space):
    """
    Bootstrap only at the YTM knots; discount factors at intermediate coupon dates come
    from the interpolation rule 'space':
      'zero_annual' : linear in the annual-compounded zero rate      (KICPA variant 1)
      'zero_cont'   : linear in the continuous zero rate             (KICPA variant 2)
      'logdf'       : linear in ln DF == constant continuous forward (KICPA variant 4)
    Solved by bisection on DF(T) for each knot in turn.
    """
    Ts, DFs = [], []

    def z_of(t, df):
        return annual_zero(t, df) if space == "zero_annual" else cont_spot(t, df)

    def df_from_z(t, z):
        return (1.0 + z) ** (-t) if space == "zero_annual" else math.exp(-z * t)

    def make_df_of(T, DF_T):
        xs = Ts + [T]
        ds = DFs + [DF_T]

        def df_of(t):
            if t >= xs[-1] - 1e-12:
                return ds[-1]
            j = bisect_right(xs, t) - 1
            if j < 0:
                return df_from_z(t, z_of(xs[0], ds[0]))
            t0, t1 = xs[j], xs[j + 1]
            w = (t - t0) / (t1 - t0)
            if space == "logdf":
                return math.exp((1 - w) * math.log(ds[j]) + w * math.log(ds[j + 1]))
            z = (1 - w) * z_of(t0, ds[j]) + w * z_of(t1, ds[j + 1])
            return df_from_z(t, z)
        return df_of

    for T, c in zip(kT, kY):
        cfs = cashflows(T, m, c)
        lo, hi = 1e-6, 1.5
        for _ in range(120):
            mid = 0.5 * (lo + hi)
            p = sum(a * make_df_of(T, mid)(t) for t, a in cfs)
            if p < 1.0:
                lo = mid
            else:
                hi = mid
        Ts.append(T)
        DFs.append(0.5 * (lo + hi))
    return dict(zip(Ts, DFs))


def main():
    # ---- A. as specified: native coupon grid bootstrap (semiannual 국채, quarterly 회사채)
    qg, gov_native = run_curve("A1. 국채 native SEMIANNUAL grid", TENORS, GOV_YTM, 2, 0.5)
    kicpa_compare("A1", gov_native)
    _, corp_native = run_curve("A2. 회사채 native QUARTERLY grid", CORP_T, CORP_YTM, 4, 0.25)

    # ---- B. 국채 on a quarterly grid with stub (prorated) first coupons -- reproduces KICPA 3M/9M
    _, gov_q = run_curve("B. 국채 QUARTERLY grid, semiannual coupons with prorated stub", TENORS, GOV_YTM, 2, 0.25)
    kicpa_compare("B", gov_q)
    print("-- B quarterly continuous forwards (%%) -- odd/even quarter chains are bootstrapped independently:")
    for m, _ in METHODS:
        f = gov_q[m]["fq"]
        print("   %-6s " % m + " ".join("%.3f" % (v * 100) for v in f))
        saw = [abs(f[i] - 0.5 * (f[i - 1] + f[i + 1])) for i in range(1, len(f) - 1)]
        print("   %-6s max sawtooth amplitude |f_i - (f_{i-1}+f_{i+1})/2| = %.2f bp" % ("", max(saw) * 1e4))
    for m, _ in METHODS:
        fa = gov_native[m]["fq"]
        fb = gov_q[m]["fq"]
        print("   %-6s max |fwd(B) - fwd(A1)| on quarterly grid = %.2f bp" % (m, max(abs(a - b) for a, b in zip(fa, fb)) * 1e4))

    # probe: 9M knot residual vs KICPA 0.033424 -- which stub coupon fraction reproduces it exactly?
    df3 = 1.0 / (1.0 + GOV_YTM[0] * 0.25)
    c9 = GOV_YTM[2]
    z_exact = annual_zero(0.75, (1.0 - c9 * 0.25 * df3) / (1.0 + c9 * 0.5))
    df9_target = (1.0 + 0.033424) ** (-0.75)
    stub_needed = (1.0 - df9_target * (1.0 + c9 * 0.5)) / (c9 * df3)
    print("-- 9M probe: 3M zero exact = %.7f (KICPA 0.032898); 9M zero with stub c*0.25 = %.7f (KICPA 0.033424);"
          " stub fraction that reproduces 0.033424 exactly = %.5f yr (vs 0.25)" % (annual_zero(0.25, df3), z_exact, stub_needed))
    for label, cfs in [("full c/2 first coupon, par", [(0.25, c9 * 0.5), (0.75, 1 + c9 * 0.5)]),
                       ("single CF 1+c*0.75 at 9M", [(0.75, 1 + c9 * 0.75)])]:
        pv = sum(a * df3 for t, a in cfs[:-1])
        d = (1 - pv) / cfs[-1][1]
        print("   alt convention %-34s -> 9M zero %.6f" % (label, annual_zero(0.75, d)))

    # ---- C. knot-only bootstrap under the KICPA interpolation variants (all 14 published knots)
    print("\n" + "=" * 100)
    print("C. knot-only bootstrap of 국채 (m=2) under KICPA 사례 1130 interpolation variants vs published zeros")
    print("=" * 100)
    variants = [("zero_annual", "(1) 연복리 현물이자율 선형보간"), ("zero_cont", "(2) 연속복리 현물이자율 선형보간"),
                ("logdf", "(4) 연속복리 선도이자율 constant (log-linear DF)")]
    # variant (3) YTM linear then bootstrap == case A1/B with linear
    results_c = {}
    for key, desc in variants:
        DFk = bootstrap_knots(TENORS, GOV_YTM, 2, key)
        results_c[key] = DFk
    print("   %-5s %-9s " % ("T", "KICPA") + "".join("%-20s" % d[:18] for _, d in variants) + "%-20s" % "(3) YTM-lin (B)")
    worst = {k: 0.0 for k, _ in variants}
    worst["ytm_lin"] = 0.0
    for T in sorted(KICPA_GOV_ZERO):
        row = "   %-5g %-9.6f " % (T, KICPA_GOV_ZERO[T])
        for key, _ in variants:
            z = annual_zero(T, results_c[key][T])
            worst[key] = max(worst[key], abs(z - KICPA_GOV_ZERO[T]) * 1e4)
            row += "%-20s" % ("%.6f(%+.2f)" % (z, (z - KICPA_GOV_ZERO[T]) * 1e4))
        if T <= HORIZON:
            z = annual_zero(T, gov_q["linear"]["dfq_d"][T])
            worst["ytm_lin"] = max(worst["ytm_lin"], abs(z - KICPA_GOV_ZERO[T]) * 1e4)
            row += "%-20s" % ("%.6f(%+.2f)" % (z, (z - KICPA_GOV_ZERO[T]) * 1e4))
        print(row)
    for key, _ in variants:
        print("   DF(50Y) %-12s %.6f  (KICPA %.5f, diff %.2e)" % (key, results_c[key][50.0], KICPA_GOV_DF[50.0], results_c[key][50.0] - KICPA_GOV_DF[50.0]))
        print("   DF(10Y) %-12s %.6f  (KICPA %.6f, diff %.2e)" % (key, results_c[key][10.0], KICPA_GOV_DF[10.0], results_c[key][10.0] - KICPA_GOV_DF[10.0]))
    print("   max|diff| bp vs KICPA: " + ", ".join("%s %.2f" % (k, v) for k, v in worst.items()))

    # ---- D. spot-only interpolation of KICPA's published zero knots by 4 methods -> forward smoothness
    print("\n" + "=" * 100)
    print("D. interpolate KICPA 국채 continuous spot knots (14) onto quarterly grid to 10Y: forward behaviour by method")
    print("=" * 100)
    kt = sorted(KICPA_GOV_ZERO)
    kr = [math.log(1.0 + KICPA_GOV_ZERO[t]) for t in kt]
    kdf = [(1.0 + KICPA_GOV_ZERO[t]) ** (-t) for t in kt]
    d_res = {}
    for name, fn in [("linear spot", lambda: linear(kt, kr)(qg)), ("pchip spot", lambda: pchip(kt, kr)(qg)),
                     ("natural cubic spot", lambda: natural_cubic_spline(kt, kr)(qg)),
                     ("loglinear DF (const fwd)", lambda: loglinear_df(kt, kdf).spot(qg))]:
        r = fn()
        f = forwards(qg, r)
        neg, chg, mxd = flags(f)
        d_res[name] = (r, f)
        print("   %-26s negative fwd=%d  sign changes(delta f)=%d  max|delta f|=%6.2f bp  min f=%.4f%%  max f=%.4f%%"
              % (name, neg, chg, mxd * 1e4, min(f) * 100, max(f) * 100))

    # ---- E. markdown comparison table (case A as specified)
    print("\n" + "=" * 100)
    print("E. MARKDOWN TABLE  (A1 국채 native semiannual -> quarterly; A2 회사채 native quarterly). rates in %, DF 6dp")
    print("=" * 100)
    hdr = "| t | 국채 lin spot | 국채 lin DF | 국채 lin fwd | 국채 pchip spot | 국채 pchip DF | 국채 pchip fwd | 회사채 lin spot | 회사채 lin DF | 회사채 lin fwd | 회사채 pchip spot | 회사채 pchip DF | 회사채 pchip fwd |"
    print(hdr)
    print("|" + "---:|" * 13)
    for i, t in enumerate(qg):
        cells = ["%.2f" % t]
        for res in (gov_native, corp_native):
            for m, _ in METHODS:
                R = res[m]
                cells += ["%.4f" % (R["rq"][i] * 100), "%.6f" % R["dfq"][i], "%.4f" % (R["fq"][i] * 100)]
        print("| " + " | ".join(cells) + " |")

    print("\nE2. MARKDOWN TABLE  (B 국채 quarterly stub-coupon bootstrap, KICPA convention) at knots <= 10Y")
    print("| T | KICPA zero(ann) | lin zero(ann) | lin spot_c | lin DF | lin fwd | pchip zero(ann) | pchip spot_c | pchip DF | pchip fwd |")
    print("|" + "---:|" * 10)
    for i, t in enumerate(qg):
        if t not in KICPA_GOV_ZERO:
            continue
        cells = ["%g" % t, "%.6f" % KICPA_GOV_ZERO[t]]
        for m, _ in METHODS:
            R = gov_q[m]
            cells += ["%.6f" % annual_zero(t, R["dfq"][i]), "%.4f" % (R["rq"][i] * 100), "%.6f" % R["dfq"][i], "%.4f" % (R["fq"][i] * 100)]
        print("| " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
