#!/usr/bin/python3
"""
libs_cli.py

This is a command line interface to run a minimal LIBS test using an OceanOptics FLAMT-T spectrometer and a 1064nm MicroJewel laser. This code is designed to be
run on a BeagleBone Black.

"""
import struct
import pathlib
import readline
from argparse import ArgumentParser
import time
import pickle
import platform
import serial
import binascii

import seabreeze
seabreeze.use('cseabreeze') # Select the cseabreeze backend for consistency
from seabreeze.spectrometers import Spectrometer
from seabreeze.cseabreeze._wrapper import SeaBreezeError

if platform.system() == "Linux":
    import Adafruit_BBIO.GPIO as GPIO
else:
    from gpio_spoof import DummyGPIO as GPIO # This is for debugging purposes

from ujlaser.lasercontrol import Laser, LaserCommandError

running = True
verbose = False
spectrometer = None
laser = None

external_trigger_pin = "P8_26"
devices = []

command_log = None # File handle to the log file that we will store list of command queries
SD_CARD_PATH = './sample/'  # needs to be set before testing
LOG_PATH = "logs/"
SAMPLES_PATH = "samples/"

def check_spectrometer(spec, complain=True):
    """Helper function that prints an error message if the spectrometer has not been connected yet. Returns True if the spectrometer is NOT connected."""
    global devices
    if devices != []:
        is_open = devices[0].is_open
        if is_open:
            return False
    if complain:
        print_cli("!!! This command requires the spectrometer to be connected! Use 'spectrometer connect' first!")
    return True

def check_laser(laser, complain=True):
    """Helper function that prints an error message if the laser has not been connected yet. Returns True if the laser is NOT connected."""
    if laser == None:
        if complain:
            print_cli("!!! This command requires the laser to be connected! Use 'laser connect' first!")
        return True
    return False

def dump_settings_register(spec):
    print_cli("... Dumping settings register:")
    for i in (b'\x00', b'\x04', b'\x08', b'\x0C', b'\x10', b'\x14', b'\x18', b'\x28', b'\x2C', b'\x38', b'\x3C', b'\x40', b'\x48', b'\x50', b'\x54', b'\x74', b'\x78', b'\x7C', b'\x80'):
        spec.f.raw_usb_bus_access.raw_usb_write(struct.pack(">ss",b'\x6B',i),'primary_out')
        output = spec.f.raw_usb_bus_access.raw_usb_read(endpoint='primary_in', buffer_length=3)
        print_cli((binascii.hexlify(i)).decode("ascii") + "\t" + (binascii.hexlify(output[1:])).decode("ascii"))

def query_settings(spec):
    print_cli("Querying Spectrometer Settings...")
    spec.f.raw_usb_bus_access.raw_usb_write(struct.pack(">s",b'\xFE'),'primary_out')
    output = spec.f.raw_usb_bus_access.raw_usb_read(endpoint='primary_in', buffer_length=16)
    pixel_count, integration_time, lamp_enable, trigger_mode, spectral_status, spectra_packets, power_down, packet_count, comm_speed = struct.unpack(">HI?BcB?BxxBx", output) 
    print_cli("Pixel Count: " + str(pixel_count))
    print_cli("Integration_time: " + str(integration_time))
    print_cli("Lamp Enable: " + str(lamp_enable))
    print_cli("Trigger Mode: " + str(trigger_mode))
    print_cli("Spectrum Status: " + str(spectral_status))
    print_cli("Spectra packets: " + str(spectra_packets))
    print_cli("Power Down Flags: " + str(power_down))
    print_cli("Packet Count: " + str(packet_count))
    print_cli("USB Speed: " + str(comm_speed))

