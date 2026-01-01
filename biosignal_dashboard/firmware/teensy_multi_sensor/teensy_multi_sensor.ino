/*
 * Teensy 4.1 Multi-Sensor Firmware
 * Outputs both GSR and ECG data with labels for the Biosignal Dashboard
 * 
 * Output format:
 *   millis,GSR,value
 *   millis,ECG,value,STATUS
 * 
 * Hardware Wiring:
 *   - GSR SIG → Pin 14 (A0)
 *   - ECG OUTPUT → Pin 15 (A1)
 *   - ECG LO+ → Pin 1
 *   - ECG LO- → Pin 2
 *   - Both GND → Teensy GND
 *   - GSR VCC → Teensy 3.3V
 *   - ECG 3.3V + SDN → Teensy 3.3V
 * 
 * Baud rate: 115200
 */

// ============ PIN CONFIGURATION FOR TEENSY 4.1 ============
const int GSR_PIN = 14;          // A0 - GSR SIG
const int ECG_PIN = 15;          // A1 - ECG OUTPUT (AD8232)
const int ECG_LO_PLUS_PIN = 1;   // ECG LO+ (leads off detection)
const int ECG_LO_MINUS_PIN = 2;  // ECG LO- (leads off detection)

// Sampling rates (approximate)
const int GSR_SAMPLE_INTERVAL_MS = 20;   // ~50 Hz for GSR
const int ECG_SAMPLE_INTERVAL_MS = 4;    // ~250 Hz for ECG

// Enable/disable sensors (set to false if sensor not connected)
const bool ENABLE_GSR = true;
const bool ENABLE_ECG = true;
// ===========================================================

unsigned long lastGSRSample = 0;
unsigned long lastECGSample = 0;

void setup() {
  Serial.begin(115200);
  
  // Wait for serial connection (optional, for debugging)
  // while (!Serial) { delay(10); }
  
  // Configure GSR pin
  if (ENABLE_GSR) {
    pinMode(GSR_PIN, INPUT);
  }
  
  // Configure ECG pins
  if (ENABLE_ECG) {
    pinMode(ECG_PIN, INPUT);
    pinMode(ECG_LO_PLUS_PIN, INPUT);
    pinMode(ECG_LO_MINUS_PIN, INPUT);
  }
  
  // Initial delay for sensor stabilization
  delay(500);
  
  // Print header for debugging (comment out for production)
  // Serial.println("Teensy Multi-Sensor Started");
  // Serial.println("Format: millis,LABEL,value[,status]");
}

void loop() {
  unsigned long now = millis();
  
  // ===== GSR Sampling =====
  if (ENABLE_GSR && (now - lastGSRSample >= GSR_SAMPLE_INTERVAL_MS)) {
    lastGSRSample = now;
    
    int gsrValue = analogRead(GSR_PIN);
    
    // Output: millis,GSR,value
    Serial.print(now);
    Serial.print(",GSR,");
    Serial.println(gsrValue);
  }
  
  // ===== ECG Sampling =====
  if (ENABLE_ECG && (now - lastECGSample >= ECG_SAMPLE_INTERVAL_MS)) {
    lastECGSample = now;
    
    // Check leads-off detection
    bool loPlus = digitalRead(ECG_LO_PLUS_PIN);
    bool loMinus = digitalRead(ECG_LO_MINUS_PIN);
    
    int ecgValue = analogRead(ECG_PIN);
    
    // Determine status
    const char* status;
    if (loPlus || loMinus) {
      status = "LO";  // Leads off
    } else {
      status = "OK";
    }
    
    // Output: millis,ECG,value,STATUS
    Serial.print(now);
    Serial.print(",ECG,");
    Serial.print(ecgValue);
    Serial.print(",");
    Serial.println(status);
  }
}
