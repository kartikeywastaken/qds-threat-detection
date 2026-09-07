"""Public errors for local quantum execution; never imply a fallback."""


class QuantumBackendError(RuntimeError):
    """Quantum execution could not complete."""
    code = 'quantum_backend_error'


class QVMUnavailableError(QuantumBackendError):
    """The requested local Google QVM is unavailable."""
    code = 'qvm_unavailable'


class CircuitValidationError(QuantumBackendError):
    """Circuit violates the selected execution contract."""
    code = 'circuit_validation_error'


class CircuitCompilationError(QuantumBackendError):
    """Circuit could not be faithfully compiled."""
    code = 'circuit_compilation_error'


class BaselineMissingError(QuantumBackendError):
    """No matching measured baseline is available."""
    code = 'baseline_missing'


class UnknownQuantumBackend(QuantumBackendError):
    """An unknown or reserved backend was requested."""
    code = 'unknown_quantum_backend'
