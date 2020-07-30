import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import seabreeze
from seabreeze.spectrometers import Spectrometer
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import laser_control
import random
import pandas as pd
import numpy as np
import threading
import time
import interface_config
if interface_config.ON_BBB:
	import Adafruit_BBIO.GPIO as GPIO # Adafruit library for safe GPIO control
else:
	from debug import DummyGPIO as GPIO
from testing_utils import generate_dummy_spectra


# laser = laser_control.Laser()

root = tk.Tk()
root.resizable(0, 0)
root.title("Spectrometer Tool")
matplotlib.use("TkAgg")

device_name = tk.StringVar()
device_name.set('No Device Detected')

int_time_entry = tk.StringVar()
int_time_entry.set("100000")
int_time = int(1E5)  # default integration time = 20us

trigger_mode_entry = tk.StringVar()
trigger_mode_entry.set('0')
trigger_mode = 0

collect_control = True  # enable collection controls
sample_control = True  # enable sampling controls
test_mode = False  # activate test mode
spec = None

spec_range = None
spec_intensity = None

max_intensity_var = tk.StringVar()
max_intensity_var.set('N/A')
integration_limits_var = tk.StringVar()
integration_limits_var.set('N/A')
pixel_var = tk.StringVar()
pixel_var.set('N/A')
sample_var = tk.StringVar()
sample_var.set('N/A')
dark_count_var = tk.IntVar()
dark_count_var.set(0)
sync_fire_var = tk.IntVar()
sync_fire_var.set(0)
devices = seabreeze.spectrometers.list_devices()


# laser control variables
pulse_options = {'Continuous', 'Single Shot', 'Burst'}
pulse_mode = tk.StringVar()
pulse_mode.set('Continuous')
rep_rate_control = tk.StringVar()
rep_rate_control.set('10')
resonator_temp_var = tk.StringVar()
resonator_temp_var.set('N/A')
power_options = {'Manual', 'Low Power', 'High Power'}
power_mode = tk.StringVar()
power_mode.set('Manual')
burst_count_var = tk.StringVar()
burst_count_var.set('1000')
diode_current_var = tk.StringVar()
diode_current_var.set(0.1)
diode_current_measurement_var = tk.StringVar()
diode_current_measurement_var.set('N/A')
pulse_width_var = tk.StringVar()
pulse_width_var.set('10')
diode_trigger_options = {'Internal', 'External'}
diode_trigger_var = tk.StringVar()
diode_trigger_var.set('Internal')


# laser status vars
status_var = tk.StringVar()
status_var.set('N/A')
fet_temp_var = tk.StringVar()
fet_temp_var.set('N/A')
bank_voltage_var = tk.StringVar()
bank_voltage_var.set('N/A')
safety_control = tk.IntVar()
safety_control.set(0)
bank_target_var = tk.StringVar()
bank_target_var.set('N/A')
fet_voltage_var = tk.StringVar()
fet_voltage_var.set('N/A')
fet_drop_var = tk.StringVar()
fet_drop_var.set('N/A')
fet_src_var = tk.StringVar()
fet_src_var.set('N/A')

fig = plt.Figure(figsize=(5, 5), dpi=100)
spectra_plot = fig.add_subplot(111)
spectra_plot.set_ylabel('Intensity')
spectra_plot.set_xlabel('Wavelength [nm]')
spectra_plot.set_title('Observed Emission Spectra')

emission_data = pd.DataFrame(data=None, columns=['Wavelength [nm]', 'Intensity'])