def set_trigger_delay(spec, t):
    """Sets the trigger delay of the spectrometer. Can be from 0 to 32.7ms in increments of 500ns. t is in microseconds"""
    t_nano_seconds = t * 1000 #convert micro->nano seconds
    t_clock_cycles = t//500 # number of clock cycles to wait. 500ns per clock cycle b/c the clock runs at 2MHz
    data = struct.pack("<ssH",b'\x6A',b'\x28',t_clock_cycles)
    spec.f.raw_usb_bus_access.raw_usb_write(data,'primary_out')
    # self.spec.f.spectrometer.set_delay_microseconds(t)
    
def set_external_trigger_pin(pin):
    """Sets the GPIO pin to use for external triggering."""
    global external_trigger_pin
    GPIO.setup(pin, GPIO.OUT)
    external_trigger_pin = pin

def auto_connect_spectrometer():
    """Use seabreeze to autodetect and connect to a spectrometer. Returns a Spectrometer object on success, None otherwise"""
    global devices

    if devices == []:
        devices = seabreeze.spectrometers.list_devices()
    if devices != []:
        try:
            spec = seabreeze.spectrometers.Spectrometer(devices[0])
            print_cli("*** Found spectrometer, serial number: " + spec.serial_number)
            return spec
        except SeaBreezeError as e:
            print_cli("!!! " + str(e))
        except:
            print_cli("Unknown Error")
    print_cli("!!! No spectrometer autodetected!")

    # if seabreeze.spectrometers.list_devices():
    #     spec = seabreeze.spectrometers.Spectrometer.from_first_available()
    #     print_cli("*** Found spectrometer, serial number: " + spec.serial_number)
    #     return spec
    # else:
    #     print_cli("!!! No spectrometer autodetected!")

def set_sample_mode(spec, mode):
    """Sets the spectrometer sampling trigger to the specified mode."""
    i = None
    # TODO: Verify that these are the correct modes. The datasheets are vague.
    # ^ should be correct for the seabreeze library v1.1.0 (at least 0 and 3 should be which are the ones that matter)
    if mode == "NORMAL":
        i = 0
    elif mode == "EXT_LEVEL":
        i = 1
    elif mode == "EXT_SYNC":
        i = 2
    elif mode == "EXT_EDGE":
        i = 3

    try:
        spec.trigger_mode(i)
        print_cli("*** Spectrometer trigger mode set to " + mode + " (" + str(i) + ")")
        return True
    except SeaBreezeError as e:
        print_cli("!!! " + str(e))
        print_cli("!!! Spectrometer does not support mode number " + str(i) + " (" + mode + ")!")
        return False

def set_integration_time(spec, time):
    """Sets the integration time of the spectrometer. Returns True on success, False otherwise."""
    spec.integration_time_micros(time)
    print_cli("*** Integration time set to " + str(time) + " microseconds.")
    return True

def do_sample(spec, pin):
    """Sets the GPIO pin to high and stores the data from integration."""
    GPIO.output(pin, GPIO.LOW)
    time.sleep(0.01)  # delay for spectrum, can be removed or edited if tested
    GPIO.output(pin, GPIO.HIGH)
    wavelengths, intensities = spec.spectrum()
    timestamp = str(time.time())  # gets time immediately after integrating
    data = wavelengths, intensities
    with open(SAMPLES_PATH + str(timestamp) + "_SAMPLE.pickle", 'ab') as file:
        pickle.dump(data, file)

# Takes a sample from the spectrometer without the laser firing
def get_spectrum(spec):
    wavelengths, intensities = spec.spectrum()
    timestamp = time.time()
    timestamp = str(timestamp)
    data = wavelengths, intensities
    filename = "SAMPLE_" + timestamp + ".pickle"
    f = input("Save sample as [" + filename + "]:")
    log_input(f)
    if f != "":
        filename = f
    with open("samples/" + filename, 'ab') as file:
        pickle.dump(data, file)
    #save_sample_csv("samples/" + filename, wavelengths, intensities)

def load_data(filename):
    """Prints the data in files. Not added in yet"""
    with open(SD_CARD_PATH+filename, 'rb') as file:
        data = pickle.load(file)
        print_cli(data)

