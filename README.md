# 🛡️ Teleportation-Assisted QDS Threat Detection Framework

> **A real-time Quantum Digital Signature (QDS) security system that detects eavesdropping, forgery, and replay attacks using quantum teleportation circuits and statistical physics.**

Built with **Python 3.12**, **Qiskit Aer**, **Strawberry Fields**, **FastAPI**, and interactive web terminals for live demonstration.

---

## 📖 What is this Project? (In Simple Words)

In today's digital world, when you make a bank payment or sign a document, classical math algorithms (like RSA or ECDSA) create a **digital signature**. 

### The Problem:
1. **Quantum computers can break classical signatures:** A sufficiently powerful quantum computer running Shor's algorithm can mathematically forge existing digital signatures.
2. **Passive wiretapping is invisible:** On classical optical fibers, an eavesdropper can silently copy electrical or light pulses without leaving any trace.

### The Quantum Solution:
This project implements **Quantum Digital Signatures (QDS)** assisted by **Quantum Teleportation**:
* According to the **Heisenberg Uncertainty Principle** and the **Quantum No-Cloning Theorem**, quantum states **cannot be copied or measured without disturbing them**.
* If an attacker (**Eve**) tries to tap into the quantum link, intercept qubits, or alter classical instructions, the quantum states collapse.
* This disturbance creates an immediate spike in the **Quantum Bit Error Rate (QBER)** and destroys **quantum entanglement**.
* Our system monitors these quantum properties in real-time, **detects tampering within milliseconds**, and mathematically attributes the attack type.

---

## 🌟 Key Features

