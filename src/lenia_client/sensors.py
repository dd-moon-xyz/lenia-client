"""Combine proximity and motion into one steering command, with continuous speed from sensor intensity."""

import asyncio

from lenia_client.indicator import IndicatorLight
from lenia_client.motion import MotionSensor
from lenia_client.proximity import ProximitySensor


def steering_command(proximity_active, motion_active, proximity_strength=0.0, motion_strength=1.0):
    # The stronger input wins; motion cannot slow down a proximity response.
    strength = max(proximity_strength if proximity_active else 0.0,
                   motion_strength if motion_active else 0.0)
    speed = round(1.0 + min(1.0, max(0.0, strength)), 2)
    return {
        'action': 'movement',
        'direction': 'outward' if proximity_active or motion_active else 'inward',
        'speed_multiplier': speed,
    }


class SensorInputs:
    def __init__(self, device, proximity_threshold, motion_threshold):
        self.proximity = ProximitySensor(device, proximity_threshold)
        try:
            self.motion = MotionSensor(device, motion_threshold)
            try:
                self.indicator = IndicatorLight()
            except BaseException:
                self.motion.close()
                raise
        except BaseException:
            self.proximity.close()
            raise

    def poll(self):
        self.proximity.poll()
        motion_active = self.motion.poll()
        self.indicator.update(self.proximity.active or motion_active)
        return steering_command(self.proximity.active, motion_active,
                                self.proximity.strength, self.motion.strength)

    def close(self):
        try:
            self.indicator.close()
        finally:
            try:
                self.motion.close()
            finally:
                self.proximity.close()


async def monitor_sensors(commands, device='/dev/i2c-1', proximity_threshold=30, motion_threshold=0.12):
    # Establish the idle mode immediately, including during startup calibration.
    previous = steering_command(False, False)
    commands.put_nowait(previous)
    opening = asyncio.create_task(asyncio.to_thread(SensorInputs, device, proximity_threshold, motion_threshold))
    try:
        sensors = await asyncio.shield(opening)
    except asyncio.CancelledError:
        sensors = await opening
        await asyncio.to_thread(sensors.close)
        raise
    try:
        while True:
            reading = asyncio.create_task(asyncio.to_thread(sensors.poll))
            try:
                command = await asyncio.shield(reading)
            except asyncio.CancelledError:
                await reading
                raise
            if command != previous:
                commands.put_nowait(command)
                print(f'Sensor steering: {command}', flush=True)
                previous = command
            await asyncio.sleep(0.05)
    finally:
        await asyncio.to_thread(sensors.close)