def save_sample_csv(filename, wavelengths, intensities):
    debug_log("Saving sample as CSV: " + filename + "; len(wavelengths) = " + len(wavelengths) + ", len(intensities) = " + len(intensities))
    with open(filename, "w") as f:
        f.write("Wavelengths,Intensities\n")
        for i in range(0,len(wavelengths)):
                f.write(str(wavelengths)+","+str(intensities)+"\n")
        f.close()

def user_select_port():
    ports = serial.tools.list_ports.comports()
    if len(ports) == 0:
        print_cli("No serial ports detected!")
        return
    print_cli("\t0) Cancel")
    for i,p in enumerate(ports):
        print_cli("\t" + str(i+1) + ") " + str(p))

    try:
        i = input("Select a port or 0 to cancel: ")
        log_input(i)
        i = int(i)
    except ValueError:
        i = -1

    if i == 0:
         return
    if i < 0 or i > len(ports):
         print_cli("Invalid entry, please try again.")
         return user_select_port()
    else:
         return ports[i-1].device

def give_status(spec, l):
    """Prints out a status report of the spectrometer and laser. Also saves the report to a file"""
    s = "Status at: " + str(time.time()) + "\n"
    
    if check_spectrometer(spec, False):
        s += "Spectrometer is not connected.\n"
    else:
        s += "Spectrometer\n\t"
        s += "Model-ID:\n\t"
        s += "Spectrometer:\n\t"
        s += "Sample Mode:\n"
    
    s + "\n"
    if check_laser(l, False):
        s += "Laser is not connected.\n"
    else:
        s += "Laser:\n"
        s += str(l.get_status())

    cli_print(s)

# Please use the below function when printing to the command line. This will both print to the command line and print it to the log file.
def cli_print(txt):
    global command_log
    command_log.write(str(int(time.time())) + ">: " + txt + "\n")
    print(txt)

# This is a helper function because I'm REALLY lazy and don't feel like getting Python's runtime errors. I know this is an atrocity. Not sorry.
def print_cli(txt):
    cli_print(txt)

# Print to the log file. Will print to CLI if verbose mode is enabled.
def debug_log(txt):
    global command_log, verbose
    command_log.write(str(time.time()) + "D:" + txt + "\n")
    if verbose:
        print("D: " + txt)

# Writes user input/commands to the command log file.
def log_input(txt):
    global command_log
    command_log.write(str(int(time.time())) + "?:" + txt + "\n")

