"""Simulated E91 shared-key experiment on Qiskit Aer.

Adapted from Yash-programs16/SIH_ quantum/e91/key_exchange.py (2026-09-08).
A Bell source distributes pairs; independent angles select key and CHSH rounds.
Half the sifted bits are publicly compared and discarded. Surviving outcomes
are hashed independently. Eve changes correlations, not the existence of bits.
SHA256 is a demonstration digest, not a composable privacy-amplification proof.
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit_aer import AerSimulator

__all__ = [
    "ABORT_QBER",
    "ALICE_ANGLES",
    "BOB_ANGLES",
    "CHSH_CLASSICAL_BOUND",
    "E91Result",
    "EveConfig",
    "run_e91",
]

#: Alice's three measurement angles, in radians, in the X-Z plane.
ALICE_ANGLES: tuple[float, ...] = (0.0, math.pi / 4, math.pi / 2)

#: Bob's three measurement angles. Two of them coincide with Alice's — those are
#: the rounds that can produce key.
BOB_ANGLES: tuple[float, ...] = (math.pi / 4, math.pi / 2, 3 * math.pi / 4)

#: (alice_index, bob_index) pairs whose angles are equal, so E = +1.
KEY_PAIRS: tuple[tuple[int, int], ...] = ((1, 0), (2, 1))

#: Alice/Bob index pairs entering the CHSH sum, with the sign each carries.
#: S = E(0, pi/4) - E(0, 3pi/4) + E(pi/2, pi/4) + E(pi/2, 3pi/4).
CHSH_TERMS: tuple[tuple[tuple[int, int], int], ...] = (
    ((0, 0), +1),
    ((0, 2), -1),
    ((2, 0), +1),
    ((2, 2), +1),
)

#: Angles Eve measures in when she intercepts.
EVE_ANGLES: tuple[float, ...] = (0.0, math.pi / 2)

#: QBER above which the key is discarded.
#:
#: Intercepting a fraction ``f`` of rounds costs Eve a QBER of ``0.25 * f``, so
#: this threshold catches any ``f`` above roughly 8%. It is set tight because an
#: undisturbed *simulated* channel has a QBER of exactly zero — there is no
#: hardware noise here to leave headroom for. Running against real hardware, or
#: against the noise models of Phase 5, means recalibrating this against a
#: measured honest baseline rather than keeping the value.
#:
#: No threshold catches everything: an attacker who intercepts only a few
#: percent of rounds stays underneath it, learns very little, and still leaves
#: Alice and Bob holding different keys. That case is not silently accepted —
#: the payment gate requires :attr:`E91Result.usable`, which fails on a key
#: mismatch whether or not the QBER test fired. Detection and consequence are
#: deliberately two separate checks.
ABORT_QBER = 0.02

#: Local hidden-variable bound. Honest |Phi+> gives 2*sqrt(2) ~ 2.828.
CHSH_CLASSICAL_BOUND = 2.0

#: Fraction of the raw key sacrificed to estimate the QBER.
SAMPLE_FRACTION = 0.5


@dataclass(frozen=True)
class EveConfig:
    """Intercept-and-resend eavesdropper on the Alice -> Bob leg.

    Args:
        fraction: Share of rounds Eve intercepts, in [0, 1]. 0 is an absent
            eavesdropper; 1 is full interception, which costs her a 25% QBER on
            the key rounds. Intermediate values model an attacker trying to stay
            under the abort threshold, and are why the threshold matters.
    """

    fraction: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.fraction <= 1.0:
            raise ValueError(f"fraction must be in [0, 1], got {self.fraction}")

    @property
    def active(self) -> bool:
        return self.fraction > 0.0


@dataclass(frozen=True)
class E91Result:
    """Everything both gateways observed, and what they concluded.

    The verdict is reported next to the evidence and the thresholds that
    produced it, so it can be re-derived and disputed.
    """

    rounds: int
    #: Rounds surviving sifting, before any were spent on error estimation.
    raw_key_bits: int
    #: Bits published and compared to estimate the QBER. Discarded afterwards.
    sampled_bits: int
    #: Disagreements among the sampled bits, over the sample size.
    qber: float
    chsh_s: float
    chsh_samples: int
    #: Final key each gateway derived locally, as hex. Equal iff the channel was
    #: undisturbed. Empty when the key was aborted.
    alice_key: str = field(repr=False)
    bob_key: str = field(repr=False)
    final_key_bits: int
    aborted: bool
    reason: str
    eve_fraction: float
    seed: int
    metadata: dict[str, Any] = field(default_factory=dict)

    _rounds: tuple[tuple[int, int, int, bool], ...] = field(default=(), repr=False, compare=False)

    @property
    def keys_match(self) -> bool:
        """Whether both gateways ended up with the same key.

        A False here is the *consequence* an attacker causes; the QBER and CHSH
        figures are how it is *detected*, before any key is used.
        """
        return bool(self.alice_key) and self.alice_key == self.bob_key

    @property
    def usable(self) -> bool:
        """Whether a payment may be signed with this key."""
        return not self.aborted and self.keys_match

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable summary, for the HTTP API and the dashboard."""
        return {
            "rounds": self.rounds,
            "raw_key_bits": self.raw_key_bits,
            "sampled_bits": self.sampled_bits,
            "qber": round(self.qber, 6),
            "qber_threshold": ABORT_QBER,
            "chsh_s": round(self.chsh_s, 6),
            "chsh_classical_bound": CHSH_CLASSICAL_BOUND,
            "chsh_samples": self.chsh_samples,
            "keys_match": self.keys_match,
            "final_key_bits": self.final_key_bits,
            "aborted": self.aborted,
            "usable": self.usable,
            "reason": self.reason,
            "eve_fraction": self.eve_fraction,
            "simulated": True,
            "intercepted_rounds": self.metadata.get("intercepted_rounds", 0),
            "surviving_bits": self.final_key_bits,
        }


