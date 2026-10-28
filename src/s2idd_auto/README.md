## Demo Instrument

For one downstream ion chamber measurement in a session started with
`s2idd_auto.startup`, run:

```python
RE(read_dsic_counts(count_time=1.0))  # integration time in seconds
```

This triggers the Joerger scaler once and records `joerger_scaler_dsic_counts`
in one primary event, along with the other scaler readings. The DSIC count is
also logged. The scaler remains in one-shot mode with the requested integration
time. Acquisition completion uses the device's preset-time wait plus settling
margin; it does not monitor a hardware done signal.

The plan returns the numeric count through `yield from read_dsic_counts(...)`
when called by another plan. A normal `RE(...)` call returns run UIDs according
to the RunEngine configuration.
