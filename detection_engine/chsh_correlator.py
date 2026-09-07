"""CHSH correlations consume measurements only, independent of source configuration."""
import math
import numpy as np


def correlate(rows: list[tuple[int,int,int,int]], delta: float=.01) -> dict:
    """Compute signed correlations, |S| and simultaneous Hoeffding interval (§2)."""
    if not rows or not 0<delta<1: raise ValueError('Invalid CHSH sample or confidence')
    groups={(a,b):[] for a in (0,1) for b in (0,1)}
    for row in rows:
        if len(row)!=4 or any(x not in (0,1) for x in row): raise ValueError('CHSH row must contain four bits')
        a,b,x,y=row;groups[a,b].append(1 if x==y else -1)
    if any(not x for x in groups.values()): raise ValueError('Every CHSH setting requires observations')
    correlations={f'{a}{b}':float(np.mean(values)) for (a,b),values in groups.items()}
    s=abs(correlations['00']+correlations['01']+correlations['10']-correlations['11'])
    radius=sum(math.sqrt(2*math.log(8/delta)/len(v)) for v in groups.values())
    return {'s':s,'lower':min(2*math.sqrt(2),max(0.,s-radius)),'upper':min(4.,s+radius),
            'correlations':correlations,'counts':{f'{a}{b}':len(v) for (a,b),v in groups.items()},'delta':delta}
