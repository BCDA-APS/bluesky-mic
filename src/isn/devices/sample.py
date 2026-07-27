import logging

from ophyd import Component
from ophyd import FormattedComponent
from ophyd import Device
from ophyd import EpicsMotor
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import Signal

from ophyd import PseudoPositioner
from ophyd import PseudoSingle
from ophyd.pseudopos import pseudo_position_argument
from ophyd.pseudopos import real_position_argument

import numpy as np

from time import sleep, time as _time
from threading import Thread

from apstools.devices.motor_mixins import EpicsMotorServoMixin

from ophyd.status import Status
from ophyd.status import wait as status_wait
from ophyd.utils import InvalidState

from apsbits.core.instrument_init import oregistry

logger = logging.getLogger(__name__)
logger.info(__file__)

if_cap_tracker = oregistry['if_cap_tracker']

class ServoMotor(EpicsMotorServoMixin, EpicsMotor):

    @property
    def enabled(self):
        return self.servo.get() in ("Enable")

    def enable(self):
        self.servo.put("Enable")

    def disable(self):
        self.servo.put("Disable")

    def set(self, value, **kwargs):
        if not self.enabled:
            self.enable()
        return super().set(value, **kwargs)


class FineYMotor(EpicsMotor):
    """EpicsMotor for fine_y that disables sample.y before moving.

    sample.y (ServoMotor) and fine_y share the same physical axis.
    The servo must be off during fine_y motion to avoid the two
    controllers fighting each other.
    """

    def set(self, value, **kwargs):
        y_motor = self.parent.y
        if y_motor.enabled:
            y_motor.disable()
        return super().set(value, **kwargs)


class EpicsMotorWithTweak(EpicsMotor):

    tweak_value = Component(EpicsSignal, ".TWV")
    tweak_forward = Component(EpicsSignal, ".TWF", kind="config")
    tweak_reverse = Component(EpicsSignal, ".TWR", kind="config")


class CorTheta(Device):
    """
    Positioner component of Sample that moves theta to a target angle,
    then corrects sample.x and sample.z using the capacitance sensor
    differential to keep the sample on the center of rotation.

    Requires sample.capture_initial_position() to have been called first.

    Usage (from a plan):
        yield from bps.mv(sample.cor_theta, 15.0)

    Usage (interactively):
        sample.cor_theta.set(15.0).wait()
    """

    _CAP_ANGLES_DEG = [229.9, 122.9, 55.0]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._status_obj = Status(self)
        self._status_obj.set_finished()  # start in a done state

    # @property
    # def position(self):
    #     """Current theta angle, proxied from the real motor readback."""
    #     return self.parent.theta.user_readback.get()

    # def read(self):
    #     """Return current position so bluesky relative-move wrappers work."""
    #     return {self.name: {'value': self.position, 'timestamp': _time()}}

    def set(self, theta_position):
        self._status_obj = Status(self)
        thread = Thread(target=self._move, args=(theta_position,), daemon=True)
        thread.start()
        return self._status_obj

    def _calc_corrected_position(self):

        sample = self.parent

        # Internal helper to calculate the required correction

        # 1. Read new cap values (already in mm via IfCapTracker.read())
        if_cap_tracker.trigger().wait()
        new_readings = if_cap_tracker.read()

        for key in new_readings.keys():
            new_readings[key]['value'] = 0

        for _ in range(100):
            if_cap_tracker.trigger().wait()
            data = if_cap_tracker.read()
            for key in new_readings.keys():
                new_readings[key]['value'] += data[key]['value']

        for key in new_readings.keys():
            new_readings[key]['value'] /= 100


        logger.info("New capacitance sensor readings (mm):")
        for key, value in new_readings.items():
            logger.info(f"  {key}: {value['value']}")

        # 3. Compute deltas for the first 3 sensors
        c1 = new_readings['if_cap_tracker_caps_cap1']['value'] - sample.cap1.get()
        c2 = new_readings['if_cap_tracker_caps_cap2']['value'] - sample.cap2.get()
        c3 = new_readings['if_cap_tracker_caps_cap3']['value'] - sample.cap3.get()
        c5 = new_readings['if_cap_tracker_caps_cap5']['value'] - sample.cap5.get()
        c6 = new_readings['if_cap_tracker_caps_cap6']['value'] - sample.cap6.get()
        c7 = new_readings['if_cap_tracker_caps_cap7']['value'] - sample.cap7.get()

        Dyscf = 127.291

        logger.info(f"Capacitance sensor deltas (mm): c1={c1}, c2={c2}, c3={c3}")

        # 4. Compute Dx and Dz
        angles_rad = [np.radians(a) for a in self._CAP_ANGLES_DEG]

        x_runout = -1*((-c1 * np.cos(angles_rad[0])
                        -c2 * np.cos(angles_rad[1])
                        -c3 * np.cos(angles_rad[2])) / 3)

        x_wobble = -1*((c7 - c5) * Dyscf/71)

        logger.info(f"X stage corrections (mm): Runout={x_runout}, Wobble={x_wobble}")

        z_runout = -1*((-c1 * np.sin(angles_rad[0])
                        -c2 * np.sin(angles_rad[1])
                        -c3 * np.sin(angles_rad[2])) / 3)

        z_wobble = -1*((c6-(c5 + c7)/2) * Dyscf/35.5)

        logger.info(f"Z stage corrections (mm): Runout={z_runout}, Wobble={z_wobble}")

        Dx = x_runout + x_wobble
        
        Dz = z_runout + z_wobble
        
        logger.info(f"Calculated corrections (mm): Dx={Dx}, Dz={Dz}")

        return Dx, Dz



    def _move(self, theta_position):
        try:
            sample = self.parent

            if not sample._initial_position_captured:
                raise RuntimeError(
                    "sample.capture_initial_position() must be called before "
                    "using sample.cor_theta."
                )

            # 1. Move theta and wait for completion
            status_wait(sample.theta.set(theta_position))

            # We repeat the measurement three times as sometimes the first reading is not correct.
            Dx, Dz = self._calc_corrected_position()
            Dx, Dz = self._calc_corrected_position()
            Dx, Dz = self._calc_corrected_position()

            # 3. Capture current X, Z positions and calculate absolute position.

            Xi = sample.x_initial.get()
            Zi = sample.z_initial.get()

            Xf = Xi + Dx
            Zf = Zi + Dz

            # 5. Move x by Dx (relative), wait
            status_wait(sample.x.set(Xf))

            # 6. Move z by Dz (relative), wait
            status_wait(sample.z.set(Zf))

            # 7. Mark the outer status done
            self._finish_status()

        except Exception as exc:
            self._status_obj.set_exception(exc)

    def _finish_status(self):
        try:
            self._status_obj.set_finished()
        except InvalidState:
            pass

    def stop(self, *, success=False):
        self.parent.theta.stop(success=success)
        self.parent.x.stop(success=success)
        self.parent.z.stop(success=success)
        self._finish_status()


