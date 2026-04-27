# LST Project B: Integrating force measurement system for measuring muscle activity

## 1. Introduction and description

This project implements a force measurement system based on an 
Arduino microcontroller and the HX711 load cell amplifier. 
The system is designed to accurately measure muscle force produced 
during ankle dorsiflexion.

The project is part of a broader research effort investigating muscle 
activity using magnetomyography (MMG), 
where force data serves as a complementary measurement modality.

The system enables real-time acquisition and visualization of muscle force, 
allowing subjects to perform controlled trials with different force tracking tasks. 
It supports multiple predefined force paths, trial configurations and saving of 
results. This project includes code implementations in 

1. Arduino (Arduino IDE) for load cell calibration and data acquisition
2. Python for implementing measurement protocols and providing two different visualization paradigms

---
## 2. Hardware and wiring

All the components used are non-magentic, 
suited for the purposes of this project.

---

## 3. Software and files

The Project combines Arduino and Python components to handle data acquisition, processing, and visualization of force measurements.

### Arduino

**Calibration**
- ***Calibration.ino***  
 Script used to calibrate the load cell to measure weight in grams. It calculates
 the calibration factor using a known mass. This calibration factor is later required
 for converting raw sensor readings into accurate weight measurements.

**Measurement**
- ***Measurement.ino***  
  The main Arduino script. It reads data from the load cell using the HX711 module and
  converts it into weight using the calibration factor. Weight values are printed to the
  Serial Monitor, enabling communication with Python via serial. In addition, the script
  controls a 10-LED bar to visualize the applied force as a percentage of a predefined maximum value.

### Python

**maximum measurement**
- ***measure_max.py***  
  Script used to determine the subject’s maximum force output. It reads force data from the Arduino via
  serial communication, visualizes it in real time, and saves the data to a CSV file. The program supports 
  multiple trials and computes the maximum force as the highest 3-second moving average for each trial, as well
  as the overall maximum across all trials.

**general measurement**
- ***plot_force_moving_background.py***  
  Script for force tracking tasks with a moving (dynamic) background. It reads force data from the Arduino via serial
  communication, visualizes the subject’s force output in real time, and saves each trial to a CSV file. The target
  follows predefined patterns (e.g., square, triangle, trapezoid, sinusoidal), which the subject attempts to match during the task.

- ***plot_force_stationary_background.py***  
  Script for force tracking tasks with a fixed (stationary) background and a predefined trial duration. It reads force data from the Arduino
  via serial communication, visualizes the subject’s force output in real time, and saves each trial to a CSV file. The target follows predefined
  patterns (e.g., square, triangle, trapezoid, sinusoidal), which the subject attempts to match during the task.
---
## 4. Setup and Usage

---
## 14. Contributions

Oiva Kylmä
Teemu Hartikainen
Petra Häggqvist
Erin Karjalahti
Jenny Ruokolainen
Villa Mustajoki
---   

    
