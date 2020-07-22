# Laser-Spectrometer-Interface-GUI

python-seabreeze spectroscopy and sensor library demo, written as a proof of concept to use Ocean Insights spectrometers (specifically the FLAME-T-VIS-NIR) and a MicroJewel laser connected via USB to perform LIBS. 
Designed as a proof of concept for python GUI controls for sample aquisition and processing.

# Requirements
Python: Version 3.7 (NOTE: matplotlib does not currently support python 3.8 and above)

To install the libraries below, just run: `pip install -r requirements.txt`  

`matplotlib`: version 3.2.0rc3 or higher

`numpy`: version 1.18.1 or higher

`seabreeze`: version 1.0.1 or higher

`pyusb`: version 1.0.2 or higher

# Usage
To open up the control UI, run: 
`python3 core_ui.py`

# Sources
Code taken from Github user MGPSU's seabreeze demo laser-interface branch with edits to connect the laser GUI frontend with backend operations to operate the laser.
