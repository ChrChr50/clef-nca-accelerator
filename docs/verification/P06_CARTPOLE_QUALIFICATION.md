# P06 model2 qualification and freeze evidence

Status: **completed 10/10; qualification failed 6/10 versus required 8/10;
no freeze**. Accepted decision: ADR-0009. P06 returns to G3E. No retraining,
Hanoi P05 work, RTL, quantization or changed event variant is part of P06.

## Predeclared protocol and identities

- Source: ignored `self-organized-control` revision
  `8c85be11b0838ea14ac51a11dac3098db43afed2`.
- Released model2 TFJS weight-blob SHA-256:
  `ee8e4ad597d73dc616e60e91a5af056c96beb9f2c18652cfb1a1906247fbc009`.
- Protocol: `sw/cartpole/qualification.v1.json`, SHA-256
  `e0c57dca542b7b5677381f27d573c4ba4e68533f2927c4d828c5f2b85556246e`.
- Harness: `sw/cartpole/qualification.py`, SHA-256
  `6536eb55f3e4f089c968dbc4d26380181f7fc23a7e9a25b403fa5092c1531a35`;
  runner `experiments/p06_cartpole/run_qualification.py`, SHA-256
  `0d0f2245bcfef2438ef10d295c3af6e85b8b37a2ea591561eff0d6bff56ef4ec`.
- E01 boundary: `sw/cartpole/deployment.py`, SHA-256
  `62e8ea26846fc425f65bf8892d5d0f2ddef064202a2682bb1f241d937c4ddc9e`.
- Pinned execution environment: Python 3.12.14, NumPy 2.3.5 on Windows
  x86-64. The run records its actual runtime in every completed episode.
- Seeds 10–19, each mapped to a fresh source plant with `RandomState(seed)`
  and separate `seeded_initial_grid(seed ^ 0x5A17)`. Subsequent schedule and
  mask draws consume that plant RNG in logical action/epoch/cell order.
- Primary plant `max_steps=10000`, balanced horizon at action 10,001;
  50–59 NCA epochs/action, update predicate `uniform <= 0.5`, persistent
  grid within episode, no noise/damage/input deletion or random in-episode
  reinitialization. Score sums source runtime reward including final action.
- Pass only if all ten episodes complete, at least eight end balanced at
  action 10,001, and pinned checkpoint goldens pass. If not, return to G3E;
  no threshold relaxation, retry pooling, checkpoint substitution or
  automatic retraining.

The executable run command is:

```text
.venv-p05\Scripts\python.exe -u experiments/p06_cartpole/run_qualification.py
```

## Results

The run completed all ten prescribed seeds without retry pooling. The pinned
upstream verifier passed its revision, 13 artifact hashes and three
fixed-checkpoint rollouts at runner startup. All ten records use the same
protocol hash and model2 blob hash on Python 3.12.14 / NumPy 2.3.5.

| Seed | Actions | Score | Source termination | Reached balanced horizon? |
|---:|---:|---:|---|---|
| 10 | 10,001 | 9,718.27 | horizon | yes |
| 11 | 8,228 | 8,035.34 | pole-angle limit | no |
| 12 | 1,334 | 1,307.09 | pole-angle limit | no |
| 13 | 10,001 | 9,690.47 | horizon | yes |
| 14 | 6,891 | 6,742.72 | pole-angle limit | no |
| 15 | 10,001 | 9,750.24 | horizon | yes |
| 16 | 3,976 | 3,783.03 | pole-angle limit | no |
| 17 | 10,001 | 9,779.15 | horizon | yes |
| 18 | 10,001 | 9,698.86 | horizon | yes |
| 19 | 10,001 | 9,789.89 | horizon | yes |

**Observed result: 6/10**, below the accepted >=8/10. Mean action count
8,043.5 (range 1,334–10,001), mean score 7,829.51 (range
1,307.09–9,789.89). The six horizon-ending scores are finite and include
the terminal transition. All four early failures were the source pole-angle
limit. This small ten-seed result is not a population reliability estimate
or a reproduction of the paper's 100-run table.

The complete scores, counts, action hashes, ordered-mask-hash digests,
initial/final plant/grid hashes, termination labels and runtime are in
`experiments/p06_cartpole/results.jsonl`; the decision is in `summary.json`.
Their respective SHA-256 identities are
`7e63b5eddb23eb3a40527beb026d1e91360d91d54ed49073cf02d1b9b0ff85f5`
and `885d5207577809c00ee35e8ada4c4378d324dc916c28060bcfd9134cab2d95b8`.
An ignored progress snapshot was never counted as a completed result. P03
seeds 0–2 and its 30,000-action diagnostic were not substituted.

The command exited nonzero after writing the failed summary, as intended.
Invoking the local exporter then raised `ValueError: accepted qualification
has not passed; refusing export`; no restricted model2 export exists under
`artifacts/p06_cartpole/restricted/`. No resolved P06 freeze manifest was
created. The unchanged original reference and E01 manifests remain the
software authorities; the conditional candidate in ADR-0009 is not a
frozen/deployable weight decision.

## Scope and next checks

Fast E01/qualification-harness and synthetic export regressions are added to
hosted smoke CI without upstream weights; no hosted run is claimed. Local
pinned-checkpoint verification and this long control run remain separate.
The exporter is implemented but gated off by the failed summary. No
quantized or FPGA image is authorized. P07 profiling, G4 numerical choice,
RTL and FPGA quality remain future stages. See the G3E return packet and
unaccepted ADR-0010 for evidence-based alternatives; nothing is silently
relaxed or retrained.

## Subsequent user-authorized direct source comparison

On 2026-10-07, the failing seed 12 was replayed against actual upstream
`NeuralCA`/CartPole Python classes in an isolated TensorFlow 2.15.1 runtime,
with model2 and the identical ADR-0009 replay inputs. **Both implementations
chose identical actions and terminated at action 1,334 with exactly the same
score and plant state.** Maximum full-grid endpoint error was 5.00679e-6,
with no P03 tolerance violation. See `P06_UPSTREAM_PARITY.md` for the full
method, tests, runtime and distinction from the historical DQN/paper protocol.
This verifies one early failure also occurs with the released source operator;
it does not directly establish upstream's ten-seed success rate, reproduce the
paper table, pass the existing gate or authorize a model freeze.
