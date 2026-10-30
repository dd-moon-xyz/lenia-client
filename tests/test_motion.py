import struct
import unittest
from unittest.mock import Mock

from lenia_client.motion import MotionDetector, MotionSensor
from lenia_client.sensors import steering_command


class MotionTests(unittest.TestCase):
    def test_stationary_gravity_in_any_orientation_does_not_trigger(self):
        for gravity in [(0, 0, 1), (1, 0, 0), (0, -1, 0)]:
            detector = MotionDetector()
            for sample in range(20):
                self.assertFalse(detector.update(gravity, (0, 0, 0), sample * .05))

    def test_stillness_clears_motion_after_quiet_interval(self):
        detector = MotionDetector()
        detector.update((0, 0, 1), (0, 0, 0), 0)
        self.assertTrue(detector.update((.2, 0, 1), (0, 0, 0), .05))
        self.assertTrue(detector.update((.2, 0, 1), (0, 0, 0), .2))
        self.assertFalse(detector.update((.2, 0, 1), (0, 0, 0), .31))

    def test_stopping_in_new_orientation_restores_proximity_base_state(self):
        detector = MotionDetector()
        detector.update((0, 0, 1), (0, 0, 0), 0)
        self.assertTrue(detector.update((1, 0, 0), (0, 30, 0), .05))
        self.assertTrue(detector.update((1, 0, 0), (0, 0, 0), .2))
        moving = detector.update((1, 0, 0), (0, 0, 0), .31)
        self.assertFalse(moving)
        for proximity in (False, True):
            self.assertEqual(steering_command(proximity, moving), steering_command(proximity, False))

    def test_rotation_retriggers_hold(self):
        detector = MotionDetector()
        self.assertTrue(detector.update((0, 0, 1), (0, 25, 0), 0))
        self.assertTrue(detector.update((0, 0, 1), (0, 25, 0), .9))
        self.assertTrue(detector.active(1.1))
        self.assertFalse(detector.active(1.16))

    def test_motion_strength_increases_and_caps(self):
        strengths = []
        for rotation in (20, 40, 60, 80, 160):
            detector = MotionDetector()
            self.assertTrue(detector.update((0, 0, 1), (rotation, 0, 0), 0))
            strengths.append(detector.strength)
        self.assertEqual(strengths, [0, 1/3, 2/3, 1, 1])

    def test_speed_scales_with_stronger_active_sensor(self):
        for strength, speed in ((0, 1), (.25, 1.25), (.75, 1.75), (1, 2), (5, 2)):
            for near, moving in ((True, False), (False, True)):
                command = steering_command(near, moving, strength, strength)
                self.assertEqual(command['direction'], 'outward')
                self.assertEqual(command['speed_multiplier'], speed)
        self.assertEqual(steering_command(True, True, .8, .2)['speed_multiplier'], 1.8)
        self.assertEqual(steering_command(False, False, 1, 1)['speed_multiplier'], 1)

    def test_invalid_thresholds(self):
        for threshold in [0, -1, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                MotionDetector(threshold_g=threshold)

    def test_sensor_decodes_little_endian_acceleration_and_gyro(self):
        sensor = MotionSensor.__new__(MotionSensor)
        sensor.detector = Mock()
        sensor._read = Mock(side_effect=[b'\x03', struct.pack('<6h', 1000, -2000, 0, 0, 0, 16384)])
        sensor.poll()
        acceleration, rotation, _ = sensor.detector.update.call_args.args
        self.assertAlmostEqual(acceleration[2], .999424)
        self.assertEqual(rotation, (8.75, -17.5, 0))

    def test_stale_readings_do_not_retrigger_motion(self):
        sensor = MotionSensor.__new__(MotionSensor)
        sensor.detector = Mock()
        sensor._read = Mock(return_value=b'\x00')
        sensor.poll()
        sensor.detector.update.assert_not_called()
        sensor.detector.active.assert_called_once()

    def test_motion_overrides_both_proximity_states(self):
        self.assertEqual(steering_command(False, False), {'action': 'movement', 'direction': 'inward', 'speed_multiplier': 1.0})
        self.assertEqual(steering_command(True, False), {'action': 'movement', 'direction': 'outward', 'speed_multiplier': 1.0})
        for proximity in (False, True):
            self.assertEqual(steering_command(proximity, True), {'action': 'movement', 'direction': 'outward', 'speed_multiplier': 2.0})


class SensorMonitorTests(unittest.IsolatedAsyncioTestCase):
    async def test_initial_mode_and_transitions_and_cleanup(self):
        import asyncio
        from unittest.mock import patch
        from lenia_client.sensors import monitor_sensors

        inputs = Mock()
        idle, near, moving = (steering_command(False, False), steering_command(True, False), steering_command(False, True))
        inputs.poll.side_effect = [idle, near, moving, moving, near, idle, OSError('disconnected')]
        commands = asyncio.Queue()
        with patch('lenia_client.sensors.SensorInputs', return_value=inputs):
            with self.assertRaisesRegex(OSError, 'disconnected'):
                await monitor_sensors(commands)
        self.assertEqual([commands.get_nowait() for _ in range(commands.qsize())],
                         [idle, near, moving, near, idle])
        inputs.close.assert_called_once()

    async def test_partial_startup_failure_closes_camera(self):
        from unittest.mock import patch
        from lenia_client.sensors import SensorInputs
        with patch('lenia_client.sensors.CameraSensor') as camera, patch('lenia_client.sensors.MotionSensor', side_effect=OSError('missing motion sensor')):
            with self.assertRaisesRegex(OSError, 'missing motion sensor'):
                SensorInputs('/dev/i2c-1', .5, .12)
            camera.return_value.close.assert_called_once()
