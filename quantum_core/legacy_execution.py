"""Retained Qiskit execution service, separated from protocol/attack builders."""
from qiskit import transpile
from quantum_core.channel_noise_model import logical_simulator
from quantum_core.randomness import simulator_seed

BASIS = ['id', 'rz', 'sx', 'x', 'cx', 'reset', 'measure', 'if_else']


def run_legacy(circuit, repetitions: int, exposure: float, seed: int, stream: int = 0):
    """Execute the original calibrated circuit and preserve Aer memory ordering."""
    compiled = transpile(circuit, basis_gates=BASIS, optimization_level=0, seed_transpiler=seed)
    return logical_simulator(exposure).run(compiled, shots=repetitions, memory=True,
                                           seed_simulator=simulator_seed(seed, stream)).result()
