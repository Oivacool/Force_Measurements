"""
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
separately in the output file. A target force profile (i.e., force tracking path) is displayed in the background (e.g., square wave, triangle,
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
import numpy as np


class Forceplot:

    def __init__(self, port: object, baud: object, filename, max_value) -> None:
        """
        Initialize Forceplot object for subject for real-time force measurement and visualization.

        Parameters
        ----------
        port : str
            Serial port connected to Arduino
        baud : int
            Baud rate for serial communication
        filename : str
            Output CSV file name for storing measurement data
        max_value : float
            Maximum force value used for scaling to percentage
        """

        # External resources
        self.ser = serial.Serial(port, baud, timeout=0.1)   # Open same serial port as in arduino
        self.filename = filename

        # Configuration
        self.maxLen = 500   # Describes the amount of datapoints shown
        self.max_value = max_value
        self.value_to_percent = 100.0 / self.max_value
        self.percent_to_value = 1 / self.value_to_percent

        # Data Buffers
        self.ax = deque(maxlen=self.maxLen)   # x-values shown
        self.ay = deque(maxlen=self.maxLen)   # y-values shown
        self.target_x = []
        self.target_y = []

        # State
        self.start_time = None  # Start time will be set when first valid datapoint arrives
        self.started = False
        self.ntrial = 0

        # Plot styling
        self.linewidth = 3
        self.color = 'red'

        # Serial setup
        self.ser.reset_input_buffer()

        # Textfile setup
        if not os.path.isfile(filename):
            self.create_datafile(filename)


    def add(self, deque_obj, val):
        """
        Adds a new value to the deque. If the deque is at max capacity, the oldest value is automatically removed.
        """

        deque_obj.append(val)


    def update(self, frameNum, line, ax, cursor_line):
        """
        Update function for real-time plotting. Reads force data from the serial connection, updates the plot,
        computes the corresponding target value, and writes the data to file.

        Parameters
        ----------
        frameNum : int
            Frame index (used by animation)
        line : matplotlib.lines.Line2D
            Line object for measured force
        ax : matplotlib.axes.Axes
            Plot axes
        cursor_line : matplotlib.lines.Line2D
            Vertical line indicating current time

        Returns
        -------
        tuple
            Updated line and cursor_line objects
        """

        if not self.started:
            return line, cursor_line

        value = self.ser.readline()
        if not value:
            return line, cursor_line

        try:
            value = float(value.strip())
            percent_value = value * self.value_to_percent
        except ValueError:
            return line, cursor_line

        # Setting start_time when first valid datapoint arrives
        if self.start_time is None:
            self.start_time = time.perf_counter()

        t = time.perf_counter() - self.start_time
        target_value = self.target_value(t) * self.percent_to_value # Get target value

        # Adding data to drawn line
        self.add(self.ax, t)
        self.add(self.ay, percent_value)
        line.set_data(self.ax, self.ay)

        # Writing data to file
        self.write_data(self.filename, t, value, target_value)

        if len(self.ax) >= 2:
            window = 50  # Length of the window
            center = self.ax[-1]
            ax.set_xlim(center - window / 2, center + window / 2)

        # Setting the cursor_line to current t value
        cursor_line.set_xdata([t, t])

        return line, cursor_line


    def start_measurement(self, line, cursor_line):
        """
        Start a new measurement trial. Resets buffers, initializes timing, increments trial count,
        and prepares plotting and file headers.

        Parameters
        ----------
        line : matplotlib.lines.Line2D
            Line object for measured force
        cursor_line : matplotlib.lines.Line2D
            Cursor line for current time
        """

        # Resetting values
        self.ax.clear()
        self.ay.clear()
        self.start_time = None
        self.started = True
        self.ntrial += 1

        # Serial setup
        self.ser.reset_input_buffer()

        line.set_data([], [])
        cursor_line.set_xdata([0, 0])
        cursor_line.set_color("cyan")

        # Adding headers to the CSV file
        self.create_headers(self.filename, self.ntrial)

        print("Measurement started")


    def wait_first_value(self, timeout_s=10.0):
        """
        Wait for the first valid numeric value from the Arduino.

        Parameters
        ----------
        timeout_s : float
            Maximum waiting time in seconds (default = 10)

        Returns
        -------
        float
            First valid force value
        """

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


    def target_value(self, t):
        """
        Interpolate target force value at given time.

        Parameters
        ----------
        t : float
            Time (seconds)

        Returns
        -------
        float
            Target force value at time t
        """

        if not self.target_x or not self.target_y:
            return 0.0

        if t < self.target_x[0] or t > self.target_x[-1]:
            return 0.0

        return float(np.interp(t, self.target_x, self.target_y))


    def add_target_segment(self, x, y):
        """
        Append a new target segment to the target profile.
        Ensures continuity between segments by removing duplicate points.

        Parameters
        ----------
        x : list
            Time values of the segment
        y : list
            Target force values of the segment
        """

        # initialize target profile in case no target profiles have been initialized
        if not self.target_x:
            self.target_x = list(x)
            self.target_y = list(y)
            return

        # Remove duplicate point in case new segment/shape starts from the same point that the previous ends
        if self.target_x[-1] == x[0] and self.target_y[-1] == y[0]:
            self.target_x.extend(x[1:])
            self.target_y.extend(y[1:])
        else:
            self.target_x.extend(x)
            self.target_y.extend(y)


    def plot_trap(self, ax, start=10, end=50, level=30, slope=3):
        """
        Plot a trapezoidal target force profile.
        """

        ramp_time = level / slope

        t1 = start
        t2 = start + ramp_time
        t3 = end - ramp_time
        t4 = end

        x = [t1, t2, t3, t4]
        y = [0, level, level, 0]

        self.add_target_segment(x, y)

        ax.plot(x, y, color=self.color, linewidth=self.linewidth, scalex=False, scaley=False, zorder=1)


    def plot_rect(self, ax, start=10, end=50, level=30):
        """
        Plot a rectangular target force profile.
        """

        t1 = start
        t2 = start
        t3 = end
        t4 = end

        x = [t1, t2, t3, t4]
        y = [0, level, level, 0]

        self.add_target_segment(x, y)

        ax.plot(x, y, color=self.color, linewidth=self.linewidth, scalex=False, scaley=False, zorder=1)


    def plot_triangle(self, ax, start=10, end=50, level=30):
        """
        Plot a triangular target force profile.
        """

        peak = (start + end) / 2

        x = [start, peak, end]
        y = [0, level, 0]

        self.add_target_segment(x, y)

        ax.plot(x, y, color=self.color, linewidth=self.linewidth, scalex=False, scaley=False, zorder=-1)


    def plot_square_sine(self, ax, start=10, end=50, slope=3):
        """
        Plot a sinusoidal square target force profile.
        """

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

        # Start ramp 0 -> 20
        ax.plot([start, wave_start], [0, base_level], color=self.color, linewidth= self.linewidth, scalex=False, scaley=False, zorder=1)

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

            ax.plot(x, y, color='red', linewidth=self.linewidth, scalex=False, scaley=False, zorder=1)

        # End ramp 20 -> 0
        ax.plot([start, end], [base_level, 0], color=self.color, linewidth=self.linewidth, scalex=False, scaley=False, zorder=1)


    def create_datafile(self, filename):
        """
        Create a new CSV datafile for subject.
        """

        with open(filename, "x") as csvfile:
            pass


    def create_headers(selfself, filename, ntrial):
        """
        Create a new CSV headers for a file
        """

        with open(filename, "a", newline="") as csvfile:
            try:
                writer = csv.writer(csvfile)
                writer.writerow([f"Trial_{ntrial}"])
                writer.writerow(["time", "force", "target_force"])
            except ValueError:
                pass


    def write_data(self, filename, t, value, target_value):
        """
        Write time, measured force, and target force (tracking path) to a CSV file.
        """

        with open(filename, "a", newline="") as csvfile:
            try:
                writer = csv.writer(csvfile)
                writer.writerow([round(t, 3), round(value, 3), round(target_value, 3)])
            except ValueError:
                pass


    def close(self):
        """
        Flushes and closes the serial connection.
        """

        self.ser.flush()
        self.ser.close()


def main():
    PORT = "/dev/cu.usbserial-D30JZCYI"   # Choose the Arduino port
    BAUD = 57600
    filename = ""   # User's filename
    max_value = 9861   # Measured maximum value in grams (g)

    # Initializing
    force_plot = Forceplot(PORT, BAUD, filename, max_value)
    force_plot.wait_first_value(timeout_s=8.0)

    print("Starting plotting")

    # Figure setup
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.set_ylim(0, 70)
    ax.set_xlim(-25, 25)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Percent(%)")

    # Plotting elements
    line, = ax.plot([], [], linewidth=3, zorder=2)

    cursor_line = ax.axvline(x=0, color='cyan', linestyle='--', linewidth=2)  # cursor_line shows the current point

    # Choosing measurement setup (sin_square, square, trapezoidal, triangle)
    force_plot.plot_square_sine(ax, start=10, end=70, slope=3)
    force_plot.plot_rect(ax, start=80, end=100)
    force_plot.plot_trap(ax, start=110, end=150)
    force_plot.plot_triangle(ax, start=160, end=200)

    # Animation
    anim = animation.FuncAnimation(
        fig,
        force_plot.update,
        fargs=(line, ax, cursor_line),
        interval=20
    )

    force_plot.anim = anim
    # Controlling
    def on_key(event):
        if event.key in (" ", "enter"):
            force_plot.start_measurement(line, cursor_line)

    fig.canvas.mpl_connect("key_press_event", on_key)

    # Initial draw
    plt.show(block=False)
    fig.canvas.draw()
    plt.pause(0.01)

    print("Click the figure window and press SPACE / ENTER to start...")
    plt.show()

    # Cleaning up
    force_plot.close()
    print('exiting.')


if __name__ == '__main__':
    main()

