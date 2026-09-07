from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from quantum_core.pauli_operations import prepare, rotate_measurement

def test_pauli():
    for basis in ('X','Y','Z'):
        for bit in (0,1):
            qc=QuantumCircuit(1); prepare(qc,0,bit,basis); rotate_measurement(qc,0,basis)
            assert Statevector.from_instruction(qc).probabilities()[bit]>.999999
