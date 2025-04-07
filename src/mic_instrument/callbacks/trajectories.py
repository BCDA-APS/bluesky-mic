'''
Trajectories for the mic instrument
'''


import matplotlib.pyplot as plt
import numpy as np


def snake(dwell, step_size, x_center, y_center, x_width, y_width):
    """
    snake function callback
    """
    rows = int(np.ceil(y_width / step_size))
    cols = int(np.ceil(x_width / step_size))
    ypts = np.linspace(y_center - y_width / 2, x_center + y_width / 2, int(rows + 1))
    x, y = [], []
    for i in range(rows):
        xpts = list(
            np.round(
                np.linspace(
                    x_center - x_width / 2, x_center + x_width / 2, int(cols + 1)
                ),
                5,
            )
        )

        if i % 2:
            x += xpts
        else:
            x += xpts[::-1]
        y += list(np.ones_like(xpts) * ypts[i])
        # curve_x, curve_y = semi_circle((xpts[-1],ypts[i]), (xpts[-1],ypts[i]+step),
        # step, step/2)
        # x += list(curve_x*-1)
        # y += list(curve_y)
    x = np.asarray(x)
    y = np.asarray(y)

    times = np.ones_like(x) * dwell
    dt = dwell
    times = np.ones_like(x) * dt
    return x, y, times


def raster(dwell, step_size, x_center, y_center, x_width, y_width, x_return_vel):
    """
    raster function callback
    """
    rows = int(np.ceil(y_width / step_size))
    cols = int(np.ceil(x_width / step_size))
    ypts = np.linspace(y_center - y_width / 2, y_center + y_width / 2, int(rows + 1))
    x, y = [], []
    for i in range(rows):
        xpts = list(
            np.round(
                np.linspace(
                    x_center - x_width / 2, x_center + x_width / 2, int(cols + 1)
                ),
                5,
            )
        )
        x += xpts
        y += list(np.ones_like(xpts) * ypts[i])

    x = np.asarray(x)
    y = np.asarray(y)

    dt = dwell  # noqa: F841
    times = raster_times(x, y, dwell, x_return_vel)
    return x, y, times


def raster_times(x, y, dt, return_vel):
    """
    raster times callback
    """
    times = np.ones_like(x)
    # find index where y changes.
    # calculate time for return velocity
    # create times arrays

    return times


def spiral(dwell, r_step_size, step_size, x_center, y_center, diameter):
    """
    spiral function callback
    """
    arc_num = int(np.ceil(diameter / r_step_size))
    start = x_center, y_center + r_step_size
    end = x_center, y_center - r_step_size
    x, y = [], []
    for r in range(arc_num):
        R = np.round((1 + 0.5 * r) * r_step_size, 5)
        pts_x, pts_y = semi_circle(start, end, R, step_size)

        x = np.append(x, np.round(pts_x, 5))
        y = np.append(y, np.round(pts_y, 5))
        start = np.round((pts_x[-1], pts_y[-1]), 5)
        if r % 2:
            end = np.round((x_center, y_center - (1.5 + 0.5 * r) * r_step_size), 5)
        else:
            end = np.round((x_center, y_center + (2 + 0.5 * r) * r_step_size), 5)
    dt = dwell
    times = np.ones_like(x) * dt
    # TODO: consider passing coordinared through equidistant()
    return np.asarray(x), np.asarray(y), np.asarray(times)


def semi_circle(start, end, R, step):
    """
    semi_circle function callback
    """
    xc = np.round((start[0] + end[0]) / 2, 5)
    yc = np.round((start[1] + end[1]) / 2, 5)
    d = np.round(np.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2), 5)
    # TODO: find way to calculate arc length instead of assuming semi-circle
    arc_length = np.round(2 * R * np.arcsin(d / (2 * R)), 5)
    try:
        npts = int(np.ceil(arc_length / step))
    except:  # noqa: E722
        print("why")
    t0 = np.arctan2(start[1] - yc, start[0] - xc)
    t1 = np.arctan2(end[1] - yc, end[0] - xc)
    thetas = np.linspace(t0, t1, int(npts))
    x = xc + R * np.cos(thetas)
    if t0 < t1:
        x *= -1
    y = yc + R * np.sin(thetas)
    return x, y


