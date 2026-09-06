# Pure-Python Hagan-West monotone convex (unameliorated) — implementation per
# Hagan & West (2008) Wilmott §6, eqs (22)-(34), collar step (6.1), and
# West (2011) §3.2 integration formulas (30)-(32). Verified below against
# QuantLib 1.43 ConvexMonotoneInterpolation(quadraticity=0, monotonicity=1).
import math

def collar(a, x, b):
    return max(a, min(x, b))

class MonotoneConvex:
    def __init__(self, tau, values, inputs_are_forwards=False, force_positive=True):
        # tau: knot times t_1..t_n (>0). values: continuous zero rates r_i (r*t basis) or discrete fwds f^d_i
        n = len(tau)
        self.n = n
        self.tau = [0.0] + list(tau)                     # tau_0 = 0
        if inputs_are_forwards:
            fd = [None] + list(values)
        else:
            r = [0.0] + list(values)
            fd = [None] + [(r[i]*self.tau[i] - r[i-1]*self.tau[i-1])/(self.tau[i]-self.tau[i-1]) for i in range(1, n+1)]
        self.fd = fd
        f = [0.0]*(n+1)
        for i in range(1, n):
            f[i] = ((self.tau[i]-self.tau[i-1])/(self.tau[i+1]-self.tau[i-1]))*fd[i+1] \
                 + ((self.tau[i+1]-self.tau[i])/(self.tau[i+1]-self.tau[i-1]))*fd[i]       # (22)
        f[0] = fd[1] - 0.5*(f[1]-fd[1])                                                     # (23)
        f[n] = fd[n] - 0.5*(f[n-1]-fd[n])                                                   # (24)
        if force_positive:                                                                  # §6.1 step (3)
            f[0] = collar(0.0, f[0], 2*fd[1])
            for i in range(1, n):
                f[i] = collar(0.0, f[i], 2*min(fd[i], fd[i+1]))
            f[n] = collar(0.0, f[n], 2*fd[n])
        self.f = f

    def _interval(self, t):
        # unique i with tau_{i-1} <= t < tau_i (i in 1..n); t>=tau_n -> n
        n = self.n
        if t >= self.tau[n]:
            return n
        lo, hi = 1, n
        while lo < hi:
            mid = (lo+hi)//2
            if t < self.tau[mid]:
                hi = mid
            else:
                lo = mid+1
        return lo

    def _g_and_G(self, i, x):
        """return g(x) and G(x)=int_0^x g on interval i, per the 4 sectors."""
        g0 = self.f[i-1] - self.fd[i]
        g1 = self.f[i] - self.fd[i]
        if x <= 0.0:
            return g0, 0.0
        if x >= 1.0:
            return g1, 0.0
        if g0 == 0.0 and g1 == 0.0:                       # origin
            return 0.0, 0.0
        # sector tests (H&W 2008 Fig. 4 / H&W 2006 regions (i)-(iv))
        if (g0 < 0 and -0.5*g0 <= g1 <= -2*g0) or (g0 > 0 and -0.5*g0 >= g1 >= -2*g0):
            # (i): unmodified quadratic (27)
            g = g0*(1 - 4*x + 3*x*x) + g1*(-2*x + 3*x*x)
            G = g0*(x - 2*x*x + x**3) + g1*(-x*x + x**3)
        elif (g0 < 0 and g1 > -2*g0) or (g0 > 0 and g1 < -2*g0):
            # (ii): flat then quadratic (28),(29); G per West 2011 (30)
            eta = (g1 + 2*g0)/(g1 - g0)
            if x <= eta:
                g = g0
                G = g0*x
            else:
                g = g0 + (g1-g0)*((x-eta)/(1-eta))**2
                G = g0*x + (g1-g0)*(x-eta)**3/(3*(1-eta)**2)
        elif (g0 > 0 and 0 > g1 > -0.5*g0) or (g0 < 0 and 0 < g1 < -0.5*g0):
            # (iii): quadratic then flat (30),(31); G per West 2011 (31)
            eta = 3*g1/(g1 - g0)
            if x < eta:
                g = g1 + (g0-g1)*((eta-x)/eta)**2
                G = g1*x + (g0-g1)*(eta - (eta-x)**3/eta**2)/3
            else:
                g = g1
                G = g1*x + (g0-g1)*eta/3
        else:
            # (iv): g0,g1 same sign (incl. one zero): two quadratics (32)-(34); G per West 2011 (32)
            eta = g1/(g1 + g0)
            A = -g0*g1/(g0 + g1)
            if x < eta:
                g = A + (g0-A)*((eta-x)/eta)**2
                G = A*x + (g0-A)*(eta - (eta-x)**3/eta**2)/3
            else:
                g = A + (g1-A)*((x-eta)/(1-eta))**2
                G = A*x + (g0-A)*eta/3 + (g1-A)*(x-eta)**3/(3*(1-eta)**2)
        return g, G

    def forward(self, t):
        n = self.n
        if t >= self.tau[n]:
            return self.f[n]                  # flat extrapolation of the forward (West 2011 §3.3)
        i = self._interval(t)
        x = (t - self.tau[i-1])/(self.tau[i]-self.tau[i-1])
        g, _ = self._g_and_G(i, x)
        return g + self.fd[i]                 # (26)

    def rt(self, t):
        """r(t)*t = integral_0^t f  (eq. 12 with West 2011 eq. 29)"""
        n = self.n
        if t <= 0:
            return 0.0
        if t > self.tau[n]:
            return self.rt(self.tau[n]) + (t - self.tau[n])*self.f[n]
        i = self._interval(t)
        acc = 0.0
        for k in range(1, i):
            acc += self.fd[k]*(self.tau[k]-self.tau[k-1])
        x = (t - self.tau[i-1])/(self.tau[i]-self.tau[i-1])
        _, G = self._g_and_G(i, x)
        return acc + (t - self.tau[i-1])*self.fd[i] + (self.tau[i]-self.tau[i-1])*G

    def zero(self, t):
        return self.rt(t)/t