def command_loop():
    global running, spectrometer, laser, external_trigger_pin
    while running:
        c = input("?").strip() # Get a command from the user and remove any extra whitespace
        log_input("?" + c)
        parts = c.split() # split the command up into the command and any arguments
        
        if c == "help": # check to see what command we were given
            give_help()

        elif c == "spectrometer spectrum":
            if check_spectrometer(spectrometer):
                continue
            get_spectrum(spectrometer)
 
        elif c == "spectrometer dump_registers":
            if check_spectrometer(spectrometer):
                continue
            dump_settings_register(spectrometer)

        elif c == "spectrometer query_settings":
            if check_spectrometer(spectrometer):
                continue
            query_settings(spectrometer)

        elif parts[0:3] == ["spectrometer","set","trigger_delay"]:
            if check_spectrometer(spectrometer):
                continue
            if len(parts) < 4:
                print_cli("!!! Invalid command: Set Trigger Delay command expects at least 1 argument.")
                continue
            try:
                t = int(parts[3]) # t is the time in microseconds to delay
                set_trigger_delay(spectrometer, t)
            except ValueError:
                print_cli("!!! Invalid argument: Set Trigger Delay command expected an integer.")
                continue

        elif parts[0:3] == ["spectrometer","set","integration_time"]:
            if check_spectrometer(spectrometer):
                continue
            if len(parts) < 4:
                print_cli("!!! Invalid command: Set Integration Time command expects at least 1 argument.")
                continue
            try:
                t = int(parts[3])
                set_integration_time(spectrometer, t)
            except ValueError:
                print_cli("!!! Invalid argument: Set Integration Time command expected an integer!")
                continue
            except SeaBreezeError as e:
                print_cli("!!! " + str(e))
                continue

        elif parts[0:3] == ["spectrometer","set","sample_mode"]:
            if check_spectrometer(spectrometer):
                continue
            if len(parts) < 4:
                print_cli("!!! Invalid command: Set Sample Mode command expects at least 1 argument.")
                continue

            if parts[3] == "NORMAL" or parts[3] == "EXT_LEVEL" or parts[3] == "EXT_SYNC" or parts[3] == "EXT_EDGE":
                set_sample_mode(spectrometer, parts[3])
            else:
                print_cli("!!! Invalid argument: Set Sample Mode command expected one of: NORMAL, EXT_SYNC, EXT_LEVEL, EXT_EDGE")
                continue

        elif c == "status":
            give_status(spectrometer, laser)
            continue

        elif parts[0:4] == ["set","external_trigger_pin"]:
            if len(parts) < 3:
                print_cli("!!! Invalid command: Set external trigger pin command expects at least 1 argument.")
                continue
            try:
                pin = parts[2]
                if not pin.startswith("P8_") or pin.startswith("P9_"):
                    raise ValueError("Invalid pin!")
                set_external_trigger_pin(spectrometer, pin)
                external_trigger_pin = pin
            except:
                cli_print("!!! " + pin + " is not a valid pin name! Should follow format such as: P8_22 or P9_16 (these are examples).")
                continue

        elif c == "get external_trigger_pin":
            print_cli("External trigger pin is set to: " + external_trigger_pin)
            continue

        elif parts[0:3] == ["spectrometer","connect"]:
            if len(parts) == 2:
                spectrometer = auto_connect_spectrometer()
            elif len(parts) == 3:
                spectrometer = connect_spectrometer(parts[2])

        elif c == "laser connect":
            port = user_select_port()
            if not port:
                cli_print("!!! Aborting connect laser.")
                continue
            laser = Laser()
            laser.connect(port)
            s = laser.get_status()
            cli_print("Laser Status:")
            cli_print("ID: " + laser.get_laser_ID() + "\n")
            cli_print(str(s))

        elif c == "laser arm":
            if check_laser(laser):
                continue
            if laser.arm():
                print_cli("*** Laser ARMED")

        elif c == "laser disarm":
            if check_laser(laser):
                continue
            if laser.disarm():
                print_cli("*** Laser DISARMED")

        elif c == "laser status":
            if check_laser(laser):
                print_cli("Laser is not connected.")
                continue
            s = laser.get_status()
            print_cli(str(s))

        elif c == "laser fire":
            if check_laser(laser):
                continue
            print_cli("Being implemented") #TODO

        elif parts[0:3] == ["laser","set","rep_rate"]: # TODO: Add check to see if this is within the repetition rate.
            if check_laser(laser):
                continue
            
            if len(parts) < 4:
                print_cli("!!! Set Laser Rep Rate expects an integer argument!")
                continue
            try:
                rate = int(parts[3])
                if rate < 0:
                    raise ValueError("Repetition Rate must be positive!")
                laser.set_rep_rate(rate)
            except ValueError:
                print_cli("!!! Set Laser Rep Rate expects a positive integer argument! You did not enter an integer.")
                continue
            except LaserCommandError as e:
                print_cli("!!! Error encountered while commanding laser! " + str(e))
                continue
                
        elif parts[0:3] == ["laser","set","pulse_width"]:
            if check_laser(laser):
                continue
                
            if len(parts) < 4:
                print_cli("!!! Set Laser Pulse Width expects an integer argument!")
                continue
            try:
                width = float(parts[3])
                laser.set_pulse_width(width)
            except ValueError:
                print_cli("!!! Set Laser Pulse Width expects an integer argument! You did not enter an integer.")
                continue
            except LaserCommandError as e:
                print_cli("!!! Error encountered while commanding laser! " + str(e))
                continue

        elif parts[0:3] == ["laser","set","energy_mode"]:
            if check_laser(laser):
                continue
            if len(parts) < 4:
                print_cli("!!! Set Laser Energy Mode expects one of: LOW, HIGH, or MANUAL!")
                continue
            
            m = -1
            if parts[3] == "MANUAL":
                m = 0
            elif parts[3] == "LOW":
                m = 1
            elif parts[3] == "HIGH":
                m = 2
            else:
                print_cli("!!! Set Laser Energy Mode expects one of: LOW, HIGH, or MANUAL!")
                continue
            try:
                laser.set_energy_mode(m)
                print_cli("Set Laser energy mode to " + parts[3])
                continue
            except LaserCommandError as e:
                print_cli("!!! Error while commanding laser! " + str(e))
                continue

        elif parts[0:3] == ["laser","get","fet_temp"]:
            if check_laser(laser):
                continue
            t = laser.get_fet_temp()
            print_cli("Laser FET temperature: " + str(t))

        elif c == "do_libs_sample":
            if check_laser(laser) or check_spectrometer(spectrometer):
                continue
            try:
                do_sample(spectrometer, external_trigger_pin)
            except SeaBreezeError as e:
                print_cli("!!! " + str(e))
                continue
            except LaserCommandError as e:
                print_cli("!!! Error while commanding laser! " + str(e))
            except:
                print_cli("!!! Check External Triggering PIN")
                continue
            # print_cli("Being implemented") #TODO
        
        elif c == "do_trigger":
            GPIO.output(external_trigger_pin, GPIO.LOW)
            time.sleep(0.01)
            GPIO.output(external_trigger_pin, GPIO.HIGH)
            print_cli("Triggered " + external_trigger_pin + ".") 
        elif c == "exit" or c == "quit":
            if spectrometer:
                spectrometer.close()
            if laser:
                laser.disconnect()
            running = False
        else:
            print_cli("!!! Invalid command. Enter the 'help' command for usage information")

