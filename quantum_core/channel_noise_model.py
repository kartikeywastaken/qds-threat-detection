"""Offline IBM calibration-derived Aer channels, scaled by exposure."""
from functools import lru_cache
import math
import numpy as np
from qiskit.quantum_info import SuperOp, Operator
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, QuantumError, ReadoutError
from qiskit_ibm_runtime.fake_provider import FakeManilaV2


@lru_cache(maxsize=16)
def noise_model(exposure: float = 1.) -> NoiseModel:
    """Interpolate calibration channels with identity; compose for exposure >1."""
    if not math.isfinite(exposure) or not 0 <= exposure <= 4:
        raise ValueError('Noise exposure must be finite in [0,4]')
    base = NoiseModel.from_backend(FakeManilaV2())
    if exposure == 1:
        return base
    result = NoiseModel(basis_gates=base.basis_gates)
    if exposure == 0:
        return result
    for item in base.to_dict()['errors']:
        for qubits in item.get('gate_qubits', []):
            if item['type'] == 'qerror':
                channel = SuperOp(QuantumError.from_dict(item))
                identity = SuperOp(Operator(np.eye(2**len(qubits)))).data
                whole = np.linalg.matrix_power(channel.data, int(exposure))
                frac = exposure-int(exposure)
                scaled = whole @ ((1-frac)*identity + frac*channel.data)
                result.add_quantum_error(QuantumError(SuperOp(scaled)), item['operations'], qubits)
            elif item['type'] == 'roerror':
                p = np.asarray(item['probabilities'])
                scaled = np.linalg.matrix_power(p, int(exposure)) @ ((1-exposure%1)*np.eye(2) + (exposure%1)*p)
                result.add_readout_error(ReadoutError(scaled), qubits)
            else:
                raise ValueError(f'Unsupported calibration error: {item["type"]}')
    return result


def simulator(exposure: float = 0.) -> AerSimulator:
    """One-thread density-matrix simulator; seeds are supplied per execution."""
    return AerSimulator(method='density_matrix', noise_model=noise_model(exposure), max_parallel_threads=1)


def calibration_metadata() -> dict:
    """Return auditable source and physical qubit calibration values."""
    backend = FakeManilaV2()
    props = backend.properties()
    return {'backend': backend.name, 'last_update': str(props.last_update_date),
            'qubits': [{'t1':props.t1(i), 't2':props.t2(i), 'readout_error':props.readout_error(i)} for i in range(5)]}


@lru_cache(maxsize=16)
def homogeneous_model(exposure: float=1.) -> NoiseModel:
    """Mean of calibration CPTP channels per gate; covers logical probe connections.

    This is an all-to-all simulator, not a hardware-routing prediction. Mixing
    calibrated channels is CPTP and retains T1/T2/gate/readout contributions.
    """
    from collections import defaultdict
    base=noise_model(exposure)
    result=NoiseModel(basis_gates=base.basis_gates)
    gates=defaultdict(list); readout=[]
    for item in base.to_dict()['errors']:
        if item['type']=='qerror':
            for gate in item['operations']: gates[gate].append(SuperOp(QuantumError.from_dict(item)).data)
        elif item['type']=='roerror': readout.append(item['probabilities'])
    for gate,channels in gates.items():
        result.add_all_qubit_quantum_error(QuantumError(SuperOp(np.mean(channels,axis=0))),gate)
    if readout: result.add_all_qubit_readout_error(ReadoutError(np.mean(readout,axis=0)))
    return result


def logical_simulator(exposure: float=0.) -> AerSimulator:
    """Calibrated homogeneous noise on every logical connection, including probes."""
    return AerSimulator(method='density_matrix',noise_model=homogeneous_model(exposure),max_parallel_threads=1)
