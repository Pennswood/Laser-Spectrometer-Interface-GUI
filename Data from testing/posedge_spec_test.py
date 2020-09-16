import Adafruit_BBIO.GPIO as GPIO
import seabreeze
import seabreeze.spectrometers
import time

# Change the pin when Tyler gets back.
GPIO_Pin = "P8_10"
GPIO.setup(GPIO_Pin, GPIO.OUT)
GPIO.output(GPIO_Pin, GPIO.LOW)
spec = seabreeze.spectrometers.Spectrometer(seabreeze.spectrometers.list_devices()[0])
delay_in_micros = 10
spec.f.spectrometer.set_delay_microseconds(delay_in_micros)
spec.trigger_mode(3)
integration_time_in_millis = 20

spec.integration_time_micros(integration_time_in_millis*1000)
timeElapsed = time.time()
GPIO.output(GPIO_Pin, GPIO.HIGH)
# This should hang until the first data comes back
first_spectrum = spec.spectrum()
timeElapsed = time.time() - timeElapsed
print("Elapsed time: "+str(timeElapsed)+"\n")

# Test to see if it will give back old data, or if it hangs.
if(first_spectrum == spec.spectrum()):
    print("Gave back old data.\n")
print("First test finished without issues"+"\n")

GPIO.output(GPIO_Pin, GPIO.LOW)

# Test to see if we get the spectrum or not, and if not does it hang or what happens?
time.sleep(2)
GPIO.output(GPIO_Pin, GPIO.HIGH)
time.sleep(1)
second_spectrum = spec.spectrum()
print("Second test finished without issues"+"\n")

time.sleep(2)
integration_time_in_millis = 5000

spec.integration_time_micros(integration_time_in_millis*1000)
GPIO.output(GPIO_Pin, GPIO.HIGH) # Start sample
timeElapsed = time.time()
third_spectrum = spec.spectrum()
timeElapsed = time.time() - timeElapsed
print("Elapsed time 1: "+str(timeElapsed)+"\n")
time.sleep(1)

# Get spectrum DURING a sample
timeElapsed = time.time()
fourth_spectrum = spec.spectrum()
timeElapsed = time.time() - timeElapsed
print("Elapsed time 2: "+str(timeElapsed)+"\n")
time.sleep(8)
fifth_spectrum = spec.spectrum()

if(fourth_spectrum == fifth_spectrum):
    print("The integration time did not change." + "\n")
else:
    print("Integration time changed appropriately." + "\n")
print("All tests finished without issues."+"\n")

