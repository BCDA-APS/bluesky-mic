from .run_engine import cat

def wax(scanno=None, label='None'):
    if not scanno:
        scanno=-1

    data = cat[scanno].baseline.read().to_pandas()
    if label:
        selected_cols = [c for c in data.columns if label in c]
        data = data[selected_cols]
    return data