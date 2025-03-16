"""
Watch PVs (using ophyd) and write to HDF5 file group.

Accept information about PVs from YAML files.

.. tip:: If ``oregistry`` warns about "duplicate objects", turn that off:
    ``oregistry.warn_duplicates = False``
"""

import datetime
import pathlib
import time

import h5py
import yaml
from ophyd import Component
from ophyd import EpicsMotor
from ophyd import EpicsSignalRO

THIS_DIR = pathlib.Path(__file__).parent
CONFIGS_DIR = THIS_DIR / ".." / "configs"
PROJECT_DIR = THIS_DIR / "."  # TODO: get this from DM data dir

MASTER_YAML_FILE = CONFIGS_DIR / "masterFileConfig_gen.yml"
MASTER_SCAN_FILE = PROJECT_DIR / "example_pvs.h5"

pv_db = {}

# TODO: Refactor to use epics.PV objects instead.


class WatchedEpicsMotor(EpicsMotor):
    """EPICS motor for reporting in HDF5 file."""

    # TODO: Can we limit this to read-only?

    description_ = Component(EpicsSignalRO, ".DESC", kind="config", string=True)
    record_type = Component(EpicsSignalRO, ".RTYP", kind="config", string=True)

    @property
    def _description(self):
        return self.description_.get()

    @property
    def _record_type(self):
        return self.record_type.get()


class WatchedEpicsSignal(EpicsSignalRO):
    """EPICS signal for reporting in HDF5 file."""

    def __init__(self, read_pv="", units_pv="", **kwargs):
        """."""
        import epics  # cheat here

        try:
            super().__init__(read_pv=read_pv, **kwargs)
        except Exception as reason:
            raise RuntimeError(
                f"{read_pv=} {units_pv=} {kwargs=} {reason=}"
            ) from reason

        pv_base = read_pv.split(".")[0]
        tmot = 0.5

        def caget_now(pv, default=None, timeout=5):
            value = default
            if len(pv) > 0:
                try:
                    value = epics.caget(
                        pv,
                        timeout=timeout,
                        connection_timeout=timeout,
                    )
                except TimeoutError:
                    value = default
            return value

        # cheat here, only during initial construction
        # Signal has no Component attributes.  Gotta fake it.
        self._description = caget_now(
            f"{pv_base}.DESC",
            default=f"EPICS PV: {pv_base}",
            timeout=tmot,
        )

        self._record_type = caget_now(
            f"{pv_base}.RTYP",
            default="-timeout-",
            timeout=tmot,
        )

        if ":" not in units_pv or "." not in units_pv:
            self.egu = units_pv  # Assume text, not a PV
        else:
            self.egu = caget_now(
                units_pv,
                default=self.metadata.get("units", ""),
                timeout=tmot,
            )

        if self._description == "":
            self._description = f"EPICS PV: {self.pvname}"

    @property
    def position(self):
        """Current value."""
        value = self.get()
        if isinstance(value, int):
            # If enum, then use str, if defined.
            choices = self.metadata.get("enum_strs")
            try:
                value = choices[value]
            except IndexError:
                pass
        return value


def connect_with_EPICS(specifications, db):
    """
    Watch various EPICS objects specified in a micdata YAML file.

    =====================   =====================
    content                 class
    =====================   =====================
    entries with "RBV_PV"   WatchedEpicsMotor
    any other entries       WatchedEpicsSignal
    =====================   =====================
    """
    for section_name, specs in specifications.items():
        db[section_name] = {}
        for key, entry in specs.items():
            if not isinstance(entry, dict):
                raise TypeError(f"Expected a dictionary: {key=} {entry=}")
            name = entry["NAME"]
            if "RBV_PV" in entry:
                pv = entry["RBV_PV"].split(".")[0]
                device = WatchedEpicsMotor(pv, name=name)
            else:
                kwargs = {"name": name}
                pv = entry.get("VALUE_PV", entry.get("PV"))
                units_pv = entry.get("UNITS_PV")
                if units_pv is not None:
                    if units_pv != f"{pv.split('.')[0]}.EGU":
                        kwargs["units_pv"] = units_pv
                device = WatchedEpicsSignal(pv, **kwargs)
            db[section_name][name] = device


def load_config_yaml(path):
    """Local developer copy."""
    return yaml.load(open(path, "r").read(), yaml.Loader)


def write_h5_dataset(
    h5parent: h5py.Group,
    entry: tuple[WatchedEpicsMotor, WatchedEpicsSignal],
) -> h5py.Dataset:
    """Write this watched entry to the HDF5 group."""
    if not entry.connected:
        return

    value = entry.position
    setpoint = None
    try:
        pv = entry.pvname
    except AttributeError:
        pv = entry.prefix

    if not isinstance(entry, (WatchedEpicsMotor, WatchedEpicsSignal)):
        raise TypeError(f"Unexpected type: {type(entry): {entry!r}}")
    if isinstance(entry, WatchedEpicsMotor):
        setpoint = entry.user_setpoint.get()

    ds = h5parent.create_dataset(entry.name, data=value)
    # https://manual.nexusformat.org/nxdl_desc.html#long-name
    ds.attrs["long_name"] = entry._description
    if entry.egu not in (None, "None", ""):
        # https://manual.nexusformat.org/nxdl_desc.html#units
        ds.attrs["units"] = entry.egu
    if setpoint is not None:
        ds.attrs["setpoint"] = setpoint
    ds.attrs["EPICS_PV"] = pv
    ds.attrs["EPICS_record_type"] = entry._record_type

    return ds


def write_h5_watched_pvs(h5parent: h5py.Group, db: dict, yaml_file=None):
    """Report the monitored PVs to the HDF5 parent group."""
    if yaml_file is not None:
        h5parent.attrs["yaml_configuration_file"] = str(yaml_file)
        # TODO: write the YAML text here?
    for section_name, entries in db.items():
        group = h5parent.create_group(section_name)
        for entry in entries.values():
            write_h5_dataset(group, entry)


def developer_report(db):
    """Convenience for the developer."""
    from pyRestTable import Table

    table = Table()
    table.labels = "section dataset value units record_type PV PV_description".split()
    for section_name, entries in db.items():
        for name, entry in entries.items():
            if not entry.connected:
                print(f"{entry.name} is not connected.")
                continue
            try:
                pv = entry.pvname
            except AttributeError:
                pv = entry.prefix
            row = [
                section_name,
                name,
                entry.position,
                entry.egu if str(entry.egu) != "None" else "",
                entry._record_type,
                pv,
                entry._description,
            ]
            table.addRow(row)
    print(table)


def write_scan_master_h5(master_file_yaml: dict, 
                        master_scan_file: str):
    """Demonstrate this code."""
    # specifications = master_file_yaml
    pv_db = {}
    connect_with_EPICS(master_file_yaml, pv_db)
    time.sleep(1)  # plenty of time for PV connections
    developer_report(pv_db)

    try:
        with h5py.File(master_scan_file, "w") as h5root:
            h5root.attrs["filename"] = str(master_scan_file)
            h5root.attrs["datetime"] = str(datetime.datetime.now())
            write_h5_watched_pvs(h5root, pv_db, master_file_yaml)
    except PermissionError as reason:
        print(f"PermissionError: {reason}")


if __name__ == "__main__":
    example()
