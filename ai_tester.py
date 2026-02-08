#!/usr/bin/env python3
"""
AI-Based HIL Battery Behavior Monitor
------------------------------------

Role in the HIL chain:
- Acts as a passive observer on the Virtual CAN Bus (UDP)
- Learns NORMAL battery behavior without labels
- Detects BEHAVIORAL anomalies, not simple threshold violations

Design philosophy:
- Safety logic remains in C (Gateway)
- AI only observes and flags suspicious behavior
- Features are engineered to represent physical behavior

This file is intentionally written in a clean, readable,
and interview-friendly style.
"""

import socket
import struct
import time
import warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

UDP_IP = "127.0.0.1"
UDP_PORT = 5000

TRAINING_SAMPLES = 200      # Number of samples used to learn "normal"
WINDOW_SIZE = 20            # Rolling window for noise estimation
CONTAMINATION = 0.02        # Expected anomaly ratio (2%)

# Suppress sklearn warnings for clean console output
warnings.filterwarnings("ignore")

# ------------------------------------------------------------
# UDP Socket Setup (Virtual CAN Bus Listener)
# ------------------------------------------------------------

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("=================================================")
print("   AI-BASED HIL BATTERY BEHAVIOR MONITOR")
print("=================================================")
print(f"Listening on UDP {UDP_IP}:{UDP_PORT}")

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

def parse_can_frame(data):
    """
    Parse the fake CAN frame sent by the C gateway.

    Frame layout (13 bytes total):
    - uint32 : CAN ID
    - uint8  : DLC
    - 8 bytes payload
        [0] Voltage High Byte
        [1] Voltage Low Byte
        [2] Temperature
        [3] Status
    """
    can_id, dlc, payload = struct.unpack("<IB8s", data)
    voltage = (payload[0] << 8) | payload[1]
    temp = payload[2]
    status = payload[3]
    return can_id, voltage, temp, status


# ------------------------------------------------------------
# PHASE 1: Learning Normal Behavior
# ------------------------------------------------------------

print("\n[PHASE 1] LEARNING NORMAL BATTERY BEHAVIOR")
print("Collecting clean data for AI baseline...")
print(f"Target: {TRAINING_SAMPLES} samples")

training_features = []
voltage_window = []
prev_voltage = None

while len(training_features) < TRAINING_SAMPLES:
    data, _ = sock.recvfrom(1024)

    if len(data) != 13:
        continue

    _, voltage, temp, _ = parse_can_frame(data)

    if prev_voltage is not None:
        # Feature 1: Absolute voltage level
        # Feature 2: Voltage delta (trend information)
        delta_v = voltage - prev_voltage

        # Feature 3: Short-term noise / variance
        voltage_window.append(voltage)
        if len(voltage_window) > WINDOW_SIZE:
            voltage_window.pop(0)

        noise_std = np.std(voltage_window)

        training_features.append([
            voltage,
            delta_v,
            noise_std
        ])

        if len(training_features) % 20 == 0:
            print(f"  -> Collected {len(training_features)}/{TRAINING_SAMPLES}")

    prev_voltage = voltage

print("[PHASE 1] COMPLETE")
print("Baseline behavior captured.")

# ------------------------------------------------------------
# PHASE 2: AI Model Training
# ------------------------------------------------------------

print("\n[PHASE 2] TRAINING AI MODEL (Isolation Forest)")

df = pd.DataFrame(
    training_features,
    columns=["Voltage", "DeltaVoltage", "NoiseStd"]
)

model = IsolationForest(
    n_estimators=200,
    contamination=CONTAMINATION,
    random_state=42
)

model.fit(df)

print("AI model trained successfully.")
print("Learned normal behavior envelope:")
print(f"  Voltage Range     : {df['Voltage'].min()} mV -> {df['Voltage'].max()} mV")
print(f"  Avg Voltage Delta : {df['DeltaVoltage'].mean():.2f} mV")
print(f"  Avg Noise StdDev  : {df['NoiseStd'].mean():.2f} mV")

# ------------------------------------------------------------
# PHASE 3: Live Monitoring
# ------------------------------------------------------------

print("\n[PHASE 3] LIVE AI MONITORING")
print("Press Ctrl+C to stop.")
print("-------------------------------------------------")

voltage_window.clear()
prev_voltage = None

try:
    while True:
        data, _ = sock.recvfrom(1024)

        if len(data) != 13:
            continue

        can_id, voltage, temp, status = parse_can_frame(data)

        if prev_voltage is not None:
            delta_v = voltage - prev_voltage

            voltage_window.append(voltage)
            if len(voltage_window) > WINDOW_SIZE:
                voltage_window.pop(0)

            noise_std = np.std(voltage_window)

            sample = [[voltage, delta_v, noise_std]]

            prediction = model.predict(sample)[0]
            score = model.decision_function(sample)[0]

            if prediction == -1:
                print(
                    f"\033[91m[ANOMALY]\033[0m "
                    f"Volt={voltage:4d}mV | "
                    f"dV={delta_v:4d}mV | "
                    f"Noise={noise_std:6.2f} | "
                    f"Score={score:6.3f}"
                )
            else:
                print(
                    f"\033[92m[OK]\033[0m "
                    f"Volt={voltage:4d}mV | "
                    f"dV={delta_v:4d}mV | "
                    f"Noise={noise_std:6.2f}"
                )

        prev_voltage = voltage
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nAI Monitoring stopped gracefully.")
