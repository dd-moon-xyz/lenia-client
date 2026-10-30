import unittest
from unittest.mock import Mock, patch

from lenia_client.indicator import IndicatorLight
from lenia_client.sensors import SensorInputs


class IndicatorTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.gpio = Mock()
        self.led = IndicatorLight(self.gpio, lambda: self.now)

    def advance(self, active, seconds):
        for _ in range(round(seconds / .05)):
            self.now += .05
            self.led.update(active)
        return self.led.brightness

    def test_idle_pulses_slowly_and_trigger_fades_off(self):
        self.assertAlmostEqual(self.advance(False, 4), .25)
        self.assertAlmostEqual(self.advance(True, .05), .25)
        self.assertAlmostEqual(self.advance(True, 1), .125)
        self.assertAlmostEqual(self.advance(True, 1.05), 0)
        self.assertAlmostEqual(self.advance(True, 4), 0)
        self.gpio.set_brightness.assert_called_with(0)
        self.assertGreater(self.advance(False, 2), 0)

    def test_idle_pulse_stays_dim_after_eight_seconds(self):
        self.assertAlmostEqual(self.advance(False, 4), .25)
        self.assertAlmostEqual(self.advance(False, 4), .02)

    def test_idle_never_turns_completely_off(self):
        for _ in range(320):
            self.advance(False, .05)
            self.assertGreaterEqual(self.led.brightness, .02)
            self.assertLessEqual(self.led.brightness, .25)

    def test_sensor_fade_is_twice_as_fast_as_idle_fade(self):
        self.led.update(True)
        self.assertAlmostEqual(self.advance(True, 1), .01)
        self.assertAlmostEqual(self.advance(True, 1), 0)
        self.led.update(False)
        self.assertAlmostEqual(self.advance(False, 2), .125)
        self.assertAlmostEqual(self.advance(False, 2), .25)

    def test_shutdown_stops_pwm_drives_low_and_releases_chip(self):
        self.led.close()
        self.gpio.close.assert_called_once()

    def test_either_sensor_triggers_indicator(self):
        inputs = SensorInputs.__new__(SensorInputs)
        inputs.proximity = Mock(strength=0)
        inputs.motion = Mock(strength=0)
        inputs.indicator = Mock()
        for near, moving in [(False, False), (True, False), (False, True), (True, True)]:
            inputs.proximity.active = near
            inputs.motion.poll.return_value = moving
            inputs.poll()
            inputs.indicator.update.assert_called_with(near or moving)

    def test_indicator_failure_closes_open_sensors(self):
        with patch('lenia_client.sensors.CameraSensor') as near, patch('lenia_client.sensors.MotionSensor') as motion, patch('lenia_client.sensors.IndicatorLight', side_effect=OSError('GPIO busy')):
            with self.assertRaisesRegex(OSError, 'GPIO busy'):
                SensorInputs('/dev/i2c-1', .5, .12)
            near.return_value.close.assert_called_once()
            motion.return_value.close.assert_called_once()


class HardwarePWMTests(unittest.TestCase):
    def test_hardware_duty_scaling_clamping_and_shutdown(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from lenia_client.indicator import HardwarePWM
        with TemporaryDirectory() as directory:
            root = Path(directory)
            chip = root / 'devices' / '1f00098000.pwm' / 'pwm' / 'pwmchip0'
            channel = chip / 'pwm2'
            channel.mkdir(parents=True)
            (root / 'pwmchip0').symlink_to(chip, target_is_directory=True)
            configure = Mock()
            pwm = HardwarePWM(root, configure)
            configure.assert_called_once()
            self.assertEqual((channel / 'period').read_text(), '500000')
            self.assertEqual((channel / 'enable').read_text(), '1')
            for brightness, duty in [(0.25, 125000), (-1, 0), (2, 500000)]:
                pwm.set_brightness(brightness)
                self.assertEqual(int((channel / 'duty_cycle').read_text()), duty)
            pwm.close()
            self.assertEqual((channel / 'duty_cycle').read_text(), '0')
            self.assertEqual((channel / 'enable').read_text(), '1')

    def test_missing_rp1_controller_is_reported(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from lenia_client.indicator import HardwarePWM
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(OSError, 'RP1 PWM0 controller unavailable'):
                HardwarePWM(Path(directory))

    def test_pwm1_controller_is_not_selected_for_gpio18(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from lenia_client.indicator import HardwarePWM
        with TemporaryDirectory() as directory:
            root = Path(directory)
            chip = root / 'devices' / '1f0009c000.pwm' / 'pwm' / 'pwmchip0'
            chip.mkdir(parents=True)
            (root / 'pwmchip0').symlink_to(chip, target_is_directory=True)
            with self.assertRaisesRegex(OSError, 'RP1 PWM0 controller unavailable'):
                HardwarePWM(root)
