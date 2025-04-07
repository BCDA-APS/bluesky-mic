"""
Watch PVs (using PyEpics).

Future: ... and write to HDF5 file group.

Accept information about PVs from YAML files.

.. tip:: If ``oregistry`` warns about "duplicate objects", turn that off:
    ``oregistry.warn_duplicates = False``
.. tip:: If EPICS warns about "Identical process variable names on multiple servers"
   then *one way* to resolve is to adjust environment variable EPICS_CA_ADDR_LIST.
   https://wiki-ext.aps.anl.gov/blc/index.php?title=EPICS_networking
"""

import pathlib
import time

import epics
import yaml

TIMEOUT = 0.1
THIS_DIR = pathlib.Path(__file__).parent
CONFIGS_DIR = THIS_DIR / ".." / "configs"
MASTER_YAML_FILE = CONFIGS_DIR / "masterFileConfig_gen.yml"

TEST_CONFIG = yaml.load(open(MASTER_YAML_FILE).read(), yaml.SafeLoader)


class WatchedPvRO(epics.PV):
    """Read-only Process Variable with metadata support."""

    def put(self, *args, **kwargs):
        """Not writable.

        Raises:
            NotImplementedError: Always raised as this is read-only.
        """
        raise NotImplementedError(f"{self} is read-only.")

    @property
    def value(self):
        """Get PV value with metadata.

        Returns:
            Value of the PV, with enum string if applicable.
        """
        contents = self.get_with_metadata(with_ctrlvars=True)
        value = contents["value"]
        if isinstance(value, int):
            # If enum, then use str, if defined.
            choices = contents.get("enum_strs")
            try:
                value = choices[value]
            except IndexError:
                pass
        return value


class WatchedPvGroup:
    """Watch a group of related PVs.

    Attributes:
        db (dict): Dictionary of PVs.
        name (str): Name of the group.
    """

    def __init__(self, **kwargs):
        """Initialize WatchedPvGroup.

        Parameters:
            **kwargs: Keyword arguments including NAME and PV specifications.
        """
        self.db = {}
        self.name = kwargs.pop("NAME")
        for key, value in kwargs.items():
            if "PV" in key:
                if key not in ("PV", "PVNAME"):
                    key = key.replace("PV", "").strip("_")
                self.db[key] = WatchedPvRO(value)

    @property
    def connected(self):
        """Check if all PVs are connected.

        Returns:
            bool: True if all PVs are connected.
        """
        for item in self.db.values():
            if not item.connected:
                return False
        return True

    def wait_for_connection(self, timeout=5, interval=0.01):
        """Wait for all items to connect.

        Parameters:
            timeout (float): Maximum time to wait.
            interval (float): Time between connection checks.

        Returns:
            bool: True if all PVs connected.
        """
        deadline = time.monotonic() + timeout
        while not self.connected and time.monotonic() < deadline:
            for item in self.db.values():
                if not item.connected:
                    item.connect(timeout=timeout)
                if time.monotonic() > deadline:
                    break
            if not self.connected:
                epics.ca.poll()
        return self.connected

    def asdict(self):
        """Get content as dictionary.

        Returns:
            dict: Dictionary of PV values.
        """
        return {
            self.name: {
                key: item.value for key, item in self.db.items() if item.connected
            }
        }


def watch_single_pv(pvname):
    """Watch a single PV.

    Parameters:
        pvname (str): Name of the PV to watch.
    """
    pv = WatchedPvRO(pvname, connection_timeout=TIMEOUT)
    pv.wait_for_connection(timeout=TIMEOUT)
    print(f"{pv=!r}")
    print(f"{pv.value=!r}")
    print(pv.value)


def watch_group(group_dict):
    """Watch a group of PVs.

    Parameters:
        group_dict (dict): Dictionary with group specifications.
    """
    group = WatchedPvGroup(**group_dict)
    group.wait_for_connection(timeout=0.1)
    print(f"{group.asdict()=}")


def watch_config(config):
    """Watch PVs based on configuration.

    Parameters:
        config (dict): Configuration dictionary.
    """
    db = {}
    for section_name, section in config.items():
        db[section_name] = {}
        for item, specs in section.items():
            db[section_name][item] = WatchedPvGroup(**specs)

    for section in db.values():
        for group in section.values():
            group.wait_for_connection(timeout=TIMEOUT)

    for section_name, section in db.items():
        for group_name, group in section.items():
            print(f"{section_name!r} {group_name!r} {group.asdict()}")


if __name__ == "__main__":
    # watch_single_pv("19idSFT:TetrAMM1:Range")
    # watch_single_pv("19IDRobot:TwoTheta")

    # watch_group(dict(NAME="tetramm1", RANGE_PV="19idSFT:TetrAMM1:Range"))

    watch_config(TEST_CONFIG)
