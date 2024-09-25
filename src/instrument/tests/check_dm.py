"""
Test to check if dm is setup properly
"""

import os


def check_dm():
    """
    Test to check if DM will succesfully instatiate.
    """
    for k, v in os.environ.items():
        if k.startswith("DM_"):
            print(f"{k=}  {v=}")
