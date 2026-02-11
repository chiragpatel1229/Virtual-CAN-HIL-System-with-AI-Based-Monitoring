## 📊 Example Results & Validation Data

The system collects detailed time-series data during live monitoring.

**Generated file:** `logs/live_monitoring_log.csv`

**Columns:**
- `Time` – seconds since monitoring start
- `Voltage` – battery voltage in mV
- `DeltaVoltage` – voltage change since last sample
- `NoiseStd` – rolling standard deviation of voltage (noise indicator)
- `Temperature` – temperature in °C
- `Anomaly` – boolean (true = Isolation Forest flagged anomaly)

**Purpose:**
- Allows post-analysis of AI detection performance
- Shows correlation between injected faults and detected anomalies
- Used to generate plots (voltage trend, delta, noise, temperature)

**Sample content preview (first few rows):**

```csv
Time,Voltage,DeltaVoltage,NoiseStd,Temperature,Anomaly
0.0,3300,0,2.45,45,False
0.1,3312,12,2.78,45,False
0.2,3305,-7,3.12,45,False
...
299.9,100,-3200,18.45,45,True