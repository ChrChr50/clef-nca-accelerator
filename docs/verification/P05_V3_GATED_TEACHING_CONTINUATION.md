# P05 gated teaching continuation (2026-09-30)

## Authorization and boundary

The user authorized autonomous repair of the failed v2 paper-mechanics
teaching run, incremental training, clean replacement of its experiment data,
and periodic reporting. This work remains P05/G3 experimentation. It does not
accept a frozen model, alter the P04 observation/action/transition contract,
or authorize P06. The immutable CartPole reference and accepted v2 experiment
are not modified.

## Failed reference run

The earlier run's full warm-up ended at fresh-grid MSE 25.5460949 versus goal
0.02. All 48 fresh validation examples had six scores exactly -5; a
two-example backward probe yielded zero gradients for all six model tensors.
At imitation iteration 3,000, loss was 1.79175949 = ln(6), with gradient norm
zero. See `P05_V2_PAPER_TEACHING_CONTINUATION.md`. Its process was stopped, and
its 4.6 MB output directory was removed at the user's request. The retained
report and last checkpoint SHA-256 preserve the negative measurement, not the
full historical checkpoint.

## Trial 1: unclipped relay

The first replacement trial used the same 2,338-parameter eight-channel local
rule and v2 layout but removed the hard residual clamp. It trained a
fixed-near-input/one-output synthetic relay with target variance matched to
the original eight-input notebook, a 50% fresh-grid mixture, Adam at 0.001,
global gradient-norm clipping, and training-only overflow penalty. At update
500, it passed the preregistered relay gate: fresh normalized MSE 0.004985
(MSE 0.003473 against zero-baseline 0.696638), persistent-pool normalized MSE
0.013404 (MSE 0.009338), fresh max state 1.6290, aged max state 4.7151.
This establishes a learned local relay under that trial, not all-input
communication or Hanoi competence.

At update 94 of the next arbitrary-source relay stage (total update 594), a
state exceeded the trial's absolute-50 safety guard or became non-finite; the
numerical guard stopped the run before an optimizer step. The failed trial's
last resume SHA-256 was
`2dc3d34a4453f2a8b1e470d63584816ec2c1377a12a864c73b8e002ea75bdd75`.
The trial's bulky output was removed before the next run, per the user's
replacement-data preference. This is a numerical stability failure despite
successful local communication; it is not a model-capacity verdict.

## Trial 2: smooth bounded residual

Trial 2 uses a smooth arctangent bound with range (-5,5) and
nonzero derivative for every finite pre-bound state. It retains the same
logical interface, layout, local graph, target-variance curriculum, fresh/
persistent mixture, training-only labels, and gate-before-next-stage rule.
The bound is an experimental operator change that would require a separate
numerical/hardware decision before any model freeze. The first trial's
unclipped operator remains in `v3_runtime.py` for reproducibility.

The clean replacement run began at 2026-09-30 11:02 Eastern under
`experiments/p05_v2_paper_flow/`, now with schema
`clef.p05.hanoi-v4-gated-teaching.v1`. At local-relay iteration 500 it passed
both fresh and persistent-grid gates. It then failed the arbitrary-source
relay gate at that stage's iteration 2,500: fresh normalized MSE 0.742418,
persistent-pool normalized MSE 0.796377, versus goal 0.15. States remained
bounded below 5, so this was a communication-learning failure, not numerical
overflow. A deterministic fresh validation probe at stage iteration 2,000
showed source-output correlation approximately 0.94 for source distance two,
but only about 0.19--0.37 for distances three through six (small distance
strata, so these are diagnostic rather than confidence intervals). The
10--16-step half-fire curriculum had jumped too abruptly from one nearby
site to all 36 source sites. The failed checkpoint SHA-256 was
`7f87a4396f728cc8e3bde33b41b66007576a36c4e9fd8983e25271351150f804`.
This bulky run output will be replaced rather than appended.

## Trial 3: distance-and-time curriculum

The next trial keeps the smooth bound but expands single-input sources by
Chebyshev radius 3, 4, 5, then 6 from the first output cell. Recurrent steps
increase with distance before six-output broadcast and multi-input
combination. Its distinct schema prevents accidental resume from trial 2.
This change is motivated by the measured distance-stratified failure above.
The clean trial began at 2026-09-30 11:16 Eastern under the same single
replacement output directory, now with schema
`clef.p05.hanoi-v5-gated-teaching.v1`. It passed local relay at iteration
500: fresh normalized MSE 0.005670, persistent-pool normalized MSE 0.008606,
and maximum fresh/aged state magnitudes 2.475/3.436. It then entered the
radius-three relay stage. This is interim signal learning, not completion of
the full teaching flow.