# class MicronixStage(PseudoPositioner):

#     xp = Component(EpicsMotor, ":m2")
#     zp = Component(EpicsMotor, ":m3")
#     thetap = Component(EpicsMotor, ":m4")

#     _real = ["xp", "zp", "thetap"]
#     _pseudo = ["x", "z", "theta"]

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.theta_offset = 0

#     def calc_wx

#     @pseudo_position_argument
#     def forward(self, pseudo_pos):


class Sample(Device):

    x = FormattedComponent(EpicsMotorWithTweak, "{aero_prefix}"+"m2")
    y = FormattedComponent(ServoMotor, "{aero_prefix}"+"m3")
    z = FormattedComponent(EpicsMotorWithTweak, "{aero_prefix}"+"m1")

    # Thermocouple readbacks
    temp_x = FormattedComponent(EpicsSignalRO, "{rtd_prefix}"+"AI0.VAL")
    temp_y = FormattedComponent(EpicsSignalRO, "{rtd_prefix}"+"AI1.VAL")
    temp_z = FormattedComponent(EpicsSignalRO, "{rtd_prefix}"+"AI2.VAL")
    temp_theta = FormattedComponent(EpicsSignalRO, "{rtd_prefix}"+"AI3.VAL")

    vacuum = FormattedComponent(EpicsSignalRO, "{vacuum_prefix}"+"cc10_vs:sc1.VAL")

    fine_y = FormattedComponent(FineYMotor, "{aero_prefix}"+"SM1")

    analog_on = FormattedComponent(EpicsSignal, "{aero_prefix}"+"userStringSeq2.PROC")
    analog_off = FormattedComponent(EpicsSignal, "{aero_prefix}"+"userStringSeq1.PROC")
    query = FormattedComponent(EpicsSignal, "{aero_prefix}"+"userStringSeq3.PROC")
    query_output = FormattedComponent(EpicsSignalRO, "{aero_prefix}"+"pi:c0:asyn.TINP")

    theta = FormattedComponent(EpicsMotor, "{micronix_prefix}"+"m4") #TODO: We need to create an offsetable component that we can use to calibrate sample to sample the real theta position.
    mic_x = FormattedComponent(EpicsMotor, "{micronix_prefix}"+"m3")
    mic_z = FormattedComponent(EpicsMotor, "{micronix_prefix}"+"m2")

    cor_theta = Component(CorTheta, '')

    # Capacitance snapshot (mm, from if_cap_tracker.caps)
    cap1 = Component(Signal, name='cap1', kind='config', value=0.0)
    cap2 = Component(Signal, name='cap2', kind='config', value=0.0)
    cap3 = Component(Signal, name='cap3', kind='config', value=0.0)
    cap4 = Component(Signal, name='cap4', kind='config', value=0.0)
    cap5 = Component(Signal, name='cap5', kind='config', value=0.0)
    cap6 = Component(Signal, name='cap6', kind='config', value=0.0)
    cap7 = Component(Signal, name='cap7', kind='config', value=0.0)

    # Stage position snapshot (EGU, from x/y/z motor readbacks)
    x_initial = Component(Signal, name='x_initial', kind='config', value=0.0)
    y_initial = Component(Signal, name='y_initial', kind='config', value=0.0)
    z_initial = Component(Signal, name='z_initial', kind='config', value=0.0)

    def __init__(self, aero_prefix, micronix_prefix, rtd_prefix, vacuum_prefix, *args, **kwargs):
        self.aero_prefix = aero_prefix
        self.micronix_prefix = micronix_prefix
        self.rtd_prefix = rtd_prefix
        self.vacuum_prefix = vacuum_prefix
        self._initial_position_captured = False
        super().__init__(*args, **kwargs)
    
    @property
    def in_analog_mode(self):
        strings = []
        self.query.put(1)
        sleep(0.1)
        for i in range(3):
            strings.append(self.query_output.get())
            if i == 2:
                continue
            sleep(2)

        vals = [int(i[-1]) for i in strings]
        return vals == [4, 4, 4] #4 is analog control, 0 is digital


    def enable_analog_control(self):
        self.analog_on.put("1", wait=True)
        sleep(4.1)

    def disable_analog_control(self):
        self.analog_off.put("1", wait=True)
        sleep(4.1)

    def capture_initial_position(self):
        """Snapshot the current capacitance sensor readings (mm) from
        if_cap_tracker and the current x/y/z motor positions into soft
        Signals. Call this before a scan to establish reference values
        for use in positioner calculations."""
        # --- capacitance sensors ---
        if_cap_tracker.trigger().wait()
        readings = if_cap_tracker.read()

        for key in readings.keys():
            readings[key]['value'] = 0

        for _ in range(100):
            if_cap_tracker.trigger().wait()
            data = if_cap_tracker.read()
            for key in readings.keys():
                readings[key]['value'] += data[key]['value']

        for key in readings.keys():
            readings[key]['value'] /= 100

        for i in range(1, 8):
            key = f'if_cap_tracker_caps_cap{i}'
            getattr(self, f'cap{i}').put(readings[key]['value'])

        # --- stage positions ---
        self.x_initial.put(self.x.user_readback.get())
        self.y_initial.put(self.y.user_readback.get())
        self.z_initial.put(self.z.user_readback.get())
        self._initial_position_captured = True

    def compensating_z(self, x_step):
        '''Returns the amount the z stage would need to compensate for an x_step to keep the sample in focus.'''
        th = self.theta.user_readback.get()
        return (x_step * np.sin(-1*np.radians(th)))
    

