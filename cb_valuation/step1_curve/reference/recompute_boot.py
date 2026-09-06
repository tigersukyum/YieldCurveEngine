# -*- coding: utf-8 -*-
"""
recompute_boot.py  --  standard library only.

Re-derives sheet BOOT of the KBI-metal CB model from the cached cell dump
(xl_BOOT.txt) and the YTM matrix dump (xl_KIS-NET.txt) and compares every
recomputed value with the cached Excel value.

Sections
  A. parse dumps
  B. recompute H, I (RF semiannual bootstrap) from G ; W, X (RD quarterly) from V
  C. recompute M, N (RF quarterly re-grid, annual-effective / continuous) from L
     and AB, AC from AA ; also check L (midpoint re-grid of H) and AA (= W)
  D. hypothesis tests on the hardcoded G / V columns
       D1  G, V are linear interpolations (in the per-period rate) between tenor knots
       D2  knot values G*2 vs KIS-NET row 2 ; V*4 vs KIS-NET row 58   (stale?)
  E. par verification : price of a par bond with coupon c_n for n periods == 1
  F. what the app SHOULD produce if G / V were derived live from KIS-NET
  G. MF_INTERPOL semantics check (VBA port) against the observed BM value
"""
import math, re, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOOT_TXT = os.path.join(HERE, "xl_BOOT.txt")
KIS_TXT = os.path.join(HERE, "xl_KIS-NET.txt")

# ---------------------------------------------------------------- A. parse
LINE_RE = re.compile(r"^(?:\d+\t)?([A-Z]{1,3}\d+)\tVAL=(.*?)(?:\tFORMULA=(.*))?$")


def parse_dump(path):
    vals, forms = {}, {}
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.rstrip("\r\n")
            if not raw:
                continue
            m = LINE_RE.match(raw)
            if not m:
                # tolerate a leading line-number column if present
                parts = raw.split("\t")
                if len(parts) >= 2 and parts[0].isdigit():
                    m = LINE_RE.match("\t".join(parts[1:]))
            if not m:
                raise ValueError("unparsed line: %r" % raw)
            cell, v, f = m.group(1), m.group(2), m.group(3)
            if v.startswith("'"):
                vals[cell] = v.strip("'")
            else:
                vals[cell] = float(v)
            if f is not None:
                forms[cell] = f
    return vals, forms


boot, boot_f = parse_dump(BOOT_TXT)
kis, _ = parse_dump(KIS_TXT)


def col(letter, r0, r1):
    return [boot["%s%d" % (letter, r)] for r in range(r0, r1 + 1)]


