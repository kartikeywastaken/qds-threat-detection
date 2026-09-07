"""Preparation and inverse measurement rotations for Pauli eigenstates."""
from qiskit import QuantumCircuit


def prepare(qc: QuantumCircuit, qubit: int, bit: int, basis: str) -> None:
    """Prepare |bit> in X, Y or Z basis from |0>."""
    if bit not in (0,1) or basis not in ('X','Y','Z'):
        raise ValueError('Invalid bit or Pauli basis')
    if bit: qc.x(qubit)
    if basis in ('X','Y'): qc.h(qubit)
    if basis == 'Y': qc.s(qubit)


def rotate_measurement(qc: QuantumCircuit, qubit: int, basis: str) -> None:
    """Rotate a Pauli measurement into the computational basis."""
    if basis not in ('X','Y','Z'): raise ValueError('Unknown Pauli basis')
    if basis == 'Y': qc.sdg(qubit)
    if basis in ('X','Y'): qc.h(qubit)
