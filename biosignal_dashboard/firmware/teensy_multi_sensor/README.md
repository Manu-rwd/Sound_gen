# Teensy 4.1 Multi-Sensor Firmware

Firmware for Teensy 4.1 that outputs labeled GSR and ECG data for the Biosignal Dashboard.

## Output Format

```
millis,GSR,value
millis,ECG,value,STATUS
```

Example:
```
12345,GSR,2555
12349,ECG,4028,OK
12353,ECG,4031,OK
12365,GSR,2560
12369,ECG,4025,LO
```

## Wiring (Your Setup)

| Component | Teensy 4.1 Pin |
|-----------|----------------|
| GSR SIG | 14 (A0) |
| GSR VCC | 3.3V |
| GSR GND | GND |
| ECG OUTPUT | 15 (A1) |
| ECG 3.3V | 3.3V |
| ECG SDN | 3.3V |
| ECG LO+ | 1 |
| ECG LO- | 2 |
| ECG GND | GND |

## Upload Instructions

1. **Open Arduino IDE** (with Teensyduino installed)
2. **Open**: `File → Open → teensy_multi_sensor.ino`
3. **Select board**: `Tools → Board → Teensy 4.1`
4. **Select USB type**: `Tools → USB Type → Serial`
5. **Upload**: Click Upload (→), press button on Teensy if prompted

## Verify

Open Serial Monitor at 115200 baud. You should see:
```
12345,GSR,2555
12349,ECG,4028,OK
```

## Status Codes

- `OK` - ECG leads connected properly
- `LO` - Leads off (electrodes not attached or poor contact)