def maxabs(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def report(name, recomputed, cached, extra=""):
    err = maxabs(recomputed, cached)
    print("  %-28s n=%2d  max|err| = %.3e %s" % (name, len(cached), err, extra))
    return err


# ---------------------------------------------------------------- B. bootstrap


def bootstrap(par_per_period):
    """Excel BOOT recursion.
    spot_1 = c_1
    spot_n = ((1+c_n)/(1-c_n*SUM(DF_1..DF_{n-1})))^(1/n) - 1
    DF_n   = 1/(1+spot_n)^n
    All rates are PER-PERIOD (semiannual for RF, quarterly for RD); n = period index (1-based).
    """
    spots, dfs, cum = [], [], 0.0
    for n, c in enumerate(par_per_period, start=1):
        if n == 1:
            s = c
        else:
            s = ((1.0 + c) / (1.0 - c * cum)) ** (1.0 / n) - 1.0
        df = 1.0 / (1.0 + s) ** n
        spots.append(s)
        dfs.append(df)
        cum += df
    return spots, dfs


print("=" * 78)
print("B. bootstrap recursion  (H, I from G ; W, X from V)")
# RF semiannual block rows 10..29 (20 half-years)
E = col("E", 10, 29)
F = col("F", 10, 29)
G = col("G", 10, 29)
H = col("H", 10, 29)
I = col("I", 10, 29)
assert F == [float(k) for k in range(1, 21)], F
assert all(abs(E[k] - 0.5 * (k + 1)) < 1e-12 for k in range(20))
H_re, I_re = bootstrap(G)
errB_H = report("RF  H (D-SPOT H) from G", H_re, H)
errB_I = report("RF  I (PV FACTOR)", I_re, I)

# RD quarterly block rows 10..49 (40 quarters)
T = col("T", 10, 49)
U = col("U", 10, 49)
V = col("V", 10, 49)
W = col("W", 10, 49)
X = col("X", 10, 49)
assert U == [float(k) for k in range(1, 41)], U
assert all(abs(T[k] - 0.25 * (k + 1)) < 1e-12 for k in range(40))
W_re, X_re = bootstrap(V)
errB_W = report("RD  W (D-SPOT Q) from V", W_re, W)
errB_X = report("RD  X (PV FACTOR)", X_re, X)

# ---------------------------------------------------------------- C. re-grid + compounding
print("=" * 78)
print("C. quarterly re-grid and compounding conversions")
K = col("K", 10, 49)
L = col("L", 10, 49)
M = col("M", 10, 49)
N = col("N", 10, 49)
Z = col("Z", 10, 49)
AA = col("AA", 10, 49)
AB = col("AB", 10, 49)
AC = col("AC", 10, 49)
assert all(abs(K[k] - 0.25 * (k + 1)) < 1e-12 for k in range(40))
assert all(abs(Z[k] - 0.25 * (k + 1)) < 1e-12 for k in range(40))

# C1. L: hardcoded except L10 (=C10/2).  Hypothesis: L(0.25)=C10/2 ; L(0.5k)=H_k ; L(midpoint)= (L_prev+L_next)/2
C10 = boot["C10"]
L_re = [None] * 40
L_re[0] = C10 / 2.0
for k in range(20):            # half-year points 0.5,1.0,...,10 -> index 1,3,5,...,39
    L_re[2 * k + 1] = H[k]
for j in range(2, 40, 2):      # quarter midpoints 0.75,1.25,...,9.75 -> index 2,4,...,38
    L_re[j] = 0.5 * (L_re[j - 1] + L_re[j + 1])
errC_L = report("RF  L (re-grid of H, midpoint avg)", L_re, L, "[L10=C10/2, L(0.5k)=H_k, midpoints=avg]")
errC_L_fromcached = report("RF  L midpoints from cached H", [0.5 * (L[j - 1] + L[j + 1]) for j in range(2, 40, 2)],
                           [L[j] for j in range(2, 40, 2)])

# C2. M = (1+L)^2-1 ; N = LN(1+M)
M_re = [(1.0 + l) ** 2 - 1.0 for l in L]
N_re = [math.log(1.0 + m) for m in M]
errC_M = report("RF  M (D-SPOT Y)=(1+L)^2-1", M_re, M)
errC_N = report("RF  N (C-SPOT Y)=LN(1+M)", N_re, N)
# chained from recomputed L
M_chain = [(1.0 + l) ** 2 - 1.0 for l in L_re]
N_chain = [math.log(1.0 + m) for m in M_chain]
errC_Mc = report("RF  M chained from G", M_chain, M)
errC_Nc = report("RF  N chained from G", N_chain, N)

# C3. AA = W ; AB = (1+AA)^4-1 ; AC = LN(1+AB)
errC_AA = report("RD  AA (= W)", W, AA)
AB_re = [(1.0 + a) ** 4 - 1.0 for a in AA]
AC_re = [math.log(1.0 + b) for b in AB]
errC_AB = report("RD  AB (D-SPOT Y)=(1+AA)^4-1", AB_re, AB)
errC_AC = report("RD  AC (C-SPOT Y)=LN(1+AB)", AC_re, AC)
AB_chain = [(1.0 + a) ** 4 - 1.0 for a in W_re]
AC_chain = [math.log(1.0 + b) for b in AB_chain]
errC_ABc = report("RD  AB chained from V", AB_chain, AB)
errC_ACc = report("RD  AC chained from V", AC_chain, AC)

# ---------------------------------------------------------------- D. G / V origin
print("=" * 78)
print("D. origin of hardcoded G (RF (H)) and V (RD (Q))")

TENOR_LABELS = ["3M", "6M", "9M", "1Y", "1.5Y", "2Y", "2.5Y", "3Y", "4Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y", "50Y"]
TENOR_YEARS = [0.25, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 7, 10, 15, 20, 30, 50]
KIS_COLS = ["D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S"]


def kis_row(r):
    out = []
    for c in KIS_COLS:
        v = kis.get("%s%d" % (c, r))
        out.append(v if isinstance(v, float) else None)
    return out


kis_rf = kis_row(2)     # 국고채
kis_rd = kis_row(58)    # 회사채BB+ (사모무보증)
print("  KIS-NET row 2  (국고채)   :", kis_rf)
print("  KIS-NET row 58 (회사채BB+):", kis_rd)

# check header rows 4/5 and columns C/R of BOOT vs KIS-NET (these ARE live / current)
row4 = [boot["%s4" % c] for c in "BCDEFGHIJKLMNOPQ"]
row5 = [boot.get("%s5" % c) for c in "BCDEFGHIJKLMNOPQ"]
print("  BOOT row4 (RF) - KIS-NET row2/100  max|d| = %.3e" % max(abs(a - b / 100) for a, b in zip(row4, kis_rf)))
print("  BOOT row5 (RD) - KIS-NET row58/100 max|d| = %.3e  (P5,Q5 absent -> 30Y/50Y are '-' in KIS-NET)"
      % max(abs(a - b / 100) for a, b in zip(row5[:14], kis_rd[:14])))
Ccol = col("C", 10, 25)
Rcol = col("R", 10, 25)
print("  BOOT col C (RF-YTM, hardcoded) - KIS-NET row2/100  max|d| = %.3e" % max(abs(a - b / 100) for a, b in zip(Ccol, kis_rf)))
print("  BOOT col R (RD-YTM, hardcoded) - KIS-NET row58/100 max|d| = %.3e ; R24,R25 (30Y,50Y) = %r,%r"
      % (max(abs(a - b / 100) for a, b in zip(Rcol[:14], kis_rd[:14])), boot["R24"], boot["R25"]))


def lin_interp_knots(xs, kx, ky):
    """plain linear interpolation on sorted knots, no extrapolation needed (xs inside)."""
    out = []
    for x in xs:
        for i in range(1, len(kx)):
            if kx[i - 1] <= x <= kx[i]:
                w = (x - kx[i - 1]) / (kx[i] - kx[i - 1])
                out.append(ky[i - 1] + w * (ky[i] - ky[i - 1]))
                break
        else:
            raise ValueError(x)
    return out


# D1a. G: knots at 0.5,1,1.5,2,2.5,3,4,5,7,10 (semiannual grid 0.5..10)
RF_KNOTS = [0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 7, 10]
rf_knot_idx = [int(round(t / 0.5)) - 1 for t in RF_KNOTS]     # index into rows 10..29
G_knot = [G[i] for i in rf_knot_idx]
G_interp = lin_interp_knots(E, RF_KNOTS, G_knot)
errD_G = report("G vs linear interp of its own knots", G_interp, G, "[knots 0.5,1,1.5,2,2.5,3,4,5,7,10]")

# D1b. V: knots at 0.25,0.5,0.75,1,1.5,2,2.5,3,4,5,7,10 (quarterly grid 0.25..10)
RD_KNOTS = [0.25, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 7, 10]
rd_knot_idx = [int(round(t / 0.25)) - 1 for t in RD_KNOTS]
V_knot = [V[i] for i in rd_knot_idx]
V_interp = lin_interp_knots(T, RD_KNOTS, V_knot)
errD_V = report("V vs linear interp of its own knots", V_interp, V, "[knots 0.25..10]")

# D2. knot values vs KIS-NET (current)
print("\n  D2. RF knots: G*2 (implied YTM %) vs KIS-NET row 2 (국고채, %)")
print("      %-6s %12s %12s %12s" % ("tenor", "G*2 (%)", "KIS-NET(%)", "diff(%p)"))
rf_knot_diffs = []
for t, g in zip(RF_KNOTS, G_knot):
    j = TENOR_YEARS.index(t)
    imp = g * 2 * 100
    cur = kis_rf[j]
    rf_knot_diffs.append(imp - cur)
    print("      %-6s %12.4f %12.3f %+12.4f" % (TENOR_LABELS[j], imp, cur, imp - cur))
print("      max|diff| = %.4f %%p ; mean diff = %+.4f %%p" % (max(abs(d) for d in rf_knot_diffs), sum(rf_knot_diffs) / len(rf_knot_diffs)))

print("\n  D2. RD knots: V*4 (implied YTM %) vs KIS-NET row 58 (회사채BB+ 사모무보증, %)")
print("      %-6s %12s %12s %12s" % ("tenor", "V*4 (%)", "KIS-NET(%)", "diff(%p)"))
rd_knot_diffs = []
for t, v in zip(RD_KNOTS, V_knot):
    j = TENOR_YEARS.index(t)
    imp = v * 4 * 100
    cur = kis_rd[j]
    rd_knot_diffs.append(imp - cur)
    print("      %-6s %12.4f %12.3f %+12.4f" % (TENOR_LABELS[j], imp, cur, imp - cur))
print("      max|diff| = %.4f %%p ; mean diff = %+.4f %%p" % (max(abs(d) for d in rd_knot_diffs), sum(rd_knot_diffs) / len(rd_knot_diffs)))

# D3. does G*2 match ANY other KIS-NET row (i.e. was a different row pasted)?  scan rows 2..60
def scan_rows(target_pct, knots):
    best = []
    for r in range(2, 61):
        row = kis_row(r)
        try:
            d = max(abs(target_pct[i] - row[TENOR_YEARS.index(t)]) for i, t in enumerate(knots))
        except TypeError:
            continue
        best.append((d, r, kis.get("C%d" % r)))
    best.sort()
    return best[:3]


print("\n  D3. closest KIS-NET rows to G*2 :", scan_rows([g * 200 for g in G_knot], RF_KNOTS))
print("      closest KIS-NET rows to V*4 :", scan_rows([v * 400 for v in V_knot], RD_KNOTS))

# ---------------------------------------------------------------- E. par verification
print("=" * 78)
print("E. par verification  price_n = c_n * SUM(DF_1..DF_n) + DF_n  (must equal 1)")


def par_check(cpp, dfs):
    devs = []
    cum = 0.0
    for n, (c, df) in enumerate(zip(cpp, dfs), start=1):
        cum += df
        devs.append(c * cum + df - 1.0)
    return devs


for label, cpp, dfs in [("RF (cached I)", G, I), ("RF (recomputed I)", G, I_re),
                        ("RD (cached X)", V, X), ("RD (recomputed X)", V, X_re)]:
    devs = par_check(cpp, dfs)
    print("  %-20s n=%2d max|price-1| = %.3e" % (label, len(devs), max(abs(d) for d in devs)))

# par check on the ANNUAL-EFFECTIVE re-gridded curve is NOT exact (re-gridding changes DFs) -- report it too
# reprice RF par bonds on the quarterly grid K using M (annual eff.) at the semiannual coupon dates
DF_from_M = {K[k]: 1.0 / (1.0 + M[k]) ** K[k] for k in range(40)}
devs = []
for n in range(1, 21):
    t_n = 0.5 * n
    cum = sum(DF_from_M[0.5 * j] for j in range(1, n + 1))
    devs.append(G[n - 1] * cum + DF_from_M[t_n] - 1.0)
print("  RF re-priced with M(annual eff.) at half-year nodes : max|price-1| = %.3e (should also be ~0: same DFs)" % max(abs(d) for d in devs))

# ---------------------------------------------------------------- F. live from KIS-NET
print("=" * 78)
print("F. what the app SHOULD produce with G / V derived live from KIS-NET")


def live_rf():
    ytm = {t: kis_rf[TENOR_YEARS.index(t)] / 100.0 for t in RF_KNOTS}
    knot_pp = [ytm[t] / 2.0 for t in RF_KNOTS]
    grid = [0.5 * k for k in range(1, 21)]
    g_live = lin_interp_knots(grid, RF_KNOTS, knot_pp)
    h, i = bootstrap(g_live)
    # quarterly re-grid exactly as BOOT does
    l = [None] * 40
    l[0] = kis_rf[0] / 100.0 / 2.0
    for k in range(20):
        l[2 * k + 1] = h[k]
    for j in range(2, 40, 2):
        l[j] = 0.5 * (l[j - 1] + l[j + 1])
    m = [(1 + x) ** 2 - 1 for x in l]
    nn = [math.log(1 + x) for x in m]
    return g_live, h, i, l, m, nn


def live_rd():
    ytm = {t: kis_rd[TENOR_YEARS.index(t)] / 100.0 for t in RD_KNOTS}
    knot_pp = [ytm[t] / 4.0 for t in RD_KNOTS]
    grid = [0.25 * k for k in range(1, 41)]
    v_live = lin_interp_knots(grid, RD_KNOTS, knot_pp)
    w, x = bootstrap(v_live)
    ab = [(1 + s) ** 4 - 1 for s in w]
    ac = [math.log(1 + b) for b in ab]
    return v_live, w, x, ab, ac


g_live, h_live, i_live, l_live, m_live, n_live = live_rf()
v_live, w_live, x_live, ab_live, ac_live = live_rd()

print("  RF live (KIS-NET row 2, semiannual):")
print("     G_live(10Y)=%.10f  H_live(10Y, per half-year)=%.10f" % (g_live[-1], h_live[-1]))
print("     D-SPOT(Y) 10Y = %.10f   C-SPOT(Y) 10Y = %.10f   PV(10Y) = %.10f" % (m_live[-1], n_live[-1], i_live[-1]))
print("     D-SPOT(Y) 0.25Y = %.10f (=(1+3M/2)^2-1)  1Y = %.10f  3Y = %.10f  5Y = %.10f" % (m_live[0], m_live[3], m_live[11], m_live[19]))
print("     (cached stale model: D-SPOT(Y) 10Y = %.10f  C-SPOT 10Y = %.10f)" % (M[-1], N[-1]))
print("  RD live (KIS-NET row 58, quarterly):")
print("     V_live(10Y)=%.10f  W_live(10Y, per quarter)=%.10f" % (v_live[-1], w_live[-1]))
print("     D-SPOT(Y) 10Y = %.10f   C-SPOT(Y) 10Y = %.10f   PV(10Y) = %.10f" % (ab_live[-1], ac_live[-1], x_live[-1]))
print("     D-SPOT(Y) 0.25Y = %.10f  1Y = %.10f  3Y = %.10f  5Y = %.10f" % (ab_live[0], ab_live[3], ab_live[11], ab_live[19]))
print("     (cached stale model: D-SPOT(Y) 10Y = %.10f  C-SPOT 10Y = %.10f)" % (AB[-1], AC[-1]))
# par check on live curves
print("  par check live RF : %.3e ; live RD : %.3e" % (
    max(abs(d) for d in par_check(g_live, i_live)), max(abs(d) for d in par_check(v_live, x_live))))
# monotonic / positivity sanity
print("  live RF spot(Y) min=%.6f max=%.6f ; live RD spot(Y) min=%.6f max=%.6f" % (
    min(m_live), max(m_live), min(ab_live), max(ab_live)))
print("  live RD - RF spread at 10Y (annual eff.) = %.6f" % (ab_live[-1] - m_live[-1]))

# full live tables for reference
print("\n  live RF quarterly table (t, L per-half-year, M annual-eff, N continuous):")
for k in range(40):
    print("     %5.2f  %.10f  %.10f  %.10f" % (K[k], l_live[k], m_live[k], n_live[k]))
print("\n  live RD quarterly table (t, V per-quarter, W spot per-quarter, AB annual-eff, AC continuous):")
for k in range(40):
    print("     %5.2f  %.10f  %.10f  %.10f  %.10f" % (T[k], v_live[k], w_live[k], ab_live[k], ac_live[k]))

# ---------------------------------------------------------------- G. MF_INTERPOL port
print("=" * 78)
print("G. MF_INTERPOL (VBA Module1) port and semantics check")


def mf_interpol(x, xs, ys):
    """Faithful port of MF_INTERPOL (vertical-range branch).
    - first knot i with x <= xs[i]
    - i == 0 : ys[0] * x / xs[0]            (linear from the ORIGIN (0,0))
    - else   : linear between knots i-1 and i
    - x > xs[-1] : loop never matches -> VBA returns Empty (shows as 0 in Excel)
    """
    for i, xi in enumerate(xs):
        if x <= xi:
            if i == 0:
                return ys[0] * x / xs[0]
            return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1])
    return None   # Empty


