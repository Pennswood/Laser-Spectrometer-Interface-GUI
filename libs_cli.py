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

import seabreeze
from seabreeze.spectrometers import Spectrometer
from seabreeze.cseabreeze._wrapper import SeaBreezeError
#import Adafruit_BBIO.GPIO as GPIO
from OASIS-Laser import Laser

# Created using Notepad++. I have no regrets. And notice that it works. :)

seabreeze.use('cseabreeze') # Select the cseabreeze backend for consistency

running = True
spectrometer = None
laser = None
use_external_trigger = False
external_trigger_pin = None

def check_spectrometer(spec):
    """Helper function that prints an error message if the spectrometer has not been connected yet. Returns True if the spectrometer is NOT connected."""
    if spec == None:
        print("!!! This command requires the spectrometer to be connected! Use 'connect_spectrometer' first!")
        return True
    return False
    
def check_laser(laser):
    """Helper function that prints an error message if the laser has not been connected yet. Returns True if the laser is NOT connected."""
    if laser == None:
        print("!!! This command requires the laser to be connected! Use 'connect_laser' first!")
        return True
    return False

def dump_settings_register(spec):
    print("... Dumping settings register:")
    for i in (b'\x00', b'\x04', b'\x08', b'\x0C', b'\x10', b'\x14', b'\x18', b'\x28', b'\x2C', b'\x38', b'\x3C', b'\x40', b'\x48', b'\x50', b'\x54', b'\x74', b'\x78', b'\x7C', b'\x80'):
        spec.f.raw_usb_bus_access.raw_usb_write(struct.pack(">ss",b'\x6B',i),'primary_out')
        output = spec.f.raw_usb_bus_access.raw_usb_read(endpoint='primary_in', buffer_length=3)
        print(str(i) + "\t" + str(output[1:]))

def set_trigger_delay(spec, t):
    """Sets the trigger delay of the spectrometer. Can be from 0 to 32.7ms in increments of 500ns. t is in microseconds"""
    t_nano_seconds = t * 1000 #convert micro->nano seconds
    t_clock_cycles = t//500 # number of clock cycles to wait. 500ns per clock cycle b/c the clock runs at 2MHz
    data = struct.pack("<ssH",b'\x6A',b'\x28',t_clock_cycles)
    print(data)
    spec.f.raw_usb_bus_access.raw_usb_write(data,'primary_out')
    
def set_external_trigger_pin(pin):
    """Sets the GPIO pin to use for external triggering."""

def auto_connect_spectrometer():
    """Use seabreeze to autodetect and connect to a spectrometer. Returns a Spectrometer object on success, None otherwise"""
    if seabreeze.spectrometers.list_devices():
        spec = seabreeze.spectrometers.Spectrometer.from_first_available()
        print("*** Found spectrometer, serial number: " + spec.serial_number)
        return spec
    else:
        print("!!! No spectrometer autodetected!")

#TODO: Implement the below function, currently only autodetection works.
def connect_spectrometer(device):
    """Explicitly connect to the spectrometer at the given device file. Returns a Spectrometer on success, None otherwise."""
    return None

def set_sample_mode(spec, mode):
    """Sets the spectrometer sampling trigger to the specified mode."""
    i = None
    # TODO: Verify that these are the correct modes. The datasheets are vague.
    if mode == "NORMAL":
        i = 0
    elif mode == "SOFTWARE":
        i = 1
    elif mode == "EXT_LEVEL":
        i = 2
    elif mode == "EXT_EDGE":
        i = 3

    try:
        spec.trigger_mode(i)
        print("*** Spectrometer trigger mode set to " + mode + " (" + str(i) + ")")
        return True
    except SeaBreezeError as e:
        print("!!! " + str(e))
        print("!!! Spectrometer does not support mode number " + str(i) + " (" + mode + ")!")
        return False

def set_integration_time(spec, time):
    """Sets the integration time of the spectrometer. Returns True on success, False otherwise."""
    spec.integration_time_micros(time)
    print("*** Integration time set to " + str(time) + " microseconds.")
    return True

