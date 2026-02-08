# Virtual CAN HIL System with AI Based Battery Behavior Monitoring

## Project Overview

This repository implements a **fully virtual Hardware in the Loop HIL system** for validating embedded ECU logic and **AI based behavioral anomaly detection**, without requiring:

- Physical ECUs  
- CAN hardware  
- Kernel level CAN drivers  

All components run locally and emulate a realistic automotive ECU data flow, making the setup suitable for **early development, validation, and algorithm prototyping**.

A key design goal of this project is the **clear separation of deterministic safety logic and AI based behavioral monitoring**, following best practices used in safety critical automotive systems.

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
   Simulates an STM32 based battery sensor node  
   Generates voltage trends with realistic noise  
   Injects rare and probabilistic fault conditions  

2. **Gateway ECU (C)**  
   Acts as an edge ECU  
   Performs checksum validation and safety checks  
   Encapsulates data into CAN like frames  
   Broadcasts frames over UDP as a Virtual CAN Bus  

3. **AI Monitor (Python)**  
   Listens passively on the Virtual CAN Bus  
   Learns normal battery behavior using unsupervised learning  
   Detects behavioral anomalies in real time  

All communication is implemented using TCP and UDP sockets to ensure full portability.

---

## 📂 Project Structure

- `sensor`  
  Generates voltage data and injects fault conditions

- `gateway`  
  Receives and validates frames, forwards data

- `ai_validator`  
  Trains and monitors anomalies using AI

- `README.md`


---

## 🧠 Technical Highlights

### Pure Virtual HIL Strategy

This project intentionally bypasses kernel CAN dependencies.

**Why**  
- Enables development on any machine  
- Eliminates dependency on CAN hardware  
- Accelerates early stage validation  

**How**  
- CAN frames are emulated using a packed C structure  
- Frames are transported over UDP  
- Behavior matches a real ECU pipeline at application level  

---

### 🔋 Battery Behavior Modeling

The virtual sensor models:

- Incremental voltage trends  
- ADC like noise and jitter  
- Reset behavior  
- Random low probability fault injection  

This produces data that resembles real embedded sensor output rather than synthetic test vectors.

---

### 🧠 AI Based Behavioral Monitoring

The AI component uses an **unsupervised Isolation Forest model** and is designed to observe **behavior**, not raw values.

#### Feature Engineering

Instead of raw voltage alone, the AI learns from:

- Absolute voltage level  
- Voltage delta between samples (trend)  
- Rolling voltage variance (noise envelope)  

This enables detection of:

- Sudden voltage drops  
- Abnormal trend changes  
- Noise growth and instability  
- Early signs of degradation  

#### Training Phase

- The first 200 clean samples are used to learn baseline behavior  
- No fault labels are required  

#### Monitoring Phase

- Each incoming frame is evaluated in real time  
- Anomalies are flagged based on multivariate behavior  
- Safety decisions remain exclusively in the gateway ECU  

---

## 🧭 Design Philosophy

- Deterministic safety logic must not rely on AI  
- AI is used as an observer, not a controller  
- Behavioral understanding is more valuable than threshold checks  
- Architecture should scale toward real automotive systems  

This approach aligns with industry practices used in safety critical validation environments.

---

## 🗺 Roadmap

**Completed**
- Fully virtual HIL signal chain  
- Realistic sensor behavior modeling  
- AI based behavioral anomaly detection  

**Planned**
- Battery degradation modeling  
- Explainable anomaly reasoning  
- Anomaly persistence and confidence logic  
- Optional migration to Linux SocketCAN `vcan0`  
- Safe bidirectional AI feedback to the gateway  

---

## ⭐ Why This Project Matters

This repository demonstrates how **AI can be integrated correctly** into an embedded validation pipeline without compromising safety, determinism, or engineering discipline.

It is intended as a **portfolio quality project** showcasing system level thinking across embedded software, communication protocols, and applied machine learning.
