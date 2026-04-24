"""
Maximum Force Measurement with Real-Time Plotting

Main Contributor:
- Oiva Kylmä
- Erin Karjalahti

Contributors and assistance:
- Petra Häggqvist
- Villa Mustajoki
- Jenny Ruokolainen

Description:
Reads force data from an Arduino via serial communication, visualizes it in real time,
and logs the data to a CSV file. The program supports multiple measurement trials. After each trial, it computes the
maximum force as the highest 3-second moving average of the signal, and stores both
the trial maximum and the overall maximum across all trials.

Usage:
- Change calibration value to arduino code
- Define the serial port (PORT) and baud rate (BAUD) to match the Arduino setup
- Set the output file name (filename)
- Press SPACE to start a trial (default duration: 15 s)

Requirements:
- Python3, pyserial, matplotlib, pandas
"""


import sys, serial
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import csv, os
import pandas as pd
import matplotlib
import numpy as np
from matplotlib.pyplot import legend


class Forceplot:

    def __init__(self, port: object, baud: object, filename) -> None:
        self.ser = serial.Serial(port, baud, timeout=0.1)  # open same serial port as in arduino
        self.filename = filename    # User datafile name
        self.max_value = 0

        # start with EMPTY list
        self.ax = [] # x-values shown
        self.ay = [] # y-values shown

        self.start_time = None  # start time will be set when first valid datapoint arrives
        self.started = False

        self.end_time = 15
        self.anim = None
        self.ntrial = 0 # calculating number of trials

        # clear serial buffer so old data doesn't affect start
        self.ser.reset_input_buffer()

        # initalize text file and get the write trial number
        if not os.path.isfile(self.filename):
            self.create_datafile(self.filename)
        else:
            self.ntrial, self.max_value = self.initialize_from_file(self.filename)


    # add to array
    def add(self, array, val):
        array.append(
            val)  # Adds newest value to the end of list

    # update plot
    def update(self, frameNum, line, ax, cursor_line):

        if self.max_value != 0:
            self.max_line.set_ydata([self.max_value, self.max_value])
            self.max_line.set_visible(True)

        if not self.started:
            return line, cursor_line

        measured_value = self.ser.readline()
        if not measured_value:
            return line, cursor_line

        try:
            measured_value = float(measured_value.strip())
        except ValueError:
            return line, cursor_line

        # set start_time when first valid datapoint arrives
        if self.start_time is None:
            self.start_time = time.perf_counter()

        t = time.perf_counter() - self.start_time
        # adding data to drawn line (persentage value)
        self.add(self.ax, t)
        self.add(self.ay, measured_value)
        line.set_data(self.ax, self.ay)

        # write data to file (actual value)
        self.write_data(self.filename, t, measured_value)

        # set the cursor_line to current t value
        cursor_line.set_xdata([t, t])

        # stopping measurement when cursor arrives to the end
        if t >= self.end_time - 0.01:
            cursor_line.set_xdata([self.end_time, self.end_time])
            cursor_line.set_color("green")
            print(f"Measurement Trial {self.ntrial} finished")
            self.started = False
            # calculating maximum value (trial maximum)
            if self.ntrial != 0:
                trial_max = self.calculate_max(self.ntrial)
                self.write_max_forces(self.filename, trial_max, self.max_value)
                # draw line for trial maximum
                self.max_trial_line.set_ydata([trial_max, trial_max])
                self.max_trial_line.set_visible(True)


        return line, cursor_line

    def calculate_max(self, ntrial):
        # calculating maximum value
        trial_max = calculate_3s_maximum_mean(self.filename, ntrial)

        if trial_max > self.max_value:
            self.max_value = trial_max

        print("trial_max", trial_max)
        print("total_max", self.max_value)

        return trial_max

    def restart_measurement(self, line, cursor_line):
        # reset values
        self.ax.clear()
        self.ay.clear()

        self.start_time = None
        self.started = True
        self.ntrial += 1

        self.ser.reset_input_buffer()

        line.set_data([], [])
        cursor_line.set_xdata([0, 0])
        cursor_line.set_color("cyan")
        line.figure.canvas.draw_idle()
        # hide trial_max_line
        self.max_trial_line.set_visible(False)
        # add headers to the CSV file
        self.create_headers(self.filename, self.ntrial)

        print(f"Measurement Trial {self.ntrial} started")

    def wait_first_value(self, timeout_s=10.0):
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            raw = self.ser.readline()
            if not raw:
                continue
            try:
                v = float(raw.strip())
                return v
            except ValueError:
                continue
        raise TimeoutError("No valid data from Arduino (check baud/port/Arduino code).")
        # clean up

    def close(self):
        # calculating last maximum value
        self.calculate_max(self.ntrial)
        # close serial
        self.ser.flush()
        self.ser.close()

    def write_data(self, filename, t, measured_value):
        with open(filename, "a", newline="") as csvfile:
            try:
                writer = csv.writer(csvfile)
                writer.writerow([round(t, 3), round(measured_value, 3)])
            except ValueError:
                pass

    def create_datafile(self, filename):
        with open(filename, "x") as csvfile:
            pass

    def create_headers(self, filename, ntrial):
        # creates headers including trial and time and force but not the max force at the end of the file
        with open(filename, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([f"Trial_{ntrial}"])
            writer.writerow(["time", "force"])


    def write_max_forces(self, filename, trial_max, total_max):
        #writes trial maximum an d total maximum
        with open(filename, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["max_force_trial", round(trial_max, 3)])
            writer.writerow(["max_force_total", round(total_max, 3)])

    def initialize_from_file(self, filename):
        max_trial = 0
        max_value = 0

        try:
            with open(filename, "r") as f:
                for line in f:
                    line = line.strip()

                    if line.startswith("Trial_"):
                        try:
                            trial_num = int(line.split("_")[1])
                            if trial_num > max_trial:
                                max_trial = trial_num
                        except:
                            pass

                    elif line.startswith("max_force_total"):
                        try:
                            parts = line.split(",")
                            value = float(parts[1])
                            if value > max_value:
                                max_value = value
                        except:
                            pass

        except FileNotFoundError:
            return 0, 0

        return max_trial, max_value


def calculate_3s_maximum_mean(filename, trial_number):
    # calculate maximum for current trial
    trials = []
    current_trial = []

    with open(filename, "r") as f:
        for line in f:
            line = line.strip()

            # uusi trial alkaa
            if line.startswith("Trial_"):
                if current_trial:
                    trials.append(current_trial)
                    current_trial = []
                continue

            if not line:
                continue

            current_trial.append(line)

        if current_trial:
            trials.append(current_trial)

    # check if trial excists
    if trial_number < 1 or trial_number > len(trials):
        raise ValueError

    trial_lines = trials[trial_number - 1]

    # header + data
    header = trial_lines[0].split(",")
    rows = [row.split(",") for row in trial_lines[1:]]

    df = pd.DataFrame(rows, columns=header)

    # numeromuunnokset
    df["time"] = pd.to_numeric(df["time"], errors="coerce")
    df["force"] = pd.to_numeric(df["force"], errors="coerce")

    df = df.dropna(subset=["time", "force"])

    df["time"] = pd.to_timedelta(df["time"], unit="s")
    df = df.set_index("time")

    df = df.sort_index()

    # Rolling 3-second average force
    rolling_avg = df["force"].rolling("3s", min_periods=1).mean()

    # Peak 3-second average
    peak_3s_avg_force = rolling_avg.max()

    print(f"Trial {trial_number} peak 3s average force: {peak_3s_avg_force:.2f}")
    return peak_3s_avg_force


def main():
    PORT = "/dev/cu.usbserial-D30JZCYI"  # Choose the arduino port
    BAUD = 57600
    filename = "max_example_Villa.csv"
    # plot parameters
    force_plot = Forceplot(PORT, BAUD, filename)  # create plotting object
    # wait for the first value
    force_plot.wait_first_value(timeout_s=8.0)

    print("starting plotting")

    # set up animation
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.set_ylim(0, 15000)
    ax.set_xlim(0, force_plot.end_time)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Mass (g)")

    #drawing 5s area for measurement
    #ax.axvline(x=5, color='red', linestyle='--', linewidth=2)
    #ax.axvline(x=10, color='red', linestyle='--', linewidth=2)
    #ax.axvspan(5, 10, alpha=0.15, color='red')

    #drawing maxline
    force_plot.max_line = ax.axhline(y=0, color='green', linestyle='-', linewidth=2, label="Total max")
    force_plot.max_line.set_visible(False)

    # drawing trial maxline
    force_plot.max_trial_line = ax.axhline(y=0, color='orange', linestyle='--', linewidth=2, label="Trial max")
    force_plot.max_trial_line.set_visible(False)

    line, = ax.plot([], [], linewidth=3, zorder=2)
    cursor_line = ax.axvline(x=0, color='cyan', linestyle='--', linewidth=2)  # cursor_line showing the current point
    # show legends
    ax.legend()

    anim = animation.FuncAnimation(
        fig,
        force_plot.update,
        fargs=(line, ax, cursor_line),
        interval=20
    )
    force_plot.anim = anim

    def on_key(event):
        if event.key == " ":
            force_plot.restart_measurement(line, cursor_line)

    fig.canvas.mpl_connect("key_press_event", on_key)

    plt.show(block=False)

    # draw plot with force paths
    fig.canvas.draw()
    plt.pause(0.01)


    plt.show()
    # clean up
    force_plot.close()
    print('exiting.')

# call main
if __name__ == '__main__':
    main()
