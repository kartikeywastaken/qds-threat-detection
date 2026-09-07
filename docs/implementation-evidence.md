# Implementation evidence

## Phase 0

Baseline on main: 129 tests passed (18.05 seconds). After additive dashboard port:
129 passed (21.17 seconds), same three dependency deprecation warnings.
Protected engine files, existing tests and requirements are unchanged.

Live HTTP: honest accepted at QBER 0.78%; individual 24.41%, collective 30.08%,
coherent 37.70%, impersonation 26.37%, and manipulation 22.27% all refused.
Replay refused at 0.78%: replay rejection is an integrity check and does not
physically disturb qubits, so its QBER correctly stays at the honest baseline.
All seven modes produced a verdict within 0.46 seconds in the acceptance run.
The inherited frontend had a JavaScript array syntax error; repaired and verified
connected, changing telemetry in the browser with no new console errors.
Case-insensitive forbidden-provider scan clean. Dashboard copied file by file
from origin/ojasv e2ac6a0; no branch integration was performed.

Telemetry uses a fresh verifier each cycle and two bounded hash-chain segments
(100 events or 256 kB each, plus at most one event over the byte threshold).
