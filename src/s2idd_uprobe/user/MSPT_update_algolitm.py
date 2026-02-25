#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 23 19:36:57 2024
Modified on 2025-02-20
@author: gk
"""

import csv
import time
import numpy as np
from scipy import stats
import sys
import os
# import pyvisa
import logging

# -------------------- Experiment Parameters --------------------
USER_DESKTOP = os.path.join(os.environ.get('USERPROFILE', '.'), 'Desktop')
CSV_NAME = '20251231_CELIV_test2.csv'
FILE_PATH = os.path.join(USER_DESKTOP, CSV_NAME)

JV_DURATION = 50.0          # 전체 JV 스윕 기간 (초)
N_VALUE = 0.95              # VJ/(V+JRs)^n 계산에 사용되는 n 값
AREA = 0.0625               # 셀 면적 (cm²)
INITIAL_PCE_INPUT = 100     # 초기 입사 전력 밀도 (mW/cm²)

DURATION_MODE = 10750.0     # MPPT/MSPT 모드 측정 기간 (초)
EXPERIMENT_MODE = 'MSPT'    # 'MPPT', 'MSPT', 'PT' 중 선택

DELTA_V_THRESHOLD = 0.5    # 전압 변화 임계치 (V)

# Pulsatile Therapy 관련 파라미터
pulse_intervals = [180000, 1800, 1800]  # PT 주기 (초)
pulse_voltages = [-0.2, -0.2, -0.2]       # PT 전압 값 (V)
pulse_durations = [30, 30, 30]            # PT 지속 시간 (초)
stabilization_time_initial = 0.7          # 초기 안정화 시간 (초)

# -------------------- Global Variables --------------------
V_mpp = 0.0         # JV 스윕을 통해 산출된 최대 전력점 전압
V_msp = 0.0         # JV 스윕을 통해 산출된 MSPT 기준 전압
V_app_MSPT = 0.0    # MSPT 모드에서 실제 적용할 보간 전압
max_power = 0.0
start_time = 0.0

# MSPT 구간별 누적 데이터 (각 MSPT 구간마다 최초/최종 데이터 1쌍씩 추가)
MSPT_T_start_list = []   # 각 구간 시작 시각
MSPT_T_end_list = []     # 각 구간 종료 시각
MSPT_J_start_list = []   # 각 구간 시작 전류밀도 (mA/cm²)
MSPT_J_end_list = []     # 각 구간 종료 전류밀도 (mA/cm²)

ALPHA = 0.0          # 누적 MSPT 구간 열화 상수 (time-weighted average)

pulse_index = 0
next_pt_time = 0.0
total_pulse_time = 0.0

# -------------------- Logging Setup --------------------
# 기본 로깅 설정: 콘솔과 파일에 동시에 출력
log_name = 'instrument_communication.log'
log_path = os.path.join(USER_DESKTOP, log_name)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# 콘솔 핸들러
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)

# 파일 핸들러
fh = logging.FileHandler(log_path, mode='a')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

# -------------------- MSPT Alpha Update Functions --------------------
def compute_alpha_from_MSPT(J_initial, J_final, T):
    """
    MSPT 구동 동안의 초기 전류밀도 J_initial와 종료 전류밀도 J_final, 구동 시간 T를 이용해
    exponential decay 모델(J = J0 * exp(-alpha*T))에서 alpha를 계산.
    """
    if J_initial <= 0 or J_final <= 0:
        logging.warning("전류밀도 값이 0 이하입니다. alpha 계산 불가.")
        return 0.0
    alpha = - (1.0 / T) * np.log(J_final / J_initial)
    return alpha

def update_alpha_from_MSPT_cycles(T_start_list, T_end_list, J_start_list, J_end_list):
    """
    각 MSPT 구간에 대해 alpha_i = -1/(T_end - T_start) * ln(J_end/J_start)를 계산하고,
    전체 구간에 대해 시간 가중 평균(alpha_cum)을 계산.
    """
    total_time = 0.0
    weighted_alpha_sum = 0.0
    for i in range(len(T_start_list)):
        deltaT = T_end_list[i] - T_start_list[i]
        if deltaT <= 0:
            continue
        try:
            alpha_i = - (1.0 / deltaT) * np.log(J_end_list[i] / J_start_list[i])
        except Exception as e:
            logging.warning(f"Alpha 계산 에러 (구간 {i}): {e}")
            continue
        weighted_alpha_sum += alpha_i * deltaT
        total_time += deltaT
    if total_time > 0:
        return weighted_alpha_sum / total_time
    else:
        return 0.0

# -------------------- Function Definitions --------------------
def run_JV_sweep(keithley2400_1, file_path, attempt=1, max_attempts=2, JV_duration=JV_DURATION, n=N_VALUE):
    global V_mpp, V_msp, max_power, start_time
    logging.info(f"JV Sweep Attempt {attempt}")

    JV_start = -0.1
    JV_end = 1.3
    voltage_step = 0.01
    number_of_sweeps = 2
    area = AREA
    initial_PCE_input = INITIAL_PCE_INPUT

    total_steps = int((JV_end - JV_start) / voltage_step) + 1
    total_sweeps = number_of_sweeps * total_steps
    stabilization_time = JV_duration / total_sweeps

    max_power_local = 0.0
    V_mpp_local = JV_start
    V_msp_local = 0.0  # 미리 초기화

    if start_time == 0.0:
        start_time = time.time()
        logging.info(f"Measurement started at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")

    measurements = []
    try:
        with open(file_path, 'a', newline='') as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                writer.writerow(["Time", "Voltage", "Current (mA/cm²)", "Mode", "Comm Delay (ms)", "Exec Time (ms)", "Total Delay (ms)"])
            for sweep_count in range(number_of_sweeps):
                if sweep_count % 2 == 0:  # 포워드 스캔
                    voltage = JV_start
                    while voltage <= JV_end:
                        try:
                            keithley2400_1.write(f"SOUR:VOLT {voltage}")
                            logging.debug(f"Set voltage to {voltage} V")
                        except Exception as e:
                            logging.error(f"Failed to set voltage: {e}")
                            voltage += voltage_step
                            continue
                        time.sleep(stabilization_time)
                        try:
                            write_time = time.time()
                            keithley2400_1.write("MEAS:CURR?")
                            read_start_time = time.time()
                            current_response = keithley2400_1.read()
                            read_end_time = time.time()
                            current = float(current_response.split(',')[1])
                            current = -current
                            logging.debug(f"Measured current: {current} A")
                            comm_delay = (read_start_time - write_time) * 1000  # ms
                            exec_time = (read_end_time - read_start_time) * 1000  # ms
                            total_delay = (read_end_time - write_time) * 1000  # ms
                        except Exception as e:
                            logging.error(f"JV Sweep - 전류 측정 오류: {e}")
                            current = 0.0
                            comm_delay = 0.0
                            exec_time = 0.0
                            total_delay = 0.0
                        power = voltage * current
                        if power > max_power_local:
                            max_power_local = power
                            V_mpp_local = voltage
                            logging.debug(f"New max power: {max_power_local} W at {V_mpp_local} V")
                        measurement_time = time.time() - start_time
                        j_current = (current * 1000) / area
                        if j_current < -5.0:
                            logging.warning(f"J={j_current:.2f} mA/cm² < -5 mA/cm². Terminating current sweep.")
                            sweep_end_voltage = voltage
                            break
                        sweep_end_voltage = JV_end
                        output = [f"{measurement_time:.1f}", f"{voltage:.3f}", f"{j_current:.6f}", "JVsweep", f"{comm_delay:.3f}", f"{exec_time:.3f}", f"{total_delay:.3f}"]
                        logging.info(output)
                        writer.writerow(output)
                        measurements.append((voltage, j_current))
                        voltage += voltage_step
                        elapsed_time = time.time() - start_time
                        remaining_time = JV_duration - elapsed_time
                        remaining_sweeps = total_sweeps - (sweep_count * total_steps + int((voltage - JV_start) / voltage_step))
                        if remaining_sweeps > 0:
                            stabilization_time = max(remaining_time / remaining_sweeps, 0)
                else:  # 백워드 스캔
                    voltage = sweep_end_voltage
                    while voltage >= JV_start:
                        try:
                            keithley2400_1.write(f"SOUR:VOLT {voltage}")
                            logging.debug(f"Set voltage to {voltage} V")
                        except Exception as e:
                            logging.error(f"Failed to set voltage: {e}")
                            voltage -= voltage_step
                            continue
                        time.sleep(stabilization_time)
                        try:
                            write_time = time.time()
                            keithley2400_1.write("MEAS:CURR?")
                            read_start_time = time.time()
                            current_response = keithley2400_1.read()
                            read_end_time = time.time()
                            current = float(current_response.split(',')[1])
                            current = -current
                            logging.debug(f"Measured current: {current} A")
                            comm_delay = (read_start_time - write_time) * 1000  # ms
                            exec_time = (read_end_time - read_start_time) * 1000  # ms
                            total_delay = (read_end_time - write_time) * 1000  # ms
                        except Exception as e:
                            logging.error(f"JV Sweep - 전류 측정 오류: {e}")
                            current = 0.0
                            comm_delay = 0.0
                            exec_time = 0.0
                            total_delay = 0.0
                        power = voltage * current
                        if power > max_power_local:
                            max_power_local = power
                            V_mpp_local = voltage
                            logging.debug(f"New max power: {max_power_local} W at {V_mpp_local} V")
                        measurement_time = time.time() - start_time
                        j_current = (current * 1000) / area
                        output = [f"{measurement_time:.1f}", f"{voltage:.3f}", f"{j_current:.6f}", "JVsweep", f"{comm_delay:.3f}", f"{exec_time:.3f}", f"{total_delay:.3f}"]
                        logging.info(output)
                        writer.writerow(output)
                        measurements.append((voltage, j_current))
                        voltage -= voltage_step
                        elapsed_time = time.time() - start_time
                        remaining_time = JV_duration - elapsed_time
                        remaining_sweeps = total_sweeps - (sweep_count * total_steps + int((JV_end - voltage) / voltage_step))
                        if remaining_sweeps > 0:
                            stabilization_time = max(remaining_time / remaining_sweeps, 0)
    except IOError as e:
        logging.error(f"Failed to write to CSV file: {e}")
        return None

    if not measurements:
        logging.warning("No measurements were taken.")
        return None

    incident_power = initial_PCE_input * area / 1000
    initial_PCE = (max_power_local / incident_power) * 100 if incident_power != 0 else 0

    voltages = np.array([v for v, j in measurements])
    currents = np.array([j for v, j in measurements])
    window=3
   
    if len(currents) < 2:
        # 최소 2개 이상 있어야 linregress가 의미 있게 동작
        logging.warning("Insufficient data points for Voc/Rs extraction.")
    else:
        idx_j_closest = np.argmin(np.abs(currents))  # J=0에 가장 가까운 점의 인덱스
        # window=3이면, idx_j_closest를 중심으로 앞뒤로 3개씩 => 최대 7개
        start_j = max(idx_j_closest - window, 0)
        end_j   = min(idx_j_closest + window + 1, len(currents))  # slice는 end 인덱스를 포함하지 않으니 +1
        # 해당 구간 slice
        j_slice = currents[start_j:end_j]
        v_slice = voltages[start_j:end_j]

        if len(j_slice) < 2:
            logging.warning("Not enough data in the selected J=0 window slice.")
        else:
            slope_j, intercept_j, _, _, _ = stats.linregress(j_slice, v_slice)
            # slope_j = dV/dJ, intercept_j = V when J=0
            Voc = intercept_j
            Rs  = abs(slope_j)
            
    if len(voltages) < 2:
        logging.warning("Insufficient data points for Jsc/Rsh extraction.")
    else:
        idx_v_closest = np.argmin(np.abs(voltages))  # V=0에 가장 가까운 점의 인덱스
        # window=3이면, idx_v_closest를 중심으로 앞뒤로 3개씩 => 최대 7개
        start_v = max(idx_v_closest - window, 0)
        end_v   = min(idx_v_closest + window + 1, len(voltages))
        # 해당 구간 slice
        v_slice = voltages[start_v:end_v]
        j_slice = currents[start_v:end_v]

        if len(v_slice) < 2:
            logging.warning("Not enough data in the selected V=0 window slice.")
        else:
            slope_v, intercept_v, _, _, _ = stats.linregress(v_slice, j_slice)
            # slope_v = dJ/dV, intercept_v = J when V=0
            Jsc = intercept_v
            Rsh = abs(1.0 / slope_v) if slope_v != 0 else 0.0

    power_array = voltages * (currents / area)
    idx_max_power = np.argmax(power_array)
    Vmp = voltages[idx_max_power]
    Jmp = currents[idx_max_power]
    FF = (100 * Vmp * Jmp) / (Voc * Jsc) if (Voc * Jsc) != 0 else 0

    with np.errstate(divide='ignore', invalid='ignore'):
        denominator = (voltages + currents * Rs) ** n
        VJ_over_V_plus_JRs = np.where(denominator != 0, voltages * currents / denominator, 0)
    finite_mask = np.isfinite(VJ_over_V_plus_JRs)
    if np.any(finite_mask):
        valid_values = VJ_over_V_plus_JRs[finite_mask]
        valid_voltages = voltages[finite_mask]
        idx_max_vsp = np.argmax(valid_values)
        V_msp_local = valid_voltages[idx_max_vsp]
    else:
        V_msp_local = 0.0
        logging.warning("Unable to calculate V_msp due to no finite metric values.")

    characteristics = [
        initial_PCE, Voc, Jsc, Rsh, Rs, FF, Vmp, Jmp, V_msp_local, V_mpp_local
    ]

    try:
        with open(file_path, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["", "", "", "", "Characteristics"])
            writer.writerow(["", "", "", "", "Initial PCE (%)", "Voc (V)", "Jsc (mA/cm²)", "Rsh (Ohm)", "Rs (Ohm)", "FF (%)", "Vmp (V)", "Jmp (mA/cm²)", "V_msp (V)", "V_mpp (V)"])
            writer.writerow(["", "", "", "", f"{initial_PCE:.3f}", f"{Voc:.4f}", f"{Jsc:.4f}", f"{Rsh:.4f}", f"{Rs:.4f}", f"{FF:.2f}", f"{Vmp:.4f}", f"{Jmp:.6f}", f"{V_msp_local:.4f}", f"{V_mpp_local:.4f}"])
    except IOError as e:
        logging.error(f"Failed to write characteristics to CSV: {e}")

    V_mpp = V_mpp_local
    V_msp = V_msp_local
    max_power = max_power_local

    logging.info(
    f"JV Sweep Characteristics:\n"
    f"  PCE={initial_PCE:.3f}%, FF={FF:.2f}%,\n"
    f"  Voc={Voc:.4f} V, Jsc={Jsc:.4f} mA/cm²,\n"
    f"  Rsh={Rsh:.4f} Ω, Rs={Rs:.4f} Ω,\n"
    f"  Vmp={Vmp:.4f} V, Jmp={Jmp:.6f} mA/cm²,\n"
    f"  V_msp={V_msp_local:.4f} V, V_mpp={V_mpp_local:.4f} V"
)

    def is_within_range(value, lower=-2, upper=2.05):
        return lower <= value <= upper

    if not (is_within_range(V_mpp) and is_within_range(V_msp)):
        logging.warning(f"V_mpp ({V_mpp:.2f} V) or V_msp ({V_msp:.2f} V) out of range.")
        if attempt < max_attempts:
            logging.info("Re-running JV Sweep due to out-of-range values.")
            return run_JV_sweep(keithley2400_1, file_path, attempt=attempt+1, max_attempts=max_attempts, JV_duration=JV_duration, n=n)
        else:
            logging.error("V_mpp and V_msp are still out of range after 2 attempts. Please replace the sample.")
            sys.exit("Critical Error: V_mpp and V_msp out of range. Experiment stopped.")
    return characteristics

def run_MSPT(keithley2400_1, file_path, duration, area=AREA, stabilization_time=0.5):
    global V_msp, start_time, V_app_MSPT, ALPHA, MSPT_T_start_list, MSPT_T_end_list, MSPT_J_start_list, MSPT_J_end_list
    if V_msp == 0.0:
        logging.warning("V_msp is not set. Please run JV Sweep first.")
        return

    cycle_measurements = []  # (time, j_current) 쌍

    if V_app_MSPT == 0.0:
        V_app_MSPT = V_msp

    try:
        keithley2400_1.write(f"SOUR:VOLT {V_app_MSPT}")
        logging.info(f"Applying V_app (MSPT): {V_app_MSPT:.3f} V")
    except Exception as e:
        logging.error(f"MSPT - 전압 설정 오류: {e}")
        return

    T_cycle_start = time.time() - start_time
    end_time_cycle = time.time() + duration
    while time.time() < end_time_cycle:
        try:
            write_time_curr = time.time()
            keithley2400_1.write("MEAS:CURR?")
            read_start_time_curr = time.time()
            current_response = keithley2400_1.read()
            read_end_time_curr = time.time()
            current = float(current_response.split(',')[1])
            current = -current
            
            write_time_volt = time.time()
            keithley2400_1.write("MEAS:VOLT?")
            read_start_time_volt = time.time()
            voltage_response = keithley2400_1.read()
            read_end_time_volt = time.time()
            voltage = float(voltage_response.split(',')[0])
            
            meas_time = time.time() - start_time
            j_current = (current * 1000) / area
            cycle_measurements.append((meas_time, j_current))
            
            # 현재 측정의 통신 지연 사용 (MEAS:CURR? 기준)
            comm_delay = (read_start_time_curr - write_time_curr) * 1000  # ms
            exec_time = (read_end_time_curr - read_start_time_curr) * 1000  # ms
            total_delay = (read_end_time_curr - write_time_curr) * 1000  # ms
            
            output = [f"{meas_time:.1f}", f"{V_app_MSPT:.3f}", f"{j_current:.6f}", "MSPT", f"{comm_delay:.3f}", f"{exec_time:.3f}", f"{total_delay:.3f}"]
            logging.info(output)
            with open(file_path, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(output)
        except Exception as e:
            logging.error(f"MSPT - 측정 오류: {e}")
        time.sleep(stabilization_time)

    if len(cycle_measurements) < 2:
        logging.warning("MSPT 구간 동안 충분한 측정값이 없습니다.")
        return
    T_initial, J_initial = cycle_measurements[0]
    T_final, J_final = cycle_measurements[-1]
    MSPT_T_start_list.append(T_initial)
    MSPT_J_start_list.append(J_initial)
    MSPT_T_end_list.append(T_final)
    MSPT_J_end_list.append(J_final)

    # 구간 전체에 대해 time-weighted average로 α 업데이트
    ALPHA = update_alpha_from_MSPT_cycles(MSPT_T_start_list, MSPT_T_end_list, MSPT_J_start_list, MSPT_J_end_list)
    logging.info(f"MSPT: Updated dynamic α from cumulative cycles: {ALPHA:.3e}")

    delta_V = abs(V_app_MSPT - V_msp)
    if delta_V >= DELTA_V_THRESHOLD:
        V_app_MSPT = (1 - ALPHA) * V_msp + ALPHA * V_app_MSPT
        logging.info(f"MSPT: 큰 전압 변화({delta_V:.3f} V)가 감지되어 보간 적용. 새로운 V_app = {V_app_MSPT:.3f} V")
    else:
        V_app_MSPT = V_msp

    logging.info(f"MSPT 구간 종료 후 최종 V_app = {V_app_MSPT:.3f} V")

def run_pulsatile_therapy(keithley2400_1, file_path):
    global pulse_index, next_pt_time, total_pulse_time, V_mpp, V_msp
    pt_start_time = time.time()
    pulse_voltage = pulse_voltages[min(pulse_index, len(pulse_voltages) - 1)]
    pulse_duration = pulse_durations[min(pulse_index, len(pulse_durations) - 1)]
    try:
        keithley2400_1.write(f"SOUR:VOLT {pulse_voltage}")
        logging.debug(f"Pulsatile Therapy: Set voltage to {pulse_voltage} V")
    except Exception as e:
        logging.error(f"Pulsatile Therapy - 전압 설정 오류: {e}")
        return
    try:
        file_obj = open(file_path, 'a')
    except IOError as e:
        logging.error(f"Pulsatile Therapy - 파일 열기 오류: {e}")
        return
    with file_obj:
        writer = csv.writer(file_obj)
        while time.time() - pt_start_time < pulse_duration:
            try:
                write_time_curr = time.time()
                keithley2400_1.write("MEAS:CURR?")
                read_start_time_curr = time.time()
                current_response = keithley2400_1.read()
                read_end_time_curr = time.time()
                current = float(current_response.split(',')[1])
                
                write_time_volt = time.time()
                keithley2400_1.write("MEAS:VOLT?")
                read_start_time_volt = time.time()
                voltage_response = keithley2400_1.read()
                read_end_time_volt = time.time()
                voltage = float(voltage_response.split(',')[0])
                
                measurement_time = time.time() - start_time
                
                # 현재 측정의 통신 지연 사용 (MEAS:CURR? 기준)
                comm_delay = (read_start_time_curr - write_time_curr) * 1000  # ms
                exec_time = (read_end_time_curr - read_start_time_curr) * 1000  # ms
                total_delay = (read_end_time_curr - write_time_curr) * 1000  # ms
                
                output = [f"{measurement_time:.1f}", f"{pulse_voltage:.3f}", f"{current * 1000 / AREA:.6f}", "PT", f"{comm_delay:.3f}", f"{exec_time:.3f}", f"{total_delay:.3f}"]
                logging.info(output)
                writer.writerow(output)
                time.sleep(stabilization_time_initial)
            except Exception as e:
                logging.error(f"Pulsatile Therapy - 측정 오류: {e}")
                break
    total_pulse_time += (pulse_intervals[pulse_index] + pulse_duration)
    if pulse_index < len(pulse_intervals) - 1:
        pulse_index += 1
    try:
        next_pt_time = start_time + ((time.time() - start_time) // pulse_intervals[pulse_index] + 1) * pulse_intervals[pulse_index] + pulse_durations[pulse_index]
    except IndexError:
        next_pt_time = float('inf')
    logging.info(f"Pulsatile Therapy completed. Next PT time set to {next_pt_time}.")

def run_MPPT(keithley2400_1, file_path, duration, area=AREA, stabilization_time=0.5):
    global V_mpp, start_time
    if V_mpp == 0.0:
        logging.warning("V_mpp is not set. Please run JV Sweep first.")
        return
    try:
        keithley2400_1.write(f"SOUR:VOLT {V_mpp}")
        logging.info(f"Applying V_mpp: {V_mpp:.3f} V")
    except Exception as e:
        logging.error(f"MPPT - 전압 설정 오류: {e}")
        return
    end_time = time.time() + duration
    while time.time() < end_time:
        try:
            write_time_curr = time.time()
            keithley2400_1.write("MEAS:CURR?")
            read_start_time_curr = time.time()
            current_response = keithley2400_1.read()
            read_end_time_curr = time.time()
            current = float(current_response.split(',')[1])
            
            write_time_volt = time.time()
            keithley2400_1.write("MEAS:VOLT?")
            read_start_time_volt = time.time()
            voltage_response = keithley2400_1.read()
            read_end_time_volt = time.time()
            voltage = float(voltage_response.split(',')[0])
            
            measurement_time = time.time() - start_time
            j_current = (current * 1000) / area
            
            # 현재 측정의 통신 지연 사용 (MEAS:CURR? 기준)
            comm_delay = (read_start_time_curr - write_time_curr) * 1000  # ms
            exec_time = (read_end_time_curr - read_start_time_curr) * 1000  # ms
            total_delay = (read_end_time_curr - write_time_curr) * 1000  # ms
            
            output = [f"{measurement_time:.2f}", f"{V_mpp:.3f}", f"{j_current:.6f}", "MPPT", f"{comm_delay:.3f}", f"{exec_time:.3f}", f"{total_delay:.3f}"]
            logging.info(output)
            with open(file_path, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(output)
        except Exception as e:
            logging.error(f"MPPT - 측정 오류: {e}")
        time.sleep(stabilization_time)

def main():
    try:
        rm = pyvisa.ResourceManager()
        logging.info("PyVISA Resource Manager initialized successfully.")
    except Exception as e:
        logging.exception("Failed to initialize PyVISA Resource Manager")
        sys.exit("Critical Error: PyVISA initialization failed.")

    try:
        desktop_path = os.path.join(os.environ.get('USERPROFILE', '.'), 'Desktop')
        csv_name = CSV_NAME
        file_path = os.path.join(desktop_path, csv_name)
        logging.info(f"CSV file will be saved to: {file_path}")
    except Exception as e:
        logging.exception("Failed to define file path")
        sys.exit("Critical Error: File path setup failed.")

    def find_rs232_device():
        resources = rm.list_resources()
        logging.debug(f"Available resources: {resources}")
        for resource in resources:
            if 'ASRL' in resource:
                return resource
        return None

    rs232_address = find_rs232_device()
    if rs232_address is None:
        logging.error("No RS232 devices found.")
        sys.exit("Critical Error: No RS232 devices found.")

    try:
        keithley2400_1 = rm.open_resource(rs232_address)
        logging.info(f"Keithley2400 initialized successfully at address {rs232_address}.")
        keithley2400_1.timeout = 5000
        keithley2400_1.read_termination = '\n'
        keithley2400_1.write_termination = '\n'
        idn_response = keithley2400_1.query("*IDN?")
        logging.info(f"Instrument ID: {idn_response.strip()}")
    except Exception as e:
        logging.exception("Failed to initialize Keithley2400")
        sys.exit("Critical Error: Keithley2400 initialization failed.")

    global start_time
    start_time = time.time()
    logging.info(f"Measurement started at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")

    logging.info(f"Selected mode: {EXPERIMENT_MODE}")
    if EXPERIMENT_MODE not in ['MPPT', 'MSPT', 'PT']:
        logging.error(f"Invalid mode selected: {EXPERIMENT_MODE}.")
        sys.exit("Critical Error: Invalid mode selected.")

    logging.info("Entering the measurement loop. Press Ctrl+C to stop.")
    try:
        while True:
            try:
                characteristics = run_JV_sweep(keithley2400_1, file_path, JV_duration=JV_DURATION, n=N_VALUE)
                if characteristics:
                    logging.info(f"JV Sweep completed successfully: {characteristics}")
            except SystemExit as e:
                logging.error(e)
                break
            except Exception as e:
                logging.exception(f"An unexpected error occurred during JV Sweep: {e}")
                continue

            if EXPERIMENT_MODE == 'MPPT':
                try:
                    run_MPPT(keithley2400_1, file_path, DURATION_MODE, area=AREA, stabilization_time=1)
                    logging.info("MPPT completed successfully.")
                except Exception as e:
                    logging.exception(f"An error occurred during MPPT: {e}")
            elif EXPERIMENT_MODE == 'MSPT':
                try:
                    run_MSPT(keithley2400_1, file_path, DURATION_MODE, area=AREA, stabilization_time=1)
                    logging.info("MSPT completed successfully.")
                except Exception as e:
                    logging.exception(f"An error occurred during MSPT: {e}")
            elif EXPERIMENT_MODE == 'PT':
                try:
                    run_pulsatile_therapy(keithley2400_1, file_path)
                    logging.info("Pulsatile Therapy completed successfully.")
                except Exception as e:
                    logging.exception(f"An error occurred during Pulsatile Therapy: {e}")
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("\nMeasurement loop interrupted by user.")
    finally:
        try:
            keithley2400_1.close()
            logging.info("Keithley2400 connection closed.")
        except Exception as e:
            logging.error(f"Failed to close Keithley2400: {e}")

if __name__ == "__main__":
    main()

'''
import matplotlib.pyplot as plt

plt.plot(voltages, VJ_over_V_plus_JRs_n, label='VJ / (V + JRs)^n')
plt.axvline(x=V_msp_local, color='r', linestyle='--', label=f'V_msp = {V_msp_local:.2f} V')
plt.xlabel('Voltage (V)')
plt.ylabel('VJ / (V + JRs)^n')
plt.title('VJ_over_V_plus_JRs_n vs Voltage')
plt.legend()
plt.show()
'''
