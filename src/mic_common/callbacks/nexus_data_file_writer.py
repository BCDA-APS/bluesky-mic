"""
Nexus data file writer callback.

This module provides callbacks for writing data to Nexus data files.
"""

import logging

from apsbits.utils.aps_functions import host_on_aps_subnet
from apsbits.utils.config_loaders import get_config
import datetime
import pathlib


logger = logging.getLogger(__name__)
logger.bsdev(__file__)

# Get the configuration
iconfig = get_config()


if host_on_aps_subnet():
    from apstools.callbacks import NXWriterAPS as NXWriter
else:
    from apstools.callbacks import NXWriter


class MicNXWriter(NXWriter):
    """Patch to get sample title from metadata, if available."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.savedata = None

    def set_savedata(self, savedata):
        self.savedata = savedata

    def get_sample_title(self):
        """
        Get the title from the metadata or modify the default.

        default title: S{scan_id}-{plan_name}-{short_uid}
        """
        try:
            title = self.metadata["title"]
        except KeyError:
            # title = super().get_sample_title()  # the default title
            title = f"S{self.scan_id:05d}-{self.plan_name}-{self.uid[:7]}"
        return title

    def make_file_name(self, micdata_mountpath="/mnt/micdata1"):
        """
        Override the default file name to use the savedata.next_file_name

        override in subclass to change
        """

        if self.savedata is None:
            start_time = datetime.datetime.fromtimestamp(self.start_time)
            # fmt: off
            fname = (
                f"{start_time.strftime('%Y%m%d-%H%M%S')}"
                f"-S{self.scan_id:05d}"
                f"-{self.uid[:7]}.{self.file_extension}"
            )
            # fmt: on
            path = self.file_path or pathlib.Path(".")
            return path / fname
        else:
            self.savedata.update_next_file_name()
            fname = self.savedata.next_file_name.replace(".mda", "_run.h5")
            path = pathlib.Path(
                self.savedata.get().file_system.replace("//micdata/data1", micdata_mountpath), "bluesky"
            )

            # Check if path exists, create it if it doesn't
            path.mkdir(parents=True, exist_ok=True)

            self.file_path = path
            return path / fname


def nxwriter_init(RE):
    """Initialize the Nexus data file writer callback."""
    nxwriter = MicNXWriter()  # create the callback instance
    """The NeXus file writer object."""

    if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
        RE.subscribe(nxwriter.receiver)  # write data to NeXus files

    nxwriter.file_extension = iconfig.get("NEXUS_DATA_FILES", {}).get("FILE_EXTENSION", "hdf")

    print(nxwriter.file_extension)
    warn_missing = iconfig.get("NEXUS_DATA_FILES", {}).get("WARN_MISSING", False)
    nxwriter.warn_on_missing_content = warn_missing

    return nxwriter
