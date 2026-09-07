# Demo runbook

All quantum results are **simulated** on Qiskit Aer. No physical quantum hardware
is used. The E91 channel abort threshold is calibrated for a noiseless simulator
(ABORT_QBER = 0.02).

## Prerequisites

```sh
# Terminal 1 — QDS engine (port 8000)
cd /path/to/qds-threat-detection
source .venv/bin/activate

# Terminal 2 — Alice gateway (port 8001)
cd /path/to/qds-threat-detection
source .venv/bin/activate

# Terminal 3 — Bob gateway (port 8002)
cd /path/to/qds-threat-detection
source .venv/bin/activate

# Terminal 4 — FastPay wallet (port 3000)
cd /path/to/FastPay
```

## Start services (in order)

### 1. QDS engine (port 8000)

```sh
python app.py
```

Wait for `Uvicorn running on http://127.0.0.1:8000`. The teleportation simulation
loop starts publishing verdicts at 1 Hz. Open http://127.0.0.1:8000 for the
command center dashboard.

### 2. Alice gateway (port 8001)

```sh
python -m gateways.alice_service
```

### 3. Bob gateway (port 8002)

```sh
python -m gateways.bob_service
```

### 4. FastPay wallet (port 3000)

```sh
node server.js
```

Open http://127.0.0.1:3000 and log in as **alice** (password: `demo-wallet-2026`).
Bob's dashboard is visible by logging in as **bob** with the same password.

---

## Scenario 1: Honest channel (eve_fraction = 0)

1. On the QDS dashboard (port 8000), click the **Key Management** tab (key icon).
2. Ensure the **Eve Interception** slider is at **0%**.
3. On FastPay (port 3000), click **Pay Bob ₹100**.

**Expected outcome:**

| Field | Value |
|---|---|
| Status | ACCEPTED |
| Stage | committed |
| QBER | 0.00% (exactly zero on noiseless simulator) |
| CHSH S | ≈ 2.83 (near Tsirelson bound 2√2) |
| Alice's key | 64-hex-char string |
| Bob's key | identical to Alice's |
| Alice balance | −₹100 |
| Bob balance | +₹100 |
| Dashboard keys | all green, identical character-by-character |

---

## Scenario 2: Light attack (eve_fraction = 10%)

1. Drag the **Eve Interception** slider to **10%**.
2. Click **Pay Bob ₹100** again.

**Expected outcome:**

| Field | Value |
|---|---|
| Status | REFUSED |
| Stage | signature |
| QBER | ≈ 2.5% (may stay under the 2% abort threshold on some seeds) |
| CHSH S | ≈ 2.6–2.8 (above classical bound) |
| Alice's key | 64-hex-char string |
| Bob's key | **different** 64-hex-char string |
| Reason | gateways derived different keys — channel disturbed |
| Alice balance | unchanged |
| Bob balance | unchanged |
| Dashboard keys | red/mismatch characters visible |

This is the most interesting scenario to show the judges: the error rate stays
below the abort threshold but the keys still diverge. Detection (QBER, CHSH) and
consequence (key mismatch) are two separate checks, and the payment gate requires
both.

---

## Scenario 3: Full attack (eve_fraction = 100%)

1. Drag the **Eve Interception** slider to **100%**.
2. Click **Pay Bob ₹100** again.

**Expected outcome:**

| Field | Value |
|---|---|
| Status | REFUSED |
| Stage | quantum_channel |
| QBER | ≈ 19–25% (well above 2% abort threshold) |
| CHSH S | ≈ 1.2–1.5 (below classical bound 2.0) |
| Alice's key | empty (not derived) |
| Bob's key | empty (not derived) |
| Reason | Channel aborted: QBER exceeded threshold / CHSH below classical bound |
| Alice balance | unchanged |
| Bob balance | unchanged |
| Dashboard keys | empty/dashes, red status |

---

## Teleportation threat detection (independent subsystem)

The dropdown on the main Command Center tab controls the teleportation QDS
engine, which runs independently from the E91 payment channel:

- **HONEST** → ACCEPT, low QBER, CHSH ≈ 2.7
- **INDIVIDUAL** → REJECT, QBER ≈ 24%, attribution: forgery
- **COLLECTIVE** → REJECT, QBER ≈ 30%
- **COHERENT** → REJECT, QBER ≈ 38%
- **IMPERSONATION** → REJECT, attribution: impersonation
- **CHANNEL_MANIPULATION** → REJECT, attribution: channel_manipulation
- **REPLAY** → REJECT, attribution: replay (nonce reuse)

---

## Verification

```sh
# All tests pass
DPM_QUANTUM_BACKEND=ideal python -m pytest -q

# No Razorpay references
grep -ri razorpay . --include='*.py' --include='*.html' --include='*.js'

# No key material in logs
grep -E '[0-9a-f]{64}' artifacts/events.jsonl | head -5
# (should be empty or only contain session_ids, never hex keys)
```
