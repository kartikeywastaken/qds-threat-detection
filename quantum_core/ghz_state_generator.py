"""GHZ resources in the Qiskit DV core."""
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


def ghz_circuit(n: int = 3) -> QuantumCircuit:
    """Construct an n-qubit GHZ state with a fanout circuit."""
    if not isinstance(n,int) or not 2 <= n <= 10:
        raise ValueError('GHZ size must be an integer in [2,10]')
    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(1,n): qc.cx(0,i)
    return qc


def ghz_statevector(n: int = 3) -> Statevector:
    """Execute the GHZ circuit."""
    return Statevector.from_instruction(ghz_circuit(n))
