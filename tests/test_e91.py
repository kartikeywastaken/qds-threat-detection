import math
import statistics
import pytest
from e91.key_exchange import ABORT_QBER, EveConfig, run_e91


def test_honest_reproducibility_and_redaction():
    a = run_e91(seed=7)
    b = run_e91(seed=7)
    assert a.qber == 0 and a.keys_match and a.usable
    assert abs(a.chsh_s - 2 * math.sqrt(2)) < .25
    assert (a.alice_key, a.qber, a.chsh_s) == (b.alice_key, b.qber, b.chsh_s)
    assert run_e91(seed=8).alice_key != a.alice_key
    assert a.alice_key not in str(a.to_dict()) and a.alice_key not in repr(a)
    assert a.to_dict()['simulated'] is True


@pytest.mark.parametrize('fraction', [.25, .5, 1.])
def test_interception_statistics(fraction):
    runs = [run_e91(rounds=4096, eve=fraction, seed=seed) for seed in range(8)]
    tolerance = .03 if fraction == 1 else .04
    assert abs(statistics.mean(r.qber for r in runs) - .25 * fraction) < tolerance
    if fraction == 1:
        assert all(r.chsh_s <= 2 and r.aborted and not r.alice_key and not r.bob_key for r in runs)


def test_light_attack_finite_sample():
    # Mean at 10% interception is 2.5%, ABOVE 2%. A selected finite sample
    # can pass the threshold while retained bits disagree. Never widen it.
    result = run_e91(eve=.1, seed=7)
    assert result.qber < ABORT_QBER and not result.aborted
    assert not result.keys_match and not result.usable


@pytest.mark.parametrize('fraction', [-.1, 1.5, float('nan'), float('inf')])
def test_invalid_fraction(fraction):
    with pytest.raises(ValueError):
        EveConfig(fraction)


@pytest.mark.parametrize('rounds', [0, -1, 1.5, True, 65537])
def test_invalid_rounds(rounds):
    with pytest.raises(ValueError):
        run_e91(rounds)


def test_insufficient_rounds_abort():
    result = run_e91(1)
    assert result.aborted and result.reason and not result.alice_key
