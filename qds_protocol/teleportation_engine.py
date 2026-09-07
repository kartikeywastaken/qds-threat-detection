"""Dynamic Bell measurement, extraction, and conditional Pauli correction."""
from quantum_core.randomness import simulator_seed
from collections import defaultdict
from typing import Callable
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import DensityMatrix, partial_trace, state_fidelity, Statevector
from quantum_core.channel_noise_model import logical_simulator as simulator
from quantum_core.pauli_operations import prepare, rotate_measurement
from qds_protocol.measurement_record import Distribution, MeasurementRecord

BASIS = ['id','rz','sx','x','cx','reset','measure','if_else']


def teleport_gates(qc: QuantumCircuit, source: int=0, alice: int=1, bob: int=2, c: int=0) -> None:
    """Teleport source using Bell resource; correct X before Z."""
    qc.h(alice); qc.cx(alice,bob)
    qc.cx(source,alice); qc.h(source)
    qc.measure(source,c); qc.measure(alice,c+1)
    with qc.if_test((qc.clbits[c+1],1)): qc.x(bob)
    with qc.if_test((qc.clbits[c],1)): qc.z(bob)


def fidelity(amplitudes: tuple[complex,complex]=(.6,.8), exposure: float=0., seed: int=7, shots: int=512) -> float:
    """Average corrected receiver-state fidelity, excluding final readout noise."""
    if not np.isclose(sum(abs(a)**2 for a in amplitudes),1): raise ValueError('State must be normalized')
    qc=QuantumCircuit(3,2); qc.initialize(amplitudes,0); teleport_gates(qc)
    compiled=transpile(qc,basis_gates=BASIS,optimization_level=0,seed_transpiler=seed)
    compiled.save_density_matrix()
    result=simulator(exposure).run(compiled,shots=shots,seed_simulator=simulator_seed(seed)).result()
    reduced=partial_trace(DensityMatrix(result.data(0)['density_matrix']),[0,1])
    return float(state_fidelity(reduced,Statevector(list(amplitudes))))


def transmit(distribution: Distribution, exposure: float=0., seed: int=1,
             circuit_hook: Callable | None=None, variant: Callable | None=None) -> list[MeasurementRecord]:
    """Group identical physical circuits, retain original chronological ordering."""
    groups=defaultdict(list); rng=np.random.default_rng(seed)
    for i,(bit,basis) in enumerate(zip(distribution.bits,distribution.bases)):
        key=(bit,basis,variant(rng) if variant else ())
        groups[key].append(i)
    records={}
    sim=simulator(exposure)
    for group_id,((bit,basis,choice),indices) in enumerate(sorted(groups.items())):
        qc=QuantumCircuit(4,4); prepare(qc,0,bit,basis)
        if circuit_hook: circuit_hook(qc,0,3,3,choice)
        teleport_gates(qc); rotate_measurement(qc,2,basis); qc.measure(2,2)
        compiled=transpile(qc,basis_gates=BASIS,optimization_level=0,seed_transpiler=seed)
        result=sim.run(compiled,shots=len(indices),memory=True,seed_simulator=simulator_seed(seed,group_id)).result()
        for index,memory in zip(indices,result.get_memory()):
            b=memory.replace(' ','')[::-1]
            records[index]=MeasurementRecord(index=index,expected=bit,observed=int(b[2]),basis=basis,bell_bits=(int(b[0]),int(b[1])))
    return [records[i] for i in range(len(distribution.bits))]
