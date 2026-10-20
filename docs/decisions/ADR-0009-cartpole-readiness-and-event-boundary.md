# ADR-0009: CartPole checkpoint readiness and event boundary

- Status: **Accepted — G3E complete; model2 freeze conditional**
- Proposed: 2026-10-07
- Accepted: 2026-10-07
- Decider: User
- Stage/gate: E02/G3E
- Supersedes: None
- Related requirements: CART-002 through CART-004, EMB-003 through EMB-005, E02-001 through E02-006

## Context

ADR-0008 selected the original-reference CartPole as the first FPGA
benchmark, not a weight/protocol freeze. E01 consolidated its plant and
controller boundary. P03 verified three released checkpoints and measured
three-seed long-control comparisons, with one model2 30,000-action censoring
and incomplete historical paper-statistics reproduction. The detailed G3E
evidence and decision dimensions are in
`docs/architecture/E02_G3E_CARTPOLE_READINESS_PACKET.md`.

## Options

1. **Conditional model2 (recommended):** choose the pinned released model2
   as a freeze candidate under fresh-grid-per-episode, persistent-between-
   action, source 10,001-action, no-perturbation primary protocol. Require a
   prospective 10-seed qualification at >=8/10 horizon completions and the
   existing exact golden tests before final freeze. Keep extended/noise/damage
   studies diagnostic and local weights restricted pending rights disposition.
2. **Model1:** same protocol and qualification, accepting the observed
   long-control disadvantage in exchange for a deliberately different
   checkpoint/robustness tradeoff. Model3 remains measured but is not
   recommended on ordinary longevity evidence.
3. **Defer freeze:** gather more software/reset/rights evidence without
   starting P06 or retraining. This preserves choice at schedule cost.

## Proposed cross-cutting boundary

Reference-faithful execution is the ordinary baseline. Only work avoidance
proved to preserve complete logical state/action and RNG assignment may be
classified exact-preserving. State-change sleeping and event-triggered update
semantics are a separately named, separately accepted behavior variant; they
must not be inserted into the published controller by default. The simulated
20 ms plant step is not a measured real-time deadline. No inferred state
clamp, fixed-point format, public weight license, or board fit is decided
here.

## Accepted decision

On 2026-10-07 the user explicitly accepted Option 1 and the recommended
cross-cutting protocol. Select the released **model2** TFJS checkpoint as the
*conditional* CartPole FPGA freeze candidate, not a frozen or qualified model.
Its pinned weight-blob SHA-256 is
`ee8e4ad597d73dc616e60e91a5af056c96beb9f2c18652cfb1a1906247fbc009`.
The immutable P03 operator and E01 host/plant boundary remain authoritative.

- Start each episode with a fresh seeded NCA grid. Persist that grid across
  all decisions within the episode. Do not add the notebook's optional 1%
  within-episode grid reinitialization to the primary baseline. The released
  multi-episode harness's different/ambiguous pool behavior remains a
  documented discrepancy, not a claim of historical equivalence.
- Use the released CartPole `max_steps=10000` behavior: a balanced episode
  terminates after action 10,001. The 30,000-action runs, injected update
  noise, damage, input deletion and alternative reset protocols are
  separately labeled diagnostics, never part of the primary qualification.
- Before **final P06 weight freeze**, directly qualify model2 on held-out
  seeds 10–19 with the source-default plant, fresh-grid/no-perturbation
  protocol. Record each score and action count. Require at least **8 of 10**
  episodes to reach action 10,001 and all pinned fixed-checkpoint golden tests
  to pass. This is a prospective threshold; the run has **not** occurred and
  no success is asserted. Failure returns to G3E for a new human decision;
  it does not authorize a lower threshold, another checkpoint or retraining.
- Use step-synchronized simulated control: complete 50–59 NCA updates and
  one action before advancing the plant one simulated 20 ms step. Measure
  wall-clock latency later; do not claim a 20 ms real-time deadline.
- Preserve the original unclipped float inference semantics for this
  decision. Recurrent state range, fixed-point widths, saturation and
  equivalence are P07/G4 questions, not inferred from finite weight ranges.
- Permit **local-only** use of hash-pinned weights from the ignored upstream
  clone for the private lab prototype. Do not commit, publish, ship, or share
  weight bytes or FPGA images containing them absent an explicit
  upstream/institutional rights determination. A local-only P06 manifest may
  reference the hash without including restricted tensors in Git.
- Keep reference-faithful synchronous execution as the baseline. Only
  proved-equivalent work avoidance may be labeled exact-preserving.
  State-change sleeping, event-triggered updates and other changed dynamics
  are **not accepted** as a baseline variant; they need a separate proposal,
  evidence and human decision.

G3E is complete as a protocol/conditional-candidate decision. Acceptance
does not itself run the ten-seed qualification, freeze weights, start P06,
clear redistribution rights, establish hardware fit/timing or authorize
CartPole retraining. The user explicitly instructed a stop before P06.

## Consequences and validation

Model2's observed three-seed extended control provides a strong candidate,
but not held-out reliability. The accepted bounded source-default
qualification and hash-pinned deterministic golden pass are prerequisites to
a local-only P06 freeze; failure returns to G3E rather than silently lowering
the criterion or retraining. Rights review controls any committed or shared
weight image. P07 measures numerical range/quantization; P12–P14 measure
actual latency, throughput, work and FPGA control quality. Portable
SystemVerilog and ASIC wrapper isolation remain governed by ADR-0001.

This decision selects a conventional fixed-weight NCA candidate baseline. It
does not establish sparse body-wide scaling, autopoiesis, CEC,
Medium Rosen, or transferable weights for later custom-surface/EvoGym tasks.
