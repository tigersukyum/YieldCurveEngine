import math
# KICPA bootstrapped KTB zero rates (annual comp.)
u=[0.25,0.5,0.75,1,1.5,2,2.5,3,4,5,7,10,20,50]
z=[0.032898,0.03312,0.033424,0.033786,0.034095,0.033936,0.03341,0.032936,0.033051,0.032805,0.033734,0.033452,0.034003,0.033793]
m=[(1+r)**(-t) for r,t in zip(z,u)]
UFR_annual=0.048; w=math.log(1+UFR_annual); a=0.1
def H(s,t): return a*min(s,t)-math.exp(-a*max(s,t))*math.sinh(a*min(s,t))
def W(s,t): return math.exp(-w*(s+t))*H(s,t)
N=len(u)
# solve W zeta = m - mu  (Gaussian elimination, no numpy)
A=[[W(u[i],u[j]) for j in range(N)] for i in range(N)]
b=[m[i]-math.exp(-w*u[i]) for i in range(N)]
for c in range(N):
    p=max(range(c,N),key=lambda r:abs(A[r][c])); A[c],A[p]=A[p],A[c]; b[c],b[p]=b[p],b[c]
    for r in range(c+1,N):
        f=A[r][c]/A[c][c]
        for k in range(c,N): A[r][k]-=f*A[c][k]
        b[r]-=f*b[c]
zeta=[0]*N
for r in range(N-1,-1,-1):
    zeta[r]=(b[r]-sum(A[r][k]*zeta[k] for k in range(r+1,N)))/A[r][r]
def P(t): return math.exp(-w*t)+sum(zeta[j]*W(t,u[j]) for j in range(N))
def zero(t): return P(t)**(-1/t)-1
def fwd(t,h=1e-4): return -(math.log(P(t+h))-math.log(P(t-h)))/(2*h)
print("node reproduction max err:",max(abs(P(t)-mm) for t,mm in zip(u,m)))
for t in [0.1,1,3,4.5,6,8.5,10,12,15,20,30,40,50,60,90,100]:
    print(f"t={t:5.1f} P={P(t):.6f} zero_annual={zero(t)*100:.4f}% fwd_cont={fwd(t)*100:.4f}%")
print("omega=",w)
