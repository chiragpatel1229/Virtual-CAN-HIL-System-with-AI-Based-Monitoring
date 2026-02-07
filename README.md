# Virtual CAN HIL Simulation with AI Anomaly Detection

## Project Goal

This project demonstrates a **hardware independent virtual HIL setup** for validating embedded application logic and AI based anomaly detection **without relying on physical CAN hardware or kernel level drivers**.

The focus is on:
- Application layer logic validation
- Communication flow testing
- AI driven fault detection

All components run locally and simulate a real ECU pipeline.

---

## Components

- Virtual Sensor (C)
- Gateway (C)
- AI Validator (Python)
- UDP based CAN frame emulation

---

## 📂 Project Structure

- `sensor/`  
  Generates voltage data and injects fault conditions

- `gateway/`  
  Receives and validates frames, forwards data

- `ai_validator/`  
  Trains and monitors anomalies using AI

---

## 🚀 Getting Started

### Prerequisites
 
- OS: Linux (Ubuntu 20.04+) or Windows 11 (WSL2)
- Compiler: GCC (sudo apt install build-essential)
- Python: 3.8+ (pip3 install pandas numpy scikit-learn)

**Installation & Execution**  

1. Clone the Repository
2. Build the C Modules
3. Run the Simulation (3 Terminals)
-- Terminal 1: Start the Sensor
-- Terminal 2: Start the Gateway
-- Terminal 3: Start the AI Validator

## 🧠 Technical Overview

### Pure Virtual Strategy (Plan C)

To decouple application logic verification from kernel dependencies, physical CAN drivers are bypassed.

#### Why

- Enables development of checksums, safety rules, and AI models on any machine

#### How

- A `fake_can_frame_t` structure mimics standard CAN frames  
- Frames are transported over UDP  

---

### AI Model: Isolation Forest

#### Training Phase

- The model observes the first 200 packets  
- Learns the normal sawtooth voltage pattern between 3000 mV and 4000 mV  

#### Inference Phase

- The system switches to monitoring mode  
- A 100 mV battery failure injected by the sensor is detected as an anomaly in real time  

---

## 🗺 Roadmap

- Phase 1: Core logic (C) and basic TCP and UDP communication  
- Phase 2: Integration of AI based anomaly detection  
- Phase 3: Migration to Linux SocketCAN using `vcan0`  
- Phase 4: Bidirectional control where AI sends safe mode commands back to the ECU  
