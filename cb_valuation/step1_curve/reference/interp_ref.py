# -*- coding: utf-8 -*-
"""
interp_ref.py -- pure-Python (standard library only) reference implementations of the
1-D interpolation methods used in yield-curve construction.

    pchip(x, y)                 Fritsch-Carlson / Fritsch-Butland shape-preserving piecewise
                                cubic Hermite.  Slope rules are identical to
                                scipy.interpolate.PchipInterpolator (and MATLAB pchip / Moler
                                pchiptx.m); see pchip_slopes() for the exact formulas.
    linear(x, y)                piecewise linear
    loglinear_df(t, df)         linear in ln(DF)  ==  piecewise-constant continuous forward
                                (KICPA 사례 1130 variant (4): 연속복리 선도이자율 constant 보간)
    natural_cubic_spline(x, y)  C2 cubic spline with zero second derivative at both ends

Every constructor returns a callable f(xq) that accepts a float or any sequence and
returns a float or a list.  Each object also has .deriv(xq) (first derivative) and the
knots .x, .y.  Evaluation outside [x[0], x[-1]] uses the end polynomial (scipy default
extrapolate=True); pass extrapolate=False to raise ValueError instead.
"""
import math
from bisect import bisect_right

__all__ = ["pchip", "pchip_slopes", "linear", "loglinear_df", "natural_cubic_spline"]


# ----------------------------------------------------------------------------- helpers
def _sign(v):
    """-1 / 0 / +1, same as numpy.sign for finite floats."""
    return (v > 0) - (v < 0)


def _prep(x, y):
    x = [float(v) for v in x]
    y = [float(v) for v in y]
    if len(x) != len(y):
        raise ValueError("x and y must have the same length")
    if len(x) < 2:
        raise ValueError("need at least two knots")
    for i in range(len(x) - 1):
        if not x[i + 1] > x[i]:
            raise ValueError("x must be strictly increasing")
    return x, y


class _Interp1D:
    """Base: piecewise polynomial on segments [x[i], x[i+1]]."""

    def __init__(self, x, y, extrapolate=True):
        self.x, self.y = _prep(x, y)
        self.n = len(self.x)
        self.h = [self.x[i + 1] - self.x[i] for i in range(self.n - 1)]
        self.extrapolate = extrapolate

    def _segment(self, xq):
        if not self.extrapolate and (xq < self.x[0] or xq > self.x[-1]):
            raise ValueError("x=%r outside [%r, %r]" % (xq, self.x[0], self.x[-1]))
        i = bisect_right(self.x, xq) - 1
        if i < 0:
            i = 0
        elif i > self.n - 2:
            i = self.n - 2
        return i

    def _eval(self, xq):      # scalar -> scalar
        raise NotImplementedError

    def _deriv(self, xq):     # scalar -> scalar
        raise NotImplementedError

    def __call__(self, xq):
        try:
            return [self._eval(float(v)) for v in xq]
        except TypeError:
            return self._eval(float(xq))

    def deriv(self, xq):
        try:
            return [self._deriv(float(v)) for v in xq]
        except TypeError:
            return self._deriv(float(xq))


# ----------------------------------------------------------------------------- PCHIP
def _pchip_edge_case(h0, h1, m0, m1):
    """
    scipy PchipInterpolator._edge_case (== Moler, Numerical Computing with MATLAB,
    ch. 3.6, pchiptx.m).  h0, m0 = spacing / secant slope of the end segment,
    h1, m1 = of the segment next to it.
    """
    # one-sided three-point estimate for the derivative
    d = ((2.0 * h0 + h1) * m0 - h0 * m1) / (h0 + h1)
    # try to preserve shape
    if _sign(d) != _sign(m0):                                   # scipy: mask
        return 0.0
    if _sign(m0) != _sign(m1) and abs(d) > 3.0 * abs(m0):       # scipy: mask2 & ~mask
        return 3.0 * m0
    return d


