import unittest
from unittest.mock import Mock
from ujlaser.lasercontrol import Laser, LaserCommandError, LaserStatusResponse
import time
import libs_cli

class TestDoSample(unittest.TestCase):
    def test_typical_sample(self):
        spec = MockSpec()
        libs_cli.command_log = MockLog()
        assert libs_cli.do_sample(spec, "RANDOM", 5, 4, 10) == None
        libs_cli.do_sample(spec, "NORMAL", 5, 4, 10)

class MockSpec():
    def __init__(self):
        global stage_sleep_time, sleep_time
        sleep_time = 1
        stage_sleep_time = 1
    def integration_time_micros(self, micros):
        global stage_sleep_time, sleep_time
        sleep_time = stage_sleep_time
        stage_sleep_time = micros
    def spectrum(self):
        global sleep_time
        print("Spectrometer sampling with duration "+ str(sleep_time))
        time.sleep(sleep_time)
        print("Finished spectrometer sampling with duration " + str(sleep_time))
        sleep_time = stage_sleep_time
        return [1,2,3], [1,2,3]


class MockLog():
    def write(self, text):
        print(text)

if __name__ == "__main__":
    unittest.main()