obs = mf_interpol(0.019199, K, M)
print("  mf_interpol(0.019199, K10:K49, M10:M49) = %.7f  (BM observed 0.0018713 ; M10 = %.7f)" % (obs, M[0]))
print("  mf_interpol(0.25, K, M) = %.10f (== M10 exactly: %s)" % (mf_interpol(0.25, K, M), mf_interpol(0.25, K, M) == M[0]))
print("  mf_interpol(10.0, K, M) = %.10f ; mf_interpol(10.25, K, M) = %r  (beyond last knot -> Empty/0)"
      % (mf_interpol(10.0, K, M), mf_interpol(10.25, K, M)))
print("  mf_interpol(0.0, K, M) = %r ; mf_interpol(-0.1, K, M) = %r" % (mf_interpol(0.0, K, M), mf_interpol(-0.1, K, M)))
# what if instead flat extrapolation were used below 0.25?
print("  alternative (flat-left) value at 0.019199 would be M10 = %.7f ; BM uses %.7f -> ratio %.4f"
      % (M[0], obs, obs / M[0]))

print("=" * 78)
print("SUMMARY max|err| : H %.2e  I %.2e  W %.2e  X %.2e | L %.2e  M %.2e  N %.2e  AA %.2e  AB %.2e  AC %.2e | "
      "G-lin %.2e  V-lin %.2e" % (errB_H, errB_I, errB_W, errB_X, errC_L, errC_M, errC_N, errC_AA, errC_AB, errC_AC, errD_G, errD_V))
