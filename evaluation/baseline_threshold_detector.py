"""Independent fixed-sample binomial threshold baseline; no SPRT imports."""
from scipy.stats import binom


def design(p0: float, p1: float, alpha: float=.01, beta: float=.01, max_n: int=10000) -> dict:
    """Find the smallest N with an integer rejection cutoff meeting both errors."""
    if not 0<p0<p1<1 or not 0<alpha<.5 or not 0<beta<.5: raise ValueError('Invalid design probabilities')
    for n in range(1,max_n+1):
        cutoff=int(binom.isf(alpha,n,p0))+1
        fpr=float(binom.sf(cutoff-1,n,p0));fnr=float(binom.cdf(cutoff-1,n,p1))
        if fpr<=alpha and fnr<=beta:
            return {'n':n,'cutoff':cutoff,'fpr_under_h0':fpr,'fnr_under_h1':fnr}
    raise ValueError('No fixed-sample design within max_n')


def detect(mismatches: list[int], n: int, cutoff: int) -> dict:
    """Count a fixed prefix without adaptive likelihood computations."""
    if n<1 or not 0<=cutoff<=n or any(x not in (0,1) for x in mismatches): raise ValueError('Invalid baseline input')
    if len(mismatches)<n: return {'decision':'INCONCLUSIVE','rounds':len(mismatches),'score':sum(mismatches)/max(1,len(mismatches))}
    errors=sum(mismatches[:n])
    return {'decision':'REJECT' if errors>=cutoff else 'ACCEPT','rounds':n,'score':errors/n}
