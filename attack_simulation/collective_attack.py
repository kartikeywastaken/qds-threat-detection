"""Independent signal/probe interactions followed by deferred joint measurement."""
from quantum_core.randomness import simulator_seed
from collections import defaultdict
import numpy as np
from qiskit import QuantumCircuit, transpile
from attack_simulation.attack_strategy_base import AttackStrategyBase
from quantum_core.pauli_operations import prepare, rotate_measurement
from quantum_core.channel_noise_model import logical_simulator
from qds_protocol.teleportation_engine import teleport_gates, BASIS
from qds_protocol.measurement_record import Distribution, MeasurementRecord


class CollectiveAttackStrategy(AttackStrategyBase):
    """Two independent probes, one per signal, jointly measured in Bell basis."""
    def interact(self, qc: QuantumCircuit) -> None:
        """Independent controlled rotations produce physical information/disturbance."""
        qc.cry(np.pi*self.strength,0,2); qc.cry(np.pi*self.strength,1,3)

    def transmit(self, distribution: Distribution, exposure: float, seed: int) -> list[MeasurementRecord]:
        """Two-signal blocks; deferred probes measured before reused teleport registers."""
        if len(distribution.bits)%2: raise ValueError('Block attacks require an even token count')
        groups=defaultdict(list)
        for i in range(0,len(distribution.bits),2):
            groups[(distribution.bits[i:i+2],distribution.bases[i:i+2])].append(i)
        result_records={}; self.probe_outcomes=[]
        sim=logical_simulator(exposure)
        for group_id,((bits,bases),indices) in enumerate(sorted(groups.items())):
            qc=QuantumCircuit(4,8)
            for j in range(2): prepare(qc,j,bits[j],bases[j])
            self.interact(qc)
            qc.cx(2,3); qc.h(2); qc.measure(2,6); qc.measure(3,7)
            for j in range(2):
                qc.reset(2);qc.reset(3)
                teleport_gates(qc,j,2,3,2+2*j)
                rotate_measurement(qc,3,bases[j]); qc.measure(3,j)
            compiled=transpile(qc,basis_gates=BASIS,optimization_level=0,seed_transpiler=seed)
            memories=sim.run(compiled,shots=len(indices),memory=True,seed_simulator=simulator_seed(seed,group_id)).result().get_memory()
            for index,memory in zip(indices,memories):
                b=list(map(int,memory.replace(' ','')[::-1])); self.probe_outcomes.append(b[6:8])
                for j in range(2):
                    result_records[index+j]=MeasurementRecord(index=index+j,expected=bits[j],observed=b[j],basis=bases[j],bell_bits=(b[2+2*j],b[3+2*j]))
        return [result_records[i] for i in range(len(distribution.bits))]
