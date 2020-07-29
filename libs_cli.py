#!/usr/bin/python3
import struct
from argparse import ArgumentParser

import seabreeze
from seabreeze.spectrometers import Spectrometer
import laser_control

# Created using Notepad++. I have no regrets. And notice that it works. :)

running = True
spectrometer = None
laser = None

def set_trigger_delay(d):
    """Sets the trigger delay of the spectrometer. Can be from 0 to 32.7ms in increments of 500ns."""

def auto_connect_spectrometer(spec):
    """Use seabreeze to autodetect and connect to a spectrometer. Returns True on success, False otherwise."""
    if seabreeze.spectrometers.list_devices():
		spec = seabreeze.spectrometers.Spectrometer.from_first_available()
        print("*** Found spectrometer, serial number: " + spec.serial_number)
        return True
	else:
		print("!!! No spectrometer autodetected!")
        return False
        
def connect_spectrometer(spec, device):
    """Explicitly connect to the spectrometer at the given device file. Returns True on success, False otherwise."""

def command_loop():
    global running, spectrometer, laser
    while running:
        c = input("?").strip() # Get a command from the user and remove any extra whitespace
        parts = c.split() # split the command up into the command and any arguments
        if parts[0] == "help": # check to see what command we were given
            give_help()
        elif parts[0] == "set_td":
            if len(parts) < 2:
                print("!!! Invalid command: Set Trigger Delay command expects at least 1 argument.")
                continue
            try:
                t = int(parts[1])
            except:
                print("!!! Invalid argument: Set Trigger Delay command expected an integer.")
                continue
            set_trigger_delay(t)
        elif parts[0] == "connect_spectrometer":
            if len(parts) == 1:
                auto_connect_spectrometer(spectrometer)
            else:
                connect_spectrometer(spectrometer, parts[1])
        elif parts[0] == "connect_laser":
            print("Being implemented")
        elif parts[0] == "ping_spectrometer":
            print("Being implemented")
        elif parts[0] == "exit" or parts[0] == "quit":
            running = False
        else:
            print("!!! Invalid command. Enter the 'help' command for usage information")
            

def give_help():
    """Outputs a list of commands to the user for use in interactive mode."""
    print("\nInteractive Mode Commands")
    print("\thelp\t\t\t\tDisplay this help message.")
    print("\texit OR quit\t\t\tExit the program.")
    print("\nSPECTROMETER")
    print("\tconnect_spectrometer [DEV]\tInitialize connection with the spectrometer using DEV device file. DEV is optional and autodetection will be used instead.")
    print("\tset_td TIME\t\t\tSet the trigger delay for the spectrometer. TIME is in microseconds.")
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
        command_loop()
    
if __name__ == "__main__":
    main()