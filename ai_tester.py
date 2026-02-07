import socket
import struct
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import time
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

UDP_IP = "127.0.0.1"
UDP_PORT = 5000

# Setup UDP Socket (Same as before)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("=================================================")
print("       AI-BASED HIL ANOMALY DETECTOR             ")
print("=================================================")

# --- PHASE 1: DATA COLLECTION ---
print("\n[PHASE 1] LEARNING NORMAL BEHAVIOR...")
print("Please leave the Mock Sensor running normally.")
print("Collecting 200 samples (approx 20 seconds)...")

training_data = []

while len(training_data) < 200:
    data, addr = sock.recvfrom(1024)
    if len(data) == 13:
        can_id, dlc, payload = struct.unpack("<IB8s", data)
        volt_hi, volt_lo, temp, status = payload[0], payload[1], payload[2], payload[3]
        voltage = (volt_hi << 8) | volt_lo
        
        # Store for training: [Voltage, Temp]
        training_data.append([voltage, temp])
        
        # Progress Bar
        if len(training_data) % 20 == 0:
            print(f"--> Captured {len(training_data)}/200 samples...")

print("[PHASE 1] COMPLETE. Data Collected.")

# --- PHASE 2: MODEL TRAINING ---
print("\n[PHASE 2] TRAINING AI MODEL...")
df = pd.DataFrame(training_data, columns=['Voltage', 'Temp'])

# Isolation Forest: Unsupervised Anomaly Detection
# contamination=0.01 means we assume 99% of training data is 'clean'
model = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
model.fit(df)

print("Model Trained! Baseline established.")
print(f"Normal Voltage Range: {df['Voltage'].min()}mV - {df['Voltage'].max()}mV")
print(f"Normal Temp Range:    {df['Temp'].min()}C - {df['Temp'].max()}C")

# --- PHASE 3: LIVE MONITORING ---
print("\n[PHASE 3] LIVE AI MONITORING (Ctrl+C to stop)")
print("Waiting for data...")

try:
    while True:
        data, addr = sock.recvfrom(1024)
        if len(data) == 13:
            can_id, dlc, payload = struct.unpack("<IB8s", data)
            voltage = (payload[0] << 8) | payload[1]
            temp = payload[2]

            # Prepare for AI (Must be 2D array)
            live_sample = [[voltage, temp]]
            
            # Predict: 1 = Normal, -1 = Anomaly
            prediction = model.predict(live_sample)[0]
            
            # Formatting
            status_text = "✅ OK" if prediction == 1 else "⚠️ ANOMALY DETECTED!"
            color_code = "\033[92m" if prediction == 1 else "\033[91m" # Green vs Red
            reset_code = "\033[0m"

            print(f"{color_code}[{status_text}] Voltage: {voltage}mV | Temp: {temp}C{reset_code}")

except KeyboardInterrupt:
    print("\nSystem Halted.")