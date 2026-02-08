#!/usr/bin/env python3
"""
AI Battery Monitor (Beginner Friendly Version)

This script listens to battery data coming from a virtual CAN bus (UDP).
It first learns what "normal" battery behavior looks like and then
monitors the system in real time to detect unusual behavior.

The goal is not just to detect failures, but also early degradation,
noise growth, and suspicious trends, while keeping all safety decisions
outside the AI logic.

This file is written in a clear and readable way so that it is easy to
understand, debug, and improve later.
"""

import socket
import struct
import time
import warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
# import matplotlib.pyplot as plt

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

UDP_IP = "127.0.0.1"
UDP_PORT = 5000

TRAINING_SAMPLES = 200       # Samples used to learn normal behavior
WINDOW_SIZE = 20             # Rolling window for noise estimation
CONTAMINATION = 0.02         # Expected anomaly ratio

# Phase C: confidence and persistence settings
ANOMALY_WINDOW = 10          # How many recent samples we look at
ANOMALY_THRESHOLD = 3        # How many anomalies trigger a real alert

# Suppress sklearn warnings for clean output
warnings.filterwarnings("ignore")

# ------------------------------------------------------------
# UDP Socket Setup (Virtual CAN Listener)
# ------------------------------------------------------------

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("=================================================")
print("   AI BASED HIL BATTERY BEHAVIOR MONITOR")
print("=================================================")
print(f"Listening on UDP {UDP_IP}:{UDP_PORT}")

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

def parse_can_frame(data):
    """
    Decode the fake CAN frame sent by the C gateway.

    Frame layout (13 bytes total):
    - uint32 : CAN ID
    - uint8  : DLC
    - 8 byte payload
        [0] Voltage high byte
        [1] Voltage low byte
        [2] Temperature
        [3] Status
    """
    can_id, dlc, payload = struct.unpack("<IB8s", data)
    voltage = (payload[0] << 8) | payload[1]
    temp = payload[2]
    status = payload[3]
    return can_id, voltage, temp, status


def explain_anomaly(voltage, delta_v, noise_std, temp):
    """
    Try to explain why the AI thinks this sample is abnormal.
    These rules make the AI output easier to trust and defend.
    """
    reasons = []

    if abs(delta_v) > 3 * BASELINE["std_delta"]:
        reasons.append("Sudden voltage change")
    if noise_std > BASELINE["mean_noise"] + 3 * BASELINE["std_noise"]:
        reasons.append("Noise growth detected")
    if voltage < df["Voltage"].min():
        reasons.append("Voltage below learned normal range")
    if temp < df["Temperature"].min() or temp > df["Temperature"].max():
        reasons.append("Temperature out of normal range")
    if not reasons:
        reasons.append("Behavioral outlier")
    return " + ".join(reasons)


def ai_recommendation(reason):
    """
    Phase D: AI feedback loop (read only).
    The AI suggests actions, but never enforces them.
    """
    if "Noise" in reason:
        return "Recommend derating"
    if "Voltage below" in reason:
        return "Recommend safe mode"
    if "Temperature" in reason:
        return "Check cooling / thermal system"
    return "Monitor only"

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
        delta_v = voltage - prev_voltage

        voltage_window.append(voltage)
        if len(voltage_window) > WINDOW_SIZE:
            voltage_window.pop(0)

        noise_std = np.std(voltage_window)

        training_features.append([
            voltage,
            delta_v,
            noise_std,
            temp
        ])

        if len(training_features) % 20 == 0:
            print(f"  -> Collected {len(training_features)}/{TRAINING_SAMPLES}")

    prev_voltage = voltage

print("[PHASE 1] COMPLETE")
print("Baseline behavior captured")

# Save training data for learning curve analysis
df_training = pd.DataFrame(
    training_features,
    columns=["Voltage", "DeltaVoltage", "NoiseStd", "Temperature"]
)
df_training.to_csv('training_data.csv', index=False)
print("Training data saved to training_data.csv")

# ------------------------------------------------------------
# PHASE 2: AI Model Training
# ------------------------------------------------------------

print("\n[PHASE 2] TRAINING AI MODEL")

df = pd.DataFrame(
    training_features,
    columns=["Voltage", "DeltaVoltage", "NoiseStd", "Temperature"]
)

model = IsolationForest(
    n_estimators=200,
    contamination=CONTAMINATION,
    random_state=42
)

model.fit(df)

BASELINE = {
    "mean_delta": df["DeltaVoltage"].mean(),
    "std_delta": df["DeltaVoltage"].std(),
    "mean_noise": df["NoiseStd"].mean(),
    "std_noise": df["NoiseStd"].std()
}

print("AI model trained successfully")
print("Learned normal behavior:")
print(f"  Voltage range : {df['Voltage'].min()} -> {df['Voltage'].max()} mV")
print(f"  Avg delta     : {df['DeltaVoltage'].mean():.2f} mV")
print(f"  Avg noise     : {df['NoiseStd'].mean():.2f}")
print(f"  Temp range    : {df['Temperature'].min()} -> {df['Temperature'].max()} °C")

