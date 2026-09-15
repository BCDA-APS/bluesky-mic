# AI_README — Orientation guide for AI agents

> **Purpose.** This file is a durable, high-density map of this repository written for an AI
> agent starting a fresh session. Read it before touching code. It covers what the repo is,
> how a session boots, where every subsystem lives, the conventions you must follow, and the
> known landmines. `README.md` is the human-facing install/BITS-boilerplate doc; this file is
> the architecture doc.
>
> **Last verified against the tree at commit `15c2af4` (2026-07-27) plus the uncommitted work
> on branch `isn_main`.** If something below disagrees with the code, the code wins — and
> please update this file.

---

## Table of contents

1. [30-second orientation](#1-30-second-orientation)
2. [Runtime and entry points](#2-runtime-and-entry-points)
3. [Repository map](#3-repository-map)
4. [The startup sequence (order is load-bearing)](#4-the-startup-sequence-order-is-load-bearing)
5. [Configuration files](#5-configuration-files)
6. [Device layer](#6-device-layer)
7. [Motion: sample stack, KB mirrors, diffractometer](#7-motion-sample-stack-kb-mirrors-diffractometer)
8. [Triggering and the fly-scan architecture](#8-triggering-and-the-fly-scan-architecture)
9. [Detectors and AreaDetector conventions](#9-detectors-and-areadetector-conventions)
10. [Data output and on-disk layout](#10-data-output-and-on-disk-layout)
11. [Plans](#11-plans)
12. [Callbacks, suspenders, preprocessors](#12-callbacks-suspenders-preprocessors)
13. [Utilities and the `mictools` companion package](#13-utilities-and-the-mictools-companion-package)
14. [Queueserver](#14-queueserver)
15. [Conventions used in this repo](#15-conventions-used-in-this-repo)
16. [Known quirks, tech debt, latent bugs](#16-known-quirks-tech-debt-latent-bugs)
17. [Playbooks for common tasks](#17-playbooks-for-common-tasks)
18. [Verifying changes without beam](#18-verifying-changes-without-beam)

---

## 1. 30-second orientation

* This is a **Bluesky / Ophyd / EPICS beamline-control package** for **APS sector 19-ID**,
  built on the APS **BITS** framework (`apsbits`). It is not a library — it is an
  *instrument session*: importing it connects to live EPICS IOCs and builds device objects.
* The **live instrument is `src/isn/`** ("ISN" = In Situ Nanoprobe, 19-ID-E). Everything you
  will realistically be asked to change lives there.
* `src/mic_common/` is the **shared microscopy layer** (detectors, file writers, DM helpers)
  reused across instruments.
* `src/s2idd_uprobe/` and `src/s2ide_uprobe/` are **separate, largely dormant instruments**
  for sector 2-ID-D / 2-ID-E microprobes. Treat them as out of scope unless named explicitly.
* The flagship capability is a **hardware-timed 2-D fly scan** driven by an FPGA
  (SoftGlue Zynq) that snakes a piezo stage while gating detectors over TTL — see
  [§8](#8-triggering-and-the-fly-scan-architecture). Almost all recent development is here.
* There is **no test suite** and **no CI**. Correctness is established by reading, by
  `python -c "import ..."`-level checks, and ultimately by running on the beamline.

**The single most important structural fact:** most plan and helper modules resolve their
devices from the `oregistry` **at module import time**, not inside the plan function. See
[§15.1](#151-import-time-device-resolution-read-this-before-editing-any-plan). Getting this
wrong breaks session startup entirely.

---

## 2. Runtime and entry points

| Thing | Value |
|---|---|
| Python | 3.11 |
| Conda env (beamline) | `/home/beams/STAFF19ID/.conda/envs/isn_2026_2` |
| Package name | `mic_instrument` (`pyproject.toml`), src-layout under `src/` |
| Core dependency | `apsbits` (BITS) → pulls bluesky, ophyd, databroker, apstools |
| Other notable deps | `hklpy2` (+ `gi`), `tiled`, `epics`/`pyepics`, `h5py`, `mictools` (external sibling repo) |
| Active git branch | `isn_main` (PRs usually target `main`) |
| Interactive start | `from isn.startup import *` in IPython / Jupyter |
| Queueserver start | `./scripts/isn_qs_host.sh restart` |

Sibling instruments start the same way: `from s2idd_uprobe.startup import *`, etc.

`mictools` is **not vendored** — it is a separate repo (on this machine at
`/home/beams43/STAFF19ID/mictools`) installed into the env. `startup.py` imports from it
unconditionally, so a missing/broken `mictools` breaks the session.

---

## 3. Repository map

```
bluesky-mic/
├── README.md                     BITS boilerplate: install, DM setup, queueserver
├── AI_README.md                  ← this file
├── pyproject.toml                packaging + black/ruff/isort/pytest config
├── .pre-commit-config.yaml       ruff + ruff-format + standard hygiene hooks
├── scripts/
│   ├── isn_qs_host.sh            queueserver host manager for ISN
│   ├── s2idd_qs_host.sh          … for 2-ID-D
│   └── s2ide_qs_host.sh          … for 2-ID-E
└── src/
    ├── isn/                      ★ THE LIVE 19-ID-E INSTRUMENT
    │   ├── startup.py            session bootstrap — read this first (§4)
    │   ├── configs/              iconfig + device YAMLs + DM workflow YAMLs (§5)
    │   ├── devices/              ophyd device classes (§6)
    │   ├── plans/                bluesky plans (§11); plans/old_plans/ is dead code
    │   ├── plans/utils/          detector setup, trajectories, master-file generation
    │   ├── callbacks/            NeXus + SPEC writers (thin wrappers over mic_common)
    │   ├── suspenders/           shutter suspenders (defined, currently NOT installed)
    │   ├── utils/                RunEngine holder, experiment loading, misc session tools
    │   └── qserver/              queueserver config + permissions
    ├── mic_common/               ★ SHARED MICROSCOPY LAYER
    │   ├── devices/              Eiger, Xspress3, TetrAMM, SaveData, AD file plugins
    │   ├── callbacks/            NXWriter subclass, SPEC writer, trajectory generators
    │   ├── plans/                generalized 1-D scan
    │   └── utils/                DM (APS Data Management) helpers, HDF5 master files, misc
    ├── s2idd_uprobe/             2-ID-D microprobe instrument (dormant)
    └── s2ide_uprobe/             2-ID-E microprobe instrument (dormant)
```

Directories to ignore: `.logs/`, `notebooks/`, `.ipynb_checkpoints/`, `*/old_plans/`,
`*/old/`, `src/mic_instrument.egg-info/`.

---

## 4. The startup sequence (order is load-bearing)

`src/isn/startup.py` is the spine of the whole session. Its ordering encodes real
dependencies; reordering it will break things. Annotated flow:

1. **`import gi`, `import hklpy2` first.** A documented workaround: importing these before
   matplotlib avoids a GTK/hkl binding crash. Do not move these imports.
2. **Load `configs/iconfig.yml`** → `iconfig` (via `apsbits.utils.config_loaders.load_config`).
   This also becomes the process-global config that `get_config()` returns elsewhere.
3. **Configure logging** from `configs/extra_logging.yml` (console + rotating file in `.logs/`
   + IPython log).
4. **`init_instrument("guarneri")`** → creates the device manager + `oregistry`, then the
   registry is immediately `.clear()`ed so only the explicit YAML loads below populate it.
5. **`dm_setup(...)`** — hook up APS Data Management using `DM_SETUP_FILE`.
6. **`register_bluesky_magics()`** — enables `%wa`, `%ct`, etc.
7. **Optional tiled client** if `TILED_PROFILE_NAME` is set in iconfig
   (**it currently is not**, so `tiled_client` is never defined).
8. **`from .utils.run_engine import RE, sd, bec, cat`** — the RunEngine is built in a
   *separate module* (`isn/utils/run_engine.py`) precisely so plans can `from ..utils.run_engine
   import RE` without a circular import back through `startup`. `RE.md['scan_id']` is then
   forced to `0` as a floor.
9. **SPEC callback** if enabled (it is not; `SPEC_DATA_FILES.ENABLE: false`).
10. **Queueserver branch**: under QS only whitelisted plans are imported; interactively you get
    `apstools.utils *`, `bluesky.plans as bp`, `bluesky.plan_stubs as bps`.
11. **`make_devices(file="config_devices.yml")` — FIRST device pass.** This file exists solely
    because these four devices are dependencies of other devices/modules:
    `savedata`, `softglue`, `softglue2`, `if_cap_tracker`.
    (`isn/devices/sample.py` does `if_cap_tracker = oregistry['if_cap_tracker']` at import
    time; `mic_ad_mixins.MicHDF5.stage()` looks up `savedata`.)
12. **Attach SoftGlue detector keymaps** from `iconfig["SOFTGLUE_OUTPUTS"]` /
    `["SOFTGLUE2_OUTPUTS"]` onto `softglue.det_keymap` / `softglue2.det_keymap`.
    Wrapped in a bare `try/except` that only logs.
13. **`make_devices(file="devices.yml")` — SECOND pass**: the main device inventory.
14. **`make_devices(file="derived_devices.yml")` — THIRD pass: THIS FILE DOES NOT EXIST.**
    `apsbits.make_devices` only `logger.error`s on a missing file and continues, so this is
    currently a harmless-but-noisy no-op. Either create the file or delete the call.
15. **Windows storage roots** — sets `WindowsHDF5.linux_root` / `.windows_root` class
    attributes from `iconfig["WINDOWS_STORAGE"]`, for IOCs hosted on Windows (Andor).
16. **Diffractometer setup** — builds a simulated `sim_psic` (hklpy2, E6C geometry,
    `lifting_detector_mu` mode) and configures the real `psic` from the registry.
17. **`setup_baseline_stream(sd, oregistry, connect=False)`** — every device carrying the
    `"baseline"` label in YAML is recorded once at the start and end of each run.
18. **NeXus writer** (`NEXUS_DATA_FILES.ENABLE: true`) — creates `nxwriter` and hands it
    `savedata` so file names follow the beamline scan numbering.
19. **`from .plans import *`** — must come *after* devices exist (see §15.1).
20. **Fast-shutter preprocessor** — `RE.preprocessors.append(fast_shutter_control)`, so every
    plan opens/closes the fast shutter automatically.
21. **`mictools` imports** — data loading/processing/plotting helpers into the namespace.
22. **`load_experiment()`** — restores the last experiment path and scan number from
    `savedata`, and calls `mictools.config.set_path(...)`.

Suspenders are defined but **commented out** at step 20's neighbourhood — see §12.

---

## 5. Configuration files

All under `src/isn/configs/`.

| File | Role |
|---|---|
| `iconfig.yml` | Master session config: catalog name, RunEngine metadata, BEC options, NeXus/SPEC toggles, storage roots, SoftGlue output maps, DM setup file, ophyd timeouts. |
| `config_devices.yml` | **Pass-1 devices.** Only `savedata`, `softglue`, `softglue2`, `if_cap_tracker`. Loaded first because other devices import them. |
| `devices.yml` | **Pass-2 devices.** The main inventory. Heavily commented out — the commented blocks are the *catalogue of everything that has ever been wired up*, not dead weight; re-enable by uncommenting. |
| `extra_logging.yml` | Console/file/IPython logging levels and formats. Third-party loggers pinned to `warning`. |
| `masterFileConfig.yml` | PV → HDF5 mapping used to build per-scan "master" files (accelerator, beamline optics, etc.). |
| `dm_workflow_configs.py` | Loads the master-file config and the three DM workflow YAMLs. |
| `xrf_workflow.yml`, `ptycho_xrf_workflow.yml`, `ptychodus_workflow.yml` | APS Data Management workflow argument sets for downstream processing. |
| `ISN_metadata_master_det.xlsx` | Reference spreadsheet for detector metadata. |

### iconfig keys worth memorising

```yaml
DATABROKER_CATALOG: 19id_isn
RUN_ENGINE.DEFAULT_METADATA: {beamline_id: 19IDE, instrument_name: XSD 19-IDE}
BASELINE_LABEL.ENABLE: true          # devices labelled "baseline" get recorded per run
NEXUS_DATA_FILES: {ENABLE: true, FILE_EXTENSION: h5}
SPEC_DATA_FILES: {ENABLE: false}
STORAGE.PATH: /gdata/dm/19ID
WINDOWS_STORAGE: {LINUX_ROOT: /net/micdata/data1/isn, WINDOWS_ROOT: 'Y:\isn'}
SOFTGLUE_OUTPUTS:  {PTYCHO: 1, XRD: 2, ME7: 3, RAYSPEC: 4}   # → softglue  FO1..FO4
SOFTGLUE2_OUTPUTS: {FAST_SHUTTER: 12}                        # → softglue2 FO12
FILE_DELIMITER: "19ID"; SCAN_OVERHEAD: 0.3
DM_SETUP_FILE: /home/dm_id/etc/dm.setup.sh
OPHYD.TIMEOUTS: 5 s for read/write/connection
```

The `SOFTGLUE*_OUTPUTS` maps are the **detector-name → TTL output channel** table.
`SoftGlueZynq.enable_detector_trigger(name)` upper-cases the ophyd device name and looks it
up here. **A detector absent from this map silently will not be hardware-triggered** (it only
logs at debug level).

---

## 6. Device layer

### 6.1 How devices are created

BITS uses **guarneri-style YAML**: each top-level key is a fully-qualified Python class path,
and under it a list of instances with `name`, constructor kwargs, and optional `labels`.

```yaml
isn.devices.sample.Sample:
- name: sample
  aero_prefix: "19idAERO:"
  micronix_prefix: "19idMMC:"
  rtd_prefix: "19idTC:ADAM:"
  vacuum_prefix: "19idVAC:"
  labels: ["baseline"]
```

Instances land in the global `oregistry` **and** in the `__main__` namespace, so in an IPython
session `sample` is just a name. In library code, always go through
`from apsbits.core.instrument_init import oregistry` → `oregistry["sample"]`.

Labels in use: `baseline` (auto-recorded per run), `detector`, `data`, `motor`,
`scanrecord`, `fileplugin`, `pss-shutter`.

### 6.2 Currently active devices

From `config_devices.yml` (pass 1):

| Name | Class | PV prefix | Notes |
|---|---|---|---|
| `savedata` | `mic_common.devices.save_data.SaveDataMic` | `19idSFT:saveData_` | synApps saveData; owns file paths + scan numbering |
| `softglue` | `isn.devices.softgluezynq.Dtacq` | `isnACQ` | FPGA #1: waveform/RAM, DAC, thresholds, interferometer trackers |
| `softglue2` | `isn.devices.softgluezynq.SoftGlueZynq` | `19idMZ1` | FPGA #2: extra gates, fast shutter, second DMA |
| `if_cap_tracker` | `isn.devices.if_cap_tracker.IfCapTracker` | `isnACQ` | 7 capacitance sensors + 15 interferometer channels, baseline |

From `devices.yml` (pass 2):

| Name | Class | PV prefix / key args | Notes |
|---|---|---|---|
| `sample` | `isn.devices.sample.Sample` | `19idAERO:`, `19idMMC:`, `19idTC:ADAM:`, `19idVAC:` | the sample stack — see §7.1 |
| `tetramm1` | `isn.devices.tetramm.MyTetrAMM` | `19idSFT:TetrAMM1:` | picoammeter, `detector` |
| `tetramm3` | idem | `19idSFT3:TetrAMM3:` | |
| `tetramm4` | idem | `19idSFT4:T4:` | |
| `eshutter` | `apstools.devices.shutters.ApsPssShutter` | `S19ID-PSS:SES:Open/CloseEPICSC` | end-station PSS shutter |
| `psic` | `isn.devices.diffractometer.RobotArmDiffractometer` | robot at `19IDRobot:` | hklpy2 E6C, baseline |
| `kb` | `isn.devices.kb.KB` | `19idKB:` | KB mirror bench — see §7.2 |
| `ptycho` | `mic_common.devices.eiger.Eiger` | `19idPTYCHO:` | Eiger, `detector` |
| `xrd` | `mic_common.devices.eiger.Eiger` | `19idXRD:` | Eiger, `detector` |
| `me7` | `isn.devices.xspress3.Me7Xspress3` | `19idME7:` | 7-channel Xspress3 XRF |
| `rayspec` | `isn.devices.xspress3.RayspecXspress3` | `19idRAYSPEC:` | 12-channel Xspress3 XRF |
| `socketserver` | `isn.devices.socketserver.SocketServer` | `19idSGSocket:` | AD-like sink that streams FPGA position data to HDF5 |
| `socketserver2` | idem | `19idSGSocket2:` | second stream (currently disabled in `flyscan`) |
| `hutch_temp` | `isn.devices.hutch.HutchTemp` | `BL19ID-Metasys:` | |
| `fast_shutter` | `isn.devices.fast_shutter.FastShutter` | (none) | pure logic device; drives a SoftGlue FO channel |

**Commented out in `devices.yml`** (i.e. previously working, currently not loaded):
`bleps`, `hhl_mirrors`, `mono`, `lateral_mirror`, `micronix`, `bda_vert`/`bda_hor`, `diamond`,
`tetramm2`, `bpm_c`/`bpm_dtrigger`, `ring`, `wbs`/`pbs` (HHL slits), `undulators`, all `flag_*`
and `xeye`, `ivm`, `cryo`, `andor`, `filters`, `rayspec_base`, `labjack_kb`, the strain-cell
devices (`rp100`, `mp240`, `lcrmeter`, `strain_cap`), the high-pressure GE controllers
(`compress`, `decompress`), `scan1`/`scan2` scan records, and the plain `samx`/`samy`/… motors.

### 6.3 Device module reference (`src/isn/devices/`)

| Module | Classes | What it is |
|---|---|---|
| `sample.py` | `Sample`, `ServoMotor`, `FineYMotor`, `EpicsMotorWithTweak`, `CorTheta`, `ScanningX` | Sample stack: Aerotech x/y/z + piezo fine_y, Micronix theta/x/z, RTD temperatures, chamber vacuum, centre-of-rotation correction. §7.1 |
| `softgluezynq.py` | `SoftGlueZynq`, `Dtacq`, plus FPGA primitives (`DivByN`, `GateDelay`, `PulseTrain`, `UpCounter`, `DownCounter`, `UpDownCounter`, `FlipFlop`, `Gate`, `Buffer`, `ScalToStream`) | The FPGA timing system. §8 |
| `xspress3.py` | `VortexXspress37`, `Me7Xspress3`, `RayspecXspress3`, `VortexROIStatPlugin`, `VortexSCA`, `TotalCorrectedSignal`, `ROIStatN` | Xspress3 XRF detectors, up to `MAX_ROIS = 48` dead-time-corrected ROI totals. **Untracked new file** replacing the deleted `me7.py`. |
| `kb.py` | `KB`, `CapSensorMotor*`, `VerticalKBAxis` | KB mirror bench with capacitance-sensor feedback and virtual differential/common-mode axes. §7.2 |
| `if_cap_tracker.py` | `IfCapTracker` | Reads 7 ADC capacitance channels (→ mm) and 15 interferometer channels (→ mm), derives `x`/`y`/`z` averages. |
| `socketserver.py` | `SocketServer` | Fakes an AreaDetector (`self.cam = self`) so the FPGA position stream can be captured with the standard HDF5 plugin machinery. |
| `diffractometer.py` | `RobotArmDiffractometer` | hklpy2 E6C diffractometer; `mu` is a real motor, `eta/chi/phi` are soft, `yaw/pitch/radius` drive the robot arm. |
| `robot.py` | `RobotArmPositioner` | `PVPositioner` for the 19-ID robot arm (setpoint / readback / MC-done / EXE / CMD). |
| `mic_ad_mixins.py` | `MicHDF5`, `MicStatsPlugin`, `MicCodecPlugin`, `VortexDetectorCam` | AreaDetector mixins. `MicHDF5.stage()` is where per-scan detector paths get set. |
| `fast_shutter.py` | `FastShutter` | Logic-only device; resolves which SoftGlue board owns `FAST_SHUTTER` and toggles that FO channel. |
| `tetramm.py` | `MyTetrAMM` | Caen TetrAMM picoammeter with stats plugins and `MicHDF5`. |
| `andor.py` | `Andor`, `AndorCam`, `Trigger` | Andor camera (XEOL); all plugins disabled on stage by default, `enable_plugins()` to opt in. Uses `WindowsHDF5`. |
| `micronix.py` | `Micronix` | `PseudoPositioner` over the Micronix controller. |
| `mono.py`, `hhl_mirrors.py`, `lateral_mirror.py`, `bda.py`, `diamond_window.py`, `filters.py`, `flag.py`, `bpm.py`, `undulators.py`, `bleps.py`, `hutch.py`, `xrayeye.py`, `ivm.py`, `cryo.py`, `rayspec.py`, `labjack.py`, `strain.py`, `ge_controller.py`, `my_motor_bundle.py`, `positioner_stream.py` | Beamline optics, diagnostics, environment, and sample-environment devices. Most are currently unloaded but functional. |

### 6.4 `mic_common/devices/`

| Module | What it is |
|---|---|
| `eiger.py` | `Eiger` + `Trigger` mixin. Software / internal / **flyscan (External Enable)** trigger modes; `set_plugins()` bulk-enables or disables the whole AD plugin chain via `caput`. |
| `eiger1m.py`, `eiger500k.py` | Older model-specific cams. |
| `xspress3.py` | Generic `Xspress3` cam (the ISN-specific one now lives in `isn/devices/xspress3.py`). |
| `save_data.py` | `SaveDataMic` — the **path authority**. `generate_det_path()` and `generate_det_path_windows()` build and create `…/Raw/Scan_NNNN/DET/`. |
| `ad_fileplugin.py`, `andor_fileplugin.py` | `DetHDF5`, `DetNetCDF`, `MicHDF5`, `WindowsHDF5` (Linux↔Windows root translation). |
| `scan_record.py`, `sis3820.py`, `xmap.py`, `profile_move.py`, `ring.py`, `data_management.py` | synApps sscan records, scalers, legacy MCA, profile moves, APS ring parameters, DM glue. |

---

## 7. Motion: sample stack, KB mirrors, diffractometer

### 7.1 `sample` (`isn/devices/sample.py`)

Axes and readbacks:

| Attribute | Class | PV | Note |
|---|---|---|---|
| `sample.x` | `EpicsMotorWithTweak` | `19idAERO:m2` | adds `.TWV/.TWF/.TWR` — the FPGA tweaks this during fly scans |
| `sample.y` | `ServoMotor` | `19idAERO:m3` | closed-loop servo; `.enable()` / `.disable()` / `.enabled` |
| `sample.z` | `EpicsMotorWithTweak` | `19idAERO:m1` | tweaked in lock-step with x to hold focus |
| `sample.fine_y` | `FineYMotor` | `19idAERO:SM1` | **same physical axis as `sample.y`**; its `set()` disables the servo first |
| `sample.theta` | `EpicsMotor` | `19idMMC:m1` | rotation |
| `sample.mic_x`, `mic_z` | `EpicsMotor` | `19idMMC:m3`, `m2` | Micronix coarse |
| `sample.temp_x/y/z/theta` | `EpicsSignalRO` | `19idTC:ADAM:AI0..3` | stage thermocouples |
| `sample.vacuum` | `EpicsSignalRO` | `19idVAC:cc10_vs:sc1` | chamber vacuum |
| `sample.cor_theta` | `CorTheta` | — | rotate + centre-of-rotation correction |
| `sample.cap1..7`, `x/y/z_initial` | soft `Signal` | — | reference snapshot, `kind="config"` |

Key behaviours:

* **Analog mode.** `enable_analog_control()` / `disable_analog_control()` fire Aerotech
  `userStringSeq` records and sleep ~4 s. `in_analog_mode` polls a 3-sample query and expects
  `[4,4,4]` (4 = analog, 0 = digital). Fly scans require analog mode so the FPGA DAC drives y.
* **Centre-of-rotation workflow.** `capture_initial_position()` averages 100 `if_cap_tracker`
  reads into `cap1..7`, snapshots x/y/z, and persists everything to
  `{analysis_path}/cor_positions.yaml`. `restore_from_yaml()` re-loads it in a later session.
  `CorTheta.set(angle)` then moves theta in a background thread and corrects x/z from the
  capacitance differential (`_CAP_ANGLES_DEG = [229.9, 122.9, 55.0]`).
* **`compensating_z(x_step)`** returns `x_step * sin(-θ)` — the z motion needed to keep the
  sample in focus while stepping x at rotation angle θ. This is used directly by `flyscan`.
* `ScanningX` is a `PseudoPositioner` mapping a single `scanning_x` onto real x/z through θ.
  **It is not instantiated in any YAML**, and it reads θ from `19idMMC:m4.RBV`, which is a
  *different* PV from `Sample.theta` (`m1`) — reconcile before using it.

### 7.2 `kb` (`isn/devices/kb.py`)

Six capacitance-sensor-instrumented axes, each combining a positioner PV, a cap sensor, and
coarse/fine motors:

| Axis | positioner | cap sensor | coarse | fine |
|---|---|---|---|---|
| `kb.x` | `19idKB:m18` | `cap4` | `m12` | `m6` |
| `kb.y_ds` | `19idKB:m16` | `cap2` | `m11` | `m2` |
| `kb.y_us` | `19idKB:m15` | `cap1` | `m7` | `m1` |
| `kb.z` | `19idKB:m17` | `cap3` | `m8` | `m5` |
| `kb.theta_y` | `19idKB:SM1` | `cap5` | `m9` | `m4` |
| `kb.theta_z` | `19idKB:SM2` | `cap6` | `m10` | — (coarse only) |

Plus `vertical_angle` / `vertical_average` (read-only calc records) and four **virtual**
`VerticalKBAxis` devices built from the ds/us pairs:

* `coarse_vertical_angle_um`, `fine_vertical_angle_um` — differential (`ds=+1, us=-1`)
* `coarse_y`, `fine_y` — common-mode (`ds=+1, us=+1`)

⚠️ `VerticalKBAxis` has **no readback PV**. `position` is a software counter starting at 0.0
each session, so `bps.mv` is absolute only with respect to that session zero. Use `bps.mvr`,
or call `axis.set_position(value)` to redefine the reference without moving anything. This is
documented at length in the class docstring — read it before touching these axes.

### 7.3 `psic` (`isn/devices/diffractometer.py`)

`RobotArmDiffractometer` is an `hklpy2` E6C diffractometer in `lifting_detector_mu` mode:
`mu` = `EpicsMotor("19idMMC:m1")`, `eta`/`chi`/`phi` = `SoftPositioner`s,
`yaw`/`pitch`/`radius` = `RobotArmPositioner`s on `19IDRobot:`.

⚠️ `psic.mu` and `sample.theta` are **the same physical motor** (`19idMMC:m1`) reached through
two ophyd objects. Moving one moves the other; neither knows about the other's software state.

`startup.py` also builds a purely simulated `sim_psic` for calculations without hardware.

---

## 8. Triggering and the fly-scan architecture

This is the heart of the instrument. Read `src/isn/plans/flyscan.py` alongside this section.

### 8.1 The hardware picture

* Two **SoftGlue Zynq FPGA** boards:
  * `softglue` (`Dtacq`, prefix `isnACQ`) — the master. Owns the waveform RAM, DAC1 (drives the
    piezo y analog input), threshold triggers, the interferometer trackers, and the DMA stream.
  * `softglue2` (`SoftGlueZynq`, prefix `19idMZ1`) — auxiliary gates, the `ckUser`/`clear`
    signals, the fast shutter output, and a second DMA.
* The boards are chained through field I/O: `softglue.io.fo6/fo7/fo8` → `softglue2.io.fi10/fi11/fi12`
  carrying `enable`, `enable1`, `ck1MHz`.
* Base clock is **10 MHz**, which is why the code multiplies milliseconds by `1e4` everywhere.
* `socketserver` / `socketserver2` are IOC-side sinks that turn the FPGA's DMA position stream
  into HDF5 files with the same shape as detector files.

### 8.2 Signal chain built by `flyscan`

```
ckIM   = DivByN-2 (period = acquire_time + det_dead)        → image / detector gate clock
ckUser = DivByN-3 (period = ckIM / interferometer_per_pixel) → interferometer sampling clock
GateDly-1 (both boards): width = acquire_time  → the TTL detector gate
GateDly-2 (sg2): → "ckUser"  width = det_dead/5, delay = acquire_time + 1·(det_dead/5)
GateDly-3 (sg2): → "clear"   width = det_dead/5, delay = acquire_time + 3·(det_dead/5)
plsTrn-1 : waveform clock, N = x_npts × 1000, period from F and y_npts
DnCntr-1 / UpDnCntr-1 : preset = x_npts + 1  → counts scan lines, tweaks x/z per line
threshTrig-1 POSTHR/NEGTHR : y turnaround thresholds that fire the per-line x/z tweak
```

### 8.3 The snake waveform

`softglue.create_snake_bits(A, F, npts, offset)` builds one period of a **trapezoid with
sinusoidal turnarounds**: `F` is the fraction of the y sweep spent in the linear (data-taking)
region, and the corners are quarter-sines so the piezo is not step-excited. `snake_y()` converts
µm to DAC bits via `y_to_bits()` (`m = (2^15−1)/90`, `b = −(2^15−1)/2`; valid range 0–90 µm) and
`write_RAM()` pushes the array into FPGA memory one address at a time.

Piezo travel is **±45 µm**, so plan-level y coordinates are relative and converted with
`y_abs = y + 45`. `flyscan` raises if `|y_min|` or `|y_max|` exceeds 45.

### 8.4 `flyscan()` execution order

Everything is wrapped in `bpp.finalize_wrapper(fly(), cleanup())`, so `cleanup()` runs even on
`Ctrl-C` twice or an exception. The commit history says this ordering was chosen deliberately —
do not casually rearrange it.

`fly()`:
1. resolve `x_npts`/`dx` and `y_npts`/`dy`; validate `F ∈ (0, 1]` and the piezo range
2. record `plan_args` for metadata; snapshot `x0/y0/z0`
3. unstage all detectors and their `hdf1` plugins (defensive)
4. couple the two boards, `stop()`, `reset()`, `clear_output_fields()`
5. program `ckUser`, `ckIM`, the gates, the pulse train
6. compute per-line x and z tweak values from θ (`dx·cos(−θ)`, `dx·sin(−θ)`), load them into
   `sample.x.tweak_value` / `sample.z.tweak_value`, set the down-counter preset
7. compute y thresholds from `F`, enter analog mode, centre the piezo, **disable `sample.y`**
8. move to the scan start (y analog, then x, then focus-compensated z)
9. write the snake to RAM, enable the waveform, point DAC1 at `funcGenPulse`
10. `savedata.next_scan_number.put(RE.md['scan_id'] + 1)`
11. stage + trigger `socketserver`
12. for each detector: `enable_detector_trigger()` on both boards, `setup_flyscan_mode(...)`,
    `stage()`
13. clear the second board's DMA
14. **`bps.open_run(md={"plan_args": plan_args})`** — note this happens *after* staging
15. open `eshutter`, then `fast_shutter`
16. `softglue.prepare()` then `bps.trigger(softglue)` → "Takeoff!"

`cleanup()`: close both shutters → flush both `scalToStream` FIFOs → unstage socket servers →
recentre piezo and restore x/y/z → unstage detectors and hdf plugins → reset both boards →
`bps.close_run()`.

### 8.5 Variants

* `flyscan_v2.py` — parallel development version (single socket server, no `softglue2`).
* `flyscan_eigerOnly.py` — Eiger-only path used while external gating was being debugged.
* `fly2d.py` — older 2-D fly implementation.

Only `flyscan` is exported from `plans/__init__.py`.

---

## 9. Detectors and AreaDetector conventions

Every detector class in this repo implements the same informal interface, and plans rely on it:

| Method | Contract |
|---|---|
| `setup_flyscan_mode(num_images, acq_time, hdf_images)` | configure `stage_sigs` for hardware-gated acquisition |
| `setup_software_trigger()` / `setup_internal_trigger()` | the other two trigger modes |
| `set_acquire_time(t)` | seconds |
| `stage()` / `unstage()` | must be paired; fly scans also unstage `det.hdf1` explicitly |
| `save_images_on()` / `save_images_off()` | toggle HDF5 capture |
| `align_on(time)` / `align_off()` | free-running alignment mode |
| `select_rois(...)` / `plot_options` / `select_plot(...)` | choose which channels are hinted for live plots |
| `write_master_h5(...)` | append this detector's metadata to the scan master file |

**Trigger modes by detector:**

* **Eiger** (`mic_common/devices/eiger.py`): software = `Internal Series` + `manual_trigger`;
  fly = **`External Enable`** with `num_triggers = num_images`.
* **Xspress3** (`isn/devices/xspress3.py`): software = `Software`; external = `TTL Veto Only`;
  `MAX_IMAGES = 12216`, `MAX_ROIS = 48`; `TotalCorrectedSignal` produces dead-time-corrected
  ROI totals; `Me7Xspress3` = 7 channels, `RayspecXspress3` = 12 channels.
* **SocketServer**: no cam; `Trigger.trigger()` puts `hdf1.capture = 1`; `unstage()` sleeps 4 s
  first so the autosave buffer does not restart capture.

**`MicHDF5.stage()` is where file naming happens** (`isn/devices/mic_ad_mixins.py`). On every
stage it looks up `savedata`, calls `savedata.generate_det_path(parent.name.upper())`, and sets
`file_template = "%s%s_%3.5d.h5"`, `file_name = base_name + f"{scan_number:04d}"`,
`auto_increment = 1`, `file_number = 1`, `file_write_mode = 2` (Stream). The scan number comes
from `RE.md['scan_id'] + 1`, falling back to `1`.

---

## 10. Data output and on-disk layout

```
{savedata.file_system}/{savedata.subdirectory}/
├── Scan_0042.h5                     ← NeXus master file (MicNXWriter)
└── Raw/
    └── Scan_0042/
        ├── ME7/        me7_00001.h5        …
        ├── PTYCHO/     ptycho_00001.h5     …
        ├── XRD/        …
        └── SOCKETSERVER/  interferometer + capacitance position stream
```

* `file_system` defaults to `/gdata/dm/19ID` (`STORAGE.PATH`).
* **Windows-hosted IOCs** (Andor) cannot mount `/gdata`. They use the shared micdata mount
  instead: `generate_det_path_windows()` creates the folder through `LINUX_ROOT`
  (`/net/micdata/data1/isn`) and returns the equivalent `Y:\isn\…\` path for the IOC's
  `file_path` PV. Roots are injected into `WindowsHDF5` class attributes at startup.
* **Scan numbering** is shared between `RE.md['scan_id']` and `savedata.next_scan_number`;
  `load_experiment()` reconciles them at startup by scanning existing `*.h5` files.
* **NeXus**: `MicNXWriter` (`mic_common/callbacks/nexus_data_file_writer.py`) overrides
  `make_file_name()` to produce `Scan_{scan_id:04d}.h5` next to the `Raw/` tree.
* **Master files**: `mic_common/utils/writeMasterH5.py` / `writeDetH5.py` +
  `isn/plans/utils/scan_master_gen.py` assemble PV snapshots described by `masterFileConfig.yml`.
* **Databroker/tiled catalog**: `19id_isn`. `cat[-1]` is the last run; `wax()` (§13) is a
  convenience reader over the baseline stream.
* **APS Data Management**: `mic_common/utils/dm_utils.py` wraps experiment creation, upload,
  ESAF/proposal queries, and workflow job submission using the three workflow YAMLs.

---

## 11. Plans

### 11.1 Actually exported (`src/isn/plans/__init__.py`)

| Name | Module | Purpose |
|---|---|---|
| `flyscan` | `flyscan.py` | the 2-D hardware-timed fly scan (§8) |
| `scan_piezo` | `scan_piezos.py` | step scan with interferometer readout per point |
| `cen`, `maxi` | `center_maximum.py` | move a positioner to the centre / maximum found by BEC peak stats |
| `count_abs_time`, `LiveAbsTimePlot` | `count_abs_time.py` | `bp.count` with live plots on an absolute time axis; the figure is built in the calling thread on purpose |
| `mv_kb`, `mvr_kb`, `set_kb_correction` | `kb_motion.py` | KB moves with automatic sample-position compensation |

`center_maximum.py` also defines `cen2`, `maxi2`, `mini2` (which auto-detect positioner and
detector from the last run) — they are in `__all__` but **not** re-exported by `plans/__init__.py`.

### 11.2 `kb_motion` coupling model

`KB_SAMPLE_COEFFICIENTS` maps each KB axis to the sample axis it moves the beam on, in
[sample EGU]/[KB EGU]. Currently calibrated: `x→x 0.001`, `theta_y.coarse/fine→x 0.0015797`,
`coarse/fine_vertical_angle_um→y 0.00586`, `coarse_y/fine_y→y 0.001`. Uncalibrated entries are
`0.0`. The correction is always computed as `post_rbv − pre_rbv` on the KB axis and applied as a
`bps.mvr` on the sample, so backlash and limit truncation are handled automatically. Pass
`correct=False` for pure alignment moves; update coefficients with `set_kb_correction(...)`.

### 11.3 Present but not exported

`flyscan_v2`, `flyscan_eigerOnly`, `fly2d`, `step2d`, `step2d_random_pos`,
`step2d_random_pos_xrf`, `generallized_scan_1d`, `nexus_gen`, `tune_roll`, `test`,
`test_logger`, `sim_plans`.

**Why they are commented out matters:** several of them resolve devices that no longer exist in
`devices.yml` (`scan1`, `scan2`, `samx`, `samy`, `xrf_me7`, `ptycho_hdf`, `shutter_open`, …) at
import time. Uncommenting the import without first restoring those devices will raise during
`from .plans import *` and abort the whole session.

`plans/old_plans/` is archived dead code. Do not extend it.

### 11.4 `plans/utils/`

* `det_setup.py` — per-detector configuration helpers for XRF/ptycho (legacy device names).
* `trajectory.py` — `generate_random_points`, `grid_points`, `process_scan_cyc`.
* `scan_master_gen.py` — build the per-scan master HDF5 and graft detector metadata into it.

`mic_common/callbacks/trajectories.py` has a richer generator set: `snake`, `raster`, `spiral`,
`semi_circle`, `lissajous`, `equidistant`, `trigger_events`, `custom_plot`.

---

## 12. Callbacks, suspenders, preprocessors

* **BestEffortCallback** — created in `isn/utils/run_engine.py`; `bec`, `peaks` are importable
  from there. `iconfig.BEC` turns off the baseline printout, keeps table/plots/heading.
* **NeXus writer** — enabled; see §10.
* **SPEC writer** — implemented (`mic_common/callbacks/spec_data_file_writer.py`) but disabled
  in iconfig.
* **Baseline stream** — automatic for every device labelled `baseline`.
* **Fast-shutter preprocessor** — `isn/utils/fast_shutter.py` wraps *every* plan the RunEngine
  executes in open/close of the fast shutter, gated on `fast_shutter._enabled`. Disable with
  `fast_shutter.disable()`, or remove the entry from `RE.preprocessors`.
* **Suspenders** — `isn/suspenders/suspender.py` defines `suspender` (front-end shutter
  `19ID:BLEPS:FES_CLOSED`, 1200 s settle) and `e_suspender` (end-station shutter
  `19ID:BLEPS:SES_CLOSED`, 2 s). **Both are commented out in `startup.py`.** The module
  docstring documents install/remove/inspect commands.

---

## 13. Utilities and the `mictools` companion package

`src/isn/utils/`

| Module | Contents |
|---|---|
| `run_engine.py` | Builds and exports `RE`, `sd`, `bec`, `peaks`, `cat`. **Import `RE` from here, never from `startup`.** |
| `experiment_utils.py` | `load_experiment()` — resolve the experiment path (from `savedata` or DM), find the last scan number, sync `RE.md['scan_id']`, and `mictools.config.set_path(...)`. |
| `acquire_time.py` | `set_acquire_time(dets, t)` — broadcast to a detector list. |
| `fast_shutter.py` | The `fast_shutter_control` preprocessor. |
| `hutch_light.py` | `light_switch('Up'/'Down')` — netcat to `10.54.120.96:5000`. |
| `wax.py` | `wax(scanno=None, label=None)` — pull the baseline stream of a run into a pandas DataFrame, optionally filtered by column substring. |
| `param_capture.py` | Serialise plan parameters (numpy-scalar safe) into metadata. |

`src/mic_common/utils/`: `dm_utils.py` (APS Data Management + ESAF/proposal API),
`misc.py` (`mkdir`, `pvget`/`pvput`, subprocess helpers, pause/resume/abort scan),
`scan_monitor.py`, `timer_decorator.py`, `watch_pvs_*.py`, `writeDetH5.py`, `writeMasterH5.py`,
`device_utils.py` (the `value_setter` / `mode_setter` decorators used by `SaveDataMic`).

**`mictools`** (external sibling repo, imported wholesale by `startup.py`):
`load_data`, `process_data`, `config`, `plot_data`, `roi_utils.Roi`. `mictools.config` owns the
session data-root (`set_path` / `get_path` / `get_analysis_path`), which is also where
`sample`'s `cor_positions.yaml` sidecar is written. If you change how experiment paths are
resolved here, check `mictools` too.

---

## 14. Queueserver

* Config: `src/isn/qserver/qs-config.yml` — redis on `localhost:6379`, ZMQ control `60615`,
  info `60625`, `startup_module: isn.startup`, IPython kernel worker with `qt5` matplotlib.
* Permissions: `user_group_permissions.yaml`; plan/device inventory:
  `existing_plans_and_devices.yaml`.
* Manage with `./scripts/isn_qs_host.sh {start|stop|restart|status|checkup|console|run}`.
* `startup.py` branches on `running_in_queueserver()`: under QS only a curated set of plans is
  imported (no `apstools.utils *`, no interactive magics). **If you add a plan that must be
  callable from the queue, check that branch.**

---

## 15. Conventions used in this repo

### 15.1 Import-time device resolution (read this before editing any plan)

Nearly every plan module opens with module-level lookups:

```python
from apsbits.core.instrument_init import oregistry
softglue = oregistry["softglue"]
sample   = oregistry["sample"]
```

Consequences you must respect:

1. **These modules cannot be imported before the devices exist.** That is exactly why
   `from .plans import *` is the *last* thing `startup.py` does, and why `config_devices.yml`
   is loaded before `devices.yml`.
2. **You cannot import these modules for linting or testing off the beamline** — the lookup
   raises immediately. Static checks must be import-free (e.g. `python -m compileall`, `ruff`).
3. **Renaming a device in YAML breaks every module that looks it up.** Grep before renaming:
   `grep -rn 'oregistry\[' src/`.
4. `isn/devices/sample.py` does this too (`if_cap_tracker`), so **device modules can have
   inter-device import-order dependencies**, not just plans.

When adding new code, prefer resolving inside the function (`oregistry["x"]` at call time) — it
avoids extending this fragility — but match the surrounding file's style when editing existing
modules.

### 15.2 `yield from` versus direct `.put()`

`flyscan` deliberately mixes two styles:

* `yield from bps.mv(...)` / `yield from bps.checkpoint()` — goes through the RunEngine, is
  interruptible, is recorded.
* `softglue.div_by_n_2.n.put(...)` / `detector.stage()` — direct EPICS I/O that bypasses the
  RunEngine.

The direct calls are intentional where the RunEngine's message overhead or its staging rules
get in the way, and `bps.checkpoint()` is sprinkled between blocks to keep the plan pausable.
**Do not "clean this up" wholesale** — each conversion changes interrupt and rewind semantics.

### 15.3 Style

`ruff` (line length 88, `force-single-line` isort, docstring rules D100–D107) and `ruff-format`
via pre-commit; `black`/`flake8` settings in `pyproject.toml` say 115 and are legacy. Existing
code does not fully comply. Match the file you are editing rather than reformatting it.

### 15.4 Naming and units

* Plan-level distances are **micrometres**; motor EGUs are **millimetres** — hence the `*1e-3`
  conversions in `flyscan`. Times are **milliseconds** at the plan level, **seconds** at the
  ophyd level, and **10 MHz ticks** (`*1e4` from ms) in SoftGlue.
* EPICS prefixes always come from YAML, never hard-coded in a plan. (Several *device* modules
  do hard-code PVs — `kb.py`, `diffractometer.py`. That is the existing pattern there.)
* Device names in `det_keymap` are matched **upper-cased** against the ophyd device name.

---

## 16. Known quirks, tech debt, latent bugs

Verified against the current tree. Treat each as a candidate improvement, not as something to
"fix on sight" without discussing beamline impact.

1. **`derived_devices.yml` does not exist** but `startup.py` calls `make_devices` for it.
   `apsbits` only logs an error, so it is noise — but it means the third pass loads nothing.
2. **`TILED_PROFILE_NAME` is absent from `iconfig.yml`**, so the `tiled_client` block never
   runs and `tiled_client` is undefined. `from tiled.client import from_profile` still happens
   unconditionally at import.
3. **`VortexXspress37.setup_images()` calls `self.auto_save_on()`, which is commented out**
   (`isn/devices/xspress3.py` lines ~513 and ~660) → `AttributeError` if that path is taken.
   It is not on the `flyscan` path (which uses `setup_flyscan_mode` + `MicHDF5.stage()`), so
   it is latent, not active.
4. **`VortexXspress37._local_folder`** is hard-coded to
   `/home/beams/STAFF19ID/pml/xpress3/data` and `setup_images()` overrides the computed path
   with it — marked `# TODO: need to temporarily change the saving folder`.
5. **11 bare `except:` clauses** (`startup.py:133`, `mic_ad_mixins.py:39`,
   `softgluezynq.py:200`, `save_data.py:40,72`, `andor_fileplugin.py:35`, `param_capture.py:149`,
   `trajectories.py:121`, …). Several swallow real failures — e.g. the SoftGlue keymap block in
   `startup.py` logs a benign-looking message whether the problem is a missing device or a typo.
6. **`psic.mu` and `sample.theta` are the same motor** (`19idMMC:m1`) with no coordination.
7. **`ScanningX` reads θ from `19idMMC:m4.RBV`**, disagreeing with `Sample.theta` (`m1`). It is
   also never instantiated.
8. **`VerticalKBAxis` absolute moves are session-relative** (no readback PV) — see §7.2.
9. **`sample.y` and `sample.fine_y` are one physical axis.** `FineYMotor.set()` disables the
   servo; nothing re-enables it automatically except `flyscan`'s cleanup and `ServoMotor.set()`.
10. **`in_analog_mode` costs ~4 s** (two 2 s sleeps in the query loop) and analog enable/disable
    each sleep 4.1 s. This is on the fly-scan critical path.
11. **Magic numbers in `flyscan`**: `snake_npts = 1000` (marked temporary), `det_dead/5`
    sub-gating, `bps.sleep(3)` after the shutter, `sleep(4)` in `SocketServer.unstage()`,
    `for _ in range(1)` loops that used to be `range(11)`.
12. **`MyTetrAMM.conf` passes `add_prefix="19idSFT:TetrAMM1:"`** — `add_prefix` in ophyd expects
    a sequence of *kwarg names*, not a PV string. Worth auditing whether `tetramm3`/`tetramm4`
    get the right port configuration PV.
13. **`socketserver2` is staged/triggered nowhere** in `flyscan` (the block is commented out)
    but is still flushed and unstaged in `cleanup()`.
14. **No tests, no CI.** `plans/test.py` and `plans/test_logger.py` are scratch plans, not tests,
    and `pytest` would try to collect them (`addopts = -x`).
15. **Three near-duplicate fly-scan implementations** (`flyscan`, `flyscan_v2`,
    `flyscan_eigerOnly`) plus `fly2d`, and near-duplicate `step2d*` plans. Consolidation is the
    obvious refactor but needs beamline validation.
16. **Uncommitted work in progress on `isn_main`**: `me7.py` deleted and replaced by the
    untracked `xspress3.py` (generalising ME7 into `VortexXspress37` + `Me7Xspress3` +
    `RayspecXspress3`), plus edits to `devices.yml`, `iconfig.yml`, `sample.py`,
    `if_cap_tracker.py`, `flyscan.py`, `startup.py`, `diffractometer.py`, `eiger.py`.
    **Check `git status` at the start of every session** — the tree is frequently mid-change.

---

## 17. Playbooks for common tasks

### Add a new device
1. Write the class in `src/isn/devices/<name>.py` (subclass `ophyd.Device` or an AD base).
2. Add a YAML block to `configs/devices.yml` with `name`, prefix/kwargs, and `labels`.
   Use `labels: ["baseline"]` for anything whose position should be recorded per run,
   `["detector"]` for detectors.
3. If **other devices or modules import it at module scope**, put it in `config_devices.yml`
   instead so it loads in pass 1.
4. If it should be TTL-triggered in fly scans, add `NAME: <FO channel>` to `SOFTGLUE_OUTPUTS`
   or `SOFTGLUE2_OUTPUTS` in `iconfig.yml`.
5. If it is a detector used by `flyscan`, implement the §9 interface — at minimum
   `setup_flyscan_mode`, `stage`/`unstage`, and an `hdf1` plugin.

### Add a new plan
1. Create `src/isn/plans/<name>.py`. Resolve devices inside the function where practical.
2. Export it from `plans/__init__.py`.
3. If it must run under queueserver, verify the QS import branch in `startup.py` and regenerate
   `qserver/existing_plans_and_devices.yaml`.
4. Wrap anything that arms hardware in `bpp.finalize_wrapper(main(), cleanup())` and put
   `bps.checkpoint()` between logical blocks so the plan stays pausable.

### Change fly-scan timing
Everything derives from `acquire_time` and `det_dead` (both ms) inside `flyscan.fly()`:
`ckIM` (`div_by_n_2.n = (acquire_time + det_dead) * 1e4`), `ckUser`
(`div_by_n_3.n = ckIM / interferometer_per_pixel`), the `GateDly-1` width (`acquire_time * 1e4`),
and the `plsTrn-1` waveform period. Change one, re-derive the others, and remember `softglue2`
mirrors `div_by_n_2` and `gate_delay_1`.

### Change where data is written
`SaveDataMic.generate_det_path()` (Linux) and `generate_det_path_windows()` (Windows IOCs) in
`mic_common/devices/save_data.py`, plus `MicHDF5.stage()` in `isn/devices/mic_ad_mixins.py` for
the file-name template, plus `MicNXWriter.make_file_name()` for the NeXus master.

### Re-enable a commented-out device or plan
1. Uncomment the YAML block.
2. `grep -rn '<device_name>' src/` — find every import-time consumer.
3. Confirm the IOC is actually up (`caget` the prefix) before enabling `labels: ["baseline"]`;
   a dead PV in the baseline stream slows every run.

### Diagnose a startup failure
Read the traceback bottom-up and check, in order: (a) is the failing name a device that moved
between `config_devices.yml` and `devices.yml`? (b) is it a plan module doing an import-time
`oregistry[...]`? (c) is `mictools` importable? (d) is the IOC up? Logs are in `.logs/`.

---

## 18. Verifying changes without beam

There is no test harness, so verification is mostly static:

```bash
# syntax check everything (safe — no imports executed)
python -m compileall -q src/isn src/mic_common

# lint / format (pre-commit is configured)
pre-commit run --all-files
ruff check src/isn

# YAML sanity
python -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" src/isn/configs/*.yml

# find every consumer of a device name before renaming it
grep -rn 'oregistry\[' src/ | grep -v old_plans
```

Do **not** try `python -c "import isn.startup"` off the beamline — it will attempt EPICS
connections, DM setup, and `mictools` imports.

A real functional check requires the beamline environment
(`conda activate isn_2026_2`, IPython, `from isn.startup import *`) and, for anything touching
`flyscan`, coordination with the beamline staff — the plan moves stages and opens shutters.

---

## Maintaining this file

When you make a structural change — a new device class, a renamed device, a change to the
startup order, a new plan export, a resolved item from §16 — update the corresponding section
here in the same change. The value of this file is entirely in its being current.
