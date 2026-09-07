# Teleportation-assisted QDS threat detection research framework

Executable Qiskit Aer + Strawberry Fields simulations, Bernoulli SPRT, CHSH,
KL divergence, scoped min-entropy bounds, deterministic attribution, a local
FastAPI service, a live desktop dashboard and a measured attack/noise sweep.
**Research prototype, not a proven production QDS system.** Read
[LIMITATIONS.md](LIMITATIONS.md) and [security model](math_model/security_proofs.md).
The supplied prompt's universal C3 security guarantee is not established; the
verification report marks it unsupported rather than manufacturing a pass.

## Install and run

Python **3.12** is tested (3.13+ is not the target). From this directory:

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

That single top-level command runs all tests, **A1–A5 first**, functional checks,
a real HTTP verification including attack injection and replay, CV/GHZ diagnostics,
the full 285-run attack grid, plots, hash-chained logs and final checklist.
No API keys or manual interaction required. Allow several minutes on a laptop.
It finishes with explicit pass counts and unsupported requirements; computational
errors raise exceptions. A completed run is not synonymous with security sign-off.

Primary outputs in `artifacts/`:

- `VERIFICATION_REPORT.md`, `verification_checklist.json`: every acceptance item.
- `tests.txt`, `anti_faking.json`, `functional_checks.json`: observed evidence.
- `evaluation_runs.json`, `evaluation_summary.json`, `roc.png`: actual sweep/ROC.
- `min_entropy.png`: derived restricted-model bound versus bit count.
- `signature_payload.json`, `measurement_records.json`, `chsh_measurements.json`:
  real envelope and receiver observations from the HTTP demo.
- `threat_report.json`, `events.jsonl`, `dashboard.png`: computed decisions/logs.
- `cv_channel.json`, `ghz_probabilities.json`: actual quantum-core diagnostics.

Use `--output artifacts/run2` to keep independent runs separate. Existing event
logs append by design; numeric decisions for a fixed seed/configuration repeat.
`--repeats` controls seeds per grid cell; default 5. Do not compare ROC reports
with different repeat counts as if they used the same sample.

## Live API and dashboard

Start the service in one terminal:

```sh
.venv/bin/python -m presentation.serve
```

Then send the generated real payload:

```sh
curl -s http://127.0.0.1:8000/verify -H 'Content-Type: application/json' --data-binary @artifacts/live/payload.json
.venv/bin/python -m presentation.dashboard --log artifacts/live/events.jsonl
```

The dashboard refreshes from the actual log every second. Repeating the same HTTP
payload demonstrates replay rejection. Interactive API documentation is at
`http://127.0.0.1:8000/docs`; `/events` exposes computed telemetry. Receipts and
secret preparation data stay server-side; clients cannot submit measurement scores.

## Architecture and methodology

`math_model` → `quantum_core` → `qds_protocol` → `attack_simulation` →
`detection_engine` → `attribution_engine` → `presentation` → `evaluation`.
Each listed implementation module has a test file. Development stages were tested
in the requested order. No detection or attribution module imports attack
simulation, reads scenario labels or contains ML. Evaluation alone knows labels.

Signing binds a session/nonce/sender/message with HMAC and sends the verifier's
BB84 token states through genuine teleportation (Bell measurement and conditional
X/Z corrections). The verifier retains the secret preparation schedule. Attacks
modify physical circuits or the actual envelope; no detector branch uses the
configured attack type. See the security model for the construction's limits.

The quantum source selects random CHSH settings and executes measurement circuits.
The correlator only sees tuples `(setting_a, setting_b, outcome_a, outcome_b)`.
SPRT uses conservative bounds `log(1/alpha)` and `log(beta)` with explicit
`INCONCLUSIVE` at exhaustion. A separately implemented binomial fixed-sample
baseline computes its own threshold. ROC is empirical threshold enumeration,
not a fitted classifier. Reference p0 comes from 8192 separate honest simulated
rounds and an exact confidence upper bound plus a documented 0.01 guard margin.

The calibration source and T1/T2/readout parameters are saved in the evaluation
summary. Seeds are explicit in each experiment; source and simulator RNGs are
separate. The dependency lock fixes the tested libraries. The min-entropy curve
is valid only under the independently stated pure-probe model, and the CHSH
entropy is only a single-round witness. Neither is silently promoted to a full
coherent-attack QDS security proof.

## Focused commands

```sh
.venv/bin/python -m pytest -q -s
.venv/bin/python evaluation/run_full_evaluation.py --output artifacts/evaluation
```

## Quantum execution backends

The DPM framework supports two quantum execution backends, selectable via
environment variable.  Neither backend is physical quantum hardware.

### Ideal Cirq Simulator

Fast, noise-free simulation using Google's Cirq framework.

```sh
DPM_QUANTUM_BACKEND=ideal
```

Used for:
- Unit tests (default)
- Deterministic debugging
- Reference / comparison baselines
- Fast development iteration

### Google Quantum Virtual Machine — Willow

Local noisy simulation of a virtual Google Willow processor environment.
**QVM does NOT execute on physical quantum hardware.**  No Google credentials,
API keys, or network access are required.

```sh
DPM_QUANTUM_BACKEND=qvm
DPM_QUANTUM_SHOTS=2000
DPM_QVM_PROCESSOR=willow
```

Used for:
- Hardware-like noise modelling (T1/T2/gate/readout noise)
- Processor-oriented circuit constraints and qubit routing
- DPM experimental results and demonstration

The QVM backend uses `cirq-google` and `qsimcirq` to create a local noisy
simulation using bundled Google calibration data for the virtual Willow
processor.  All packages are installed from `requirements.txt`.

### Run with ideal simulator

```sh
DPM_QUANTUM_BACKEND=ideal .venv/bin/python run.py
```

### Run with QVM (recommended for demonstrations)

```sh
DPM_QUANTUM_BACKEND=qvm DPM_QUANTUM_SHOTS=2000 .venv/bin/python run.py
```

### Compare backends (ideal vs QVM experiment)

```sh
.venv/bin/python evaluation/run_attack_matrix.py --compare --shots 1000
```

This runs all attack scenarios against both backends and reports:
- Error rates, TV distances, and classification decisions
- Side-by-side ideal vs Willow QVM measurements
- No real hardware required

### Backend status API

```sh
curl http://127.0.0.1:8000/quantum/status
```

Returns `{"backend": "qvm", "simulated": true, "noisy": true, ...}`.

## Primary references

- [Qiskit Aer device-noise construction](https://qiskit.github.io/qiskit-aer/tutorials/2_device_noise_simulation)
- [Aer NoiseModel API](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.NoiseModel.html)
- [Strawberry Fields ThermalLossChannel](https://strawberryfields.readthedocs.io/en/latest/code/api/strawberryfields.ops.ThermalLossChannel.html)
- [Pironio et al., Nature 2010, CHSH randomness](https://doi.org/10.1038/nature09008)
- Helstrom, *Quantum Detection and Estimation Theory*, 1976.
- Wald, *Sequential Analysis*, 1947.