def _round_circuit(alice_angle: float, bob_angle: float, eve_angle: float | None) -> QuantumCircuit:
    """Build one round: Bell pair, optional interception, both measurements.

    To measure along an axis at ``theta`` from Z in the X-Z plane, the qubit is
    rotated by ``Ry(-theta)`` and then measured in the computational basis.

    Eve's interception needs no explicit re-preparation step: measuring the
    qubit already collapses it to the state she observed, which is exactly what
    intercept-and-resend forwards to Bob. Rotating back by ``Ry(+theta_e)``
    returns that state to the lab frame before it continues down the channel.
    """
    qr = QuantumRegister(2, "q")
    # bit 0 = Alice's outcome, bit 1 = Bob's outcome, bit 2 = Eve's outcome.
    cr = ClassicalRegister(3, "c")
    qc = QuantumCircuit(qr, cr)

    qc.h(qr[0])
    qc.cx(qr[0], qr[1])

    if eve_angle is not None:
        qc.ry(-eve_angle, qr[1])
        qc.measure(qr[1], cr[2])
        qc.ry(eve_angle, qr[1])

    qc.ry(-alice_angle, qr[0])
    qc.ry(-bob_angle, qr[1])
    qc.measure(qr[0], cr[0])
    qc.measure(qr[1], cr[1])
    return qc


def _derive_key(bits: list[int]) -> str:
    """Hash a bit string into a 256-bit key.

    Privacy amplification proper would shorten the key against Eve's partial
    information; this is a demonstration-grade stand-in that makes the two
    gateways' keys either identical or visibly unrelated. A single flipped bit
    changes the whole digest, which is the point on screen.
    """
    if not bits:
        return ""
    packed = bytes(int("".join(map(str, bits[i : i + 8])).ljust(8, "0"), 2) for i in range(0, len(bits), 8))
    return hashlib.sha256(packed).hexdigest()


