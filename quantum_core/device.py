"""Willow topology selection and deterministic routing from Google's device metadata."""
from collections import deque
import cirq
import networkx as nx
from quantum_core.errors import CircuitValidationError, CircuitCompilationError


def get_qvm_device(processor: str = 'willow_pink'):
    """Load the bundled device specification locally; no Engine credentials."""
    from cirq_google.engine import create_device_from_processor_id
    return create_device_from_processor_id(processor)


def map_logical_qubits(circuit: cirq.AbstractCircuit, device) -> dict[cirq.Qid, cirq.Qid]:
    """Select the first connected BFS subset, with sorted deterministic tie breaks."""
    logical = sorted(circuit.all_qubits())
    graph = device.metadata.nx_graph
    for root in sorted(graph.nodes):
        queue = deque([root]); selected = []; seen = {root}
        while queue and len(selected) < len(logical):
            node = queue.popleft(); selected.append(node)
            for neighbor in sorted(graph.neighbors(node)):
                if neighbor not in seen:
                    seen.add(neighbor); queue.append(neighbor)
        if len(selected) == len(logical):
            return dict(zip(logical, selected))
    raise CircuitCompilationError('Virtual device has no sufficiently large connected subset')


def validate_device_circuit(circuit: cirq.AbstractCircuit, device) -> None:
    """Reject unsupported gates and nonlocal two-qubit operations."""
    try:
        device.validate_circuit(cirq.Circuit(circuit))
    except ValueError as exc:
        raise CircuitValidationError(f'Willow device validation failed: {exc}') from exc


def compile_for_google_device(circuit: cirq.AbstractCircuit, device) -> tuple[cirq.Circuit, dict]:
    """Decompose into the device gateset; route with SWAPs and restore the mapping."""
    if any(isinstance(op, cirq.ClassicallyControlledOperation) or isinstance(op.gate, cirq.ResetChannel)
           for op in circuit.all_operations()):
        raise CircuitValidationError('qvm_compatible=false: adaptive corrections/reset require an explicit deferred protocol builder')
    if not cirq.Circuit(circuit).are_all_measurements_terminal():
        raise CircuitValidationError('qvm_compatible=false: nonterminal measurements cannot be silently deferred')
    mapping = map_logical_qubits(circuit, device)
    target = device.metadata.compilation_target_gatesets[0]
    try:
        decomposed = cirq.optimize_for_target_gateset(cirq.Circuit(circuit), gateset=target, ignore_failures=False)
        graph = device.metadata.nx_graph.subgraph(mapping.values())
        routed = cirq.Circuit(); measurements = []
        for operation in decomposed.all_operations():
            if cirq.is_measurement(operation):
                measurements.append(operation.transform_qubits(mapping)); continue
            physical = operation.transform_qubits(mapping)
            if len(physical.qubits) <= 1:
                routed.append(physical); continue
            if len(physical.qubits) != 2:
                raise CircuitCompilationError('Google decomposition left an operation larger than two qubits')
            first, second = physical.qubits
            path = nx.shortest_path(graph, first, second)
            swaps = [cirq.SWAP(a, b) for a, b in zip(path[:-2], path[1:-1])]
            routed.append(swaps)
            routed.append(physical.with_qubits(path[-2], second))
            routed.append(reversed(swaps))
        routed.append(measurements)
        compiled = cirq.optimize_for_target_gateset(routed, gateset=target, ignore_failures=False)
        compiled = cirq.synchronize_terminal_measurements(compiled)
    except (ValueError, TypeError, nx.NetworkXException) as exc:
        raise CircuitCompilationError(f'Willow compilation failed: {exc}') from exc
    validate_device_circuit(compiled, device)
    return compiled, mapping
