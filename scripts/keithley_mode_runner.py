#!/usr/bin/env python3
"""Run Keithley MSPT/MPPT from terminal with console + rotating file logs."""

import argparse
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime

from s2idd_uprobe.user.keithley2400_moxa import Keithley2400, HOST

basedir = '/net/micdata/data1/2idd/2026-1/Kim/keithley'
log_dir = Path(basedir) / 'logs'
os.makedirs(log_dir, exist_ok=True)

def setup_logging(log_dir: Path, log_prefix: str) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{log_prefix}.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = TimedRotatingFileHandler(
        filename=str(log_path),
        when="h",
        interval=1,
        backupCount=24,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    return log_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Keithley MPPT or MSPT with terminal + file logging.")
    p.add_argument("mode", choices=["mspt", "mppt"], help="Run mode.")
    p.add_argument("--fname", default=None, help="CSV base name (without .csv).")
    p.add_argument("--output-dir", default=None, help="Directory to save CSV. Default: $BASEDIR/keithley.")
    p.add_argument("--log-dir", default="scripts/.logs", help="Directory to save logs.")
    p.add_argument("--log-prefix", default="keithley_run", help="Log file prefix.")

    p.add_argument("--host", default=HOST, help="Moxa host IP. Set to 'none' to use --serial-port.")
    p.add_argument("--port-number", type=int, default=4004, help="Moxa TCP port number.")
    p.add_argument("--serial-port", default=None, help="Serial port path (used when --host none).")
    p.add_argument("--baudrate", type=int, default=57600)

    p.add_argument("--duration-min", type=float, default=60.0, help="MSPT/MPPT duration (minutes).")
    p.add_argument("--stabilization-time-min", type=float, default=0.05, help="Stabilization time (minutes).")
    p.add_argument("--delta-v-threshold", type=float, default=0.5)

    p.add_argument("--no-jv", action="store_true", help="Skip initial JV sweep.")
    p.add_argument("--jv-duration", type=float, default=50.0)
    p.add_argument("--n-value", type=float, default=1.05)
    p.add_argument("--area", type=float, default=0.0625)
    p.add_argument("--initial-pce-input", type=float, default=100.0)
    p.add_argument("--jv-start", type=float, default=-0.1)
    p.add_argument("--jv-end", type=float, default=1.3)
    p.add_argument("--voltage-step", type=float, default=0.01)
    p.add_argument("--number-of-sweeps", type=int, default=2)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.duration_min > 600:
        raise ValueError("duration-min must be <= 600 (10 hours).")

    log_path = setup_logging(Path(args.log_dir), args.log_prefix)
    logger = logging.getLogger(__name__)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = args.fname or f"{args.mode}_{timestamp}"
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        basedir = os.environ.get("BASEDIR")
        output_dir = Path(basedir) / "keithley" if basedir else Path("src/s2idd_uprobe/user")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{fname}.csv"

    logger.info("Mode: %s", args.mode.upper())
    logger.info("CSV output: %s", csv_path)
    logger.info("Log file: %s", log_path)

    host = None if str(args.host).lower() == "none" else args.host
    keithley = Keithley2400(
        port=args.serial_port,
        host=host,
        port_number=args.port_number,
        baudrate=args.baudrate,
    )

    try:
        if not args.no_jv:
            logger.info("Starting JV sweep")
            keithley.run_jv_sweep(
                file_path=str(csv_path),
                jv_duration=args.jv_duration,
                n_value=args.n_value,
                area=args.area,
                initial_pce_input=args.initial_pce_input,
                jv_start=args.jv_start,
                jv_end=args.jv_end,
                voltage_step=args.voltage_step,
                number_of_sweeps=args.number_of_sweeps,
            )

        mode_duration_s = args.duration_min * 60.0
        stabilization_s = args.stabilization_time_min * 60.0

        if args.mode == "mspt":
            logger.info("Starting MSPT for %.2f min", args.duration_min)
            keithley.run_mspt(
                file_path=str(csv_path),
                duration=mode_duration_s,
                area=args.area,
                stabilization_time=stabilization_s,
                delta_v_threshold=args.delta_v_threshold,
            )
        else:
            logger.info("Starting MPPT for %.2f min", args.duration_min)
            keithley.run_mppt(
                file_path=str(csv_path),
                duration=mode_duration_s,
                area=args.area,
                stabilization_time=stabilization_s,
            )
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
    finally:
        try:
            keithley.reset()
        except Exception:
            pass
        try:
            keithley.close()
        except Exception:
            pass
        logger.info("Keithley connection closed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Example commands:
# JV only (run sweep, then zero-minute MSPT):
#   scripts/run_keithley_mode.sh mspt --duration-min 0 --fname jv_only
#
# MSPT:
#   scripts/run_keithley_mode.sh mspt --duration-min 600 --stabilization-time-min 0.05 --fname mspt_10h
#
# MPPT:
#   scripts/run_keithley_mode.sh mppt --duration-min 600 --stabilization-time-min 0.05 --fname mppt_10h
