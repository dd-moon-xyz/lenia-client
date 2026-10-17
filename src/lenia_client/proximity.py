"""LTR559 proximity input through Linux i2c-dev (no system Python packages)."""

import asyncio
import fcntl
import os
import time


class ProximitySensor:
    def __init__(self, device="/dev/i2c-1", threshold=30):
        if threshold < 2 or threshold > 2047:
            raise ValueError("Proximity threshold must be between 2 and 2047")
        self.threshold = threshold
        self.active = False
        self.confirmations = 0
        self.release_threshold = threshold // 2
        self.fd = os.open(device, os.O_RDWR)
        try:
            fcntl.ioctl(self.fd, 0x0703, 0x23)  # I2C_SLAVE
            if self._read(0x86, 1) != b"\x92":
                raise OSError("LTR559 identification failed at address 0x23")
            self._write(0x81, 0)  # Standby while configuring proximity only.
            self._write(0x82, 0x1C)  # 30 kHz, 100% duty cycle, maximum 100 mA.
            self._write(0x83, 15)  # Maximum pulse count for sensitivity.
            self._write(0x84, 0)  # New measurement every 50 ms.
            self._write(0x81, 0x23)  # Active, with saturation indication.
            # Match the reference app: calibrate with the sensor unobstructed.
            baseline = 0
            for _ in range(20):
                time.sleep(0.05)
                low, high = self._read(0x8D, 2)
                if high & 0x80:
                    raise OSError("Proximity sensor saturated during calibration; clear the sensor")
                baseline = max(baseline, low | ((high & 7) << 8))
            self.threshold = max(threshold, baseline + 15)
            self.release_threshold = max(baseline + 7, self.threshold - 8)
            print(f"Proximity baseline={baseline}, trigger={self.threshold}, release={self.release_threshold}; keep sensor clear at startup", flush=True)
        except BaseException:
            os.close(self.fd)
            raise

    def _write(self, register, value):
        os.write(self.fd, bytes((register, value)))

    def _read(self, register, size):
        os.write(self.fd, bytes((register,)))
        return os.read(self.fd, size)

    def poll(self):
        """Return a steering command only when a fresh reading changes presence."""
        if not self._read(0x8C, 1)[0] & 1:
            return None
        low, high = self._read(0x8D, 2)
        value = low | ((high & 7) << 8)
        # Saturation means a strong reflection; hysteresis avoids edge chatter.
        active = bool(high & 0x80) or value >= (self.release_threshold if self.active else self.threshold)
        if active == self.active:
            self.confirmations = 0
            return None
        self.confirmations += 1
        if self.confirmations < 2:
            return None
        self.confirmations = 0
        self.active = active
        print(f"Proximity: {value}, {'detected → outward' if active else 'clear → inward'}", flush=True)
        return "outward" if active else "inward"

    def close(self):
        try:
            self._write(0x81, 0)
        finally:
            os.close(self.fd)


async def monitor_proximity(commands, device="/dev/i2c-1", threshold=30):
    # I²C transactions run off the display/event loop. Shield each transaction
    # so cancellation cannot close its descriptor while the worker uses it.
    opening = asyncio.create_task(asyncio.to_thread(ProximitySensor, device, threshold))
    try:
        sensor = await asyncio.shield(opening)
    except asyncio.CancelledError:
        sensor = await opening
        await asyncio.to_thread(sensor.close)
        raise
    print(f"LTR559 proximity ready: {device}, threshold={threshold}, maximum LED/pulses", flush=True)
    try:
        while True:
            reading = asyncio.create_task(asyncio.to_thread(sensor.poll))
            try:
                command = await asyncio.shield(reading)
            except asyncio.CancelledError:
                await reading
                raise
            if command is not None:
                commands.put_nowait(command)
            await asyncio.sleep(0.05)
    finally:
        await asyncio.to_thread(sensor.close)