def pchip_slopes(x, y):
    """
    Knot derivatives d_k of the Fritsch-Carlson / Fritsch-Butland PCHIP, exactly as in
    scipy.interpolate.PchipInterpolator._find_derivatives:

      h_k     = x[k+1] - x[k]                     (segment spacing)
      delta_k = (y[k+1] - y[k]) / h_k             (secant slope of segment k)

      interior k = 1..n-2:
        if sign(delta_{k-1}) != sign(delta_k) or delta_{k-1} == 0 or delta_k == 0:
            d_k = 0
        else:
            w1 = 2 h_k + h_{k-1}
            w2 = h_k + 2 h_{k-1}
            whmean = (w1/delta_{k-1} + w2/delta_k) / (w1 + w2)
            d_k = 1 / whmean          ( = (w1+w2) / (w1/delta_{k-1} + w2/delta_k) )
      endpoints (non-centered three-point formula with shape-preserving clamps):
        d_0     = edge(h_0,   h_1,   delta_0,   delta_1)
        d_{n-1} = edge(h_{n-2}, h_{n-3}, delta_{n-2}, delta_{n-3})
        edge(h0,h1,m0,m1):  d = ((2h0+h1) m0 - h0 m1)/(h0+h1)
                            if sign(d) != sign(m0): d = 0
                            elif sign(m0) != sign(m1) and |d| > 3|m0|: d = 3 m0
      n == 2: d_0 = d_1 = delta_0 (straight line)
    """
    x, y = _prep(x, y)
    n = len(x)
    h = [x[i + 1] - x[i] for i in range(n - 1)]
    delta = [(y[i + 1] - y[i]) / h[i] for i in range(n - 1)]
    d = [0.0] * n
    if n == 2:
        d[0] = d[1] = delta[0]
        return d
    for k in range(1, n - 1):
        mk_1, mk = delta[k - 1], delta[k]
        if _sign(mk_1) != _sign(mk) or mk == 0.0 or mk_1 == 0.0:
            d[k] = 0.0
        else:
            w1 = 2.0 * h[k] + h[k - 1]
            w2 = h[k] + 2.0 * h[k - 1]
            whmean = (w1 / mk_1 + w2 / mk) / (w1 + w2)
            d[k] = 1.0 / whmean
    d[0] = _pchip_edge_case(h[0], h[1], delta[0], delta[1])
    d[-1] = _pchip_edge_case(h[-1], h[-2], delta[-1], delta[-2])
    return d


class _Hermite(_Interp1D):
    """Piecewise cubic Hermite given knot values y and knot slopes d."""

    def __init__(self, x, y, d, extrapolate=True):
        _Interp1D.__init__(self, x, y, extrapolate)
        self.d = [float(v) for v in d]

    def _eval(self, xq):
        i = self._segment(xq)
        h = self.h[i]
        s = (xq - self.x[i]) / h
        s2 = s * s
        s3 = s2 * s
        h00 = 2.0 * s3 - 3.0 * s2 + 1.0
        h10 = s3 - 2.0 * s2 + s
        h01 = -2.0 * s3 + 3.0 * s2
        h11 = s3 - s2
        return (h00 * self.y[i] + h10 * h * self.d[i]
                + h01 * self.y[i + 1] + h11 * h * self.d[i + 1])

    def _deriv(self, xq):
        i = self._segment(xq)
        h = self.h[i]
        s = (xq - self.x[i]) / h
        s2 = s * s
        dh00 = 6.0 * s2 - 6.0 * s
        dh10 = 3.0 * s2 - 4.0 * s + 1.0
        dh01 = -6.0 * s2 + 6.0 * s
        dh11 = 3.0 * s2 - 2.0 * s
        return (dh00 * self.y[i] / h + dh10 * self.d[i]
                + dh01 * self.y[i + 1] / h + dh11 * self.d[i + 1])


def pchip(x, y, extrapolate=True):
    """Shape-preserving piecewise cubic Hermite interpolant (Fritsch-Carlson/Butland)."""
    x, y = _prep(x, y)
    return _Hermite(x, y, pchip_slopes(x, y), extrapolate)


# ----------------------------------------------------------------------------- linear
class _Linear(_Interp1D):
    def _eval(self, xq):
        i = self._segment(xq)
        return self.y[i] + (self.y[i + 1] - self.y[i]) * (xq - self.x[i]) / self.h[i]

    def _deriv(self, xq):
        i = self._segment(xq)
        return (self.y[i + 1] - self.y[i]) / self.h[i]


def linear(x, y, extrapolate=True):
    """Piecewise linear interpolant."""
    return _Linear(x, y, extrapolate)


# ----------------------------------------------------------------------------- log-linear DF
class _LogLinearDF(_Interp1D):
    """
    ln DF(t) piecewise linear in t.  Equivalent to a piecewise-constant continuous
    forward rate f_i = -(ln DF_{i+1} - ln DF_i)/(t_{i+1}-t_i) on every segment.
    __call__(t) returns DF(t); .spot(t) = -ln DF(t)/t (continuous); .forward(t) = f on
    the segment containing t.  If t[0] > 0 and anchor_zero, the knot (0, 1) is prepended.
    """

    def __init__(self, t, df, extrapolate=True, anchor_zero=True):
        t = [float(v) for v in t]
        df = [float(v) for v in df]
        if anchor_zero and len(t) and t[0] > 0.0:
            t = [0.0] + t
            df = [1.0] + df
        if any(v <= 0.0 for v in df):
            raise ValueError("discount factors must be positive")
        _Interp1D.__init__(self, t, [math.log(v) for v in df], extrapolate)
        self.df = df
        self.f = [-(self.y[i + 1] - self.y[i]) / self.h[i] for i in range(self.n - 1)]

    def _eval(self, xq):
        i = self._segment(xq)
        lndf = self.y[i] + (self.y[i + 1] - self.y[i]) * (xq - self.x[i]) / self.h[i]
        return math.exp(lndf)

    def _deriv(self, xq):                   # d DF / dt
        i = self._segment(xq)
        return -self.f[i] * self._eval(xq)

    def forward(self, xq):
        try:
            return [self.f[self._segment(float(v))] for v in xq]
        except TypeError:
            return self.f[self._segment(float(xq))]

    def spot(self, xq):
        def one(v):
            v = float(v)
            if v == 0.0:
                return self.f[0]
            return -math.log(self._eval(v)) / v
        try:
            return [one(v) for v in xq]
        except TypeError:
            return one(xq)


