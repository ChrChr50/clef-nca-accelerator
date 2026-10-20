# P06 return to G3E — model2 qualification did not meet 8/10

Status: **human decision required; no P06 freeze**. The accepted ADR-0009
protocol was run to completion on exactly seeds 10–19. The original graph,
operator, checkpoint bytes and E01 plant/controller seam were not changed.
The full method, per-seed scores and hashes are in
`docs/verification/P06_CARTPOLE_QUALIFICATION.md` and
`experiments/p06_cartpole/`.

## What the test establishes

All three pinned checkpoint goldens and upstream artifact checks passed.
Released model2 reached the balanced source 10,001-action horizon in **6 of
10** held-out episodes, below the accepted **8 of 10** threshold. The other
four episodes lasted 1,334, 3,976, 6,891 and 8,228 actions before the
source pole-angle limit. This is a meaningful controller, but it did **not**
meet the particular pre-freeze reliability gate. P03's seeds 0–2 are separate
diagnostic evidence, not replacement qualification attempts. No P06 freeze,
weight export, numerical/RTL work or retraining followed.

The current branch/worktree preserves the tested harness and all ten records.
The failed summary actively blocks the rights-safe local exporter. Historical
paper seeds, cross-episode evaluation reset, exact dependencies and table
checkpoint remain unknown; this result does not disprove the paper's claims
or identify a training cause. It measures one explicit source-aligned
deployment protocol and its fixed ten-seed sample.

## Exact decision needed

The user must choose whether to retain ADR-0009's 8/10-at-10,001 control
requirement and pursue a more reliable controller, change the **acceptance
claim** for the unchanged released controller, or approve a distinct
evaluation/reset variant. No option has been authorized by this packet.

| Option | What must happen before any freeze | Baseline schedule/risk | Later Clef and FPGA/ASIC effect |
|---|---|---|---|
| **A — Keep the 10,001-action, 8/10 bar.** Authorize a new original-graph CartPole training/reselection effort, retaining released model2 as a control. | Pre-register training/evaluation and a new held-out seed set; prove a candidate passes the unchanged threshold; make a new checkpoint/provenance/rights decision. No automatic retraining is authorized here. | Highest schedule and learnability risk; maintains the strongest agreed control-quality claim. Existing model1/model3 three-seed baseline durations were all below 10,001, so a blind swap is not evidence-backed. | The 32×32×6, 1,916-parameter FPGA/ASIC structure may remain, but any newly trained weights require new exact vectors and numerical profiling. It remains a fixed NCA, not Clef closure. |
| **B — Recommend a narrower, honest model2 FPGA demonstration.** Keep the exact released model2, source plant and 10,001-action horizon, but qualify **at least 8/10 episodes reaching 5,000 actions** on *new* pre-registered seeds 20–29; report full 10,001-action outcomes and the failed 6/10 result prominently. | A superseding ADR must first approve this changed quality criterion. Then run the new seeds and pinned goldens; do **not** count the post-hoc 8/10-at-5,000 result from seeds 10–19 as validation. Freeze only if that independent test passes; no weight export beyond local-only rights. | Shorter path toward a faithful one-semester FPGA control demo, but weaker longevity guarantee. Five thousand actions are 100 simulated seconds, not a measured wall-clock deadline. A new independent sample can still fail. | Same graph, checkpoint, host interface and portable core; only the asserted competence threshold changes. It does not establish sparse body-wide scaling or any Clef causal-closure claim. |
| **C — Test a separately labeled source-harness/reset variant before choosing a new primary protocol.** Investigate the notebook's 1% in-episode grid reinitialization and/or cross-episode pool persistence. | Approve a distinct, pre-registered protocol, seeds and acceptance gate; measure control and exact operator differences; only then decide whether a new deployment protocol merits a superseding ADR. The two-seed post-hoc P03 reinit arm is insufficient. | Medium diagnostic and integration cost, uncertain benefit. It changes the accepted fresh-grid/no-in-episode-reset behavior and may still miss 8/10. | Could add reset/RNG control to FPGA/ASIC scheduling; must not be passed off as the unchanged model2 deployment. Still no Clef closure evidence. |

### Recommendation

Choose **B** if the priority remains a one-semester FPGA implementation of
the *actual released paper controller*, with its reliability reported
honestly. This preserves the original algorithm and checkpoint while
requiring an independent prospective test before freeze. It does **not**
retroactively pass ADR-0009, claim paper-table longevity or waive weight
rights. If full-episode 8/10 reliability is non-negotiable, choose A despite
its greater training/schedule risk. C is a diagnostic path, not a reason to
silently re-label this failed run.

## Guardrails until a decision

ADR-0009 remains the currently accepted G3E protocol and its threshold has
**failed**. Proposed ADR-0010 is unaccepted; P06 is stopped at this return
gate. Keep the qualification JSONL/summary, ignored clone/progress policy,
E01 and P03 regressions, local-only weight restriction and oracle firewall.
Do not launch seeds 20–29, retrain, change reset semantics, create a freeze
manifest/export, start P07/RTL, or claim hardware competence without the
user's explicit new decision.