def update_plot():  # take a fresh sample from source
	global spec_range
	global spec_intensity
	global emission_data
	dark_spec = pd.DataFrame(data=None, columns=['Wavelength [nm]', 'Intensity'])
	if not devices:
		ref = messagebox.askyesno('ERROR', "Error: No device detected. \nUse Testing Data?")
		if ref:  # refresh with sample data
			emission_data = generate_dummy_spectra(central_spectra=(random.randint(300, 500), random.randint(500, 700),
												   random.randint(700, 900)))
			spectra_plot.clear()
			spectra_plot.set_ylabel('Intensity')
			spectra_plot.set_xlabel('Wavelength [nm]')
			spectra_plot.set_title('Observed Emission Spectra')
			spectra_plot.plot(emission_data.iloc[0:, 0], emission_data.iloc[0:, 1])
			canvas.draw()


	else:
		spec.trigger_mode(trigger_mode)  # set trigger mode
		spec.integration_time_micros(int_time)  # set integration_time
		emission_data = \
			pd.DataFrame(data=np.asarray([spec.wavelengths(), spec.intensities(correct_dark_counts = (dark_count_var.get() == 1))]).transpose(),
						 columns=['Wavelength [nm]', 'Intensity'])
		# filter data from under 300nm
		emission_data = emission_data[emission_data > 300]
		# update plot
		spectra_plot.clear()
		spectra_plot.set_ylabel('Intensity')
		spectra_plot.set_xlabel('Wavelength [nm]')
		spectra_plot.set_title('Observed Emission Spectra')
		spectra_plot.plot(emission_data.iloc[0:, 0], emission_data.iloc[0:, 1])

		canvas.draw()

		# update settings bar
		pixel_var.set(spec.pixels)
		integration_limits_var.set(spec.integration_time_micros_limits)
		max_intensity_var.set(emission_data['Intensity'].max())


def reconnect_device():
	global spec
	if seabreeze.spectrometers.list_devices():
		spec = seabreeze.spectrometers.Spectrometer.from_first_available()
		device_name.set(spec.serial_number)
	else:
		messagebox.showerror("ERROR", "ERROR: No Device Detected")


def save_settings():
	pass


def load_settings():
	pass


def export_plot():
	name = filedialog.asksaveasfilename(initialdir="./",
										title="Select file",
										filetypes=(("PNG", "*.png"), ("all files", "*.*")),
										defaultextension='.p')
	if name and name != '.p':
		fig.savefig(name)


def export_csv():
	global emission_data
	try:
		name = filedialog.asksaveasfilename(initialdir="./",
											title="Select file",
											filetypes=(("CSV data", "*.csv"), ("all files", "*.*")),
											defaultextension='.csv')
		if name:
			emission_data.to_csv(name, index=None, header=True)
		else:
			pass
	except ValueError:
		pass



# Laser code  __________________________________________________________________________________________________________

laser_on = False
def laser_switch():
	global laser_on
	if not laser_on:
		GPIO.output(interface_config.Laser_GPIO_pin, GPIO.LOW)  # set pin LOW to disable 48V converter, and thus the laser
		laser_onoff_switch['text'] = "Turn on laser"
	if laser_on:
		GPIO.output(interface_config.Laser_GPIO_pin, GPIO.HIGH)  # set pin LOW to disable 48V converter, and thus the laser
		laser_onoff_switch['text'] = "Turn off laser"
	laser_on = not laser_on


def editConstants():
	pulseMode = 0
	if pulse_mode.get() == "Continuous":
		pulseMode = 0
	elif pulse_mode.get() == "Single Shot":
		pulseMode = 1
	elif pulse_mode.get() == "Burst":
		pulseMode = 2

	powerMode = 0
	if power_mode.get() == 'Manual':
		powerMode = 0
	elif power_mode.get() == 'Low Power':
		powerMode = 1
	elif power_mode.get() == 'High Power':
		powerMode = 2

	diodeTrigger = 0
	if diode_trigger_var.get() == 'Internal':
		diodeTrigger = 0
	elif diode_trigger_var.get() == 'External':
		diodeTrigger = 1

	laser.editConstants(pulseMode, rep_rate_control.get(), burst_count_var.get(), diode_current_var.get(), powerMode,
						pulse_width_var.get(), diodeTrigger)


def arm_laser():
	editConstants()
	if laser.check_armed():
		laser.disarm()
	else:
		laser.arm()


def fire_laser():
	if sync_fire_var.get() == 1:
		threading.Thread(target=update_plot)
	time.sleep(.001)
	laser.fire_laser()




def emergency_stop():
	laser.emergency_stop()

def acquireData():
	while True:
		status_var.set(str(laser.get_status()))
		fet_temp_var.set(str(laser.fet_temp_check()))
		fet_voltage_var.set(str(laser.fet_voltage_check()))
		diode_current_var.set(str(laser.diode_current_check()))
		resonator_temp_var.set(str(laser.resonator_temp_check()))
		time.sleep(.01)


