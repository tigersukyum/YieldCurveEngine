# -*- coding: utf-8 -*-
"""Property tests for interp_ref.py (standard library only)."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from interp_ref import pchip, pchip_slopes, linear, loglinear_df, natural_cubic_spline  # noqa: E402

FAILS = 0


def report(name, ok, detail=""):
    global FAILS
    if not ok:
        FAILS += 1
    print("%-4s %-70s %s" % ("PASS" if ok else "FAIL", name, detail))


def dense(x0, x1, n=4001):
    return [x0 + (x1 - x0) * i / (n - 1) for i in range(n)]


# ---------------------------------------------------------------- data sets
MATLAB_X = [-3, -2, -1, 0, 1, 2, 3]
MATLAB_Y = [-1, -1, -1, 0, 1, 1, 1]

KICPA_T = [0.25, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 7, 10, 20, 50]
KICPA_Z = [0.032898, 0.03312, 0.033424, 0.033786, 0.034095, 0.033936, 0.03341,
           0.032936, 0.033051, 0.032805, 0.033734, 0.033452, 0.034003, 0.033793]

CORP_T = [0.25, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 7, 10]
CORP_Y = [3.675, 3.745, 3.815, 3.863, 3.938, 3.970, 3.998, 4.032, 4.048, 4.225, 4.529, 5.094]

random.seed(20230503)
RAND_X = sorted(random.uniform(0, 30) for _ in range(12))
RAND_Y = [random.gauss(0.03, 0.01) for _ in range(12)]

DATASETS = [("MATLAB step", MATLAB_X, MATLAB_Y), ("KICPA gov zero", KICPA_T, KICPA_Z),
            ("corp YTM (monotone)", CORP_T, CORP_Y), ("random", RAND_X, RAND_Y)]
METHODS = [("linear", linear), ("pchip", pchip), ("natural cubic", natural_cubic_spline)]

# ---------------------------------------------------------------- 1. knots pass-through
print("== 1. interpolant passes through knots (max |f(x_k) - y_k|)")
for dname, x, y in DATASETS:
    for mname, ctor in METHODS:
        f = ctor(x, y)
        err = max(abs(f(xi) - yi) for xi, yi in zip(x, y))
        report("knots: %s / %s" % (mname, dname), err <= 1e-14, "max err = %.3e" % err)
    dfk = [math.exp(-0.03 * xi) if xi > 0 else 1.0 for xi in x]
    if x[0] > 0 or True:
        xx = [xi for xi in x if xi > 0]
        dd = [math.exp(-0.03 * xi) for xi in xx]
        g = loglinear_df(xx, dd)
        err = max(abs(g(xi) - di) for xi, di in zip(xx, dd))
        report("knots: loglinear_df / %s" % dname, err <= 1e-14, "max err = %.3e" % err)

# ---------------------------------------------------------------- 2. PCHIP monotone, no overshoot
print("== 2. PCHIP preserves monotonicity / no overshoot on monotone data")
for dname, x, y in [("MATLAB step", MATLAB_X, MATLAB_Y), ("corp YTM", CORP_T, CORP_Y)]:
    p = pchip(x, y)
    xs = dense(x[0], x[-1])
    ys = p(xs)
    diffs = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
    mono = min(diffs) >= -1e-15
    # per-segment containment: value within [y_i, y_{i+1}]
    over = 0.0
    for i in range(len(x) - 1):
        lo, hi = min(y[i], y[i + 1]), max(y[i], y[i + 1])
        for xq in dense(x[i], x[i + 1], 401):
            v = p(xq)
            over = max(over, lo - v, v - hi)
    report("pchip monotone (dense diffs >= 0): %s" % dname, mono, "min diff = %.3e" % min(diffs))
    report("pchip no overshoot beyond segment ends: %s" % dname, over <= 1e-15, "max excursion = %.3e" % over)

# ---------------------------------------------------------------- 3. natural cubic overshoots
print("== 3. natural cubic spline overshoots on the same monotone data (demonstration)")
for dname, x, y in [("MATLAB step", MATLAB_X, MATLAB_Y), ("corp YTM", CORP_T, CORP_Y)]:
    s = natural_cubic_spline(x, y)
    over = 0.0
    where = None
    for i in range(len(x) - 1):
        lo, hi = min(y[i], y[i + 1]), max(y[i], y[i + 1])
        for xq in dense(x[i], x[i + 1], 401):
            v = s(xq)
            e = max(lo - v, v - hi)
            if e > over:
                over, where = e, (xq, v)
    xs = dense(x[0], x[-1])
    ys = s(xs)
    diffs = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
    mono_txt = "non-monotone" if min(diffs) < -1e-12 else "monotone"
    if dname == "MATLAB step":
        report("natural cubic overshoots segment range: %s" % dname, over > 1e-6,
               "max excursion = %.4e at x=%.3f (value %.6f); min dense diff = %.3e (%s)"
               % (over, where[0], where[1], min(diffs), mono_txt))
    else:
        # informational: overshoot is data dependent; a gently curved monotone set may not trigger it
        print("INFO natural cubic on %-52s max excursion = %.3e; min dense diff = %.3e (%s)"
              % (dname, over, min(diffs), mono_txt))
s = natural_cubic_spline(MATLAB_X, MATLAB_Y)
vmax = max(s(dense(-3, 3)))
vmin = min(s(dense(-3, 3)))
report("natural cubic MATLAB example: max > 1 and min < -1", vmax > 1 and vmin < -1,
       "max = %.6f, min = %.6f (data range [-1, 1])" % (vmax, vmin))

# ---------------------------------------------------------------- 4. linear kinks, pchip C1
print("== 4. linear has kinks (derivative jumps at knots); pchip is C1; natural cubic is C2")
eps = 1e-9
for dname, x, y in [("KICPA gov zero", KICPA_T, KICPA_Z), ("random", RAND_X, RAND_Y)]:
    for mname, ctor in METHODS:
        f = ctor(x, y)
        jump = max(abs(f.deriv(xk + eps) - f.deriv(xk - eps)) for xk in x[1:-1])
        if mname == "linear":
            report("linear derivative jumps at interior knots: %s" % dname, jump > 1e-6, "max |f'(x+)-f'(x-)| = %.4e" % jump)
        else:
            report("%s derivative continuous at knots: %s" % (mname, dname), jump < 1e-6, "max |f'(x+)-f'(x-)| = %.4e" % jump)
    # natural cubic: C2 continuity holds by construction (same M_k on both sides of each knot);
    # verify the tridiagonal system residual and the natural end conditions instead
    s = natural_cubic_spline(x, y)
    hh = [x[i + 1] - x[i] for i in range(len(x) - 1)]
    dl = [(y[i + 1] - y[i]) / hh[i] for i in range(len(x) - 1)]
    resid = max(abs(hh[i - 1] * s.M[i - 1] + 2 * (hh[i - 1] + hh[i]) * s.M[i] + hh[i] * s.M[i + 1]
                    - 6 * (dl[i] - dl[i - 1])) for i in range(1, len(x) - 1))
    scale = max(1.0, max(abs(v) for v in s.M))
    report("natural cubic spline system residual ~0, M_0 = M_n = 0: %s" % dname,
           resid < 1e-12 * scale and s.M[0] == 0.0 and s.M[-1] == 0.0,
           "max residual = %.3e; max|M| = %.3e; min knot gap = %.3f" % (resid, scale, min(hh)))

# ---------------------------------------------------------------- 5. MATLAB pchip example analytic values
print("== 5. MATLAB pchip doc example x=-3:3, y=[-1 -1 -1 0 1 1 1] (analytic values from the slope rules)")
d = pchip_slopes(MATLAB_X, MATLAB_Y)
report("MATLAB example slopes == [0,0,0,1,0,0,0]", d == [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0], "d = %s" % d)
p = pchip(MATLAB_X, MATLAB_Y)
expected = {-2.5: -1.0, -1.5: -1.0, -0.5: -0.625, 0.5: 0.625, 1.5: 1.0, 2.5: 1.0, 0.0: 0.0}
err = max(abs(p(k) - v) for k, v in expected.items())
report("MATLAB example values p(-0.5)=-0.625, p(0.5)=0.625, flat = +-1", err < 1e-15, "max err = %.3e" % err)

# ---------------------------------------------------------------- 6. loglinear_df == constant forward
print("== 6. loglinear_df: piecewise-constant continuous forward, DF(0)=1")
t = [0.5, 1, 2, 3, 5]
df = [0.985, 0.968, 0.935, 0.902, 0.84]
g = loglinear_df(t, df)
fwd_exp = [-(math.log(df[i + 1]) - math.log(df[i])) / (t[i + 1] - t[i]) for i in range(len(t) - 1)]
fwd_exp = [-math.log(df[0]) / t[0]] + fwd_exp
ok = all(abs(g.forward(t[i] - 1e-6) - fwd_exp[i]) < 1e-12 for i in range(len(t)))
report("forward on each segment == -dlnDF/dt", ok, "f = %s" % ["%.6f" % v for v in g.f])
mid = 1.5
r_mid = g.spot(mid)
report("DF(0) == 1 (anchor)", abs(g(0.0) - 1.0) < 1e-15, "DF(0) = %r" % g(0.0))
report("spot(t) = -ln DF/t consistent", abs(math.exp(-r_mid * mid) - g(mid)) < 1e-15, "spot(1.5) = %.8f" % r_mid)

# ---------------------------------------------------------------- 7. two-point PCHIP == linear
p2 = pchip([0, 1], [1, 3])
report("two-knot pchip reduces to straight line", abs(p2(0.3) - 1.6) < 1e-15, "p(0.3) = %r" % p2(0.3))

# ---------------------------------------------------------------- 8. edge-case clamp (3*m0)
# data where the end three-point estimate exceeds 3*delta_0 with opposite-sign neighbour slope
x = [0, 1, 2, 3]
y = [0, 0.1, -5, -5.1]
d = pchip_slopes(x, y)
h0, h1, m0, m1 = 1, 1, 0.1, -5.1
d0_raw = ((2 * h0 + h1) * m0 - h0 * m1) / (h0 + h1)
report("edge clamp d0 = 3*delta_0 when |d| > 3|delta_0| and slope sign change",
       abs(d[0] - 0.3) < 1e-15, "raw d0 = %.4f -> d0 = %r" % (d0_raw, d[0]))
x = [0, 1, 2, 3]
y = [0, 0.1, 5, 5.1]
d = pchip_slopes(x, y)
d0_raw = (3 * 0.1 - 4.9) / 2.0
report("edge d0 = 0 when sign(d) != sign(delta_0)", d[0] == 0.0, "raw d0 = %.4f -> d0 = %r" % (d0_raw, d[0]))

print("\nTOTAL FAILURES:", FAILS)
sys.exit(1 if FAILS else 0)
