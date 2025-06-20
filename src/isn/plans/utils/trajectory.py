"""
Generate scan trajectory points

@author: yluo(grace227)

"""


import numpy as np
from bluesky.plans import plan_patterns


def generate_random_points(scan_traj, x_center, y_center, width, height, 
                           stepsize_x, stepsize_y, dr, nth):
    """
    Generate random points for the scan trajectory.
    """
    samx_points, samy_points = [], []
    if scan_traj == "spiral":
        scan_cyc = plan_patterns.spiral("samx", "samy", x_center, y_center, width, height, 
                                        dr, nth)
        
    if scan_traj == "grid":
        scan_cyc = plan_patterns.spiral_square_pattern("samx", "samy", x_center, y_center, 
                                                       width, height, int(width/stepsize_x), int(height/stepsize_y))
        
    if scan_cyc is not None:
        samx_points, samy_points = process_scan_cyc(scan_cyc)

    return samx_points, samy_points


def process_scan_cyc(scan_cyc):
    samx_points, samy_points = [], []
    for i in list(scan_cyc):
        for k, v in i.items():
            if k == "samx":
                samx_points.append(v)
            elif k == "samy":
                samy_points.append(v)
    return np.array(samx_points), np.array(samy_points)