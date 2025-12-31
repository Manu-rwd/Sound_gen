import serial
import time

s = serial.Serial('COM4', 115200, timeout=2)
time.sleep(0.5)  # Let it stabilize

print("Reading 10 sample lines from Teensy:")
for i in range(10):
    line = s.readline().decode("ascii", errors="ignore").strip()
    print(f"Line {i+1}: {line}")

s.close()
