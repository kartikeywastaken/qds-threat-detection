# Security model and derivations

This is a teleportation-assisted, verifier-held BB84 token/signature research
prototype. It is not a transferable, publicly verifiable, unconditionally secure
QDS construction. The earlier architecture discussion referenced in the supplied
prompt was not supplied. The interfaces and threat model here are explicit choices.

## 1. Restricted independent-probe bound
Let a uniformly random secret bit leave two equiprobable **pure**, independent
probe states with overlap c=1-2Q, 0<=Q<=1/2. Helstrom's binary discrimination theorem
gives p_guess=(1+sqrt(1-c²))/2=1/2+sqrt(Q(1-Q)); h=-log2(p_guess).
For n independent bits the optimal entire-string guessing probability is
p_guess^n=2^(-nh). Allowing t errors admits sum(k=0..t) binom(n,k) strings;
a union bound gives min(1, volume*2^(-nh)+epsilon). Epsilon represents a separately
justified model/parameter failure budget; it is not a security proof by itself.
Q in this formula is a stipulated probe disturbance parameter, **not an arbitrary
observed QBER substituted as a theorem**. This bound is not valid for arbitrary
coherent, replay, identity, or calibration attacks. Those receive no certificate.
Reference: C. W. Helstrom, Quantum Detection and Estimation Theory (1976).

## 2. CHSH witness and entropy
For settings a,b in {0,1}, C_ab=mean((-1)^(x xor y));
S=abs(C00+C01+C10-C11). Independent uniform settings are drawn before
executing measurement circuits. Hoeffding and a union bound give
S_lower=max(0,S-sum_ab sqrt(2 log(8/delta)/N_ab)).
For a valid quantum realization p_guess(A|E)<=
(1+sqrt(2-S_lower²/4))/2; h>=1-log2(1+sqrt(2-S_lower²/4)).
Finite experimental S can exceed 2sqrt(2); only the confidence lower bound is
capped at that value for evaluation. We do not multiply this single-round
witness into a general coherent-attack security claim.
Reference: Pironio et al., Random numbers certified by Bell's theorem,
Nature 464, 1021–1024 (2010), https://doi.org/10.1038/nature09008 .

## 3. Sequential decision
For mismatch X_i, simple iid hypotheses H0: Bernoulli(p0), H1: Bernoulli(p1),
0<p0<p1<1. L_n=sum[X_i log(p1/p0)+(1-X_i)log((1-p1)/(1-p0))].
Wald's nominal boundaries are A=log((1-beta)/alpha), B=log(beta/(1-alpha)).
We use the conservative martingale boundaries A=log(1/alpha), B=log(beta),
which guarantee error bounds for the stated simple hypotheses even with overshoot.
L>=A rejects, L<=B accepts; at budget exhaustion it remains INCONCLUSIVE.
Calibration, mixtures, dependence, and combined integrity rules fall outside the
simple-hypothesis guarantee. Their rates must be measured, not assumed.
Reference: Wald, Sequential Analysis (1947).

## 4. Distribution and empirical validation
KL(P||R)=sum P_i log(P_i/R_i), with explicitly disclosed Jeffreys pseudocounts.
ROC uses held-out labels in evaluation only, thresholds on computed observables.
An empirical proportion is random and can exceed its true probability or a bound.
Thus 'never exceeds in every finite sweep' is not a general theorem. We provide
exact-binomial intervals and restrict bound validation to its stated experiment.
A null observation does not prove negligible adversarial success probability.