# ------------------------------------------------------------
# PHASE 3: Live Monitoring with Phase C and D
# ------------------------------------------------------------

print("\n[PHASE 3] LIVE AI MONITORING")
print("Press Ctrl+C to stop")
print("-------------------------------------------------")

print("\n\n Collecting 10-min data...")
start_time = time.time()
COLLECTION_TIME = 3 * 60  # 3 minutes in seconds
data_log = []


voltage_window.clear()
prev_voltage = None
anomaly_history = []

try:
    # while True:
    while time.time() - start_time < COLLECTION_TIME:
        data, _ = sock.recvfrom(1024)

        if len(data) != 13:
            continue

        _, voltage, temp, status = parse_can_frame(data)

        if prev_voltage is not None:
            delta_v = voltage - prev_voltage

            voltage_window.append(voltage)
            if len(voltage_window) > WINDOW_SIZE:
                voltage_window.pop(0)

            noise_std = np.std(voltage_window)

            sample = [[voltage, delta_v, noise_std, temp]]
            prediction = model.predict(sample)[0]
            score = model.decision_function(sample)[0]

            persistent = False
            reason = ""
            action = ""

            # Track anomaly history for persistence logic
            anomaly_history.append(prediction == -1)
            if len(anomaly_history) > ANOMALY_WINDOW:
                anomaly_history.pop(0)

            # Phase C: only act if anomaly persists
            if anomaly_history.count(True) >= ANOMALY_THRESHOLD:
                persistent = True
                reason = explain_anomaly(voltage, delta_v, noise_std, temp)
                action = ai_recommendation(reason)

                print(
                    f"[PERSISTENT ANOMALY] "
                    f"Volt={voltage}mV | "
                    f"Temp={temp}°C | "
                    f"Reason: {reason} | "
                    f"AI Action: {action}"
                )
            else:
                print(
                    f"[OK] "
                    f"Volt={voltage:4d}mV | "
                    f"dV={delta_v:4d}mV | "
                    f"Noise={noise_std:6.2f}"
                )

            # Collecting the data for visualization and analysis later
            data_log.append({
                "Time": time.time() - start_time,
                "Voltage": voltage,
                "DeltaVoltage": delta_v,
                "NoiseStd": noise_std,
                "Temperature": temp,
                "Anomaly": prediction == -1,
                "AnomalyScore": score,
                "PersistentAnomaly": persistent,
                "Reason": reason,
                "Action": action
            })

        prev_voltage = voltage
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nAI monitoring stopped gracefully")

# Save monitoring data to CSV
df_log = pd.DataFrame(data_log)
df_log.to_csv('monitoring_log.csv', index=False)
print("Monitoring data saved to monitoring_log.csv")

# ----------------------------
# PHASE 4: Plotting Results -> Totally Optional part for learning purpose
# ----------------------------

# print("\n[PHASE 4] Plotting detailed graphs...")

# plt.figure(figsize=(15,12))

# # Voltage
# plt.subplot(4,1,1)
# plt.plot(df_log["Time"], df_log["Voltage"], label="Voltage", color="blue")
# plt.scatter(df_log["Time"][df_log["Anomaly"]], df_log["Voltage"][df_log["Anomaly"]],
#             color="red", label="Anomaly", marker="x")
# plt.ylabel("Voltage (mV)")
# plt.title("Voltage vs Time with Anomalies")
# plt.legend()
# plt.grid(True)

# # Delta Voltage
# plt.subplot(4,1,2)
# plt.plot(df_log["Time"], df_log["DeltaVoltage"], label="Delta Voltage", color="green")
# plt.scatter(df_log["Time"][df_log["Anomaly"]], df_log["DeltaVoltage"][df_log["Anomaly"]],
#             color="red", marker="x")
# plt.ylabel("Delta Voltage (mV)")
# plt.title("Delta Voltage vs Time")
# plt.legend()
# plt.grid(True)

# # Noise
# plt.subplot(4,1,3)
# plt.plot(df_log["Time"], df_log["NoiseStd"], label="Noise StdDev", color="purple")
# plt.scatter(df_log["Time"][df_log["Anomaly"]], df_log["NoiseStd"][df_log["Anomaly"]],
#             color="red", marker="x")
# plt.ylabel("Noise StdDev")
# plt.title("Noise over Time")
# plt.legend()
# plt.grid(True)

# # Temperature
# plt.subplot(4,1,4)
# plt.plot(df_log["Time"], df_log["Temperature"], label="Temperature", color="orange")
# plt.scatter(df_log["Time"][df_log["Anomaly"]], df_log["Temperature"][df_log["Anomaly"]],
#             color="red", marker="x")
# plt.xlabel("Time (s)")
# plt.ylabel("Temp (°C)")
# plt.title("Temperature vs Time with Anomalies")
# plt.legend()
# plt.grid(True)

# plt.tight_layout()
# plt.show()