def loglinear_df(t, df, extrapolate=True, anchor_zero=True):
    """Log-linear discount-factor interpolation (= constant continuous forward per segment)."""
    return _LogLinearDF(t, df, extrapolate, anchor_zero)


# ----------------------------------------------------------------------------- natural cubic spline
class _NaturalCubic(_Interp1D):
    """
    C2 cubic spline with natural end conditions (S(x_0) and S(x_{n-1}) have zero second
    derivative).  Second derivatives M_i solve the tridiagonal system
        h_{i-1} M_{i-1} + 2 (h_{i-1}+h_i) M_i + h_i M_{i+1} = 6 (delta_i - delta_{i-1}),
    i = 1..n-2, M_0 = M_{n-1} = 0  (Thomas algorithm).
    """

    def __init__(self, x, y, extrapolate=True):
        _Interp1D.__init__(self, x, y, extrapolate)
        n, h, yv = self.n, self.h, self.y
        M = [0.0] * n
        if n > 2:
            delta = [(yv[i + 1] - yv[i]) / h[i] for i in range(n - 1)]
            m = n - 2                                    # unknowns M_1..M_{n-2}
            a = [h[i] for i in range(1, n - 2)]          # sub-diagonal   (len m-1)
            b = [2.0 * (h[i - 1] + h[i]) for i in range(1, n - 1)]   # diagonal (len m)
            c = [h[i] for i in range(1, n - 2)]          # super-diagonal (len m-1)
            r = [6.0 * (delta[i] - delta[i - 1]) for i in range(1, n - 1)]
            cp = [0.0] * m
            rp = [0.0] * m
            cp[0] = c[0] / b[0] if m > 1 else 0.0
            rp[0] = r[0] / b[0]
            for i in range(1, m):
                den = b[i] - a[i - 1] * cp[i - 1]
                cp[i] = c[i] / den if i < m - 1 else 0.0
                rp[i] = (r[i] - a[i - 1] * rp[i - 1]) / den
            sol = [0.0] * m
            sol[-1] = rp[-1]
            for i in range(m - 2, -1, -1):
                sol[i] = rp[i] - cp[i] * sol[i + 1]
            for i in range(m):
                M[i + 1] = sol[i]
        self.M = M

    def _eval(self, xq):
        i = self._segment(xq)
        h = self.h[i]
        a = self.x[i + 1] - xq
        b = xq - self.x[i]
        Mi, Mj = self.M[i], self.M[i + 1]
        return (Mi * a ** 3 / (6.0 * h) + Mj * b ** 3 / (6.0 * h)
                + (self.y[i] / h - Mi * h / 6.0) * a
                + (self.y[i + 1] / h - Mj * h / 6.0) * b)

    def _deriv(self, xq):
        i = self._segment(xq)
        h = self.h[i]
        a = self.x[i + 1] - xq
        b = xq - self.x[i]
        Mi, Mj = self.M[i], self.M[i + 1]
        return (-Mi * a * a / (2.0 * h) + Mj * b * b / (2.0 * h)
                - (self.y[i] / h - Mi * h / 6.0)
                + (self.y[i + 1] / h - Mj * h / 6.0))


def natural_cubic_spline(x, y, extrapolate=True):
    """Natural (zero end curvature) C2 cubic spline interpolant."""
    return _NaturalCubic(x, y, extrapolate)


if __name__ == "__main__":
    # MATLAB pchip documentation example: x = -3:3, y = [-1 -1 -1 0 1 1 1]
    xs = [-3, -2, -1, 0, 1, 2, 3]
    ys = [-1, -1, -1, 0, 1, 1, 1]
    p = pchip(xs, ys)
    s = natural_cubic_spline(xs, ys)
    print("pchip slopes :", p.d)
    print("pchip(-0.5)  :", p(-0.5), " (analytic -0.625)")
    print("spline(-1.5) :", s(-1.5), " (natural spline undershoots below -1)")
