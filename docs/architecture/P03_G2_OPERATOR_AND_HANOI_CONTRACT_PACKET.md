# P03 G2 decision record: immutable original NCA and accepted Hanoi contract

> Historical-scope notice (2026-10-06): retained for provenance, not the active forward implementation plan. ADR-0007 and docs/architecture/EMBODIED_NCA_VISION.md supersede task-specific choices. Original-reference evidence and dated experimental decisions remain preserved; no new embodied acceptance or model freeze is implied.

## Gate outcome

**G2 accepted on 2026-09-19.** The user selected the recommended Option A
without modification. ADR-0002 is accepted. P04 is authorized by this gate but
has not begun.

## Accepted decision

The reproduced original CartPole NCA operator graph is immutable. The bounded
Option A observation/action contract below is the interface that P04 and P05 may
target. No Hanoi adapter or training has been implemented.

## Immutable original contract

The machine-readable authority is
`reference/original_nca/operator_manifest.json`. In compact form:

- State is float32 NHWC `[B,32,32,6]`, initialized uniform in `[-0.1,0.1)`.
- Local rule is learned Conv2D 3x3 6-to-20 with zero SAME padding and ReLU,
  pointwise 20-to-30 with ReLU, and pointwise 30-to-6 linear, all biased.
- The executable graph has 1,916 parameters, not the paper's 1,854.
- One scalar Bernoulli mask per cell is shared by all channels. The Python
  predicate is `uniform <= 0.5`.
- The residual update precedes I/O rewriting. Active input cells are hard
  clamped every NCA step. Output marker channel 3 is rewritten, while output
  channels 4 and 5 accumulate `+1` each step in the raw Python behavior.
- Readout is channel 0 at `(13,16)` and `(17,16)`; `argmax` ties choose action
  zero. DQN values divide those outputs by `0.01`.
- The declared `(50,60)` schedule executes 50 through 59 NCA steps. Grid state
  persists between environment moves.
- Damage replaces all channels inside a random circle with uniform values in
  `[-1,1)`. The optional update noise is added to delta before masking.

This contract stays independently regression-tested. A later adapter must not
edit it.

## Evidence and remaining gaps

- Local source clone: revision
  `8c85be11b0838ea14ac51a11dac3098db43afed2`; 13 source/checkpoint artifact
  hashes and all six archived TensorFlow checkpoint-member hashes pass.
- Three shipped TFJS checkpoints have 1,916 float32 values each. Fixed local
  delta, complete-step, readout, and four-step rollout vectors are retained.
- The historical notebook environment is not reproducible exactly: TensorFlow,
  Gym, NumPy, CUDA, cuDNN, and training/evaluation seeds were not pinned.
- The repository states MIT only in `setup.py` and contains no license text or
  copyright notice; upstream bytes therefore remain outside this repository.
- Current executable source caps an episode after 10,000 steps, which cannot
  produce the paper's reported no-damage mean of 13,273. Exact historical
  empirical reproduction is therefore unavailable from the released artifacts.

## Accepted differences for the Hanoi derivative

These are the accepted interface constraints. P05 must express them in a
separate difference manifest and rerun all original regressions.

### Common across all viable options

- Preserve the 3x3 learned full-channel perception, ReLU/ReLU/linear layer
  pattern, synchronous old-state-to-new-state semantics, stochastic mask
  interface, and persistent hidden state.
- Replace two CartPole outputs with six ordered directed moves:
  `0->1`, `0->2`, `1->0`, `1->2`, `2->0`, `2->1`. Raw deterministic argmax
  remains the primary action selection. Legality masking is not part of the
  primary contract and may appear only as a labeled fallback/ablation.
- The host supplies observations and enforces the environment's legal transition
  grammar. The accelerator contains no move table, recursive solver, oracle ROM,
  or privileged next-move signal.
- Keep hidden state between moves and reset it only at accepted episode
  boundaries. Continue accepting externally supplied update-mask traces.
- Select one compile-time bound `N_MAX`; represent smaller puzzles explicitly
  rather than changing tensor shapes at runtime.

### Option A - disk-location one-hot, `N_MAX=8` (accepted)

For each disk from smallest to largest, provide three peg-location bits and one
present bit: `8 * 4 = 32` values. Add a three-value one-hot goal peg and one
normalized active disk-count value, for 36 logical observations. Map them to a
fixed set of input cells; absent-disk slots are zero with present=0.

Effects:

- Schedule/risk: simplest independent environment oracle and clean bounded
  generalization tests; moderate input-cell count.
- Clef: transducer remains external and semantically neutral; no future
  coalition labels are introduced.
- FPGA/ASIC: fixed dimensions and sparse binary observations are straightforward;
  six outputs modestly increase the final layer. Exact fit remains measured later.

### Option B - per-peg occupancy matrix, `N_MAX=8`

Provide a `3 x 8` bottom-to-top occupancy/rank matrix plus valid and goal fields.
This is visually local but requires a more elaborate encoding and more decisions
about normalization and empty-slot semantics.

Effects: potentially useful spatial structure, but greater adapter complexity
and more ways for host encoding to leak task structure. Hardware dimensions are
similar to Option A.

### Option C - smaller bound `N_MAX=6` with Option A encoding

Uses 28 logical observations including goal/count and reduces experiment and
input-layout cost. It weakens the bounded variable-disk claim and risks forcing
an interface change if eight-disk evaluation is later desired.

## Accepted recommendation

Option A with `N_MAX=8` represents state without supplying a solution,
supports every puzzle size 1 through 8 with one fixed interface, and makes
exhaustive P04 verification tractable (`3^8 = 6,561` legal disk-location states
before goal selection). Retain all six actions even when some are illegal so
legality behavior is measurable rather than hidden.

## Gate consequences

P04 may implement only the deterministic environment/oracle against this
interface. P05 may then create a separate adapter and difference manifest. The
canonical original reproduction remains unchanged. Any later change to the
accepted interface requires a superseding ADR.
