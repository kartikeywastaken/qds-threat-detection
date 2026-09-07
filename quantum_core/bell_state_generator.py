"""Bell states and physical density-matrix execution."""
from quantum_core.randomness import simulator_seed
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector, DensityMatrix
from quantum_core.channel_noise_model import simulator


def bell_circuit() -> QuantumCircuit:
    """Prepare |Phi+> with H and CX."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0,1)
    return qc


def bell_statevector() -> Statevector:
    """Execute noiseless gates using Qiskit's exact statevector engine."""
    return Statevector.from_instruction(bell_circuit())


def bell_density(exposure: float = 1., seed: int = 1) -> DensityMatrix:
    """Execute calibrated channel on physical qubits 0 and 1."""
    qc = bell_circuit()
    sim = simulator(exposure)
    compiled = transpile(qc, basis_gates=['id','rz','sx','x','cx'], optimization_level=0, seed_transpiler=seed)
    compiled.save_density_matrix()
    return DensityMatrix(sim.run(compiled, shots=1, seed_simulator=simulator_seed(seed)).result().data(0)['density_matrix'])


def sample_chsh(n: int=4096, exposure: float=.1, seed: int=1, dephase_rate: float=0.) -> list[tuple[int,int,int,int]]:
    """Generate uniformly random settings and actual pair outcomes through Aer.

    Dephasing is an entanglement-breaking Z measurement, never an assigned S.
    Acquisition belongs to the quantum source; the correlator receives rows only.
    """
    import numpy as np
    from collections import defaultdict
    from quantum_core.channel_noise_model import logical_simulator
    if not isinstance(n,int) or n<16 or not 0 <= dephase_rate <= 1:
        raise ValueError('Require n>=16 and dephase rate in [0,1]')
    rng=np.random.default_rng(seed); groups=defaultdict(list)
    for i in range(n): groups[(int(rng.integers(2)),int(rng.integers(2)),int(rng.random()<dephase_rate))].append(i)
    rows={};sim=logical_simulator(exposure)
    for k,((a,b,replace),indices) in enumerate(sorted(groups.items())):
        qc=QuantumCircuit(2,3);qc.h(0);qc.cx(0,1)
        if replace: qc.measure(0,2)
        qc.ry(-a*np.pi/2,0);qc.ry(-((-1)**b)*np.pi/4,1)
        qc.measure(0,0);qc.measure(1,1)
        compiled=transpile(qc,basis_gates=['id','rz','sx','x','cx','measure'],optimization_level=0,seed_transpiler=seed)
        memories=sim.run(compiled,shots=len(indices),memory=True,seed_simulator=simulator_seed(seed,k)).result().get_memory()
        for i,m in zip(indices,memories): rows[i]=(a,b,int(m[-1]),int(m[-2]))
    return [rows[i] for i in range(n)]