# Root commands allow the user to specify which instrument (laser or spectrometer) they are interacting with, or interact with other aspects of the program
ROOT_COMMANDS = ["help", "exit", "quit", "laser", "spectrometer", "set", "get", "status", "do_libs_sample", "do_trigger"]

# Actions are things that the user can do to the laser and spectrometer
SPECTROMETER_ACTIONS = ["spectrum", "set", "get", "connect", "status", "dump_registers"]
LASER_ACTIONS = ["connect", "status", "arm", "disarm", "fire", "set", "get"]

# Properties are things that can be get and/or set by the user
SPECTROMETER_PROPERTIES = ["sample_mode", "trigger_delay", "spectrum"]
LASER_PROPERTIES = ["diode_current", "energy_mode", "fet_temp", "pulse_width", "rep_rate"]
ROOT_PROPERTIES = ["external_trigger_pin"]

def tab_completer(text, state):
    text = readline.get_line_buffer()
    parts = text.split(" ")

    root = None
    action = None
    prop = None
    if parts[0] in ROOT_COMMANDS:
        root = parts[0]
        if len(parts) > 1:
            if root == "laser":
                if parts[1] in LASER_ACTIONS:
                    action = parts[1]
            elif root == "spectrometer":
                if parts[1] in SPECTROMETER_ACTIONS:
                    action = parts[1]
            elif root == "set":
                root = None
                action = "set"
            elif root == "get":
                root = None
                action = "get"

    if root == None:
        if action == "get" or action == "set": # Getter and setter actions for root properties
            if len(parts) < 2:
                parts[1] = ""

            for p in ROOT_PROPERTIES:
                if p.startswith(parts[1]):
                    return p
                else:
                    state -= 1
        else:
            for cmd in ROOT_COMMANDS:
                if cmd.startswith(text):
                    if not state:
                        return cmd
                    else:
                        state -= 1

    elif not action and root == "laser":
        if len(parts) < 2:
            parts[1] = ""

        for a in LASER_ACTIONS:
            if a.startswith(parts[1]):
                if not state:
                    return a
                else:
                    state -= 1

    elif not action and root == "spectrometer":
        if len(parts) < 2:
            parts[1] = ""

        for a in SPECTROMETER_ACTIONS:
            if a.startswith(parts[1]):
                if not state:
                    return a
                else:
                    state -= 1

    elif action in ["get", "set"] and root == "laser":
        if len(parts) < 3:
            parts[2] = ""

        for p in LASER_PROPERTIES:
            if p.startswith(parts[2]):
                if not state:
                    return p
                else:
                    state -= 1
    elif action in ["get", "set"] and root == "spectrometer":
        if len(parts) < 3:
            parts[2] = ""

        for p in SPECTROMETER_PROPERTIES:
            if p.startswith(parts[2]):
                if not state:
                    return p
                else:
                    state -= 1
    else:
        return

