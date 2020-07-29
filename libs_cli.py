#!/usr/bin/python3
import struct
from argparse import ArgumentParser

import seabreeze
from seabreeze.spectrometers import Spectrometer
import laser_control

# Created using Notepad++. I have no regrets. And notice that it works. :)

def main():
    parser = ArgumentParser(description="CLI for performing LIBS using an Ocean Optics FLAME-T spectrometer and a 1064nm Quantum Composers MicroJewel laser.",
    epilog="Created for the 2020 NASA BIG Idea challenge, Penn State Oasis team. Questions: tylersengia@gmail.com")

    parser.add_argument("--spec-dev", "-s", "spec-dev", help="Specify the USB device for the spectrometer. Default is autodetected by seabreeze.", default=None, )


if __name__ == "__main__":
    main()