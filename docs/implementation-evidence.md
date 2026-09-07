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

## Phase 3

Two gateway tests pass. Integration starts three independent OS processes and
uses real HTTP: honest MAC accepted; seed-7 10% interception refused at signature;
full interception refused at quantum_channel without a MAC or a Bob request;
changing amount_paise after signing refused. Canonical encoding is order-independent
and domain-separated. Actual fetched keys were compared against all three logs
and gateway response bodies; no matches.

The long-running dashboard process has exceeded ten minutes. At the retention
check its two segments were 171415 and 258478 bytes, total 429893 bytes; rotation
has occurred repeatedly and the API remains capped at 200 events.

## Phase 4

FastPay (tauh33dkhan/FastPay) cloned and modified. server.js port changed from
hardcoded 80 to process.env.PORT || 3000. models/db.js gains a Transfers table
(id, from_user, to_user, amount_paise, status, stage, reason, session_id, qber,
chsh_s, created_at) and seeds alice/bob users at 100000 paise each.
controller/transfer_controller.js implements POST /transfer (calls Alice gateway
at :8001, validates envelope schema, commits wallet debits/credits inside an
IMMEDIATE SQLite transaction with conditional WHERE guards, publishes result to
the engine dashboard at POST /channel/payment) and GET /transfers, GET /wallet.
routes/app.js wires the three endpoints. views/dashboard.ejs provides a minimal
wallet UI with a Pay Bob button, balance display, and transfer history table.
Stripe and other original FastPay flows are untouched.

Two transfer tests pass: (1) atomic debit/credit with injected trigger fault and
concurrent double-spend guard, (2) insufficient balance rejected before gateway
fetch. grep -ri razorpay clean on both repos.

## Phase 5

frontend/index.html extended with the E91 Payment Channel panel (Key Management
tab). Components added:
1. Character-by-character key comparison with green/red per-hex-digit colouring.
2. Eve interception slider (0–100%) posting to /channel/attack with 200ms debounce.
3. QBER gauge (0–25% range, 2% abort threshold marker).
4. CHSH S-parameter gauge (0–2√2 range, 2.0 classical bound marker).
5. Payment verdict display fed by /channel/latest polling.
6. Round-by-round published sample bit stream.

All gauges transition colour at the abort/classical boundary. Slider wires to
the existing POST /channel/attack endpoint. Every panel element carries a
"simulated" tag. JS polls /channel/latest every 1.5s and fetches keys, status,
and rounds on new session_id. 149 tests still pass after changes.

## Phase 6

docs/demo-runbook.md created with four-terminal startup sequence and three
scenarios (honest, 10% attack, 100% attack) with expected outcomes table.
LIMITATIONS.md extended with items 12–16 covering E91 simulation-only status,
light attacker detection gap, denial-not-theft semantics, endpoint compromise
caveat, and absence of composable security proof. No forbidden terms
("unbreakable", "unhackable", "quantum-proof") used anywhere.
