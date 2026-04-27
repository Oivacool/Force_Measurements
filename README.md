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
2. Python for implementing measurement protocols and providing two distinct visualization paradigms

---
## 2. Hardware and wiring

All the components used are non-magentic, 
suited for the purposes of this project.

---

## 3. Software and files

The project is divided into Arduino and Python components, each responsible for a specific part of the force measuring system.

### Arduino

- **calibration.ino**  
  This script is used to calibrate the load cell to measure weight as grams. It calculates the calibration factor using a known mass. This calibration factor is later required for converting raw sensor readings into accurate weight measurements.

- **measurement.ino**  
  The main Arduino program. It reads data from the load cell using the HX711 module and converts it into weight using the calibration factor (defined using calibration.ino). Weigth values are printed to console to allow reading values in python code. In addition, the script controls a 10-LED bar to visualize the applied force as a percentage of a predefined maximum value of subject.

### Python

- **max_measurement.py**  
  This script is used to determine the maximum force value for a subject. The measured maximum is stored and later used as a reference for percentage calculations.

- **force_tasks.py**  
  This script is used for actual subject measurements. It guides the user through different force-related tasks (force plotting tasks), records the force data, and visualizes performance.

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

    
