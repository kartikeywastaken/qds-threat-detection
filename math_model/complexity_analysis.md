# Complexity
For d qubits a statevector needs O(2^d) memory and local gates O(2^d) time;
a density matrix needs O(4^d). Coherent probe blocks here contain two signal
qubits and one probe; teleportation with an individual probe uses four qubits.
For N signature rounds, simulation and sequential detection are O(N) at fixed
block size, with O(N) record storage. KL on K categories is O(K); CHSH is O(N).
An evaluation with A attacks, G strengths, L noise settings, R repetitions costs
O(AGLRN); ROC sorting is O(M log M). CV Gaussian simulation stores 2m means
and a 2m x 2m covariance, with dense Gaussian transformations O(m³).
