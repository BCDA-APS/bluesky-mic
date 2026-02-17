
"""
Control a Keithley 2400 SourceMeter via Moxa RS232 (TCP to NPort) or direct serial.

Connection options:
  - Moxa NPort (TCP): use host and port, e.g. host='192.168.1.100', port=4001
  - Direct serial: use port path, e.g. port='/dev/ttyUSB0' or 'COM3'

Requires: pyserial
  pip install pyserial
"""

import re
import time
import csv
import logging
from typing import List, Optional, Tuple
import numpy as np

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    raise ImportError("Install pyserial: pip install pyserial")


# Default RS-232 settings for Keithley 2400 (see instrument setup menu)
DEFAULT_BAUD = 57600
DEFAULT_BYTESIZE = serial.EIGHTBITS
DEFAULT_PARITY = serial.PARITY_NONE
DEFAULT_STOPBITS = serial.STOPBITS_ONE
DEFAULT_TIMEOUT = 2.0
DEFAULT_WRITE_TIMEOUT = 2.0

HOST = "10.54.113.9"
logger = logging.getLogger(__name__)

class Keithley2400Error(Exception):
    """Raised when the instrument reports an error or a command fails."""
    pass


class Keithley2400:
    """
    Control interface for Keithley 2400 SourceMeter over RS-232 (direct or via Moxa NPort).
    """

    def __init__(
        self,
        port: Optional[str] = None,
        host: Optional[str] = HOST,
        port_number: int = 4004,
        baudrate: int = DEFAULT_BAUD,
        bytesize: int = DEFAULT_BYTESIZE,
        parity: str = DEFAULT_PARITY,
        stopbits: float = DEFAULT_STOPBITS,
        timeout: float = DEFAULT_TIMEOUT,
        write_timeout: float = DEFAULT_WRITE_TIMEOUT,
    ):
        """
        Open connection to the Keithley 2400.

        For Moxa NPort (TCP):
          host='192.168.1.100', port_number=4001
          Do not set 'port'.

        For direct serial (local COM or USB-RS232):
          port='/dev/ttyUSB0' (Linux/Mac) or port='COM3' (Windows)
          Do not set host/port_number.
        """
        self._ser: Optional[serial.Serial] = None
        self._opened_here = False
        self._port = port
        self._host = host
        self._port_number = port_number
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout
        self._write_timeout = write_timeout

        self.open()

        self.v_mpp = 0.0
        self.v_msp = 0.0
        self.v_app_mspt = 0.0
        self.max_power = 0.0
        self.start_time = 0.0
        self.alpha = 0.0
        self.mspt_t_start_list: List[float] = []
        self.mspt_t_end_list: List[float] = []
        self.mspt_j_start_list: List[float] = []
        self.mspt_j_end_list: List[float] = []
        self.pulse_index = 0
        self.next_pt_time = 0.0
        self.total_pulse_time = 0.0

    def open(self) -> None:
        """Open the serial/socket connection if it is not already open."""
        if self._ser is not None:
            return

        logger.info(f"host: {self._host}")
        if self._host is not None:
            # Moxa NPort: connect via TCP socket (pyserial socket URL)
            url = f"socket://{self._host}:{self._port_number}"
            self._ser = serial.serial_for_url(
                url,
                baudrate=self._baudrate,
                bytesize=self._bytesize,
                parity=self._parity,
                stopbits=self._stopbits,
                timeout=self._timeout,
                write_timeout=self._write_timeout,
            )
        elif self._port is not None:
            self._ser = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=self._bytesize,
                parity=self._parity,
                stopbits=self._stopbits,
                timeout=self._timeout,
                write_timeout=self._write_timeout,
            )
        else:
            raise ValueError("Provide either port= (serial path) or host= (Moxa IP).")

        self._opened_here = True
        # Terminators: Keithley 2400 typically uses CR+LF or LF on RS-232
        self._ser.write_termination = "\r\n"
        self._ser.readline()  # discard any leftover data

    def close(self) -> None:
        """Close the serial/socket connection."""
        if self._ser and self._opened_here:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
            self._opened_here = False

    def __enter__(self) -> "Keithley2400":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def write(self, cmd: str) -> None:
        """Send a SCPI command (no response expected)."""
        if not cmd.endswith("\n") and "\n" not in cmd:
            cmd = cmd.strip() + "\r\n"
        self._ser.write(cmd.encode("ascii"))

    def query(self, cmd: str, strip: bool = True) -> str:
        """Send a SCPI query and return the response."""
        self.write(cmd)
        time.sleep(0.01)
        out = self._ser.readline().decode("ascii", errors="replace")
        if strip:
            out = out.strip()
        return out

    def idn(self) -> str:
        """Return instrument identification (*IDN?)."""
        return self.query("*IDN?")

    def reset(self) -> None:
        """Reset instrument to default state (*RST)."""
        self.write("*RST")
        time.sleep(0.5)

    def clear(self) -> None:
        """Clear status (*CLS)."""
        self.write("*CLS")

    def error_query(self) -> Tuple[int, str]:
        """Return next error in queue (0, 'No error') if none. Returns (code, message)."""
        s = self.query(":SYST:ERR?")
        # Format: "+0, No error" or "-123, Message"
        m = re.match(r"\s*([+-]?\d+)\s*,\s*(.+)", s)
        if m:
            return int(m.group(1)), m.group(2).strip()
        return 0, s

    def check_errors(self) -> None:
        """Raise Keithley2400Error if the instrument has an error in the queue."""
        code, msg = self.error_query()
        if code != 0:
            raise Keithley2400Error(f"Keithley 2400 error {code}: {msg}")

    # --- Source configuration ---

    def set_source_voltage(self, level_volts: float) -> None:
        """Set source function to voltage and set level (V)."""
        self.write(f":SOUR:FUNC VOLT")
        self.write(f":SOUR:VOLT:LEV {level_volts:.6e}")
        # self.check_errors()

    def set_source_current(self, level_amps: float) -> None:
        """Set source function to current and set level (A)."""
        self.write(":SOUR:FUNC CURR")
        self.write(f":SOUR:CURR:LEV {level_amps:.6e}")
        self.check_errors()

    def set_compliance_voltage(self, volts: float) -> None:
        """Set voltage compliance limit when sourcing current (V)."""
        self.write(f":SENS:VOLT:PROT {volts:.6e}")
        self.check_errors()

    def set_compliance_current(self, amps: float) -> None:
        """Set current compliance limit when sourcing voltage (A)."""
        self.write(f":SENS:CURR:PROT {amps:.6e}")
        # self.check_errors()

    def output_on(self) -> None:
        """Enable output."""
        self.write(":OUTP ON")
        self.check_errors()

    def output_off(self) -> None:
        """Disable output."""
        self.write(":OUTP OFF")
        self.check_errors()

    def set_output_state(self, on: bool) -> None:
        """Set output on (True) or off (False)."""
        self.write(":OUTP ON" if on else ":OUTP OFF")
        self.check_errors()

    # --- Measurement configuration ---

    def set_measure_voltage(self) -> None:
        """Configure to measure voltage."""
        self.write(':SENS:FUNC "VOLT"')
        # self.check_errors()

    def set_measure_current(self) -> None:
        """Configure to measure current."""
        self.write(':SENS:FUNC "CURR"')
        # self.check_errors()

    def set_format_elements(self, *elements: str) -> None:
        """Set reading format elements, e.g. ('VOLT', 'CURR') for voltage and current."""
        elem_str = ",".join(elements)
        self.write(f":FORM:ELEM {elem_str}")
        # self.check_errors()

    def read(self) -> str:
        """Trigger one measurement and return the reading (string)."""
        return self.query(":READ?")

    def read_voltage_current(self) -> Tuple[float, float]:
        """Trigger one measurement; return (voltage_V, current_A). Configure format first if needed."""
        self.set_format_elements("VOLT", "CURR")
        s = self.read()
        parts = [float(x) for x in s.strip("\x13").strip("\x11").split(",")]
        parts = [float(x) for x in s.strip("\x13").strip("\x11").split(",")]
        if len(parts) >= 2:
            return parts[0], parts[1]
        if len(parts) == 1:
            return parts[0], 0.0
        raise Keithley2400Error(f"Unexpected READ? response: {s!r}")

    def ramp_to_voltage(self, target_v: float, steps: int = 30, pause: float = 0.02) -> None:
        """Ramp source voltage from current level to target_v over steps.
        Uses write-only commands per step (no query) so step delay matches pause."""
        current = self.query(":SOUR:VOLT:LEV?")
        try:
            start_v = float(current)
        except ValueError:
            start_v = 0.0
        self.write(":SOUR:FUNC VOLT")
        for i in range(1, steps + 1):
            v = start_v + (target_v - start_v) * i / steps
            self.write(f":SOUR:VOLT:LEV {v:.6e}")
            time.sleep(pause)
        self.check_errors()

    def ramp_to_current(self, target_a: float, steps: int = 30, pause: float = 0.02) -> None:
        """Ramp source current from current level to target_a over steps.
        Uses write-only commands per step (no query) so step delay matches pause."""
        current = self.query(":SOUR:CURR:LEV?")
        try:
            start_a = float(current)
        except ValueError:
            start_a = 0.0
        self.write(":SOUR:FUNC CURR")
        for i in range(1, steps + 1):
            a = start_a + (target_a - start_a) * i / steps
            self.write(f":SOUR:CURR:LEV {a:.6e}")
            time.sleep(pause)
        self.check_errors()

    def shutdown(self) -> None:
        """Ramp to zero and turn output off (safe shutdown)."""
        try:
            mode = self.query(":SOUR:FUNC?").strip().upper()
            if "CURR" in mode:
                self.ramp_to_current(0.0)
            else:
                self.ramp_to_voltage(0.0)
        except Exception:
            pass
        self.output_off()

    def get_source_voltage(self) -> float:
        """Return current source voltage level (V)."""
        return float(self.query(":SOUR:VOLT:LEV?"))

    def voltage_sweep(
        self,
        v_start: float,
        v_stop: float,
        steps: int,
        step_delay: float = 0.05,
        output_was_on: Optional[bool] = None,
    ) -> list:
        """
        Perform a voltage sweep: set source to voltage, then step from v_start to v_stop,
        trigger one reading at each step. Returns list of (voltage_V, current_A) tuples.

        If output_was_on is None, output is left as-is. If True/False, output is
        turned on at start and optionally restored at end.
        """
        self.set_source_voltage(v_start)
        self.set_format_elements("VOLT", "CURR")
        if not output_was_on:
            self.output_on()
            time.sleep(0.1)
        results = []
        for i in range(steps + 1):
            v = v_start + (v_stop - v_start) * i / max(steps, 1)
            self.write(f":SOUR:VOLT:LEV {v:.6e}")
            time.sleep(step_delay)
            v_read, i_read = self.read_voltage_current()
            logger.info(f"voltage:{v_read=}, current:{i_read=}")
            results.append((v_read, i_read))
        if output_was_on is False:
            self.ramp_to_voltage(0.0)
            self.output_off()
        return results

    def _ensure_start_time(self) -> None:
        if self.start_time == 0.0:
            self.start_time = time.time()

    def compute_alpha_from_mspt(self, j_initial: float, j_final: float, duration_s: float) -> float:
        if j_initial <= 0 or j_final <= 0 or duration_s <= 0:
            return 0.0
        return -float(np.log(j_final / j_initial)) / duration_s

    def update_alpha_from_mspt_cycles(
        self,
        t_start_list: List[float],
        t_end_list: List[float],
        j_start_list: List[float],
        j_end_list: List[float],
    ) -> float:
        total_time = 0.0
        weighted_alpha_sum = 0.0
        for i in range(len(t_start_list)):
            delta_t = t_end_list[i] - t_start_list[i]
            if delta_t <= 0:
                continue
            try:
                alpha_i = -float(np.log(j_end_list[i] / j_start_list[i])) / delta_t
            except Exception:
                continue
            weighted_alpha_sum += alpha_i * delta_t
            total_time += delta_t
        if total_time <= 0:
            return 0.0
        return weighted_alpha_sum / total_time

    @staticmethod
    def _linregress_simple(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
        if len(x) < 2 or len(y) < 2:
            raise ValueError("Need at least 2 points for linear fit.")
        slope, intercept = np.polyfit(x, y, 1)
        return float(slope), float(intercept)

    def run_jv_sweep(
        self,
        file_path: str,
        attempt: int = 1,
        max_attempts: int = 2,
        jv_duration: float = 50.0,
        n_value: float = 0.95,
        area: float = 0.0625,
        initial_pce_input: float = 100.0,
        jv_start: float = -0.1,
        jv_end: float = 1.3,
        voltage_step: float = 0.01,
        number_of_sweeps: int = 2,
    ) -> Optional[List[float]]:
        
        logger.info("JV Sweep Attempt %s", attempt)
        total_steps = int((jv_end - jv_start) / voltage_step) + 1
        total_sweeps = number_of_sweeps * total_steps
        stabilization_time = jv_duration / total_sweeps
        logger.info(f"Before sweep: {stabilization_time=}, {total_sweeps=}, {total_steps}")

        max_power_local = 0.0
        v_mpp_local = jv_start
        v_msp_local = 0.0

        self._ensure_start_time()
        self.output_on()
        measurements: List[Tuple[float, float]] = []

        with open(file_path, "a", newline="") as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                writer.writerow(
                    [
                        "Time",
                        "Voltage",
                        "Current (mA/cm²)",
                        "Mode",
                        "Comm Delay (ms)",
                        "Exec Time (ms)",
                        "Total Delay (ms)",
                    ]
                )
            for sweep_count in range(number_of_sweeps):
                if sweep_count % 2 == 0:
                    voltage = jv_start
                    while voltage <= jv_end:
                        self.set_source_voltage(voltage)
                        time.sleep(stabilization_time)
                        t0 = time.time()
                        _, current_a = self.read_voltage_current()
                        logger.info(f"voltage <= jv_end: Voltage:{round(voltage, 5)}, Current:{round(current_a,5)}")
                        total_delay = (time.time() - t0) * 1000.0
                        current_a = -current_a
                        power = voltage * current_a
                        if power > max_power_local:
                           max_power_local = power
                           v_mpp_local = voltage
                        measurement_time = time.time() - self.start_time
                        j_current = (current_a * 1000.0) / area
                        if j_current < -5.0:
                           sweep_end_voltage = voltage
                           break
                        sweep_end_voltage = jv_end
                        output = [
                            f"{measurement_time:.1f}",
                            f"{voltage:.3f}",
                            f"{j_current:.6f}",
                            "JVsweep",
                            f"{0.0:.3f}",
                            f"{total_delay:.3f}",
                            f"{total_delay:.3f}",
                        ]
                        writer.writerow(output)
                        measurements.append((voltage, j_current))
                        voltage += voltage_step
                        elapsed_time = time.time() - self.start_time
                        remaining_time = jv_duration - elapsed_time
                        remaining_sweeps = total_sweeps - (
                            sweep_count * total_steps + int((voltage - jv_start) / voltage_step)
                        )
                        if remaining_sweeps > 0:
                            stabilization_time = max(remaining_time / remaining_sweeps, 0.0)
                else:
                    voltage = sweep_end_voltage
                    while voltage >= jv_start:
                        self.set_source_voltage(voltage)
                        time.sleep(stabilization_time)
                        t0 = time.time()
                        _, current_a = self.read_voltage_current()
                        logger.info(f"Voltage >= jv_start: Voltage: {round(voltage, 5)}, Current: {round(current_a,5)}")
                        total_delay = (time.time() - t0) * 1000.0
                        current_a = -current_a
                        power = voltage * current_a
                        if power > max_power_local:
                           max_power_local = power
                           v_mpp_local = voltage
                        measurement_time = time.time() - self.start_time
                        j_current = (current_a * 1000.0) / area
                        output = [
                            f"{measurement_time:.1f}",
                            f"{voltage:.3f}",
                            f"{j_current:.6f}",
                            "JVsweep",
                            f"{0.0:.3f}",
                            f"{total_delay:.3f}",
                            f"{total_delay:.3f}",
                        ]
                        writer.writerow(output)
                        measurements.append((voltage, j_current))
                        voltage -= voltage_step
                        elapsed_time = time.time() - self.start_time
                        remaining_time = jv_duration - elapsed_time
                        remaining_sweeps = total_sweeps - (
                            sweep_count * total_steps + int((jv_end - voltage) / voltage_step)
                        )
                        if remaining_sweeps > 0:
                            stabilization_time = max(remaining_time / remaining_sweeps, 0.0)

        if not measurements:
            return None

        self.output_off()
        
        incident_power = initial_pce_input * area / 1000.0
        initial_pce = (max_power_local / incident_power) * 100.0 if incident_power != 0 else 0.0

        voltages = np.array([v for v, _ in measurements], dtype=float)
        currents = np.array([j for _, j in measurements], dtype=float)
        window = 3
        voc = 0.0
        rs = 0.0
        jsc = 0.0
        rsh = 0.0

        if len(currents) >= 2:
            idx_j_closest = int(np.argmin(np.abs(currents)))
            start_j = max(idx_j_closest - window, 0)
            end_j = min(idx_j_closest + window + 1, len(currents))
            j_slice = currents[start_j:end_j]
            v_slice = voltages[start_j:end_j]
            if len(j_slice) >= 2:
                slope_j, intercept_j = self._linregress_simple(j_slice, v_slice)
                voc = intercept_j
                rs = abs(slope_j)

        if len(voltages) >= 2:
            idx_v_closest = int(np.argmin(np.abs(voltages)))
            start_v = max(idx_v_closest - window, 0)
            end_v = min(idx_v_closest + window + 1, len(voltages))
            v_slice = voltages[start_v:end_v]
            j_slice = currents[start_v:end_v]
            if len(v_slice) >= 2:
                slope_v, intercept_v = self._linregress_simple(v_slice, j_slice)
                jsc = intercept_v
                rsh = abs(1.0 / slope_v) if slope_v != 0 else 0.0

        power_array = voltages * (currents / area)
        idx_max_power = int(np.argmax(power_array))
        vmp = float(voltages[idx_max_power])
        jmp = float(currents[idx_max_power])
        ff = (100.0 * vmp * jmp) / (voc * jsc) if (voc * jsc) != 0 else 0.0

        with np.errstate(divide="ignore", invalid="ignore"):
            denominator = (voltages + currents * rs) ** n_value
            metric = np.where(denominator != 0, voltages * currents / denominator, 0.0)
        if np.any(metric):
            idx_max_vsp = int(np.argmax(metric))
            v_msp_local = float(voltages[idx_max_vsp])
        else:
            v_msp_local = 0.0

        characteristics = [initial_pce, voc, jsc, rsh, rs, ff, vmp, jmp, v_msp_local, v_mpp_local]

        with open(file_path, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["", "", "", "", "Characteristics"])
            writer.writerow(
                [
                    "",
                    "",
                    "",
                    "",
                    "Initial PCE (%)",
                    "Voc (V)",
                    "Jsc (mA/cm²)",
                    "Rsh (Ohm)",
                    "Rs (Ohm)",
                    "FF (%)",
                    "Vmp (V)",
                    "Jmp (mA/cm²)",
                    "V_msp (V)",
                    "V_mpp (V)",
                ]
            )
            writer.writerow(
                [
                    "",
                    "",
                    "",
                    "",
                    f"{initial_pce:.3f}",
                    f"{voc:.4f}",
                    f"{jsc:.4f}",
                    f"{rsh:.4f}",
                    f"{rs:.4f}",
                    f"{ff:.2f}",
                    f"{vmp:.4f}",
                    f"{jmp:.6f}",
                    f"{v_msp_local:.4f}",
                    f"{v_mpp_local:.4f}",
                ]
            )

        self.v_mpp = v_mpp_local
        self.v_msp = v_msp_local
        self.max_power = max_power_local

        in_range = -2.0 <= self.v_mpp <= 2.05 and -2.0 <= self.v_msp <= 2.05
        if not in_range:
            if attempt < max_attempts:
                return self.run_jv_sweep(
                    file_path=file_path,
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    jv_duration=jv_duration,
                    n_value=n_value,
                    area=area,
                    initial_pce_input=initial_pce_input,
                )
            raise Keithley2400Error("V_mpp and/or V_msp out of expected range after retries.")
        return characteristics

    def run_mspt(
        self,
        file_path: str,
        duration: float,
        area: float = 0.0625,
        stabilization_time: float = 0.5,
        delta_v_threshold: float = 0.5,
    ) -> None:
        if self.v_msp == 0.0:
            self.logger.warning("V_msp is not set. Run JV sweep first.")
            return
        self._ensure_start_time()
        self.output_on()
        if self.v_app_mspt == 0.0:
            self.v_app_mspt = self.v_msp
        self.set_source_voltage(self.v_app_mspt)

        cycle_measurements: List[Tuple[float, float]] = []
        end_time_cycle = time.time() + duration
        while time.time() < end_time_cycle:
            t0 = time.time()
            _, current_a = self.read_voltage_current()
            total_delay = (time.time() - t0) * 1000.0
            current_a = -current_a
            meas_time = time.time() - self.start_time
            j_current = (current_a * 1000.0) / area
            cycle_measurements.append((meas_time, j_current))
            with open(file_path, "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    [
                        f"{meas_time:.1f}",
                        f"{self.v_app_mspt:.3f}",
                        f"{j_current:.6f}",
                        "MSPT",
                        f"{0.0:.3f}",
                        f"{total_delay:.3f}",
                        f"{total_delay:.3f}",
                    ]
                )
            time.sleep(stabilization_time)

        if len(cycle_measurements) < 2:
            return

        t_initial, j_initial = cycle_measurements[0]
        t_final, j_final = cycle_measurements[-1]
        self.mspt_t_start_list.append(t_initial)
        self.mspt_j_start_list.append(j_initial)
        self.mspt_t_end_list.append(t_final)
        self.mspt_j_end_list.append(j_final)
        self.alpha = self.update_alpha_from_mspt_cycles(
            self.mspt_t_start_list,
            self.mspt_t_end_list,
            self.mspt_j_start_list,
            self.mspt_j_end_list,
        )
        delta_v = abs(self.v_app_mspt - self.v_msp)
        if delta_v >= delta_v_threshold:
            self.v_app_mspt = (1.0 - self.alpha) * self.v_msp + self.alpha * self.v_app_mspt
        else:
            self.v_app_mspt = self.v_msp

    def run_pt(
        self,
        file_path: str,
        pulse_intervals: List[float],
        pulse_voltages: List[float],
        pulse_durations: List[float],
        area: float = 0.0625,
        stabilization_time_initial: float = 0.7,
    ) -> None:
        self._ensure_start_time()
        self.output_on()
        pulse_voltage = pulse_voltages[min(self.pulse_index, len(pulse_voltages) - 1)]
        pulse_duration = pulse_durations[min(self.pulse_index, len(pulse_durations) - 1)]
        pt_start_time = time.time()
        self.set_source_voltage(pulse_voltage)

        with open(file_path, "a", newline="") as file:
            writer = csv.writer(file)
            while time.time() - pt_start_time < pulse_duration:
                t0 = time.time()
                _, current_a = self.read_voltage_current()
                total_delay = (time.time() - t0) * 1000.0
                measurement_time = time.time() - self.start_time
                writer.writerow(
                    [
                        f"{measurement_time:.1f}",
                        f"{pulse_voltage:.3f}",
                        f"{current_a * 1000.0 / area:.6f}",
                        "PT",
                        f"{0.0:.3f}",
                        f"{total_delay:.3f}",
                        f"{total_delay:.3f}",
                    ]
                )
                time.sleep(stabilization_time_initial)

        self.total_pulse_time += pulse_intervals[self.pulse_index] + pulse_duration
        if self.pulse_index < len(pulse_intervals) - 1:
            self.pulse_index += 1
        try:
            self.next_pt_time = (
                self.start_time
                + ((time.time() - self.start_time) // pulse_intervals[self.pulse_index] + 1)
                * pulse_intervals[self.pulse_index]
                + pulse_durations[self.pulse_index]
            )
        except IndexError:
            self.next_pt_time = float("inf")

    def run_mppt(
        self,
        file_path: str,
        duration: float,
        area: float = 0.0625,
        stabilization_time: float = 0.5,
    ) -> None:
        if self.v_mpp == 0.0:
            self.logger.warning("V_mpp is not set. Run JV sweep first.")
            return
        self._ensure_start_time()
        self.output_on()
        self.set_source_voltage(self.v_mpp)

        end_time = time.time() + duration
        while time.time() < end_time:
            t0 = time.time()
            _, current_a = self.read_voltage_current()
            logger.info(f"MPPT voltage: {round(self.v_mpp, 5)}, current: {round(current_a,5)}")
            total_delay = (time.time() - t0) * 1000.0
            measurement_time = time.time() - self.start_time
            j_current = (current_a * 1000.0) / area
            with open(file_path, "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    [
                        f"{measurement_time:.2f}",
                        f"{self.v_mpp:.3f}",
                        f"{j_current:.6f}",
                        "MPPT",
                        f"{0.0:.3f}",
                        f"{total_delay:.3f}",
                        f"{total_delay:.3f}",
                    ]
                )
            time.sleep(stabilization_time)

    # Compatibility wrappers using original script naming.
    def compute_alpha_from_MSPT(self, J_initial: float, J_final: float, T: float) -> float:
        return self.compute_alpha_from_mspt(J_initial, J_final, T)

    def update_alpha_from_MSPT_cycles(
        self,
        T_start_list: List[float],
        T_end_list: List[float],
        J_start_list: List[float],
        J_end_list: List[float],
    ) -> float:
        return self.update_alpha_from_mspt_cycles(T_start_list, T_end_list, J_start_list, J_end_list)

    def run_JV_sweep(self, file_path: str, **kwargs) -> Optional[List[float]]:
        return self.run_jv_sweep(file_path=file_path, **kwargs)

    def run_MSPT(self, file_path: str, duration: float, **kwargs) -> None:
        self.run_mspt(file_path=file_path, duration=duration, **kwargs)

    def run_pulsatile_therapy(self, file_path: str, **kwargs) -> None:
        self.run_pt(file_path=file_path, **kwargs)

    def run_MPPT(self, file_path: str, duration: float, **kwargs) -> None:
        self.run_mppt(file_path=file_path, duration=duration, **kwargs)
