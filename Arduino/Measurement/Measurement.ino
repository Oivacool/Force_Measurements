/*
   -------------------------------------------------------------------------------------
   HX711_ADC
   Arduino library for HX711 24-Bit Analog-to-Digital Converter for Weight Scales
   Olav Kallhovd sept2017
   -------------------------------------------------------------------------------------
*/

/*
   This program reads data from a load cell using the HX711 module,
   converts the measured value into weight using calibration factor (CAL_FACTOR)
   which is determined using Calibration script. The weight is then converted into
   a percentage of a predefined maximum value, and the load level is displayed using a 10-LED bar.
   Weight values are also printed to the Serial Monitor, allowing integration with Python code for visualization.

   Main Contributors:
   Oiva Kylmä
   Teemu Hartikainen
   Petra Häggqvist

   Functionality:
   - Initializes and tares the load cell at startup
   - Reads weight continuously
   - Converts weight to percentage of SAVED_MAX_VALUE
   - Lights LEDs based on percentage thresholds
   - Prints measured weight to Serial Monitor

   Setup:
   - Set CAL_FACTOR using a separate calibration sketch
   - Set SAVED_MAX_VALUE to the desired maximum weight (in grams)

   LED behavior:
   - Each LED represents a threshold level of load
   - More LEDs turn on as the measured weight increases
*/

#include <HX711_ADC.h>

// Setting Pins
const uint8_t HX711_dout = 3;
const uint8_t HX711_sck  = 2;

// LED bar 
const uint8_t LED_COUNT = 10;
const uint8_t ledPins[LED_COUNT] = {4, 5, 6, 7, 8, 9, 10, 11, 12, 13};

// LoadCell HX711
HX711_ADC LoadCell(HX711_dout, HX711_sck);

// EDIT HERE! Initializing values
const float CAL_FACTOR = 1.0f;       // set calibration value  
const float SAVED_MAX_VALUE = 2500.0f;  // set maximum value (g)


// Functions 
//  Controls LED states based on input percentage.
// Compares percent to predefined thresholds and turns LEDs on/off accordingly.
static inline void updateLedsFromPercent(float percent) {
  const float thresholds[LED_COUNT] = {5, 10, 15, 20, 22.5, 25, 27.5, 30, 40, 50};
  for (uint8_t i = 0; i < LED_COUNT; i++) {
    digitalWrite(ledPins[i], (percent >= thresholds[i]) ? HIGH : LOW);
  }
}

// Convert measurement value to percentage relative to maximum value (SAVED_MAX_VALUE).
static inline float toPercent(float value) {
  if (SAVED_MAX_VALUE <= 0.0f) return 0.0f;
  float p = 100.0f * (value / SAVED_MAX_VALUE);
  if (p < 0.0f) p = 0.0f;
 
  return p;
}

void setup() {
  Serial.begin(57600);
  delay(10);

  // LED init (optional)
  for (uint8_t i = 0; i < LED_COUNT; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW);
  }

  // HX711 init + tare
  LoadCell.begin();

  // adjust plot reactivity (how many samples are averaged)
  // Using minimal averaging: effectively takes median of 3 samples (filters noise but reacts fast)
  LoadCell.setSamplesInUse(1);

  LoadCell.start(2000, true); // 2s sstabilizing + tare (zero value)

  if (LoadCell.getTareTimeoutFlag() || LoadCell.getSignalTimeoutFlag()) {
    // wiring error, so stop (no prints, so Python stays clean)
    while (1) { }
  }

  // Set calibration value
  LoadCell.setCalFactor(CAL_FACTOR);

  // wait first valid update
  while (!LoadCell.update()) {}
}

void loop() {

  if (LoadCell.update()) {

    float value = LoadCell.getData();      

    float percent = toPercent(value);       

    updateLedsFromPercent(percent);         

    Serial.println(value, 2);              
  }
}