After the radius-curriculum edit, P05 test discovery passed 25/25, repository
smoke passed, the oracle firewall passed, and `git diff --check` passed.

The new local tests passed 4/4, a two-step stop/resume smoke passed, and the
full shared regressions passed: P03 17/17, P04 11/11, P05 24/24, and the
oracle firewall. `git diff --check` passed. The two disposable smoke output
directories were removed after their tests; only the one live replacement
run directory is retained.

Trial 3 stopped at radius-three relay iteration 2,000 (total 2,500): fresh
normalized MSE 0.550857, persistent-pool normalized MSE 0.567732, both above
the 0.15 gate. Fresh/persistent maximum state magnitudes were 2.196/2.674,
so this was not a numerical overflow. The last checkpoint SHA-256 was
`f1c82bf499e6e4ed09b26f131ed68e42987f29395f5db7bc56f504acc8b55c1b`.
The process exited before the next revision; the bulky run data is to be
replaced after preserving this record.

## Trial 4: correcting an inaccessible-input layout

Code inspection found a structural defect in the v2 experimental layout.
The 36 hard-clamped inputs occupy a dense 9-by-4 block. Fourteen sites
(`5,6,9,10,13,14,17,18,21,22,25,26,29,30`) have no noninput site in their
3-by-3 neighborhood. The local rule can use a value from one of these sites
only to change another input site, whose state is overwritten at the end of
each epoch. Consequently those 14 logical observations cannot influence an
output in this operator, regardless of weights or recurrence count. A source
response probe had already found zero response at several of these indices.
This makes the full 36-input mean warm-up impossible for v2, independently of
optimizer choice.

The reversible v6 spatial fork keeps the observation/action order, six output
coordinates, 8-channel graph, 2,338 shared parameters, stochastic schedule,
and smooth bound. It places the four fields of each disk/goal row at columns
9, 11, 13, and 15, leaving mutable interleaved columns. Static checks found
zero trapped sources and zero input/output collisions; maximum pairwise
input/output Chebyshev distance is nine, and all 36 inputs are within radius
eight of output zero. This proves topological reachability, not learned
communication. The stage curriculum now includes radius eight before
broadcast. The new layout is selected explicitly by the gated runner; the
v2 runtime's default layout remains unchanged. The new run has a separate
schema and layout hash in its checkpoint config, preventing accidental resume
from trial 3. P05 unit discovery passed 26/26 after this edit.

The clean run resumed from a two-update smoke checkpoint at 12:18 Eastern.
At total update 1,000, radius-three relay passed on the spaced layout at its
minimum stage iteration 500: fresh normalized MSE 0.061550 (raw MSE
0.035957), persistent-pool normalized MSE 0.131816 (raw MSE 0.077007), both
below 0.15. Fresh/persistent maximum state magnitudes were 3.647/3.834.
The runner advanced to radius-four relay. This directly reverses trial 3's
radius-three failure but says nothing yet about all-input aggregation or
Hanoi actions. Checkpoint SHA-256 at this gate:
`ef1c0d3970b926fd2d0c3720d2dafb72021763192c6330bba9ae144cb98e58e4`.
After the explicit-layout regression addition, P05 tests passed 27/27;
P03 17/17, P04 11/11, repository smoke, oracle firewall, compilation, and
`git diff --check` also passed.

At the 13:06 Eastern heartbeat, trial 4 had advanced through the single-source
radius gates, six-output broadcast, eight-input combination, 36-input
combination, and routing. The 36-input combination gate passed at total update
5,750 with fresh/persistent normalized MSE 0.025857/0.031589 against the
0.15 threshold. Routing passed at total update 6,750 with fresh/persistent
normalized MSE 0.078156/0.072640 against the 0.10 threshold. The latest
fresh/persistent maximum state magnitudes were 3.088/3.090, below the
absolute-5 guard; no failure file or stderr was present. The next stage is
legality (no validation result yet). The latest resume SHA-256 was
`272d24817dbe2507eea08dc8c3e8fb68f7061048f1891f2eedfa42d639d70c1b`.
These results establish synthetic aggregation and a training-only routing
target on the tested samples, not held-out action selection or closed-loop
Hanoi completion.