# ---------- test on KICPA 국채 bootstrapped zero rates (annual comp.) -> continuous ----------
tenors = [0.25, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 7, 10, 20, 50]
z_annual = [0.032898, 0.03312, 0.033424, 0.033786, 0.034095, 0.033936, 0.03341, 0.032936,
            0.033051, 0.032805, 0.033734, 0.033452, 0.034003, 0.033793]
r_cont = [math.log(1+z) for z in z_annual]
mc = MonotoneConvex(tenors, r_cont, force_positive=True)
print("discrete forwards f^d_i:", [round(v, 6) for v in mc.fd[1:]])
print("knot forwards f_i     :", [round(v, 6) for v in mc.f])

# 1) node reproduction
maxerr = max(abs(mc.zero(t) - r) for t, r in zip(tenors, r_cont))
print("max |r(t_i) - r_i| =", maxerr)
# 2) integral constraint per interval via fine numeric integration
import itertools
for i in range(1, mc.n+1):
    a, b = mc.tau[i-1], mc.tau[i]
    N = 2000
    h = (b-a)/N
    s = sum(mc.forward(a + (k+0.5)*h) for k in range(N))*h
    assert abs(s/(b-a) - mc.fd[i]) < 1e-7, (i, s/(b-a), mc.fd[i])
print("interval-average check OK")
# 3) continuity of forward at knots and positivity on fine grid
grid = [k/1000 for k in range(1, 50001)]
fwds = [mc.forward(t) for t in grid]
print("min forward on grid:", min(fwds), " max:", max(fwds))
jumps = []
for i in range(1, mc.n):
    tk = mc.tau[i]
    jumps.append(abs(mc.forward(tk-1e-9) - mc.forward(tk+1e-9)))
print("max forward jump at knots:", max(jumps))
# 4) sectors used
sec = []
for i in range(1, mc.n+1):
    g0 = mc.f[i-1]-mc.fd[i]; g1 = mc.f[i]-mc.fd[i]
    if (g0 < 0 and -0.5*g0 <= g1 <= -2*g0) or (g0 > 0 and -0.5*g0 >= g1 >= -2*g0): s='i'
    elif (g0 < 0 and g1 > -2*g0) or (g0 > 0 and g1 < -2*g0): s='ii'
    elif (g0 > 0 and 0 > g1 > -0.5*g0) or (g0 < 0 and 0 < g1 < -0.5*g0): s='iii'
    else: s='iv'
    sec.append(s)
print("sectors per interval:", sec)
# 5) sample values
for t in [0.1, 0.4, 1.25, 3.5, 6, 8.5, 15, 30, 60]:
    print(f"t={t:5}: f={mc.forward(t):.6f}  r={mc.zero(t):.6f}  DF={math.exp(-mc.rt(t)):.6f}")

# ---------- cross-check vs QuantLib ----------
try:
    import QuantLib as ql
    x = ql.Array([0.0] + tenors)
    y = ql.Array([0.0] + mc.fd[1:])      # first y ignored by QuantLib; y_i = discrete fwd of [x_{i-1}, x_i]
    qi = ql.ConvexMonotoneInterpolation(x, y, 0.0, 1.0, True)  # quadraticity=0, monotonicity=1, forcePositive
    md = 0.0
    for t in [k/100 for k in range(1, 4999)]:
        md = max(md, abs(qi(t, True) - mc.forward(t)))
    print("QuantLib(q=0,m=1,fp=True) vs python: max |f diff| on (0,50) =", md)
    qi2 = ql.ConvexMonotoneInterpolation(x, y, 0.0, 1.0, False)
    mc2 = MonotoneConvex(tenors, r_cont, force_positive=False)
    md2 = max(abs(qi2(t, True) - mc2.forward(t)) for t in [k/100 for k in range(1, 4999)])
    print("QuantLib(fp=False) vs python(no collar): max |f diff| =", md2)
    # default QuantLib settings (0.3, 0.7) differ from paper
    qi3 = ql.ConvexMonotoneInterpolation(x, y)  # defaults quadraticity=0.3, monotonicity=0.7
    md3 = max(abs(qi3(t, True) - mc.forward(t)) for t in [k/100 for k in range(1, 4999)])
    print("QuantLib defaults(q=0.3,m=0.7) vs paper: max |f diff| =", md3)
except Exception as e:
    print("QuantLib check failed:", e)

# ---------- H&W 2006 'all cubic methods produce negative forwards' curve ----------
t2 = [0.1, 1, 4, 9, 20, 30]; r2 = [0.081, 0.07, 0.044, 0.07, 0.04, 0.03]
mcx = MonotoneConvex(t2, r2, force_positive=True)
print("H&W 2006 nasty curve: fd =", [round(v,5) for v in mcx.fd[1:]], " f =", [round(v,5) for v in mcx.f])
print("  min forward:", min(mcx.forward(k/100) for k in range(1, 3000)))
mcx0 = MonotoneConvex(t2, r2, force_positive=False)
print("  min forward without collar:", min(mcx0.forward(k/100) for k in range(1, 3000)))
