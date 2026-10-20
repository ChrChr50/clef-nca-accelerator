# P08 primitive verification

```powershell
.venv-p05/Scripts/python.exe -m unittest tb.p08_primitives.test_vectors -v
.venv-p05/Scripts/python.exe tb/p08_primitives/run.py --generate-only
.venv-p05/Scripts/python.exe tb/p08_primitives/run.py
.venv-p05/Scripts/python.exe tb/p08_primitives/run.py --restricted
```

The simulation commands require `iverilog` and `vvp` on PATH and fail explicitly
with exit 2 if absent. `--generate-only --restricted` can prepare local restricted
tests without pretending simulation ran. Generated benches/results/logs are
ignored. Public CI uses synthetic fixtures only. See
`docs/architecture/P08_PRIMITIVE_INTERFACES.md` for exact semantics and gaps.
