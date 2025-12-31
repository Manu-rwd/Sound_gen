# ECG Hub (`x_ecg`)

ECG acquisition module for Teensy AD8232 devices via serial connection.

## Features

- **ECGSerialClient**: Low-level serial parser for Teensy ECG output
- **ECGSource**: Chunked stream wrapper with `SensorSource` interface
- **Feature extraction**: Basic statistics (mean, std, min, max) and status flag counting
- **CLI**: Record ECG sessions to JSONL format

## Installation

```powershell
cd D:\Projects\Sound_Gen\x_ecg
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
```

## Usage

### CLI Session Recording

```powershell
python -m ecg_hub.cli.ecg_session `
  --port COM15 `
  --duration 60 `
  --chunk-size 64 `
  --output sessions\ecg_serial_60s.jsonl
```

**Arguments:**
- `--port`: Serial port (e.g., COM15)
- `--baudrate`: Baud rate (default: 115200)
- `--duration`: Recording duration in seconds
- `--chunk-size`: Number of samples per chunk
- `--output`: Output JSONL file path

### Supported Serial Formats

The parser accepts three formats from the Teensy:

1. **Full format**: `millis,ECG,value,status`
   - Example: `42016,ECG,4028,LOFF`

2. **Partial format**: `millis,ECG,value`
   - Example: `246268,ECG,4026`

3. **Raw format**: `value`
   - Example: `1933`

## Testing

Run all tests:

```powershell
pytest -v
```

Run specific test file:

```powershell
pytest -v tests/test_ecg_serial_client.py
```

## Output Format

JSONL output contains one JSON object per chunk:

```json
{
  "backend": "ecg_serial",
  "port": "COM15",
  "chunk_index": 0,
  "timestamp_start": 1.0,
  "timestamp_end": 1.256,
  "sample_count": 64,
  "features": {
    "mean": 2048.5,
    "std": 125.3,
    "min": 1800,
    "max": 2300
  },
  "status_summary": {
    "OK": 60,
    "LOFF": 4
  }
}
```

## Project Structure

```
x_ecg/
├── src/ecg_hub/
│   ├── interfaces.py           # StreamInfo, SensorSource
│   ├── acquisition/
│   │   ├── ecg_serial_client.py  # Low-level serial parser
│   │   └── ecg_source.py         # Chunked source wrapper
│   ├── features/
│   │   └── ecg_features.py       # Feature extraction
│   └── cli/
│       └── ecg_session.py        # CLI for session recording
├── tests/                      # Comprehensive test suite
├── sessions/                   # Output directory for JSONL files
└── pyproject.toml             # Package configuration
```

## Development

All phases follow a gated test approach - no advancement until tests are green.

**Phase checklist:**
1. ✅ Project skeleton
2. ✅ Shared interfaces
3. ✅ ECGSerialClient
4. ✅ ECGSource wrapper
5. ✅ Feature extraction
6. ✅ CLI implementation
7. ⏳ Real-hardware validation (requires Teensy device)
