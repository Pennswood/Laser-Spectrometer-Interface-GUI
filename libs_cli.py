#!/usr/bin/python3
import struct
from argparse import ArgumentParser

import seabreeze
from seabreeze.spectrometers import Spectrometer
from seabreeze.cseabreeze._wrapper import SeaBreezeError
import laser_control

# Created using Notepad++. I have no regrets. And notice that it works. :)

seabreeze.use('cseabreeze') # Select the cseabreeze backend for consistency



running = True
spectrometer = None
laser = None

def dump_settings_register(spec):
    print("... Dumping settings register...")
    for i in (b'\x00', b'\x04', b'\x08', b'\x0C', b'\x10', b'\x14', b'\x18', b'\x28', b'\x2C', b'\x38', b'\x3C', b'\x40', b'\x48', b'\x50', b'\x54', b'\x74', b'\x78', b'\x7C', b'\x80'):
        spec.f.raw_usb_bus_access.raw_usb_write(struct.pack(">ss",b'\x6B',i),'primary_out')
        output = spec.f.raw_usb_bus_access.raw_usb_read(endpoint='primary_in', buffer_length=3)
        print(output)
        
def set_trigger_delay(spec, t):
    """Sets the trigger delay of the spectrometer. Can be from 0 to 32.7ms in increments of 500ns. t is in microseconds"""
    t_nano_seconds = t * 1000 #convert micro->nano seconds
    t_clock_cycles = t//500 # number of clock cycles to wait. 500ns per clock cycle b/c the clock runs at 2MHz
    data = struct.pack("<ssH",b'\x6A',b'\x28',t_clock_cycles)
    print(data)
    spec.f.raw_usb_bus_access.raw_usb_write(data,'primary_out')

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
    elif mode == "EXT_SYNC":
        i = 3
    elif mode == "EXT_EDGE": #BUG: Currently errors out on this triggering type. Again, the datasheet is crap when it comes to the trigger modes.
        i = 4

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
            dump_settings_register(spectrometer)

        elif parts[0] == "set_trigger_delay":
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
            
        elif parts[0] == "ping_spectrometer":
            print("Being implemented") #TODO
            
        elif parts[0] == "exit" or parts[0] == "quit":
            if spectrometer:
                spectrometer.close()
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
    print("\tset_sample_mode MODE\t\t\tSet the trigger mode of the spectrometer, possible values are: NORMAL, SOFTWARE, EXT_LEVEL, EXT_SYNC, EXT_EDGE")
    print("\tset_trigger_delay TIME\t\tSet the trigger delay for the spectrometer. TIME is in microseconds.")
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