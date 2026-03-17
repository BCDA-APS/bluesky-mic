from apsbits.core.instrument_init import oregistry

import bluesky.preprocessors as bpp
import bluesky.plans as bp
import bluesky.plan_stubs as bps


softglue = oregistry['softglue']
socketserver = oregistry['socketserver']


def interf_measurement_step_test(detectors, motor, step):
    
    yield from bps.abs_set(motor, step, wait=True)
    softglue.up_counter_3.clock.put("1!")
    softglue.and_1.in_2.put("1")
    yield from bps.sleep(1)
    softglue.and_1.in_2.put("0")
    return (yield from bps.trigger_and_read(detectors))


def scan_piezo(detectors, motor, position_list):
    softglue.reset()
    # socketserver.hdf1.free_buffer.put(1)
    socketserver.setup_flyscan_mode(hdf_images=10000)
    socketserver.stage()
    socketserver.trigger()
    yield from softglue.start()
    yield from bp.list_scan(detectors, motor, position_list, per_step=interf_measurement_step_test)
    for i in range(11):
        softglue.scal_to_stream_1.flush.put("1!")
        yield from bps.sleep(0.1)
    socketserver.unstage()
    socketserver.hdf1.unstage()
    softglue.stop()


def kb_y_tuning():
    for _ in range(20):
        yield from bps.mvr(kb.y_us.fine, 0.01, kb.y_ds.fine, -0.01)
        sample.y.disable()
        yield from bp.rel_scan(detectors, sample.fine_y, -0.002, 0.002, num=101)
        max_pos = bec.peaks['max']['me7_total_roi1'][0]
        rel_move = max_pos - 0.045
        sample.y.enable()
        yield from bps.mvr(sample.y, rel_move)


def kb_theta_y_tuning():
    yield from bps.mvr(kb_theta_y, -0.55)
    for _ in range(20):
        yield from bps.mvr(kb.theta_y.fine, 0.05)
        yield from bp.rel_scan(detectors, sample.x, -0.0025, 0.0025, num=101)
        max_pos = bec.peaks['max']['me7_total_roi1'][0]
        yield from bps.mv(sample.x, max_pos)