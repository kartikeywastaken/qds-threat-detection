import pytest
from attack_simulation.attack_strategy_base import AttackStrategyBase

def test_base_validation():
    with pytest.raises(ValueError): AttackStrategyBase(1.1)
