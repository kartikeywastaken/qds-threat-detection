"""Evaluation-only scenario construction; labels never enter detection inputs."""
from dataclasses import dataclass
from attack_simulation.attack_strategy_base import AttackStrategyBase
from attack_simulation.individual_attack import IndividualAttackStrategy
from attack_simulation.collective_attack import CollectiveAttackStrategy
from attack_simulation.coherent_attack import CoherentAttackStrategy
from attack_simulation.impersonation_injector import ImpersonationInjector
from attack_simulation.channel_manipulation_injector import ChannelManipulationInjector
from attack_simulation.replay_injector import ReplayInjector
from qds_protocol.key_distribution import distribute
from qds_protocol.signing_engine import sign
from qds_protocol.verification_engine import VerificationEngine, IntegrityEvidence
from qds_protocol.measurement_record import SignaturePayload, MeasurementRecord

STRATEGIES={'honest':AttackStrategyBase,'individual':IndividualAttackStrategy,'forgery':IndividualAttackStrategy,
            'collective':CollectiveAttackStrategy,'coherent':CoherentAttackStrategy,
            'impersonation':ImpersonationInjector,'channel_manipulation':ChannelManipulationInjector,'replay':AttackStrategyBase}


@dataclass
class Scenario:
    """Private harness result; observable evidence extracted before detection."""
    payload: SignaturePayload
    records: list[MeasurementRecord]
    integrity: IntegrityEvidence
    verifier: VerificationEngine


def run_scenario(kind: str='honest', strength: float=0., exposure: float=.25, seed: int=1, n: int=512) -> Scenario:
    """Distribute, sign, inject physical/classical attack, then verify."""
    if kind not in STRATEGIES: raise ValueError('Unknown attack strategy')
    strategy=STRATEGIES[kind](strength)
    if strength==0: strategy=AttackStrategyBase(0.)
    d=distribute(n,seed)
    payload,_=sign(d,'Authorize quantum channel session',0,seed+100)
    records=strategy.transmit(d,exposure,seed+200)
    if isinstance(strategy,(ImpersonationInjector,ChannelManipulationInjector)): payload=strategy.envelope(payload)
    verifier=VerificationEngine();verifier.register(d,records)
    if kind=='replay' and strength>0:
        capture=ReplayInjector();capture.capture(payload);verifier.verify(payload);payload=capture.inject()
    integrity,records=verifier.verify(payload)
    return Scenario(payload,records,integrity,verifier)
