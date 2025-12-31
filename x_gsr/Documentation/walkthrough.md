# GSR Hub Module - Implementation Walkthrough

## Summary

Successfully implemented the **x_gsr** module for GSR (Galvanic Skin Response) data acquisition from Teensy devices via serial communication at `D:\Projects\Sound_Gen\x_gsr`.

## Project Structure Created

```text
D:\Projects\Sound_Gen\x_gsr
├─ .venv/                          # Virtual environment
├─ pyproject.toml                  # Package configuration
├─ src/
│   └─ gsr_hub/
│       ├─ __init__.py
│       ├─ acquisition/
│       │   ├─ __init__.py
│       │   ├─ interfaces.py       # StreamInfo, SensorSource Protocol
│       │   ├─ gsr_serial_client.py # Low-level Teensy serial reader
│       │   └─ gsr_source.py       # SensorSource wrapper
│       ├─ features/
│       │   ├─ __init__.py
│       │   └─ gsr_features.py     # Feature extraction (mean, std, min, max)
│       └─ cli/
│           ├─ __init__.py
│           └─ gsr_session.py      # CLI for recording sessions
└─ tests/
    ├─ __init__.py
    ├─ test_interfaces.py
    ├─ test_gsr_serial_client.py
    ├─ test_gsr_source.py
    ├─ test_gsr_features.py
    └─ test_gsr_session_cli.py
```

---

## Components Implemented

### 1. Core Interfaces ([interfaces.py](file:///D:/Projects/Sound_Gen/x_gsr/src/gsr_hub/acquisition/interfaces.py))

- **StreamInfo** dataclass: Metadata for sensor streams (name, type, channel_count, nominal_srate, source_id)
- **SensorSource** Protocol: Generic interface with `connect()`, `start()`, `next_chunk()`, `stop()`, `close()`, `stream_info`

### 2. Serial Client ([gsr_serial_client.py](file:///D:/Projects/Sound_Gen/x_gsr/src/gsr_hub/acquisition/gsr_serial_client.py))

- **GSRSample** dataclass: Holds device timestamp, host timestamp, and raw value
- **GSRSerialClient**: Parses `millis,GSR,value` format from Teensy serial stream

### 3. GSRSource ([gsr_source.py](file:///D:/Projects/Sound_Gen/x_gsr/src/gsr_hub/acquisition/gsr_source.py))

- Wraps GSRSerialClient with SensorSource interface
- Returns chunks of samples with timestamps

### 4. Feature Extraction ([gsr_features.py](file:///D:/Projects/Sound_Gen/x_gsr/src/gsr_hub/features/gsr_features.py))

- Computes `gsr_mean`, `gsr_std`, `gsr_min`, `gsr_max` from sample chunks

### 5. CLI Session Runner ([gsr_session.py](file:///D:/Projects/Sound_Gen/x_gsr/src/gsr_hub/cli/gsr_session.py))

- Records GSR sessions to JSONL format
- Includes stream metadata, features, and timestamps

---

## Test Results

**22 tests passed** across 6 test files:

| Test File | Tests | Status |
|-----------|-------|--------|
| test_interfaces.py | 3 | ✅ All pass |
| test_gsr_serial_client.py | 7 | ✅ All pass |
| test_gsr_source.py | 4 | ✅ All pass |
| test_gsr_features.py | 5 | ✅ All pass |
| test_gsr_session_cli.py | 3 | ✅ All pass |

---

## Usage

### Recording a GSR Session

```powershell
cd D:\Projects\Sound_Gen\x_gsr
.\.venv\Scripts\activate

python -m gsr_hub.cli.gsr_session `
  --port COM15 `
  --duration 60 `
  --chunk-size 64 `
  --output sessions\gsr_serial_60s.jsonl
```

### JSONL Output Format

Each line in the output file contains:

```json
{
  "t_start": 1735577545.123,
  "t_end": 1735577546.456,
  "stream": {
    "name": "Teensy-GSR",
    "type": "GSR",
    "channel_count": 1,
    "nominal_srate": 50.0,
    "source_id": "gsr_serial"
  },
  "features": {
    "gsr_mean": 1500.0,
    "gsr_std": 50.0,
    "gsr_min": 1400.0,
    "gsr_max": 1600.0
  },
  "now_playing": null,
  "extra": {
    "backend": "gsr_serial",
    "port": "COM15",
    "chunk_index": 0
  }
}
```

---

## Hardware Requirements

For real hardware testing:

1. Teensy running a sketch that outputs: `millis,GSR,value` (e.g., `43534,GSR,2555`)
2. Close any Serial Monitor holding the port
3. Identify the COM port (e.g., `COM15`)
