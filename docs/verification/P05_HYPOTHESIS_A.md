# P05 Hypothesis A: locked-graph stabilization continuation

## Scope and disposition

This continuation tested whether better training could make the accepted
1,916-parameter Hanoi NCA learn a stable, task-relevant internal program
without changing its graph. It did not begin P06 or alter the immutable P03
reference, P04 environment, runtime boundary, or oracle firewall.

The experiment completed, but **Hypothesis A did not pass**. Its final
checkpoint is reproducible and finite as a file, but is not functionally or
numerically eligible for freeze.

## Implemented experiment

- Fire rate 0.5 is used in training, DAgger, probes, and evaluation.
- A deterministic mixed schedule uses 20--24 steps on three of every four
  iterations and the original 50--59 steps on every fourth iteration.
- All six exact peg permutations are implemented as equivariant state/action
  transforms and exhaustively unit-tested against P04 transitions.
- The curriculum proceeds through coherent standard-start trajectories,
  coherent arbitrary-state oracle-teacher trajectories, and coherent on-policy
  DAgger trajectories. The NCA grid persists between attempted moves.
- Training-only heads supervise legality, top disk on each peg, the
  source/auxiliary/goal peg roles for the largest-unsettled-disk subproblem,
  and that subgoal disk. Heads and labels are excluded from deployment.
- An independent post-training probe uses frozen NCA representations from all
  six channels at only the six output cells and held-out state identities.
- The graph has no inference clamp. Training uses a squared overflow penalty
  above absolute value 5, gradient clipping, and a hard training acceptance
  limit of 10. An over-limit state is not persisted or used for action; it
  supplies only a corrective gradient and its grid is reinitialized.
- Phase checkpoints contain the model, training-only heads, optimizer, RNG
  states, configuration, and curves. `--resume` passed an end-to-end smoke run.

## Recorded attempts

The first run used the measured paper-style `0.01` overflow coefficient. It
was interrupted after the standard phase produced finite but unbounded values
above 4,000. Its files remain under
`experiments/p05_hypothesis_a_attempt1_unbounded_penalty/`.

The corrected run used coefficient 1.0, a hard limit of 10, and learning rate
`0.0002`. It completed in 134.502 seconds before an evidence-only resumed pass.
Training rejected 6 standard, 4 arbitrary, and 5 DAgger states that crossed
the limit. No non-finite training state or gradient was accepted.

## Measured result

The fixed diagnostic set contains all 18 standard transfers for `n=1..6` and
one standard transfer each for unseen `n=7` and `n=8`.

| Measure | Observed |
|---|---:|
| Short 20--24 completed | 2/20 |
| Long 50--59 completed | 0/20 |
| Short legal / illegal attempts | 47 / 1,437 |
| Long legal / illegal attempts | 61 / 1,423 |
| Held-out legality-bit probe | 50.98% |
| Held-out top-disk probe | 33.33% |
| Held-out peg-role probe | 28.57% |
| Held-out subgoal-disk probe | 17.08% |

The independent 510-decision persistent-state soak remained finite in float32
but was not bounded. It eventually reached approximately `2.066e36`.
Training-time rejection therefore prevented corrupt training updates but did
not produce intrinsically stable deployed dynamics.

All seven acceptance predicates in `results.json` failed: bounded soak,
complete short and long diagnostics, and the four held-out probe thresholds.
Exact baselines, curves, rejection points, soak checkpoints, episode strata,
configuration, and the checkpoint hash are machine-readable in that file.

## Commands and observed results

| Purpose | Command | Result |
|---|---|---|
| Unit/contract validation | `.venv-p05\\Scripts\\python.exe -m unittest discover -s training/hanoi_nca/tests -v` | Pass: 12/12 before full run |
| Resume smoke | `run_hypothesis_a.py` with 1/1/1 iterations, reduced probes/soak, then `--resume` | Pass |
| First full attempt | `.venv-p05\\Scripts\\python.exe training\\hanoi_nca\\run_hypothesis_a.py --output experiments\\p05_hypothesis_a` | Interrupted after measured runaway finite state; preserved separately |
| Corrected full run | Same command after hard-limit correction | Experiment completed; acceptance failed |
| Evidence replay | Same command with `--resume experiments\\p05_hypothesis_a\\resume_after_dagger.pt` | Pass; evaluation/probes/soak reproduced |

## Interpretation

This does not establish that NCAs cannot solve Hanoi. It shows that this
bounded locked-graph continuation did not form decodable legality/relational/
subgoal state or stable long-horizon dynamics. More iterations cannot simply
be assumed to resolve those qualitative failures. Any next change remains a
G3 decision: another bounded locked-graph experiment, a declared architecture
or layout revision, or a nonfunctional structural-only freeze.
