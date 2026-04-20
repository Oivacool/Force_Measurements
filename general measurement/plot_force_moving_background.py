"""
STILL MISSING WRITING TARGET VALUE AND FILE INITIALIZATION SO COMPARE TO STATIONARY VERSION

Trial force measurement with real-time plotting using moving background and target guidance

Main Contributors:
Oiva Kylmä

Contributors and assistance:
Erin Karjalahti
Petra Häggqvist
Teemu Hartikainen

Description:
Reads force data from an Arduino via serial communication, visualizes it in real time using moving background, and
logs the data to a CSV file.The program supports multiple measurement trials. Each trial is started manually and stored
separately in the output file. A target force profile is displayed in the background (e.g., square wave, triangle,
trapezoid, sinusoidal), allowing the subject to follow a predefined force pattern during the measurement.

Usage:
- Change calibration value to arduino code
- Define the serial port (PORT) and baud rate (BAUD) to match the Arduino setup
- Set the output file name (filename)
- Define the maximum force value (max_value) for each subject (g)
- Press SPACE to start a trial (default is continuous measurement until SPACE to start new trial)

Requirements:
Python3, pyserial, matplotlib, numpy, collections
"""


import sys, serial
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import csv, os
import matplotlib


class Forceplot:

    def __init__(self, port: object, baud: object) -> None:
        self.ser = serial.Serial(port, baud, timeout=0.1)  # open same serial port as in arduino
        self.maxLen = 500  # describes the amount of datapoints shown

        # start with EMPTY deques
        self.ax = deque(maxlen=self.maxLen)  # x-values shown
        self.ay = deque(maxlen=self.maxLen)

        self.start_time = None  # start time will be set when first valid datapoint arrives

        # clear serial buffer so old data doesn't affect start
        self.ser.reset_input_buffer()
        self.started = False

        #initialize plotting variables
        self.linewidth = 20
        self.color = 'red'

    # add to deque object
    def add(self, object, val):
        object.append(val)  # newest values goes to the right and deque object deletes automatically oldest value if full

    # update plot
    def update(self, frameNum, line, ax, cursor_line):
        if not self.started:
            return line, cursor_line

        value = self.ser.readline()
        if not value:
            return line, cursor_line

        try:
            value = float(value.strip())
        except ValueError:
            return line, cursor_line

        # set start_time when first valid datapoint arrives
        if self.start_time is None:
            self.start_time = time.perf_counter()

        t = time.perf_counter() - self.start_time
        # adding data to drawn line
        self.add(self.ax, t)
        self.add(self.ay, value)
        line.set_data(self.ax, self.ay)

        # write data to file
        self.write_data("measurement_example.csv",t,value) # Specify user datafile name

        if len(self.ax) >= 2:
            window = 50  # length of the showing window
            center = self.ax[-1]
            ax.set_xlim(center - window / 2, center + window / 2)
        # set the cursor_line to current t value
        cursor_line.set_xdata([t,t])

        return line, cursor_line

    def plot_trap(self, ax, start=10, end=50, level=30, slope=3):
        # start= start time for rect, end = end time for rect,
        ramp_time = level / slope

        t1 = start
        t2 = start + ramp_time
        t3 = end - ramp_time
        t4 = end

        x = [t1, t2, t3, t4]
        y = [0, level, level, 0]

        ax.plot(x, y, color=self.color, linewidth=self.linewidth, scalex=False, scaley=False, zorder=1)

    def plot_rect(self, ax, start=10, end=50, level=30):
        # start= start time for rect, end = end time for rect,

        t1 = start
        t2 = start
        t3 = end
        t4 = end

        x = [t1, t2, t3, t4]
        y = [0, level, level, 0]

        ax.plot(x, y, color=self.color, linewidth=self.linewidth, scalex=False, scaley=False, zorder=1)
    #ax.legend()

    def plot_triangle(self, ax, start=10, end=50, level=30):

        peak = (start + end) / 2

        x = [start, peak, end]
        y = [0, level, 0]

        ax.plot(x, y, color=self.color, linewidth=self.linewidth, scalex=False, scaley=False, zorder=-1)

    def plot_square_sine(self, ax, start=10, end=50, slope=3):
        base_level = 20
        top_level = 30
        pulse_height = top_level - base_level  # 10%
        pulse_count = 4

        ramp_base_time = base_level / slope

        wave_start = start + ramp_base_time
        wave_end = end - ramp_base_time
        wave_time = wave_end - wave_start

        cycle = wave_time / pulse_count

        ramp_pulse_time = pulse_height / slope

        if 2 * ramp_pulse_time >= cycle:
            ramp_pulse_time = cycle / 2
            top_flat = 0
            base_flat = 0
        else:
            flat_total = cycle - 2 * ramp_pulse_time
            top_flat = flat_total / 2
            base_flat = flat_total / 2

        # start ramp 0 -> 20
        ax.plot([start, wave_start], [0, base_level], color=self.color, linewidth=3, scalex=False, scaley=False, zorder=1)

        start = wave_start

        for i in range(pulse_count):
            t1 = start
            t2 = start + ramp_pulse_time
            t3 = t2 + top_flat + (top_flat * 1/pulse_count)
            t4 = t3 + ramp_pulse_time
            t5 = t4 + base_flat

            if i == (pulse_count - 1):
                x = [t1, t2, t3, t4]
                y = [base_level, top_level, top_level, base_level]
                start = t4
            else:
                x = [t1, t2, t3, t4, t5]
                y = [base_level, top_level, top_level, base_level, base_level]
                start = t5

            ax.plot(x, y, color='red', linewidth=3, scalex=False, scaley=False, zorder=1)

        # end ramp 20 -> 0
        ax.plot([start, end], [base_level, 0], color=self.color, linewidth=3, scalex=False, scaley=False, zorder=1)

    def start_measurement(self, line, cursor_line):
        self.ax.clear()
        self.ay.clear()
        self.start_time = None
        self.started = True

        self.ser.reset_input_buffer()

        line.set_data([], [])
        cursor_line.set_xdata([0, 0])
        cursor_line.set_color("cyan")
        print("Measurement started")

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
        # close serial
        self.ser.flush()
        self.ser.close()

    def write_data(self, filename, t, value):
        if not os.path.isfile(filename):
            self.create_datafile(filename)

        with open("measurement_example.csv", "a", newline="") as csvfile:
            try:
                writer = csv.writer(csvfile)
                writer.writerow([t, float(value)])
            except ValueError:
                pass

    def create_datafile(self, filename):
        with open(filename, "x") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["time_s", "force"])

