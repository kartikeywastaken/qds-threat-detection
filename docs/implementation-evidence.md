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

## Phase 1

15 E91 tests pass, including eight-seed averages per interception fraction.
At 1024 rounds, seed 7 reproduces the reference: honest QBER 0%, S=2.948325;
full interception QBER 19.4444%, S=1.422039, aborted, empty keys.
Light interception at 10% gives QBER 1.85185%, S=2.810985, no channel abort,
but different independently hashed keys. Seed 7 is the reproducible demo seed.
The population mean at 10% interception is 2.5%, above the 2% threshold;
this selected finite sample illustrates missed detection, not a general claim.
Grouped Aer simulation uses up to 27 cells with partial interception (9 absent
Eve cells plus 18 intercepted cells); full interception uses 18.
Keys and private round outcomes are excluded from result summaries and repr.

## Phase 2

Three channel API tests pass: separate equal keys for honest sessions, both
key endpoints 404 on abort, status redaction, next-session attack selection,
capped animation, 200-session eviction and clock-driven TTL expiry.
Store capacity is 64, TTL 15 minutes; HTTP requests allow at most 8192 rounds.
The animation publishes only sacrificed sample bits, never the surviving bits
from which either digest could be reconstructed. Payment telemetry is bounded
to 64 public envelopes/verdicts and is not a source of authorization.
