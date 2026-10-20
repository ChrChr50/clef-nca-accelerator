# Original CartPole NCA reference

This directory is a clean-room, inference-focused Python reproduction of the
CartPole neural cellular automaton (NCA) published by Variengien et al. It is
the immutable architectural ancestor for later project work. It contains no
Tower-of-Hanoi behavior.

The implementation deliberately does not copy the upstream Python sources or
redistribute its checkpoints. The upstream repository declares `MIT` only in
`code/setup.py` and contains no license text or copyright notice. Use the local
source clone at `self-organized-control/`, whose exact revision and artifact
hashes are recorded in `provenance.json`.

## Reproduce

From the repository root with Python 3.12 and NumPy 2.3.5:

```text
python -m unittest discover -s reference/original_nca/tests -v
python reference/original_nca/tools/verify_upstream.py --upstream self-organized-control
python reference/original_nca/tools/run_empirical.py --upstream self-organized-control --model model1 --episodes 3 --max-steps 100 --output reference/original_nca/empirical_results.json
```

The unit suite uses checked-in synthetic golden vectors. The upstream verifier
adds fixed-checkpoint tests against all three shipped TensorFlow.js weight
files, including closed-loop CartPole action traces. The empirical command
evaluates a named checkpoint in a clean-room CartPole dynamics implementation;
the checked-in bounded result retains per-seed outcomes and censoring metadata.

See `PROVENANCE.md`, `DISCREPANCIES.md`, and
`../../docs/verification/P03_EMPIRICAL_REPRODUCTION.md` before interpreting
results.
