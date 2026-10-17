"""LSM6DS3/LSM6DS3TR-C movement detection on the Multi-Sensor Stick."""

import fcntl
import math
import os
import struct
import time


class MotionDetector:
    def __init__(self, threshold_g=0.12, threshold_dps=20.0, hold_seconds=0.25):
        if not all(math.isfinite(value) and value > 0 for value in (threshold_g, threshold_dps, hold_seconds)):
            raise ValueError("Motion thresholds and hold time must be positive and finite")
        self.threshold_g = threshold_g
        self.threshold_dps = threshold_dps
        self.hold_seconds = hold_seconds
        self.previous_acceleration = None
        self.strength = 0.0
        self.active_until = float('-inf')

    def update(self, acceleration, rotation, now):
        if self.previous_acceleration is None:
            self.previous_acceleration = acceleration
        delta = math.sqrt(sum((value - base) ** 2 for value, base in zip(acceleration, self.previous_acceleration)))
        spin = math.sqrt(sum(value ** 2 for value in rotation))
        if delta >= self.threshold_g or spin >= self.threshold_dps:
            self.active_until = now + self.hold_seconds
            intensity = max(delta / self.threshold_g, spin / self.threshold_dps)
            self.strength = min(1.0, max(0.0, (intensity - 1.0) / 3.0))
        self.previous_acceleration = acceleration
        return self.active(now)

    def active(self, now):
        return now < self.active_until


class MotionSensor:
    def __init__(self, device='/dev/i2c-1', threshold_g=0.12):
        self.detector = MotionDetector(threshold_g=threshold_g)
        self.fd = os.open(device, os.O_RDWR)
        try:
            fcntl.ioctl(self.fd, 0x0703, 0x6A)
            identity = self._read(0x0F, 1)[0]
            if identity not in (0x69, 0x6A):
                raise OSError(f'Unsupported motion sensor ID: 0x{identity:02x}')
            self._write(0x12, 0x44)  # BDU and register auto-increment, little endian.
            self._write(0x10, 0x40)  # Accelerometer: 104 Hz, ±2 g (0.061 mg/LSB).
            self._write(0x11, 0x40)  # Gyroscope: 104 Hz, ±245 dps (8.75 mdps/LSB).
            print(f'Motion sensor ready at 0x6a: ID=0x{identity:02x}, threshold={threshold_g} g / 20 dps', flush=True)
        except BaseException:
            os.close(self.fd)
            raise

    def _write(self, register, value):
        os.write(self.fd, bytes((register, value)))

    def _read(self, register, size):
        os.write(self.fd, bytes((register,)))
        return os.read(self.fd, size)

    def poll(self):
        now = time.monotonic()
        # Require fresh gyro and accelerometer data; never retrigger on stale data.
        if self._read(0x1E, 1)[0] & 3 != 3:
            return self.detector.active(now)
        gx, gy, gz, ax, ay, az = struct.unpack('<6h', self._read(0x22, 12))
        return self.detector.update(
            tuple(value * 0.000061 for value in (ax, ay, az)),
            tuple(value * 0.00875 for value in (gx, gy, gz)), now,
        )

    @property
    def strength(self):
        return self.detector.strength

    def close(self):
        try:
            self._write(0x10, 0)
            self._write(0x11, 0)
        finally:
            os.close(self.fd)
