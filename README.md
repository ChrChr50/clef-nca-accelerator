# Clef/NCA Accelerator

A portable fixed-weight SystemVerilog accelerator for the neural cellular
automaton in *Towards Self-organized Control: Using Neural Cellular Automata
to Robustly Control a Cart-pole Agent*. The current target is an FPGA controller
connected to the reference paper's simulated CartPole plant.

The controller maintains a 32×32×6 recurrent grid. A shared 1,916-parameter
three-layer local rule evolves the grid for 50–59 epochs per action. Four
observations are written at eight input sites; two output cells determine
left/right force. Controller state persists between actions.

## Implementation status

- The original floating-point operator and modified CartPole plant have been
  reproduced, with recorded source discrepancies and empirical limitations.
- Released model2 is frozen. Its original ten-seed qualification completed the
  source horizon in **6/10 episodes**, below the original 8/10 criterion; the
  accepted freeze explicitly retains that limitation.
- **fidelity32** is the accepted integer arithmetic: signed state 32/F24,
  kernels 24/F22 and accumulators/bias 62/F46, ties-to-even rounding and saturation.
- Portable arithmetic primitives and a folded local-rule RTL engine exist.
  Recorded HDL simulation/synthesis verification is pending. There is no complete
  grid scheduler, integrated FPGA controller, measured board fit or hardware demo.
- The initial board target is the DE1-SoC. ASIC work and further embodied-control
  benchmarks remain later work. This fixed controller does not establish
  autopoiesis or closure to efficient cause.

See [implementation status](docs/STATUS.md),
[architecture](docs/architecture/EMBODIED_NCA_VISION.md),
[local-rule explanation](docs/architecture/NCA_LOCAL_RULE_TEACHING_MAP.md), and
[design decisions](docs/decisions/README.md).

## Repository map

| Location | Purpose |
|---|---|
| `reference/original_nca/` | Original NCA and source-aligned CartPole executable reference |
| `sw/cartpole/` | Host/controller interface, deterministic replay and qualification |
| `model_export/cartpole/` | Accepted model validation, local export and bit-accurate integer golden |
| `rtl/core/` | Portable SystemVerilog primitives and folded cell-rule engine |
| `tb/` | Synthetic and separately identified checkpoint-dependent hardware verification |
| `experiments/` | Reproducible runners and compact measured results |
| `boards/`, `rtl/wrappers/`, `flows/` | Board/technology integration boundaries; currently largely placeholders |
| `docs/` | Architecture, numerical contracts, decisions and verification reports |
| `reference/hanoi/`, `training/hanoi_nca/` | Historical Hanoi experiments and retained regressions |

## Setup

Use **Python 3.12** and the pinned NumPy 2.3.5 environment. For example:

```text
python -m venv .venv
python -m pip install --require-hashes -r requirements/ci.lock
```

Activate `.venv` before the installation and commands below (`.venv/Scripts/Activate.ps1`
on PowerShell or `source .venv/bin/activate` on POSIX shells).

## Verify without released checkpoints

These checks use project sources and synthetic fixtures; no upstream weights
or FPGA board are required:

```text
python scripts/run_smoke.py
python -m unittest discover -s reference/original_nca/tests -v
python -m unittest discover -s sw/cartpole/tests -v
python -m unittest model_export.cartpole.test_export_local model_export.cartpole.test_fixed_point model_export.cartpole.test_accepted_arithmetic -v
python -m unittest tb.p08_primitives.test_vectors tb.p09_local_rule.test_support -v
python -m unittest discover -s reference/hanoi/tests -v
python -m unittest discover -s training/hanoi_nca/tests -v
```

With **Icarus Verilog** (`iverilog` and `vvp`) on PATH, run the synthetic RTL tests:

```text
python tb/p08_primitives/run.py
python tb/p09_local_rule/run.py
```

`--generate-only` produces the benches and Python comparisons without running
HDL. Successful generation is not a successful RTL simulation. The GitHub
workflow runs the synthetic software and RTL commands independently of model2.

## Run the released controller locally

Upstream checkpoint redistribution has not been established. Obtain the pinned
upstream repository separately; it remains ignored here:

```text
git clone https://github.com/aVariengien/self-organized-control.git self-organized-control
git -C self-organized-control checkout 8c85be11b0838ea14ac51a11dac3098db43afed2
python reference/original_nca/tools/verify_upstream.py --upstream self-organized-control
python reference/original_nca/tools/run_empirical.py --upstream self-organized-control --model model2 --episodes 1 --max-steps 100 --output artifacts/cartpole-smoke.json
```

Create `artifacts/` if needed. This is a bounded simulation, not a repetition of
the paper's full statistics or the ten-seed qualification. The default empirical
runner also evaluates perturbation conditions; see `--help` and its report.
Float comparisons use the documented cross-runtime tolerance; integer RTL
comparison requires exact equality at the declared boundaries.

The accepted local float export is:

```text
python model_export/cartpole/export_local.py --accepted-freeze
```

It is not already a quantized hardware memory image. Keep upstream weights,
derived fixtures and device images in ignored local artifacts. See
[provenance](reference/original_nca/PROVENANCE.md),
[numerical contract](docs/architecture/P07_INTEGER_GOLDEN_CONTRACT.md), and
[experiment instructions](experiments/p07_cartpole/README.md).

## Historical work and rights

Hanoi code, training checkpoints and negative results are retained for research
reproducibility. They are not the current deployment target. Optional historical
training dependencies are in `requirements/p05-training.lock`.

The repository remains private and all rights reserved under [LICENSE](LICENSE).
Third-party material retains its own terms. Generated build trees, local
environments and personal development records are excluded from the source tree.