def command_loop():
    global running, spectrometer, laser
    while running:
        c = input("?").strip() # Get a command from the user and remove any extra whitespace
        parts = c.split() # split the command up into the command and any arguments
        if parts[0] == "help": # check to see what command we were given
            give_help()

        elif parts[0] == "dump_spectrometer_registers":
            if check_spectrometer(spectrometer):
                continue
            dump_settings_register(spectrometer)

        elif parts[0] == "set_trigger_delay":
            if check_spectrometer(spectrometer):
                continue
            if len(parts) < 2:
                print("!!! Invalid command: Set Trigger Delay command expects at least 1 argument.")
                continue
            try:
                t = int(parts[1]) # t is the time in microseconds to delay
                set_trigger_delay(spectrometer, t)
            except ValueError:
                print("!!! Invalid argument: Set Trigger Delay command expected an integer.")
                continue

        elif parts[0] == "set_integration_time":
            if check_spectrometer(spectrometer):
                continue
            if len(parts) < 2:
                print("!!! Invalid command: Set Integration Time command expects at least 1 argument.")
                continue
            try:
                t = int(parts[1])
                set_integration_time(spectrometer, t)
            except ValueError:
                print("!!! Invalid argument: Set Integration Time command expected an integer!")
                continue
            except SeaBreezeError as e:
                print("!!! " + str(e))
                continue

        elif parts[0] == "set_sample_mode":
            if check_spectrometer(spectrometer):
                continue
            if len(parts) < 2:
                print("!!! Invalid command: Set Sample Mode command expects at least 1 argument.")
                continue

            if parts[1] == "NORMAL" or parts[1] == "SOFTWARE" or parts[1] == "EXT_LEVEL" or parts[1] == "EXT_SYNC" or parts[1] == "EXT_EDGE":
                set_sample_mode(spectrometer, parts[1])
            else:
                print("!!! Invalid argument: Set Sample Mode command expected one of: NORMAL, SOFTWARE, EXT_LEVEL, EXT_SYNC, EXT_EDGE")
                continue

        elif parts[0] == "connect_spectrometer":
            if len(parts) == 1:
                spectrometer = auto_connect_spectrometer()
            else:
                spectrometer = connect_spectrometer(parts[1])

        elif parts[0] == "connect_laser":
            print("Being implemented") #TODO
            
        elif parts[0] == "arm_laser":
            if check_laser(laser):
                continue
            if laser.arm():
                print("*** Laser ARMED")

        elif parts[0] == "disarm_laser":
            if check_laser(laser):
                continue
            if laser.disarm():
                print("*** Laser DISARMED")

        elif parts[0] == "laser_status":
            print("Being implemented") #TODO

        elif parts[0] == "fire_laser":
            if check_laser(laser):
                continue
            print("Being implemented") #TODO

        elif parts[0] == "set_laser_rep_rate": # TODO: Add check to see if this is within the repetition rate.
            if check_laser(laser):
                continue
            
            if len(parts) < 2:
                print("!!! Set Laser Rep Rate expects an integer argument!")
                continue
            try:
                rate = int(parts[1])
            except ValueError:
                print("!!! Set Laser Rep Rate expects an integer argument! You did not enter an integer.")
                continue
                
        elif parts[0] == "set_laser_pulse_width":
            if check_laser(laser):
                continue
                
            if len(parts) < 2:
                print("!!! Set Laser Pulse Width expects an integer argument!")
                continue
            try:
                rate = int(parts[1])
            except ValueError:
                print("!!! Set Laser Pulse Width expects an integer argument! You did not enter an integer.")
                continue
                
        elif parts[0] == "get_laser_fet_temp":
            if check_laser(laser):
                continue
            t = laser.fet_temp_check() # TODO: This returns a bytes object, this might be ASCII or a float? Need to do testing.
            print("*** Laser FET temperature: " + str(t))

        elif parts[0] == "do_sample":
            if check_laser(laser) or check_spectrometer(spectrometer):
                continue

            print("Being implemented") #TODO

        elif parts[0] == "exit" or parts[0] == "quit":
            if spectrometer:
                spectrometer.close()
            running = False
        else:
            print("!!! Invalid command. Enter the 'help' command for usage information")

COMMAND_LIST = ["do_sample", "connect_laser", "get_laser_fet_temp", "set_external_trigger_pin", "set_laser_pulse_width", "set_laser_rep_rate", "set_trigger_delay", "connect_spectrometer"]

# Taken from: https://stackoverflow.com/questions/5637124/tab-completion-in-pythons-raw-input
def tab_completer(text, state):
    for cmd in COMMAND_LIST:
        if cmd.startswith(text):
            if not state:
                return cmd
            else:
                state -= 1
def give_help():
    """Outputs a list of commands to the user for use in interactive mode."""
    print("\nInteractive Mode Commands")
    print("\thelp\t\t\t\tDisplay this help message.")
    print("\texit OR quit\t\t\tExit the program.")
    print("\nSPECTROMETER")
    print("\tconnect_spectrometer [DEV]\tInitialize connection with the spectrometer using DEV device file. DEV is optional and autodetection will be used instead.")
    print("\tset_sample_mode MODE\t\t\tSet the trigger mode of the spectrometer, possible values are: NORMAL, SOFTWARE, EXT_LEVEL, EXT_SYNC, EXT_EDGE")
    print("\tset_trigger_delay TIME\t\tSet the trigger delay for the spectrometer. TIME is in microseconds.")
    print("\tset_integration_time TIME\t\tSet the Integration Time/Period for the spectrometer. TIME is in microseconds.")
    print("\tdump_spectrometer_registers\t\tRequests and displays the settings register on the spectrometer.")
    print("\nLASER")
    print("\tconnect_laser [DEV]\t\tInitialize connection with the laser using DEV device file.")

def main():
    parser = ArgumentParser(description="CLI for performing LIBS using an Ocean Optics FLAME-T spectrometer and a 1064nm Quantum Composers MicroJewel laser.",
    epilog="Created for the 2020 NASA BIG Idea challenge, Penn State Oasis team. Questions: tylersengia@gmail.com",
    prog="libs_cli.py")

    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    parser.add_argument("--spec-dev", "-s", help="Specify the USB device for the spectrometer. Default is autodetected by seabreeze.", nargs=1, default=None)
    parser.add_argument("--laser-dev", "-l", help="Specify the USB device for the laser.", nargs=1, default=None)
    parser.add_argument("--config", "-c", help="Read test configuration from the specified JSON file.", nargs=1, default=None)
    parser.add_argument("--no-interact", "-n", help="Do not run in interactive mode. Usually used when a pre-written test configuration file is being used.", dest="interactive", action="store_false", default=True)
    a = parser.parse_args()
    
    if a.interactive:
        readline.parse_and_bind("tab: complete")
        readline.set_completer(tab_completer)
        command_loop()
    
if __name__ == "__main__":
    main()