threading.Thread(target = acquireData).start()


# Spectrometer UI ______________________________________________________________________________________________________
if not devices:
	spectra_plot.plot(0, 0)
else:
	spec = seabreeze.spectrometers.Spectrometer.from_first_available()
	emission_data = \
		pd.DataFrame(data=np.asarray([spec.wavelengths(), spec.intensities()]).transpose(),
					 columns=['Wavelength [nm]', 'Intensity'])
	spectra_plot.plot(emission_data.iloc[0:, 0], emission_data.iloc[0:, 1])
	device_name.set(spec.serial_number)
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().grid(row=1, column=0, columnspan=2, rowspan=16)  # plot initial data

tk.Label(root, text="Connected Device:").grid(row=0, column=0)
tk.Label(root, textvariable=device_name, bg="White", relief=tk.GROOVE).grid(row=0, column=1, sticky="NSEW")

reconnect = tk.Button(root, text="Reconnect Device", command=reconnect_device)
reconnect.grid(row=0, column=2, columnspan=2, sticky="NSEW")
reconnect.config(state=tk.DISABLED)

tk.Label(text="Sampling Controls", relief=tk.GROOVE).grid(row=1, columnspan=2, column=2, sticky="NSEW")

tk.Label(root, text="Integration Time [μs]", relief=tk.GROOVE).grid(row=2, column=2, sticky="NSEW")
int_entry = tk.Entry(textvariable=int_time_entry, relief=tk.FLAT, bg="white")
int_entry.grid(row=2, column=3, sticky="NSEW")

tk.Label(root, text="Trigger Mode", relief=tk.GROOVE).grid(row=3, column=2, sticky="NSEW")
trigger_entry = tk.Entry(root, textvariable=trigger_mode_entry, relief=tk.FLAT, bg="white")
trigger_entry.grid(row=3, column=3, sticky="NSEW")

tk.Checkbutton(root, text="Dark Spectra Subtraction", variable=dark_count_var, relief=tk.FLAT)\
	.grid(row=4, column=2, sticky="NSEW")

tk.Checkbutton(root, text="Synchronize Laser", variable=sync_fire_var, relief=tk.FLAT)\
	.grid(row=4, column=3, sticky="NSEW")


refresh = tk.Button(root, text="Acquire Sample", command=update_plot)
refresh.grid(row=5, column=2, columnspan=2, sticky="NSEW")

tk.Label(root, text="Current Status", relief=tk.GROOVE).grid(row=6, column=2, columnspan=2, sticky="NSEW")

tk.Label(root, text="Max Intensity", relief=tk.GROOVE).grid(row=7, column=2, sticky="NSEW")
tk.Label(root, textvariable=max_intensity_var, bg='gray', relief=tk.FLAT).grid(row=7, column=3, sticky="NSEW")

tk.Label(root, text="Integration Bounds", relief=tk.GROOVE).grid(row=8, column=2, sticky="NSEW")
tk.Label(root, textvariable=integration_limits_var, bg='gray', relief=tk.FLAT).grid(row=8, column=3, sticky="NSEW")

tk.Label(root, text="Pixel Count", relief=tk.GROOVE).grid(row=9, column=2, sticky="NSEW")
tk.Label(root, textvariable=pixel_var, bg='gray', relief=tk.FLAT).grid(row=9, column=3, sticky="NSEW")

tk.Label(root, text="Sample Count", relief=tk.GROOVE).grid(row=10, column=2, sticky="NSEW")
tk.Label(root, textvariable=sample_var, bg='gray', relief=tk.FLAT).grid(row=10, column=3, sticky="NSEW")

img_button = tk.Button(root, text='Export Image', command=export_plot)
img_button.grid(row=11, column=2, columnspan=2, sticky="NSEW")

csv_button = tk.Button(root, text='Export CSV', command=export_csv)
csv_button.grid(row=12, column=2, columnspan=2, sticky="NSEW")




# laser control UI______________________________________________________________________________________________________




