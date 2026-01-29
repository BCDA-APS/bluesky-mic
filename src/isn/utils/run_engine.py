"""
Setting up the RunEngine in a way that makes it accessible to other modules.
Proves ``RE`` and ``sd``.
"""
from pathlib import Path
from apsbits.utils.config_loaders import load_config
from apsbits.core.best_effort_init import init_bec_peaks
from apsbits.core.catalog_init import init_catalog
from apsbits.core.run_engine_init import init_RE

instrument_path = Path(__file__).parent.parent
iconfig_path = instrument_path / "configs" / "iconfig.yml"
iconfig = load_config(iconfig_path)

bec, peaks = init_bec_peaks(iconfig)
cat = init_catalog(iconfig)
RE, sd = init_RE(iconfig, subscribers=[bec, cat])