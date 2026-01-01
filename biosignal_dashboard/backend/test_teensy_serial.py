"""Quick test script to verify Teensy serial communication."""

import serial
import time

PORT = "COM4"
BAUDRATE = 115200

print(f"Opening {PORT} at {BAUDRATE} baud...")

try:
    ser = serial.Serial(PORT, BAUDRATE, timeout=1.0)
    time.sleep(0.5)  # Wait for Teensy reset
    ser.reset_input_buffer()
    
    print("Port opened. Reading lines for 10 seconds...")
    print("=" * 50)
    
    start = time.time()
    count = 0
    gsr_count = 0
    ecg_count = 0
    
    while time.time() - start < 10:
        if ser.in_waiting:
            line = ser.readline()
            decoded = line.decode('ascii', errors='ignore').strip()
            if decoded:
                print(f"[{count:04d}] {decoded}")
                count += 1
                
                if ",GSR," in decoded:
                    gsr_count += 1
                elif ",ECG," in decoded:
                    ecg_count += 1
        else:
            time.sleep(0.01)
    
    print("=" * 50)
    print(f"Total lines: {count}")
    print(f"GSR samples: {gsr_count}")
    print(f"ECG samples: {ecg_count}")
    
    ser.close()
    print("Port closed.")
    
except serial.SerialException as e:
    print(f"Serial error: {e}")
except Exception as e:
    print(f"Error: {e}")
