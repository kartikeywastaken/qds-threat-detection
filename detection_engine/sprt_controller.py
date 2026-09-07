"""Recursive sequential probability ratio test; security model §3."""
import math
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class SPRTController:
    """Exact Bernoulli log-likelihood updates and conservative stopping bounds."""
    p0: float
    p1: float
    alpha: float=.01
    beta: float=.01
    llr: float=field(default=0.,init=False)
    trace: list[float]=field(default_factory=list,init=False)
    decision: Literal['ACCEPT','REJECT','INCONCLUSIVE']=field(default='INCONCLUSIVE',init=False)

    def __post_init__(self) -> None:
        if not all(math.isfinite(x) for x in (self.p0,self.p1,self.alpha,self.beta)) or not 0<self.p0<self.p1<1 or not 0<self.alpha<.5 or not 0<self.beta<.5:
            raise ValueError('Invalid SPRT hypotheses or error budgets')

    @property
    def upper(self) -> float:
        """Ville boundary guarantees H0 rejection probability <= alpha."""
        return math.log(1/self.alpha)

    @property
    def lower(self) -> float:
        """Reverse likelihood martingale controls H1 acceptance probability."""
        return math.log(self.beta)

    def update(self, mismatch: int) -> str:
        """Absorbing stop: later evidence cannot change a concluded test."""
        if mismatch not in (0,1): raise ValueError('Mismatch must be 0 or 1')
        if self.decision!='INCONCLUSIVE': return self.decision
        self.llr+=math.log(self.p1/self.p0) if mismatch else math.log((1-self.p1)/(1-self.p0))
        self.trace.append(self.llr)
        if self.llr>=self.upper: self.decision='REJECT'
        elif self.llr<=self.lower: self.decision='ACCEPT'
        return self.decision