class ScanningX(PseudoPositioner):
    scanning_x = Component(PseudoSingle, kind="hinted")

    # Real motors (these are the axes the pseudo positioner controls)
    x = FormattedComponent(EpicsMotorWithTweak, "{aero_prefix}m2")
    z = FormattedComponent(EpicsMotorWithTweak, "{aero_prefix}m1")

    # Theta readback only — EpicsSignalRO so it's NOT treated as a real positioner
    theta_readback = FormattedComponent(
        EpicsSignalRO, "{micronix_prefix}m4.RBV", kind="config"
    )

    def __init__(self, aero_prefix, micronix_prefix, *args, **kwargs):
        self.aero_prefix = aero_prefix
        self.micronix_prefix = micronix_prefix
        super().__init__(*args, **kwargs)

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        theta_rad = np.radians(self.theta_readback.get())
        x_real = pseudo_pos.scanning_x * np.cos(theta_rad)
        z_real = -pseudo_pos.scanning_x * np.sin(theta_rad)
        return self.RealPosition(x=x_real, z=z_real)

    @real_position_argument
    def inverse(self, real_pos):
        theta_rad = np.radians(self.theta_readback.get())
        scanning_x = real_pos.x * np.cos(theta_rad) - real_pos.z * np.sin(theta_rad)
        return self.PseudoPosition(scanning_x=scanning_x)

