__all__ = """
    mov_osa_y
""".split()

import logging

import bluesky.plan_stubs as bps
from apsbits.core.instrument_init import oregistry

logger = logging.getLogger(__name__)
osa = oregistry["osa"]
solarsim_shutter = oregistry['solarsim_shutter']
sample = oregistry['sample']

def set_samx_speed(speed: float = 500):
    """Set the x motor speed
    
    Parameters
    ----------
    speed: float
        The speed of the x motor in mm/s. Default: 500 which is the max speed
    """
    logger.info(f"Setting x motor speed to {speed} mm/s")
    yield from bps.mv(sample.x.velocity, speed)
    logger.info(f"Set x motor speed to {sample.x.velocity.get()} mm/s")

def mov_osa_y(position: float):
    """Move the OSA y motor to the specified position."""
    logger.info(f"Moving osa.y to {position} mm")
    yield from bps.mv(osa.y, position)
    logger.info(f"Moved osa.y to {osa.y.position} mm")

def osa_in(position: float = 0):
    """Move the OSA y motor to the in position."""
    logger.info("Moving osa.y in position")
    yield from bps.mv(osa.y, position)
    logger.info(f"Moved osa.y to {osa.y.position} mm")
    yield from bps.sleep(0.2)

def osa_out(position: float = 8):
    """Move the OSA y motor to the out position."""
    logger.info("Moving osa.y out position")
    yield from bps.mv(osa.y, position)
    logger.info(f"Moved osa.y to {osa.y.position} mm")
    yield from bps.sleep(0.2)

def solarsim_on():
    """Remove solar sim shutter"""
    logger.info("Solar sim shutter out, light on")
    yield from bps.mv(solarsim_shutter, 1)
    yield from bps.sleep(0.2)

def solarsim_off():
    """Put solar sim shutter"""
    logger.info("Solar sim shutter in, light off")
    yield from bps.mv(solarsim_shutter, 0)
    yield from bps.sleep(0.2)
