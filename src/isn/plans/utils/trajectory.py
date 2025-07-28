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
        samx_points, samy_points = process_scan_cyc(scan_cyc)
        
    elif scan_traj == "spiral_grid":
        scan_cyc = plan_patterns.spiral_square_pattern("samx", "samy", x_center, y_center, 
                                                       width, height, int(width/stepsize_x), int(height/stepsize_y))
        samx_points, samy_points = process_scan_cyc(scan_cyc)
        
    elif scan_traj == "grid":
        samx_points, samy_points = grid_points(x_center, y_center, width, height, stepsize_x, stepsize_y)
        samx_points = samx_points.ravel()
        samy_points = samy_points.ravel()
        
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

def grid_points(x_center, y_center, width, height, stepsize_x, stepsize_y):
    x_start = x_center - width/2
    y_start = y_center - height/2
    x_vals = np.arange(x_start, x_start + width + stepsize_x / 2, stepsize_x)
    y_vals = np.arange(y_start, y_start + height + stepsize_y / 2, stepsize_y)

    x_coords, y_coords = np.meshgrid(x_vals, y_vals)

    return x_coords, y_coords