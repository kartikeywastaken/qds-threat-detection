"""Ordered, auditable observable rules; attribution is a hypothesis, not proof."""
import json
from pathlib import Path

RULES=json.loads(Path(__file__).with_name('rules.json').read_text())


def attribute(report: dict) -> dict:
    """Return the first matching rule, with its evidence and rationale."""
    for rule in RULES:
        if any(flag not in report['flags'] for flag in rule['requires']): raise ValueError('Missing observable flag')
        if all(report['flags'][flag] for flag in rule['requires']):
            return {'attack_class':rule['attack_class'],'reason':rule['reason'],'matched_flags':rule['requires']}
    return {'attack_class':'none' if report['decision']=='ACCEPT' else 'undetermined',
            'reason':'No attribution rule matched the observed evidence.','matched_flags':[]}