tk.Button(root, text=" ", state=tk.DISABLED).grid(row=0, column=4, rowspan=18, sticky="NSEW")  # divider
tk.Label(root, text="Laser Controls", relief=tk.FLAT).grid(row=0, column=5, columnspan=2, sticky="NSEW")

tk.Label(text="Pulse Control", relief=tk.GROOVE).grid(row=1, columnspan=2, column=5, sticky="NSEW")

tk.Label(text="Pulse Mode", relief=tk.GROOVE).grid(row=2, column=5, sticky="NSEW")
tk.OptionMenu(root, pulse_mode, *pulse_options).grid(row=2, column=6, sticky="NSEW")

tk.Label(text="Rep Rate", relief=tk.GROOVE).grid(row=3, column=5, sticky="NSEW")
tk.Entry(relief=tk.FLAT, bg="white", textvariable=rep_rate_control).grid(row=3, column=6, sticky="NSEW")

tk.Label(text="Burst Count", relief=tk.GROOVE).grid(row=4, column=5, sticky="NSEW")
tk.Entry(relief=tk.FLAT, bg="white", textvariable=burst_count_var).grid(row=4, column=6, sticky="NSEW")

tk.Label(text="Diode Settings", relief=tk.GROOVE).grid(row=5, column=5, columnspan=2, sticky="NSEW")

tk.Label(text="Diode Current", relief=tk.GROOVE).grid(row=6, column=5, sticky="NSEW")
tk.Entry(relief=tk.FLAT, bg="white", textvariable=diode_current_var).grid(row=6, column=6, sticky="NSEW")

tk.Label(text="Energy Mode", relief=tk.GROOVE).grid(row=7, column=5, sticky="NSEW")
tk.OptionMenu(root, power_mode, *power_options).grid(row=7, column=6, sticky="NSEW")

tk.Label(text="Diode Pulse Width", relief=tk.GROOVE).grid(row=8, column=5, sticky="NSEW")
tk.Entry(relief=tk.FLAT, bg="white", textvariable=pulse_width_var).grid(row=8, column=6, sticky="NSEW")

tk.Label(text="Diode Trigger", relief=tk.GROOVE).grid(row=9, column=5, sticky="NSEW")
tk.OptionMenu(root, diode_trigger_var, *diode_trigger_options).grid(row=9, column=6, sticky="NSEW")
# tk.OptionMenu(root, diode_trigger_var, *diode_trigger_options).grid(row=9, column=6, sticky="NSEW")

tk.Label(text="Laser Controls", relief=tk.GROOVE).grid(row=10, column=5, columnspan=2, sticky="NSEW")

tk.Label(text="Arm Laser", relief=tk.GROOVE).grid(row=11, column=5, sticky="NSEW")
arm = tk.Button(text='Arm', command = arm_laser)
arm.grid(row=11, column=6, sticky="NSEW")

tk.Label(text="Laser Status", relief=tk.GROOVE).grid(row=12, column=5, sticky="NSEW")
laser_status = tk.Label(textvariable=status_var, relief=tk.FLAT, bg='gray')
laser_status.grid(row=12, column=6, sticky="NSEW")


edit_constants = tk.Button(text = "Edit constants", command = editConstants)
edit_constants.grid(row=13, column=5, columnspan=2, rowspan=7, sticky="NSEW")

laser_onoff_switch = tk.Button(text='Turn on laser', bg='red', command = laser_switch)
laser_onoff_switch.grid(row=11, column=7, columnspan=2, rowspan=2, sticky="NSEW")

emergency_stop_control = tk.Button(text='Stop fire', bg='red', command = emergency_stop)
emergency_stop_control.grid(row=13, column=7, columnspan=2, rowspan=1, sticky="NSEW")

fire_control = tk.Button(text='Fire', bg='red', command = fire_laser)
fire_control.grid(row=14, column=7, columnspan=2, rowspan=1, sticky="NSEW")

tk.Label(root, text="Laser Status", relief=tk.FLAT).grid(row=0, column=7, columnspan=2, sticky="NSEW")

tk.Label(root, text="Thermals", relief=tk.GROOVE).grid(row=1, column=7, columnspan=2, sticky="NSEW")

