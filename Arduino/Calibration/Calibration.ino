/*
   -------------------------------------------------------------------------------------
   HX711_ADC
   Arduino library for HX711 24-Bit Analog-to-Digital Converter for Weight Scales
   Olav Kallhovd sept2017
   -------------------------------------------------------------------------------------
*/

/*
   This is a simplified version of the original calibration example in HX711_ADC library. 
   The calibration value is printed to the Serial Monitor and must be manually copied into the main project.

   Calibration procedure:
   1. Remove all weight and tare the scale
   2. Place a known mass on the load cell (e.g. 100 g)
   3. Enter the mass value via Serial Monitor
   4. The program calculates and prints the calibration value
   5. Write down the calibration value to copy it to the actual Arduino script
*/

#include <HX711_ADC.h>

// pins:
const int HX711_dout = 3; // mcu > HX711 dout pin
const int HX711_sck = 2;  // mcu > HX711 sck pin

// HX711 constructor:
HX711_ADC LoadCell(HX711_dout, HX711_sck);

unsigned long t = 0;

void setup() {
  Serial.begin(57600);
  delay(10);
  Serial.println();
  Serial.println("Starting...");

  LoadCell.begin();
  // LoadCell.setReverseOutput(); // uncomment to turn a negative output value to positive

  unsigned long stabilizingtime = 2000;
  bool _tare = true;
  LoadCell.start(stabilizingtime, _tare);

  if (LoadCell.getTareTimeoutFlag() || LoadCell.getSignalTimeoutFlag()) {
    Serial.println("Timeout, check MCU > HX711 wiring and pin designations");
    while (1);
  } else {
    LoadCell.setCalFactor(1.0);
    Serial.println("Startup is complete");
  }

  while (!LoadCell.update());
  calibrate();
}

void loop() {
  static bool newDataReady = false;
  const int serialPrintInterval = 0;

  if (LoadCell.update()) newDataReady = true;

  if (newDataReady) {
    if (millis() > t + serialPrintInterval) {
      float i = LoadCell.getData();
      Serial.print("Load_cell output val: ");
      Serial.println(i);
      newDataReady = false;
      t = millis();
    }
  }
}

void calibrate() {
  Serial.println("***");
  Serial.println("Start calibration:");
  Serial.println("Place the load cell on a level stable surface.");
  Serial.println("Remove any load applied to the load cell.");
  Serial.println("Send 't' from serial monitor to set the tare offset.");

  bool resume = false;
  while (resume == false) {
    LoadCell.update();

    if (Serial.available() > 0) {
      char inByte = Serial.read();
      if (inByte == 't') {
        LoadCell.tareNoDelay();
      }
    }

    if (LoadCell.getTareStatus() == true) {
      Serial.println("Tare complete");
      resume = true;
    }
  }

  Serial.println("Now, place your known mass on the load cell.");
  Serial.println("Then send the weight of this mass (for example 100.0) from serial monitor.");

  float known_mass = 0;
  resume = false;

  while (resume == false) {
    LoadCell.update();

    if (Serial.available() > 0) {
      known_mass = Serial.parseFloat();
      if (known_mass != 0) {
        Serial.print("Known mass is: ");
        Serial.println(known_mass);
        resume = true;
      }
    }
  }

  LoadCell.refreshDataSet();
  float newCalibrationValue = LoadCell.getNewCalibration(known_mass);

  Serial.print("New calibration value has been set to: ");
  Serial.println(newCalibrationValue, 2);
  Serial.println("Use this as calibration value (calFactor) in your project sketch.");

  Serial.print("Example: LoadCell.setCalFactor(");
  Serial.print(newCalibrationValue, 2);
  Serial.println("f);");

  Serial.println("End calibration");
  Serial.println("***");
}