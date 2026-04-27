"""
Trial force measurement with real-time plotting using stationary background and target guidance

Main Contributors:
Petra Häggqvist
Oiva Kylmä

Contributors and assistance:
Erin Karjalahti

Description:
Reads force data from an Arduino microcontroller via serial communication, visualizes it in real time using stationary background, and
logs the data into a CSV file.The program supports multiple measurement trials. Each trial is started manually and stored
separately in the output file. A target force profile (i.e., force tracking path) is displayed in the background (e.g., square wave, triangle,
trapezoid, sinusoidal), allowing the subject to follow a predefined force pattern during the measurement.

Usage:
- Change calibration value in the Arduino code
- Define the serial port (PORT) and baud rate (BAUD) to match the Arduino setup
- Set the output filename (filename)
- Define the maximum force value (max_value) for each subject (g)
- Press SPACE to start a trial (default duration: 65 s)
- Press SPACE again to restart a trial

Requirements:
Python3, pyserial, matplotlib, numpy
"""


import sys, serial
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
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
        self.ser = serial.Serial(port, baud, timeout=0.1)  # Open same serial port as in Arduino
        self.filename = filename

        # Configuration
        self.maxLen = 500
        self.max_value = max_value  # Describes the amount of datapoints shown
        self.value_to_percent = 100.0 / self.max_value
        self.percent_to_values = 1 / self.value_to_percent
        self.end_time = 65

        # Data buffers
        self.ax = []  # x-values shown
        self.ay = []  # y-values shown
        self.target_x = []
        self.target_y = []

        # State
        self.start_time = None  # Start time will be set when first valid datapoint arrives
        self.started = False
        self.anim = None
        self.ntrial = 0

        # Plot styling
        self.linewidth = 3
        self.color = 'red'

        # Serial setup
        self.ser.reset_input_buffer()

        # Textfile setup
        if not os.path.isfile(self.filename):
            self.create_datafile(self.filename)


    def add(self, array, val):
        """
        Adds a new value to the end of the array.
        """

        array.append(val)


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

        measured_value = self.ser.readline()
        if not measured_value:
            return line, cursor_line

        try:
            measured_value = float(measured_value.strip())
            percent_value = measured_value * self.value_to_percent  # Changing value to percent
        except ValueError:
            return line, cursor_line

        # Setting start_time when first valid datapoint arrives
        if self.start_time is None:
            self.start_time = time.perf_counter()

        t = time.perf_counter() - self.start_time
        target_value = self.target_value(t) * self.percent_to_values  # Get target value

        # Adding data to drawn line (percentage value)
        self.add(self.ax, t)
        self.add(self.ay, percent_value)
        line.set_data(self.ax, self.ay)

        # Writing data to file (actual value)
        self.write_data(self.filename, t, measured_value, target_value)

        # Setting the cursor_line to current t value
        cursor_line.set_xdata([t, t])

        # Stopping measurement when the cursor arrives to the end
        if t >= self.end_time - 0.01:
            cursor_line.set_xdata([self.end_time, self.end_time])
            cursor_line.set_color("green")
            print("Measurement finished")
            self.started = False

        return line, cursor_line


    def restart_measurement(self, line, cursor_line):
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
        line.figure.canvas.draw_idle()

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

        self.add_target_segment(x,y)

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

        self.add_target_segment(x,y)

        ax.plot(x, y, color=self.color, linewidth=self.linewidth, scalex=False, scaley=False, zorder=1)


    def plot_triangle(self, ax, start=10, end=50, level=30):
        """
        Plot a triangular target force profile.
        """

        peak = (start + end) / 2

        x = [start, peak, end]
        y = [0, level, 0]

        self.add_target_segment(x,y)

        ax.plot(x, y, color=self.color, linewidth=self.linewidth, scalex=False, scaley=False, zorder=-1)


    def plot_square_sine(self, ax, start=10, end=50, slope=3):
        """
        Plot a sinusoidal square target force profile.
        """
        # Profile shape parameters (in percent of max force)
        base_level = 20
        top_level = 30
        pulse_height = top_level - base_level  # 10%
        pulse_count = 3

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
        start_x = [start, wave_start]
        start_y = [0, base_level]
        self.add_target_segment(start_x, start_y)
        ax.plot(start_x, start_y, color=self.color, linewidth=3, scalex=False, scaley=False, zorder=1)

        start = wave_start

        for i in range(pulse_count):
            t1 = start
            t2 = start + ramp_pulse_time
            t3 = t2 + top_flat + (top_flat * 1 / pulse_count)
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

            # Adding segment to target
            self.add_target_segment(x, y)

            ax.plot(x, y, color='red', linewidth=3, scalex=False, scaley=False, zorder=1)

        # End ramp 20 -> 0
        end_x = [start, end]
        end_y = [base_level, 0]
        self.add_target_segment(end_x, end_y)
        ax.plot(end_x, end_y, color=self.color, linewidth=3, scalex=False, scaley=False, zorder=1)


    def create_datafile(self, filename):
        """
        Create a new CSV datafile for subject.
        """

        with open(filename, "x") as csvfile:
            pass


    def create_headers(self, filename, ntrial):
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


    def write_data(self, filename, t, measured_value, target_value):
        """
        Write time, measured force, and target force (tracking path) to a CSV file.
        """

        with open(filename, "a", newline="") as csvfile:
            try:
                writer = csv.writer(csvfile)
                writer.writerow([round(t, 3), round(measured_value, 3), round(target_value, 3)])
            except ValueError:
                pass


    def close(self):
        """
        Flushes and closes the serial connection.
        """

        self.ser.flush()
        self.ser.close()


def main():
    PORT = "COM3"  # Choose the Arduino port
    BAUD = 57600
    filename = "measurement_example_Villa.csv"  # User's filename
    max_value = 9861  # Measured maximum value in grams (g)

    # Initializing
    force_plot = Forceplot(PORT, BAUD, filename, max_value)
    force_plot.wait_first_value(timeout_s=8.0)

    print("Starting plotting")

    # Figure setup
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.set_ylim(0, 70)
    ax.set_xlim(0, force_plot.end_time)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Percent (%)")

    # Plotting elements
    line, = ax.plot([], [], linewidth=3, zorder=2)

    cursor_line = ax.axvline(x=0, color='cyan', linestyle='--', linewidth=2)  # cursor_line shows the current point

    # Choosing measurement setup (sin_square, square, trapezoidal, triangle)
    force_plot.plot_square_sine(ax, start=10, end=60, slope=3)
    #force_plot.plot_rect(ax, start=80, end=100)
    #force_plot.plot_trap(ax, start=10, end=40, level=20, slope=4)
    #force_plot.plot_triangle(ax, start=40, end=60)

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
        if event.key == " ":
            force_plot.restart_measurement(line, cursor_line)

    fig.canvas.mpl_connect("key_press_event", on_key)

    # Showing plot
    plt.show(block=False)
    fig.canvas.draw()
    plt.pause(0.01)
    plt.show()

    # Cleaning up
    force_plot.close()
    print('Exiting.')


if __name__ == '__main__':
    main()