def lissajous(
    dwell,
    step_size,
    x_center,
    y_center,
    x_width,
    y_width,
    cycles,
    x_freq=7.7,
    y_freq=10,
):
    """
    lissajous function callback
    """
    npts = int(np.ceil(x_width / step_size) * cycles)
    pts = np.linspace(0, 2 * np.pi * cycles, npts)
    x = x_center + x_width * np.cos(x_freq * pts) / 2
    y = y_center + y_width * np.cos(y_freq * pts) / 2
    # TODO: consider passing coordinared through equidistant()
    times = np.ones_like(x) * dwell  # noqa: F841

    return x, y


def noise(size, arr):
    """
    noise function callback
    """
    pts = np.shape(arr)[0]
    noise = (np.random.rand(pts) * 2 - 1) * size
    return arr + noise


def trigger_events(center, x_width, y_width, res, x, y):
    """
    callback to trigger events
    """
    x_bounds = int(np.ceil(x_width / res) + 1)
    x_edge = np.linspace(
        center[0] - x_width / 2, center[0] + x_width / 2, int(x_bounds)
    )
    x_trig = []
    for i in range(x_bounds):
        edge = x_edge[i]
        for p in range(1, len(x)):
            p0 = x[p - 1]
            p1 = x[p]
            if (
                (p0 <= edge and p1 > edge)
                or (p0 < edge and p1 >= edge)
                or (p1 <= edge and p0 > edge)
                or (p1 < edge and p0 >= edge)
            ):
                x_trig.append(p)

    y_bounds = int(np.ceil(y_width / res) + 1)
    y_edge = np.linspace(
        center[1] - y_width / 2, center[1] + y_width / 2, int(y_bounds)
    )
    y_trig = []
    for i in range(y_bounds):
        edge = y_edge[i]
        for p in range(1, len(y)):
            p0 = y[p - 1]
            p1 = y[p]
            if (
                (p0 <= edge and p1 > edge)
                or (p0 < edge and p1 >= edge)
                or (p1 <= edge and p0 > edge)
                or (p1 < edge and p0 >= edge)
            ):
                y_trig.append(p)

    y_trig_trim = []
    for trig in y_trig:
        if trig in x_trig or trig + 1 in x_trig or trig - 1 in x_trig:
            pass
        else:
            y_trig_trim.append(trig)
    trig_idx = np.unique(np.append(x_trig, y_trig_trim)).astype("int")

    return trig_idx


def custom_plot(x, y, noise_x, noise_y, trig_idx, title="scan"):
    """
    create custom plot
    """
    plt.figure()
    plt.plot(x, y)
    # plt.scatter(noise_x, noise_y, marker=".", c="brown")
    plt.scatter(x[trig_idx], y[trig_idx], marker="*", c="black")
    plt.grid()
    # plt.xticks(np.arange(-x_width / 2, x_width / 2 + step, step))
    # plt.yticks(np.arange(-y_width / 2, y_width / 2 + step, step))
    plt.title(title)
    # plt.legend(["trajectory", "interferometer pos", "trigger events"], loc=1)
    plt.legend(["trajectory", "trigger events"], loc=1)


def equidistant(x, y, dt):
    """
    equidistant trajectory callback
    """
    pts = len(x)
    d_arr = np.asarray(
        [
            np.sqrt((x[i] - x[i - 1]) ** 2 + (y[i] - y[i - 1]) ** 2)
            for i in range(1, pts)
        ]
    )
    ctr = 0
    trig_idx = []
    for idx, d in enumerate(d_arr):
        ctr += d
        if ctr >= dt:
            trig_idx.append(idx)
            ctr = 0
    return np.asarray(trig_idx).astype("int")