tk.Label(root, text="Resonator [°C]", relief=tk.GROOVE).grid(row=2, column=7, sticky="NSEW")
tk.Label(root, textvariable=resonator_temp_var, bg="Gray", relief=tk.FLAT).grid(row=2, column=8, sticky="NSEW")

tk.Label(root, text="FET [°C]", relief=tk.GROOVE).grid(row=3, column=7, sticky="NSEW")
tk.Label(root, textvariable=fet_temp_var, bg="Gray", relief=tk.FLAT).grid(row=3, column=8, sticky="NSEW")

"""
Heaters are not used

heater_target_var = tk.StringVar()
heater_target_var.set('N/A')
tk.Label(root, text="Heater Target [°C]", relief=tk.GROOVE).grid(row=4, column=7, sticky="NSEW")
tk.Label(root, textvariable=heater_target_var, bg="Gray", relief=tk.FLAT).grid(row=4, column=8, sticky="NSEW")


heater_temp_var = tk.StringVar()
heater_temp_var.set('N/A')
tk.Label(root, text="Heater Temp", relief=tk.GROOVE).grid(row=5, column=7, sticky="NSEW")
tk.Label(root, textvariable=heater_temp_var, bg="Gray", relief=tk.FLAT).grid(row=5, column=8, sticky="NSEW")

"""

tk.Label(root, text="Voltage", relief=tk.GROOVE).grid(row=4, column=7, columnspan=2, sticky="NSEW")

# Unused
tk.Label(root, text="Bank Voltage", relief=tk.GROOVE).grid(row=5, column=7, sticky="NSEW")
tk.Label(root, textvariable=bank_voltage_var, bg="Gray", relief=tk.FLAT).grid(row=5, column=8, sticky="NSEW")

# Unused
tk.Label(root, text="Target Bank Voltage", relief=tk.GROOVE).grid(row=6, column=7, sticky="NSEW")
tk.Label(root, textvariable=bank_target_var, bg="Gray", relief=tk.FLAT).grid(row=6, column=8, sticky="NSEW")

tk.Label(root, text="FET Voltage", relief=tk.GROOVE).grid(row=7, column=7, sticky="NSEW")
tk.Label(root, textvariable=fet_voltage_var, bg="Gray", relief=tk.FLAT).grid(row=7, column=8, sticky="NSEW")

tk.Label(root, text="Diode Current", relief=tk.GROOVE).grid(row=8, column=7, sticky="NSEW")
tk.Label(root, textvariable=diode_current_measurement_var, bg="Gray", relief=tk.FLAT).grid(row=8, column=8, sticky="NSEW")

# Unused
fet_drain_var = tk.StringVar()
fet_drain_var.set('N/A')
tk.Label(root, text="FET Drain", relief=tk.GROOVE).grid(row=9, column=7, sticky="NSEW")
tk.Label(root, textvariable=fet_drain_var, bg="Gray", relief=tk.FLAT).grid(row=9, column=8, sticky="NSEW")

# Unused
tk.Label(root, text="FET Source", relief=tk.GROOVE).grid(row=10, column=7, sticky="NSEW")
tk.Label(root, textvariable=fet_src_var, bg="Gray", relief=tk.FLAT, width=10).grid(row=10, column=8, sticky="NSEW")


def update_integration_time(a, b, c):
	global int_time
	if not int_time_entry:
		int_entry.config(bg='red')
	else:
		try:
			t = int(int_time_entry.get())
			if t:
				int_time = t
				int_entry.config(bg="white")
			else:
				int_entry.config(bg="red")
		except ValueError:
			int_entry.config(bg="red")


def update_trigger_mode(a, b, c):
	global trigger_mode
	if not trigger_mode_entry:
		trigger_entry.config(bg='red')
	else:
		try:
			t = int(trigger_mode_entry.get())
			if t in range(0, 4):
				trigger_mode = t
				trigger_entry.config(bg='white')
			else:
				trigger_entry.config(bg='red')
		except ValueError:
			trigger_entry.config(bg='red')




trigger_mode_entry.trace_variable('w', update_trigger_mode)
int_time_entry.trace_variable('w', update_integration_time)
update_plot()

root.mainloop()
