# P09 local delta verification

```powershell
.venv-p05/Scripts/python.exe -m unittest tb.p09_local_rule.test_support -v
.venv-p05/Scripts/python.exe tb/p09_local_rule/run.py --generate-only
.venv-p05/Scripts/python.exe tb/p09_local_rule/run.py --generate-only --restricted
.venv-p05/Scripts/python.exe tb/p09_local_rule/run.py
.venv-p05/Scripts/python.exe tb/p09_local_rule/run.py --restricted
```

The last two commands require Icarus `iverilog`/`vvp` and fail with exit 2 if
unavailable. They test lanes 1/2/3/4. No generation-only command proves RTL
equivalence. All parameter images/generated literals/logs remain in ignored
`artifacts/p09_local_rule/`; restricted mode needs pinned local model2 and six
accepted NPZs. Read the G5 compute packet before interpreting measurements.
