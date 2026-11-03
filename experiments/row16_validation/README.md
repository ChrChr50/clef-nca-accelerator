# Row16 numerical extension

Predeclared candidate/protocol: `protocol.v1.json`. Existing accepted fidelity32 authority and original-paper reference are unchanged.

```
python -m unittest model_export.cartpole.test_row16_candidate model_export.cartpole.test_exact_blas experiments.row16_validation.test_resume -v
python experiments/row16_validation/evaluate.py --phase screen
python experiments/row16_validation/evaluate.py --phase long
python experiments/row16_validation/vectors.py
python experiments/row16_validation/vectors.py --check
```

Current continuation is stopped at G4/ADR-0016 after the row16 seed-41 failure. Do not resume the comparison automatically. `gate_snapshot.py --runs-confirmed-stopped` only publishes aggregates after the operator has stopped and checked the relevant processes; it does not stop processes itself.

The user subsequently authorized deeper diagnosis and a hardware-cost comparison. `diagnose.py` performs bounded seed-41 replay only through its already recorded action-1150 failure, checking the exact saved grids/actions and performing one-decision numerical/late-state probes. `probe_inputs.py` isolates individual observation quantization effects at decision 101. `probe_history.py` swaps the saved controller histories and observations at four late decisions. `estimate_hardware.py` computes logical bit counts and conditional schedules from existing format authorities; it does not run synthesis. Their safe JSON summaries and `docs/verification/ROW16_DIAGNOSIS_AND_PRECISION_COST.md` preserve the evidence. These diagnostic scripts do not resume qualification, choose a new format, or tune weights/fractions.

The screen uses calibration seeds 10/12 at 128 actions and new validation seeds 40/41 at 256. The long comparison uses the same four seeds at a source horizon of 10001 actions after clearing the screen's early-rejection condition. Both are three-arm comparisons: immutable float32, accepted fidelity32 and row16. Every arm has an independent persistent grid and its own original-source plant, with identical logical mask/count draws. Action divergence changes subsequent observations and is reported, not concealed as same-input drift. Saved matched-observation error is conditional on equal current observations; after earlier divergent histories it is not a pure one-step quantization error.

`screen_summary.json`, eventual `long_summary.json` and `vectors_manifest.json` contain safe identities/aggregate measurements. All learned grids, checkpoints, traces and output-major tensor images remain local/ignored under `artifacts/row16_validation/`. Export refuses paths outside `artifacts/`. Never commit or redistribute those files.

Progress is checkpointed every 16 completed logical actions. Re-run the identical command to resume; identity mismatch refuses reuse. The declared long cases may execute independently in parallel using `evaluate.episode` with the exact same authority/case. One process must own each seed; the sequential runner checks completed per-seed results before moving on. Do not run a second writer for the same in-progress seed. Unit tests compare uninterrupted versus interrupted/restored operation using public synthetic weights and explicitly widened unit-fixture plant limits; those widened limits are never used in numerical evaluation.

`exact_blas.py` is an optional separately verified research accelerator, **not used in the recorded primary screen/long commands**. It splits integer operands when necessary to prove binary64 products/partial sums exact, then performs recombination, bias, clipping and rounding as integers. Extreme and persistent comparisons pass against the unchanged int64 golden. It does not justify accepting approximate floating MACs in RTL or improve control quality.

Short censored survival, different action traces and zero saturation do not establish full-horizon equivalence. The continuation stops at new numerical or physical human gates rather than silently treating a format preference as measured acceptance of control loss. No training or checkpoint selection is performed.