def main():
    PORT = "/dev/cu.usbserial-D30JZCYI"  # Choose the arduino port
    BAUD = 57600

    # plot parameters
    force_plot = Forceplot(PORT, BAUD)  # create plotting object
    # wait for the first value
    force_plot.wait_first_value(timeout_s=8.0)

    print("starting plotting")

    # set up animation
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.set_ylim(0, 70)
    ax.set_xlim(-25, 25)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Percent(%)")

    line, = ax.plot([], [], linewidth=3, zorder=2)
    cursor_line = ax.axvline(x=0, color='cyan', linestyle='--', linewidth=2) #cursor_line showing the current point

    # choose correct measurement setup (triangle, sin, square/hold)
    force_plot.plot_square_sine(ax, start=10, end=70, slope=3)
    force_plot.plot_rect(ax, start=80, end=100)
    force_plot.plot_trap(ax, start=110, end=150)
    force_plot.plot_triangle(ax, start=160, end=200)

    anim = animation.FuncAnimation(
        fig,
        force_plot.update,
        fargs=(line, ax, cursor_line),
        interval=20
    )

    def on_key(event):
        if event.key in (" ", "enter"):
            force_plot.start_measurement(line, cursor_line)

    fig.canvas.mpl_connect("key_press_event", on_key)

    # draw empty plot
    plt.show(block=False)
    fig.canvas.draw()
    plt.pause(0.01)
    
    # waiting for button to be pressed
    print("click the figure window and press SPACE / ENTER to start...")

    plt.show()

    # clean up
    force_plot.close()
    print('exiting.')


# call main
if __name__ == '__main__':
    main()