def laser_help(section = "root"):
    print("Laser help section")

def spectrometer_help(section = "root"):
    print("Spectrometer help section")

def give_help():
    """Outputs a list of commands to the user for use in interactive mode."""
    print("\nInteractive Mode Commands")
    print("\thelp\t\t\t\tDisplay this help message.")
    print("\texit OR quit\t\t\tExit the program.")
    print("\nSPECTROMETER")
    print("\tconnect_spectrometer [DEV]\tInitialize connection with the spectrometer using DEV device file. DEV is currently not available and autodetection will be used instead.")
    print("\tset_sample_mode MODE\t\t\tSet the trigger mode of the spectrometer, possible values are: NORMAL, EXT_LEVEL, EXT_SYNC, EXT_EDGE")
    print("\tset_trigger_delay TIME\t\tSet the trigger delay for the spectrometer. TIME is in microseconds.")
    print("\tset_integration_time TIME\t\tSet the Integration Time/Period for the spectrometer. TIME is in microseconds.")
    print("\tset_external_trigger_pin PIN\t\tSet the external trigger pin for the spectrometer. PIN is a string.")
    print("\tdo_sample \t\tStarts integration and obtains the sample data.")
    print("\tdump_spectrometer_registers\t\tRequests and displays the settings register on the spectrometer.")
    print("\nLASER")
    print("\tconnect_laser [DEV]\t\tInitialize connection with the laser using DEV device file.")

def main():
    global command_log, external_trigger_pin
    parser = ArgumentParser(description="CLI for performing LIBS using an Ocean Optics FLAME-T spectrometer and a 1064nm Quantum Composers MicroJewel laser.",
    epilog="Created for the 2020 NASA BIG Idea challenge, Penn State Oasis team. Questions: tylersengia@gmail.com",
    prog="libs_cli.py")

    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    parser.add_argument("--spec-dev", "-s", help="Specify the USB device for the spectrometer. Default is autodetected by seabreeze.", nargs=1, default=None)
    parser.add_argument("--laser-dev", "-l", help="Specify the USB device for the laser.", nargs=1, default=None)
    parser.add_argument("--config", "-c", help="Read test configuration from the specified JSON file.", nargs=1, default=None)
    parser.add_argument("--no-interact", "-n", help="Do not run in interactive mode. Usually used when a pre-written test configuration file is being used.", dest="interactive", action="store_false", default=True)
    a = parser.parse_args()
    
    command_log = open(LOG_PATH + "LOG_" + str(int(time.time())) + ".log", "w")
    GPIO.setup(external_trigger_pin, GPIO.OUT)
    GPIO.output(external_trigger_pin, GPIO.HIGH)
    
    if a.interactive:
        readline.parse_and_bind("tab: complete")
        readline.set_completer(tab_completer)
        command_loop()

    GPIO.cleanup()
    command_log.close()
    
if __name__ == "__main__":
    main()
