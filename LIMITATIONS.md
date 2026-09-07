# Limitations and explicit deviations

1. **Not production QDS.** This implements a verifier-held, one-time BB84 token
   protocol with real teleportation and HMAC-bound messages. No missing 'earlier
   architecture discussion' was available. Transferability, repudiation security,
   recipient symmetrization, composable secrecy and public verification are not
   established. HMAC is classical message authentication; its key is not claimed
   to have been distilled securely by the simulated quantum distribution.
2. **C3 cannot honestly receive universal sign-off.** The Helstrom bound is proven
   only for independent equiprobable pure probes with stipulated overlap 1-2Q.
   Ordinary measured QBER alone cannot certify that model. The evaluation runs
   a separate real probe-discrimination experiment and records successes, bounds
   and confidence intervals. Coherent attacks, replay and authentication failure
   are outside that theorem. The detector reports a labeled hypothetical bound,
   never a universal security certificate. Finite empirical proportions can exceed
   their probability bounds by statistical variation. No parameter/seed is tuned
   to hide this; the final checklist marks C3 and consequent D1/D2 unsupported.
3. **Reduced collective/coherent attacks.** Two signals interact with two probes
   independently before a deferred Bell-basis joint measurement (collective), or
   through one shared probe with noncommuting interactions (coherent). There are
   four live qubits, with probe registers reused after readout for teleportation.
   This faithfully executes a joint attack block, not a claim to optimize every
   possible attack. Density matrices grow as 4^d; arbitrary large coherent attacks
   and optimal adversarial strategies are not simulated. SPRT iid guarantees do
   not extend automatically to correlated blocks.
4. **Calibration model.** FakeManilaV2 supplies IBM calibration dated 2024-05-27.
   `noise_model` preserves physical-qubit errors for Bell-density checks. Logical
   teleportation/probe/CHSH circuits use the convex mean of calibration channels
   per gate and mean readout channel, applied to every logical connection. This
   is a disclosed homogeneous calibration-derived simulation, not a prediction
   for routing on actual Manila hardware. Fractional exposure convexly mixes
   each calibrated channel with identity; integer exposure composes it. No flat
   invented error probability replaces the calibration data. Historical fake
   calibration is offline, reproducible, and not a live hardware calibration.
5. **CV scope.** Strawberry Fields actually prepares a two-mode squeezed state
   and applies a thermal-loss channel with its Gaussian backend. Exact means,
   covariance and photon numbers are emitted by the full command. CV is a
   diagnostic module; DV signatures are not represented as a CV security protocol.
   CV channel transmissivity and thermal occupancy are explicit study parameters,
   not values inferred from IBM DV calibration. No non-Gaussian CV attacks or
   finite-squeezing CV teleportation signature construction is claimed.
6. **CHSH.** Sampling settings are uniform and independent. Bell witness samples
   are separate diagnostic pairs, not the already consumed token qubits. The
   local simulator does not close locality or detection loopholes. With fixed
   honest-optimal observables, dephased Bell resources have S=sqrt(2), not exactly
   the classical upper bound 2. The single-round entropy lower bound is not an
   entropy-accumulation proof. Small sample sizes can yield zero certified entropy.
7. **Attribution is ambiguous outside the benchmark.** Rules classify observable
   symptoms, not uniquely identify an adversary. An unknown sender maps to
   impersonation, an invalid MAC for a recognized sender to channel manipulation,
   reused nonce to replay, and excess mismatch to candidate forgery. These clear
   benchmark cases do not prove that noisy channels and arbitrary forgery are
   distinguishable. Collective/coherent labels are not inferred from QBER alone.
8. **Evaluation resources and confidence.** A zero-strength scenario bypasses
   attack gates entirely. For classical scenarios any nonzero strength activates
   envelope substitution/replay; strength scales the quantum interception or
   resource dephasing, not the degree of MAC invalidity.
    Default grid is 6 mechanisms × 3
   strengths × 3 noise exposures × 5 seeds, plus 15 honest runs. Zero observed
   false positives is a valid finite result, not evidence of faking. ROC includes
   classical integrity signals that a QBER-only baseline lacks; both aggregate
   and operating rates are reported. SPRT prefix length excludes independently
   measured CHSH pairs and calibration. The offline simulator generates full
   batches, so prefix savings are statistical sample requirements, not measured
   wall-time or total-qubit savings. No matched-sensitivity total-resource claim.
9. **Local service only.** FastAPI binds localhost; sessions and consumed nonces
   live in process memory. Restarting reinitializes them. This is not a hardened
   multiworker/authenticated/TLS deployment. Log appends use OS locks, fsync and a
   hash chain, which detects internal modification but cannot stop an owner from
   truncating or rewriting the entire file. No external trusted chain anchor.
   Failures propagate visibly. Cross-process persistent nonce atomicity and
   transactional log/session recovery are not implemented.
10. **Deterministic research seeds.** NumPy, transpiler and Aer seeds are explicit;
    reference calibration uses a disjoint fixed seed. Grouped equal circuits use
    independent, reproducible shot outcomes assigned back to chronological input
    positions. Simulator streams hash the pair (root seed, circuit group) to avoid
    adjacent-seed correlations and cross-run stream reuse. Keys are seeded for reproducible research and must never be used
    for real cryptographic secrets. Results are reproducible within the pinned
    software/runtime and platform; cross-version bitwise guarantees are not made.
11. **Dependency compatibility.** Python 3.12, NumPy 1.26, SciPy 1.13 and
    setuptools<81 are required by Strawberry Fields 0.23's legacy imports. The
    lock file captures the tested environment. Library deprecation warnings are
    visible and not swallowed. No hardware backend or quantum cloud account is
    required. The live dashboard is a local Matplotlib window watching the log;
    it updates per completed verification event and displays the complete SPRT
    trace. It does not stream intermediate quantum shots while Aer is running.
