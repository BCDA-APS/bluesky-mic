import bluesky.plan_stubs as bps

def save_ophyd_value(ophyd_obj):
    yield from bps.create(f"{ophyd_obj.name}")
    yield from bps.read(ophyd_obj)
    yield from bps.save()