* ⚛️ **Genuine Quantum Teleportation:** Alice signs messages by teleporting BB84 token states to Bob using entangled Bell pairs ($|\Phi^+\rangle$) and classical Pauli corrections ($\sigma_x \cdot \sigma_z$).
* ⚡ **Ultra-Fast Detection (Wald's SPRT):** Uses a Sequential Probability Ratio Test to statistically reject tampered signatures in under 15 measurement rounds instead of waiting for thousands.
* 🔬 **Bell Inequality Witness (CHSH):** Continuously verifies that shared photons are genuinely entangled ($S > 2.0$, up to $2\sqrt{2} \approx 2.828$), proving no classical wiretap exists.
* 🧠 **Deterministic Attack Attribution:** Automatically diagnoses *how* the channel is being attacked (Intercept-Resend, Entanglement Probe, Coherent Attack, Classical Tampering, Impersonation, or Replay).
* 📱 **3-Screen Live Demonstration Mode:**
  1. **Command Center (Alice / Financial SOC):** Live quantum circuit visualizer, real-time SPRT likelihood curves, CHSH history, and transaction logs.
  2. **Mobile UPI Receiver (Bob / Merchant):** Simulated mobile banking terminal receiving real-time funds with quantum verification.
  3. **Eve's Controller (Adversary / Red Team):** "God Mode" toggle to inject real physical quantum attacks on the fly.

---

## 🏗️ How It Works (System Architecture)

```
   [ Alice (Sender) ]
          │
          ├─ 1. Classical Message + HMAC Digest + Session Nonce
          ├─ 2. Quantum Token States (BB84 Preparation)
          │
          ▼
   [ Quantum Channel: Genuine Teleportation ]
          │
          ├─ (Bell State Measurement on Alice's Side)
          ├─ (Classical Feedforward: Pauli X & Z Corrections)
          │
      ┌───┴───┐
      │  EVE  │ <── [ Attacker taps channel, measures, or tampers ]
      └───┬───┘
          │
          ▼
   [ Bob (Receiver / Verifier) ]
          │
          ├─ 1. Measures received quantum states against private schedule
          ├─ 2. Computes Quantum Bit Error Rate (QBER)
          ├─ 3. Sequential Probability Ratio Test (SPRT) ──> Rapid Early Decision
          ├─ 4. CHSH Correlator ───────────────────────────> Entanglement Witness (S > 2.0)
          ├─ 5. Min-Entropy Evaluator ─────────────────────> Helstrom Security Bounds
          │
          ▼
   [ Attribution Engine ]
          │
          ├─ Rules Engine maps observable flags to attack class
          │
          ▼
   [ VERDICT: ACCEPT / REJECT ]
          │
          ├─ ✅ If ACCEPT ──> Funds Credited / Signature Verified
          └─ 🚨 If REJECT ──> Transaction Aborted + Forensics Logged
```

---

## 🚀 Quick Start Guide

### Prerequisites
* **Python 3.12** is required (tested on 3.12.x; Python 3.13+ is not recommended).
* Git installed.

---

### Step 1: Clone the Repository & Switch to `ojasv`

```sh
git clone https://github.com/kartikeywastaken/qds-threat-detection.git
cd qds-threat-detection
git checkout ojasv
```

---

### Step 2: Create a Virtual Environment & Install Dependencies

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**On Linux / macOS:**
```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Step 3: Run the System

You can run the project in three different ways:

#### Option A: Live Interactive Web App & 3-Screen Demo (Recommended for Presentations)

Start the unified FastAPI server:
```sh
python app.py
```
Open your browser to access the terminals:
* 🖥️ **Command Center (Alice / Central Dashboard):** [http://localhost:8000](http://localhost:8000)
* 📱 **Mobile Banking Terminal (Bob / Receiver):** [http://localhost:8000/mobile](http://localhost:8000/mobile)
* 🦹 **Eve's Attack Controller (Adversary):** [http://localhost:8000/eve](http://localhost:8000/eve)

> **Live Demo Tip:** Open the Command Center on your laptop screen, Bob's mobile terminal on one phone, and Eve's controller on another phone (connected to the same local Wi-Fi or via ngrok/Render). Tap an attack on Eve's phone and watch the Command Center and Bob's phone immediately trigger red alert forgeries!

#### Option B: Full Scientific Benchmark Pipeline

Runs all quantum simulation test cases, calibration against IBM FakeManila hardware noise models, the full 285-run attack matrix, ROC curves, and generates verification reports:
```sh
python run.py
```
Outputs will be saved in the `artifacts/` folder (`roc.png`, `min_entropy.png`, `threat_report.json`, `VERIFICATION_REPORT.md`).

#### Option C: Run Automated Tests

Run the test suite with pytest:
```sh
pytest -q -s
```

---

## 🎯 Attack Scenarios Explained Simply

Our simulation framework models the physical and classical attack hierarchy:

| Attack Mode | What the Attacker Does | What the Quantum Detector Observes |
|---|---|---|
| **Honest Channel** | Normal transmission; only physical background thermal/depolarizing noise is present. | Low QBER (< 3%), strong Bell violation ($S \approx 2.4$–$2.7$), SPRT decides **ACCEPT**. |
| **Intercept-Resend (Individual)** | Eve measures individual flying qubits and tries to re-prepare them. | Massive QBER spike ($\approx 25\%$), immediate SPRT **REJECT**, state collapse. |
| **Entanglement Probe (Collective)** | Eve entangles an ancillary probe qubit with each transmitted qubit and defers measurement. | Moderate QBER increase, noticeable drop in Bell CHSH parameter $S$, min-entropy drop. |
| **Joint Probe (Coherent)** | Eve routes multiple transmitted qubits through a single shared quantum memory with joint interactions. | High-order multi-qubit correlations altered, SPRT rejection, min-entropy breach. |
| **Classical Manipulation** | Eve modifies the message in transit (e.g., changes ₹500 to ₹50,000) or alters classical Pauli feedforward bits. | HMAC authentication tag mismatch, classical integrity failure. |
| **Impersonation** | Eve pretends to be Alice and submits an unauthenticated signature or substituted quantum source. | Sender mismatch flag, Bell deficit ($S < 2.0$). |
| **Replay Attack** | Eve records a previously valid transaction and attempts to re-send it later. | Cryptographic nonce collision detected; duplicate session rejected. |

---

## 📁 Repository Structure

```
qds-threat-detection/
├── app.py                     # Main FastAPI server with live simulation loop & web APIs
├── qds_command_center (1).html# Central SOC Command Center web frontend
├── mobile.html                # Bob's mobile banking terminal frontend
├── eve.html                   # Eve's adversary attack controller frontend
├── run.py                     # Primary one-command scientific benchmark & verification runner
├── requirements.txt           # Dependency specifications
│
├── quantum_core/              # Fundamental quantum mechanics implementations
│   ├── bell_state_generator.py# Bell pair generation & CHSH measurement circuits
│   ├── channel_noise_model.py # IBM Manila calibration noise model & thermal loss
│   ├── cv_channel_model.py    # Continuous-Variable (CV) Gaussian optics (Strawberry Fields)
│   ├── ghz_state_generator.py # Multipartite GHZ quantum states
│   └── pauli_operations.py    # Single-qubit state preparations & Pauli rotations
│
├── qds_protocol/              # Quantum Digital Signature protocol
│   ├── key_distribution.py    # BB84 token state & key distribution
│   ├── signing_engine.py      # HMAC session binding & signature envelope generation
│   ├── teleportation_engine.py# Full quantum teleportation circuits (Alice -> Bob)
│   └── verification_engine.py # Receiver-side verification & nonce-freshness enforcement
│
├── detection_engine/          # Statistical threat detection & physics monitors
│   ├── sprt_controller.py     # Sequential Probability Ratio Test (Wald's SPRT)
│   ├── chsh_correlator.py     # CHSH Bell inequality parameter estimator
│   ├── kl_divergence_scorer.py# Kullback-Leibler divergence from calibrated honest baseline
│   ├── min_entropy_evaluator.py# Conditional min-entropy calculation
│   └── integrity_monitor.py   # Fusion monitor combining quantum & classical flags
│
├── attack_simulation/         # Executable attack circuits & injectors
│   ├── individual_attack.py   # Intercept-resend strategy
│   ├── collective_attack.py   # Two-qubit ancilla entangling strategy
│   ├── coherent_attack.py     # Joint multi-qubit probe strategy
│   ├── channel_manipulation_injector.py # Classical payload tampering
│   ├── impersonation_injector.py        # Sender spoofing
│   └── replay_injector.py               # Captured payload replay
│
├── attribution_engine/        # Diagnostic classification
│   ├── rule_engine.py         # Deterministic decision rule evaluator
│   └── rules.json             # Observable flag mapping rules
│
├── presentation/              # Reporting, logging & dashboard tooling
│   ├── verification_api.py    # Cryptographic REST API endpoints
│   ├── security_event_log.py  # SHA-256 hash-chained JSONL audit logger
│   └── serve.py               # Standalone verification server
│
├── evaluation/                # Performance benchmarks
│   ├── roc_curve_generator.py # Empirical ROC curve generation
│   └── run_full_evaluation.py # 285-run parameter sweep
│
└── tests/                     # 38+ unit & integration test suites
```

---

## 🤝 Contributor & PR Guidelines

We welcome contributions! When submitting changes to branch `ojasv`:

1. **Branch Workflow:** Create a feature branch off `ojasv` (e.g., `git checkout -b fix/my-feature ojasv`).
2. **Never Mock What Physics Can Simulate:** Do not hardcode random values for quantum metrics. Always route measurement through `quantum_core` or `qds_protocol`.
3. **Cross-Platform Compatibility:** Ensure code runs seamlessly on both **Windows** and **Linux/macOS**.
4. **Run Tests Before Raising PRs:**
   ```sh
   pytest -q
   ```
5. **Submit a Clean PR:** Open a Pull Request targeting the `ojasv` branch with a clear description of changes.

---

## 📜 Scientific Foundations & References

1. **CHSH Randomness & Entanglement:** Pironio et al., *Random numbers certified by Bell's theorem*, Nature 464, 1021–1024 (2010). [DOI: 10.1038/nature09008](https://doi.org/10.1038/nature09008)
2. **Quantum Detection & Discrimination:** C. W. Helstrom, *Quantum Detection and Estimation Theory*, Academic Press (1976).
3. **Sequential Analysis:** Abraham Wald, *Sequential Analysis*, John Wiley & Sons (1947).
4. **Quantum Noise Simulation:** Qiskit Aer device noise construction ([IBM Quantum](https://qiskit.github.io/qiskit-aer/)).
5. **Continuous-Variable Quantum Optics:** Strawberry Fields ([Xanadu Quantum](https://strawberryfields.readthedocs.io/)).

---

## ⚠️ Research Notice

This project is an advanced **research and demonstration framework** simulating physical quantum circuits and statistical detection mechanisms. For real-world production deployment on quantum hardware, active optical alignment, dark count calibration, and phase stabilization over physical fiber links are required. Please consult [LIMITATIONS.md](LIMITATIONS.md) and [math_model/security_proofs.md](math_model/security_proofs.md) for full formal specifications.