## Trial 4 outcome and trial 5 controlled action-value repair

Trial 4 subsequently passed legality, but the two-disk imitation gate failed
at stage iteration 4,000 (total updates 11,250). Fresh/persistent action
accuracy was 0.4375/0.479167 against 0.85; maximum state magnitudes were
4.3799/4.3894, so this was not numerical overflow. The last training batch
loss was 0.007561, illustrating that fitting sampled training states did not
establish generalization. The previous 48-example validation repeated only
four unique held-out two-disk states. The failed `resume.pt` SHA-256 was
`35f367aefa541ecb84011d2377c079ec67109adb159ea1fc32ac05d37f547e6c`.

Trial 5 starts from trial 4's passed 36-input combination weights, preserving
its verified spatial warm-up while isolating the decision-teaching change.
The small 10 KB seed checkpoint is retained as
`experiments/p05_v6_verified_warmup_seed.npz`; bulky failed-run data is
replaced after confirming the old process exited. The new runner is
`training/hanoi_nca/run_v7_teaching.py`, with proposed design rationale in
ADR-0006. It teaches all six channel-zero scores as signed one-step distance
changes and channel-one output cells as simultaneous auxiliary legality
logits. The oracle is training/evaluation-only. Persistent grid/state pairs
advance together through P04, with identity-split checks; fresh grids remain
mixed. Recurrence grows from 12–24 to 50–59 steps. Validation uses all
distinct small-n held-out states and multiple grid/mask seeds; final held-out
and closed-loop results remain required. A two-update start/resume smoke and
focused tests passed. Trial 5 is not a G3 freeze or evidence of Hanoi solving.

The old failed-run directory (resume checkpoint, logs, and intermediate stage
checkpoints, approximately 4 MB) and disposable smoke directory were removed
after retaining the measurement/hash above and the small warm-up seed. They
are not recoverable from the live experiment directory. The clean trial 5 run
was started at about 16:32 Eastern. At its first 250-update checkpoint,
stage 0 (two-disk, 12–24-step recurrence) measured fresh action accuracy
0.125 over 16 decisions from four distinct held-out starting states and
four grid seeds; coherent-successor accuracy was 0.0 over eight nonterminal
decisions. Fresh/persistent state maxima were 1.631/1.659, well below five.
This early point is not convergence evidence. P03 17/17, P04 exhaustive
11/11, P05 29/29, oracle firewall, compileall, and `git diff --check` passed.

At 1,000 short-recurrence updates, fresh/coherent-successor accuracy remained
0.125/0.0 and state maxima remained 1.547/1.673. The run was stopped
cleanly at its saved checkpoint (SHA-256
`b9264fd0269e8c9a0f274657751f4bac9cb908a6844883d839f182f278d2d46d`).
This exposed a curriculum-gate error: asking 12–24-step decisions to meet
the final 0.85 policy gate would prevent reaching the 50–59-step phase whose
longer propagation is central to the hypothesis. The r2 schedule keeps the
first two phases at 1,000 updates each as numerically gated preparation and
applies decision-accuracy gates only at 50–59 steps. This is a new run from
the same verified warm-up seed, not an in-place continuation of the stopped
weights. The preceding bulky trial data is replaced after retaining the hash.
The r2 replacement was launched about 16:39 Eastern and its 250-update
checkpoint reports stage 0 running with finite states (fresh/persistent maxima
1.631/1.659). Post-revision P05 tests passed 30/30 and the oracle firewall
and whitespace checks passed. The first two stages are preparatory, so their
current action accuracy is diagnostic rather than a pass/fail criterion.
At total update 1,000, preparatory stage 0 completed its fixed duration with
fresh/coherent-successor action accuracy still 0.125/0.0 across 16/8
decisions, mean optimal margins -0.0513/-0.2581, and maximum absolute grid
values 1.547/1.673. It advanced to stage 1 (25–40 recurrent steps) without
claiming a policy gate. The running checkpoint SHA-256 at the transition was
`75d93ae0ea14ab8f31fcf05fa61b53139222ab051dddf0ecfdc718fff02cf1d1`.
