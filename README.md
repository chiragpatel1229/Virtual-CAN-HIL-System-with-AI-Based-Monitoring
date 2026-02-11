# Virtual CAN HIL System with AI Based Battery Behavior Monitoring

## Project Overview

This repository implements a **fully virtual Hardware-in-the-Loop (HIL)** system for validating embedded ECU logic and **AI-based behavioral anomaly detection**, without requiring:

- Physical ECUs  
- CAN hardware  
- Kernel level CAN drivers  

All components run locally and emulate a realistic automotive ECU data flow, making the setup suitable for **early-stage development, algorithm prototyping, and validation testing**.

A key design goal of this project is the **clear separation of deterministic safety logic** (handled by the gateway) and **AI based behavioral monitoring**, following best practices used in safety critical automotive systems.

---

## 🎯 Key Objectives

- Validate embedded application logic in a hardware independent environment  
- Simulate realistic battery voltage behavior with noise and fault injection  
- Apply AI to detect **behavioral anomalies**, not simple threshold violations  
- Demonstrate correct architectural placement of AI in a HIL pipeline  

---

## 🧩 System Architecture

The system emulates a complete ECU signal chain:

1. **Virtual Sensor (C)**  
   Simulates an STM32-style battery monitoring sensor  
   Generates voltage and temperature data with realistic sawtooth trends and increasing noise  
   Injects rare, probabilistic fault conditions (e.g. sudden voltage collapse) after a clean learning phase  

2. **Gateway ECU Simulation (C)**  
   Acts as an application-level data concentrator / safety gateway  
   Validates incoming sensor frames (sync + checksum)  
   Applies deterministic safety rules (temperature & voltage thresholds)  
   Repackages data into CAN-like frames and broadcasts via UDP (virtual CAN bus)  

3. **AI Monitor & HIL Validator (Python)**  
   Passively listens to the virtual CAN bus  
   Learns normal behavior from clean data using unsupervised learning (Isolation Forest)  
   Detects deviations in real time based on engineered physical features  

Communication between components uses standard TCP (sensor → gateway) and UDP (gateway → AI), ensuring full portability and zero external dependencies.

---

## 📂 Project Structure
```
.
├── README.md
├── c_src/
│   ├── common/        # Shared protocol definitions and headers
│   ├── mock_sensor/   # Sensor simulation logic
│   ├── gateway/       # ECU Gateway and Safety Logic
│   ├── main/          # Entry points for C binaries
│   └── Makefil        # Optional: build automation
├── python/
│   ├── main.py        # AI Monitoring entry point
│   ├── config.py      # Hyperparameters
│   ├── can_parser.py  # UDP or CAN frame decoding
│   ├── ai_model.py    # Isolation Forest implementation
│   └── monitor.py     # Live visualization and logging
└── logs/              # Data logs and saved plots
```

- **`c_src/`** → All embedded-style C code (modularized: common utilities, sensor simulation, gateway logic, main entry points)
- **`python/`** → Contains the AI-based monitoring, data parsing, model training, and visualization logic  
- **`logs/`** → Placeholder for future log / CSV outputs (kept trackable with `.gitkeep`)
- **`Makefile`** → (optional) Simplifies building the C components

---

## 🧠 Technical Highlights

### Pure Virtual HIL Strategy

This project intentionally bypasses kernel CAN dependencies.

**Why**  
- Enables development on any machine  
- No need for CAN interfaces, transceivers or drivers  
- Enables fast iteration during early validation

**How**  
- CAN frames use packed C structs matching real payload layout  
- UDP multicast-style broadcast simulates virtual CAN bus  
- Behavior preserved at application level (framing, validation, safety checks)

---

### 🔋 Battery Behavior Modeling

The virtual sensor models:

- Sawtooth voltage pattern (mimics charging/discharging cycles)  
- ADC-like random noise with gradually increasing amplitude (aging simulation)  
- Slow voltage sag over long runtime (capacity fade)  
- Rare probabilistic hard faults (sudden voltage drop to failure level)  

This produces data that closely resembles real embedded sensor output — not just synthetic test patterns.

---

### 🧠 AI Based Behavioral Monitoring

The AI component uses an **unsupervised Isolation Forest model** and is designed to observe **behavior**, not raw values.

#### Feature Engineering

Instead of raw voltage alone, the AI learns from:

- Absolute voltage level  
- Sample-to-sample delta voltage (trend / slew rate)  
- Rolling standard deviation of voltage (noise envelope growth)  
- Temperature value 

This enables detection of:

- Sudden voltage collapses  
- Abnormal trend / slew rate changes  
- Increasing electrical noise (early degradation indicator)  
- Out-of-distribution multivariate behavior  

#### Training & Monitoring

- One-shot training on first 200 clean samples  
- Real-time inference during 10-minute collection window  
- Persistence logic (3 out of 10 consecutive anomalies) reduces false positives  
- Human-readable explanations and non-binding recommendations  

Safety decisions **never** rely on the AI — they remain exclusively in the deterministic gateway.

---

## 🧭 Design Philosophy

- Safety-critical logic must remain deterministic and independent of AI  
- AI serves only as a passive observer and early warning system  
- Behavioral / trend-based detection is more valuable than static thresholds  
- Architecture is explicitly designed to scale toward real automotive ECUs

This approach aligns with industry practices used in safety critical validation environments.

---

## 🗺 Roadmap

**Completed**
- Fully virtual HIL signal chain (sensor → gateway → AI)  
- Realistic battery sensor modeling with fault injection  
- Unsupervised behavioral anomaly detection  
- Explainable anomaly flagging + visualization  
- Anomaly persistence and confidence logic to improve reliability 

**Planned**
- Controlled fault injection suite for quantitative evaluation
- Optional migration to Linux SocketCAN `vcan0`  
- Safe bidirectional AI feedback to the gateway  

---

## ⭐ Why This Project Matters

This repository demonstrates how **AI can be responsibly integrated** into an embedded validation pipeline without compromising safety, determinism, or engineering discipline.

It is intended as a **portfolio quality project** showcasing system level thinking across embedded software, communication protocols, and applied machine learning.