def run_e91(
    rounds: int = 1024,
    *,
    eve: EveConfig | float = 0.0,
    seed: int = 1,
) -> E91Result:
    """Run the full E91 exchange and return both gateways' evidence.

    Args:
        rounds: Bell pairs distributed. Roughly 2/9 survive sifting, and half of
            those are then spent estimating the QBER.
        eve: An :class:`EveConfig`, or a bare float taken as its ``fraction``.
        seed: Drives basis choices, sampling and the simulator. One value
            reproduces an entire run.

    Raises:
        ValueError: on a non-positive round count.
    """
    if isinstance(rounds, bool) or not isinstance(rounds, int) or not 1 <= rounds <= 65536:
        raise ValueError(f"rounds must be an integer between 1 and 65536, got {rounds}")
    if not isinstance(eve, EveConfig):
        eve = EveConfig(float(eve))

    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**31:
        raise ValueError("seed must be an integer in [0, 2**31)")
    rng = np.random.default_rng(seed)
    backend = AerSimulator(max_parallel_threads=1)

    alice_choice = rng.integers(0, len(ALICE_ANGLES), rounds)
    bob_choice = rng.integers(0, len(BOB_ANGLES), rounds)
    intercepted = rng.random(rounds) < eve.fraction
    eve_choice = rng.integers(0, len(EVE_ANGLES), rounds)

    # Rounds are independent and identically distributed, so rounds sharing a
    # configuration are simulated together as shots of one circuit and scattered
    # back into round order. This is exact, and far faster than one job per pair.
    cells: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for index in range(rounds):
        eve_key = int(eve_choice[index]) if intercepted[index] else -1
        cells[(int(alice_choice[index]), int(bob_choice[index]), eve_key)].append(index)

    alice_bits = np.zeros(rounds, dtype=int)
    bob_bits = np.zeros(rounds, dtype=int)

    for (a_idx, b_idx, e_idx), indices in sorted(cells.items()):
        circuit = _round_circuit(
            ALICE_ANGLES[a_idx],
            BOB_ANGLES[b_idx],
            EVE_ANGLES[e_idx] if e_idx >= 0 else None,
        )
        job = backend.run(
            circuit,
            shots=len(indices),
            memory=True,
            seed_simulator=int(rng.integers(0, 2**31 - 1)),
        )
        for index, shot in zip(indices, job.result().get_memory()):
            # Qiskit reports the register most-significant bit first.
            bits = shot.replace(" ", "")[::-1]
            alice_bits[index] = int(bits[0])
            bob_bits[index] = int(bits[1])

    # --- CHSH, from the mismatched-angle rounds ------------------------------
    chsh_s = 0.0
    chsh_samples = 0
    missing_chsh = False
    for (a_idx, b_idx), sign in CHSH_TERMS:
        mask = (alice_choice == a_idx) & (bob_choice == b_idx)
        count = int(mask.sum())
        if count == 0:
            missing_chsh = True
            continue
        # Outcomes are 0/1; map to +-1 so agreement is +1.
        # An empirical estimate, so it fluctuates: an honest run can land slightly
        # above the Tsirelson bound of 2*sqrt(2) on a finite sample. That is
        # sampling error, not a physics violation.
        correlation = float(np.mean(np.where(alice_bits[mask] == bob_bits[mask], 1.0, -1.0)))
        chsh_s += sign * correlation
        chsh_samples += count

    # --- Sifting -------------------------------------------------------------
    key_mask = np.zeros(rounds, dtype=bool)
    for a_idx, b_idx in KEY_PAIRS:
        key_mask |= (alice_choice == a_idx) & (bob_choice == b_idx)
    key_indices = np.flatnonzero(key_mask)
    raw_key_bits = int(key_indices.size)

    # --- Error estimation on a published, then discarded, subset -------------
    sample_size = int(raw_key_bits * SAMPLE_FRACTION)
    shuffled = rng.permutation(key_indices)
    sample_indices, remaining_indices = shuffled[:sample_size], shuffled[sample_size:]

    if sample_size:
        disagreements = int(np.count_nonzero(alice_bits[sample_indices] != bob_bits[sample_indices]))
        qber = disagreements / sample_size
    else:
        qber = 0.0

    # --- Decision, before any key is used ------------------------------------
    remaining_indices.sort()
    aborted = False
    reasons: list[str] = []
    if sample_size == 0:
        aborted = True
        reasons.append("insufficient sifted rounds to estimate an error rate")
    if qber > ABORT_QBER:
        aborted = True
        reasons.append(f"QBER {qber:.1%} exceeds the {ABORT_QBER:.0%} abort threshold")
    if missing_chsh:
        aborted = True
        reasons.append("insufficient rounds in one or more CHSH settings")
    if chsh_s <= CHSH_CLASSICAL_BOUND:
        aborted = True
        reasons.append(
            f"CHSH S = {chsh_s:.3f} does not exceed the classical bound "
            f"{CHSH_CLASSICAL_BOUND:.1f}; the measured Bell witness does not pass"
        )

    if aborted:
        alice_key = bob_key = ""
        final_key_bits = 0
    else:
        alice_key = _derive_key([int(b) for b in alice_bits[remaining_indices]])
        bob_key = _derive_key([int(b) for b in bob_bits[remaining_indices]])
        final_key_bits = int(remaining_indices.size)

    if not reasons:
        reasons.append("evidence compatible with an undisturbed channel")

    return E91Result(
        rounds=rounds,
        raw_key_bits=raw_key_bits,
        sampled_bits=sample_size,
        qber=qber,
        chsh_s=chsh_s,
        chsh_samples=chsh_samples,
        alice_key=alice_key,
        bob_key=bob_key,
        final_key_bits=final_key_bits,
        aborted=aborted,
        reason="; ".join(reasons),
        eve_fraction=eve.fraction,
        seed=seed,
        metadata={"intercepted_rounds": int(intercepted.sum())},
        _rounds=tuple((int(i), int(alice_bits[i]), int(bob_bits[i]), bool(i in sample_indices))
                      for i in range(rounds)),
    )
