# Row16 saved-case diagnosis and fidelity32 hardware cost

Date: 2026-10-28. Scope: answer the user's diagnostic/cost questions at the existing G4 return. No accepted arithmetic, gate decision, original source, qualification protocol or RTL was changed. This is bounded replay and same-input intervention on already recorded seed 41, not a resumed qualification campaign or new training.

## Why the short tests did not expose the failure

The numerical change was already visible inside the short test. For seed 41, the first changed action is 101; the short screen ends at 256, and the candidate does not fall until 1150. “Survives 256 actions” was a censored outcome, not a claim of identical control. The larger test exposed a consequence of earlier differences, rather than an error suddenly starting after the short-test cap.

All 12 short/long prefix comparisons (four seeds × three arms) have identical action histories through their respective short caps. There is no observed short/long prefix policy change caused by a different setup; the long test continues the same behavior past the earlier stopping point.

The diagnostic replays the recorded plant action sequences and checks their endpoints and rewards exactly. It reconstructs the float decision at 101 and matches the saved entire grid bit-for-bit, then replays candidate decisions 102–1150 from its saved post-101 grid and checks every action and the complete terminal grid exactly. Counts, seeds, masks and plant semantics are unchanged. Scripts: `experiments/row16_validation/diagnose.py` and `probe_inputs.py`; safe results in their JSON summaries; learned grids remain ignored/local.

## First divergent decision: a margin smaller than one coarse step

At action 101, 54 NCA epochs were executed with identical observations and masks before the first changed plant action:

| Controller | Left score | Right score | Choice |
|---|---:|---:|---|
| Float | 0.2128219604 | 0.2119068354 | Left |
| Persistent row16 | 0.2128906250 | 0.2138671875 | Right |

Float's margin is 0.0009151250; a row16 state/readout step is 0.0009765625. This is not merely rounding the final float scores: the internal recurrence and input conversion also change, giving different computed scores. The second score error is approximately +0.00196035, enough to reverse the ranking. No saturation occurs.

The first-divergence grid has maximum error 0.02011016 and RMSE 0.00196650. Identifier channels 2/3 have zero error, consistent with correct postwrites. This supports a precision/dynamics issue rather than a missing input clamp/marker implementation. It does not establish that errors grow monotonically or that the grid becomes unbounded.

## Same-input numerical interventions

Each following probe starts from the **same float pre-action-101 grid**, independently represented in the named format, and executes the same 54 masks/observations. It is a one-decision intervention, not a trained alternative or a long-run qualification.

| Probe | Choice | Interpretation for this decision |
|---|---|---|
| fidelity32 | Left | Tracks float ranking |
| Fresh row16, discarding all earlier fixed-point history | Right | Earlier fixed-grid history is not necessary for this first flip |
| Fine state/activations, coarse 16/F12 weights | Left | Coarse weights alone do not flip this probe |
| Coarse 16/F10 state/activations, fine weights | Left, by a tie | Coarse state still substantially weakens the margin; interactions matter |
| fidelity32 arithmetic/state/weights, but all four inputs quantized to row16 resolution | Right | Coarse input representation alone is sufficient to flip this decision |

Four individual-input probes each retain Left; coarsening all four together produces Right. No single sensor is uniquely identified as the sole culprit. Input precision, hidden/activation precision and coefficient precision interact through a nonlinear recurrent rule. These measurements do not justify claiming that fine weights or one selected sensor solve the entire episode.

Approximate physical observation increments imposed by 16/F10 and the original source scales:

| Observation | Approximate increment |
|---|---:|
| Cart position | 0.0004883 m |
| Cart velocity | 0.0039063 m/s |
| Pole angle | 0.0002441 rad = 0.0140 degrees |
| Pole angular velocity | 0.0065104 rad/s = 0.3730 degrees/s |

Near upright balance, relevant velocities and score margins can be small. Finite range without overflow does not imply enough resolution to distinguish them. fidelity32 state resolution is 16384 times finer; its coefficient resolution is 1024 times finer than this particular row16 proposal.

## What happens near failure

The saved 16-bit action history differs from float on 227 of 1150 decisions. After the first difference, observations and persistent hidden states differ too; later action mismatches are not same-input accuracy labels.

At the end, row16 applies Left for **12 consecutive actions, 1139–1150**. The last 12 decisions are not ties: their integer score gaps range from 6 to 182 LSBs. The candidate therefore does not fail simply because a final tie selects Left. The low-precision trajectory has reached a state where it sustains the same force while the pole accelerates away from upright.

| Completed action | Float pole angle (degrees) | row16 pole angle (degrees) |
|---|---:|---:|
| 256 | -0.0428 | -0.7763 |
| 1000 | -0.0983 | -0.9998 |
| 1100 | 0.0731 | 1.3757 |
| 1140 | 1.0598 | -0.9343 |
| 1149 | 0.4434 | 10.2339 |
| 1150 | 0.1378 | **13.2443** |

The source angle limit is 12 degrees. At the candidate's failure, float/fidelity32 remain near upright; their saved action and plant histories are identical through 1488. Across saved candidate decisions 102–1150, nine readout ties occur, none in the final 12. No candidate layer, residual, marker or observation saturation was recorded. Output hidden-channel increments are present and correctly counteracted by learned updates; an accumulating marker hitting its numerical limit is not the measured explanation.

The evidence supports: coarse numerical representation can change a near-tied decision even in a short run; the feedback loop then follows another plant/hidden-state history; a later controller/plant condition produces a sustained inappropriate force and terminal excursion. It does not prove the very first changed action is the sole cause of failure 1049 moves later, a particular hidden-state attractor exists, or every 16-bit scheme fails. Late same-state probes in the diagnostic summary further distinguish immediate arithmetic effects from the changed history; their scope is one decision, not a recovery guarantee.

At actions 1139, 1143, 1145 and 1150, starting from the **candidate's** pre-action grid and observation but performing the next complete decision with float or fidelity32 still selects Left in all four cases. Thus changing precision just for the last decision does not automatically repair the changed history. This rules out explaining those sampled late choices solely by their final coarse rounding/tie. It does not by itself distinguish a changed hidden-state history from the candidate's different physical observations; that distinction is tested separately by `probe_history.py`.

The history swaps now give stronger local evidence. Every branch uses the original float arithmetic and identical masks:

| Decision | Starting grid history | Current observation | Choice |
|---|---|---|---|
| 1143 | Float controller | Candidate plant | Right |
| 1143 | Candidate controller | Candidate plant | Left |
| 1145 | Float controller | Candidate plant | Right |
| 1145 | Candidate controller | Float plant | Right |
| 1145 | Candidate controller | Candidate plant | Left |

At 1143, changing only the initial controller grid changes the response to the same candidate measurement. At 1145, changing either the grid history or the observation changes the decision; their interaction matters. The persistent grid is therefore causally relevant to these sampled late decisions. Its history includes earlier inputs as well as hidden recurrent channels. A crossed grid/plant history is a diagnostic intervention, not a demonstrated safe recovery procedure or proof of a specific hidden attractor. The reconstructed unmodified float history matches every saved action from 102 through 1150.

There is also an exact physical timing point: before action 1150 the pole is at 10.233911 degrees with angular velocity 2.627043603 rad/s. The source uses explicit Euler, so the next angle is `theta + 0.02 * theta_dot`, independent of that action's newly computed acceleration. Both Left and Right produce 13.244281 degrees and terminate from this state. Thus failure is already unavoidable **at the final decision**; the missed corrective opportunities occur earlier. This was checked by directly stepping both actions from the identical recorded pre-1150 plant state, not by changing the environment.

## What “32-bit” actually costs here

This comparison is **fixed point**: state/activation 16/F10 → 32/F24; weight 16/F12 → 24/F22; bias/accumulator 48/F22 → 62/F46. It is not a switch to floating-point hardware. No graph size, number of cells or MAC count changes.

Exact logical counts for the intended pipeline, excluding physical packing/replication:

| Item | row16 | fidelity32 | Change |
|---|---:|---:|---:|
| One persistent grid | 12 KiB | 24 KiB | +100% |
| Three old-row buffers | 1.125 KiB | 2.25 KiB | +100% |
| Producer/consumer storage at the two activation boundaries | 6.25 KiB | 12.5 KiB | +100% |
| 1860 weights plus 56 biases | 4056 bytes | 6014 bytes | +48.3% |
| **Sum of listed storage** | **23896 bytes (23.34 KiB)** | **45694 bytes (44.62 KiB)** | **+91.2%, about 21.29 KiB extra** |
| Numerical accumulator width | 48 bits | 62 bits | +29.2% |
| Multiplication | 16×16 | 32×24 | Larger decomposition/mapping burden |

This subtotal excludes delta buffers, per-lane sums, metadata, mask/RNG/UART storage, ROM/activation replication for ports and vendor wrappers. Ordinary pipeline registers are included in the activation-boundary count; no redundant FIFO pair is assumed. The current test prototype's replicated convolution patch capture is not the intended final shared-window memory architecture and is not silently included as a production requirement.

For four 256-word state banks, simple width packing into 256×40 M10Ks suggests 12 blocks at 16-bit state and 20 at 32-bit state. That is +66.7% for this **state memory only**, not a Quartus result or whole-design RAM estimate. Supported modes are in the [official M10K tables](https://docs.altera.com/r/docs/683375/current/cyclone-v-device-handbook-volume-1-device-interfaces-and-integration/m10k-blocks-mixed-width-configurations).

## DSPs are the main uncertainty

Cyclone V supports two independent small multipliers or one 27×27 multiplier per variable-precision DSP block. Its 64-bit accumulation feature is unavailable in the dual independent multiplier mode, so two small multipliers do not imply two complete independent 48-bit MACs for free. See the official [multiplier modes](https://docs.altera.com/r/docs/683375/current/cyclone-v-device-handbook-volume-1-device-interfaces-and-integration/multipliers) and [accumulator restrictions](https://docs.altera.com/r/docs/683375/current/cyclone-v-device-handbook-volume-1-device-interfaces-and-integration/accumulator-and-chainout-adder).

A useful planning scenario, **not measured synthesis**, is one DSP-native MAC per narrow lane versus two multiplier DSP blocks plus combination/accumulation logic per 32×24 lane. At 64 physical lanes that is approximately 64 versus 128 DSP blocks. SE A5 provides 87 blocks ([device resource table](https://docs.altera.com/r/docs/683375/current/cyclone-v-device-handbook-volume-1-device-interfaces-and-integration/resources)). Packing small multiplies and doing accumulation in ALMs can reduce the narrow multiplier-only count toward 32 blocks; wide partial products can also trade DSPs for ALMs or cycles. Thus wide arithmetic can mean roughly 2–4 times the **multiplier-block pressure** compared with different narrow mappings; that is not a measured ratio for total accelerator area or power.

The likely engineering trade is fewer simultaneous wide MACs, extra soft logic, or more cycles per multiply. Actual DSP/ALM/register use, memory-port replication and Fmax require Quartus. Wider registers are not evidence that the design cannot fit, but keeping all 64 wide lanes is not established either.

## Latency is conditional, not automatically doubled

The existing row-stage simulations measure the same 1080/800/720 enabled-cycle lengths at both precisions. If lane count, one-MAC-per-cycle issue rate and clock are retained, width alone does not add cycles. It may prevent retaining those assumptions physically.

One conservative example is halving lanes to 16/12/4 at the same clock, preserving the 32-cell row barrier through time sharing:

| Assumed lanes | Stage cycles | Ideal epoch cycles | 55 epochs at 50 MHz | At 100 MHz |
|---|---|---:|---:|---:|
| 32/24/8 | 1080/800/720 | 36080 | 39.688 ms | 19.844 ms |
| 16/12/4 | 2160/1600/1440 | 72160 | 79.376 ms | 39.688 ms |

These are schedule calculations before memory/refill/writeback/transport overhead and without timing closure, not board throughput. The latter configuration was not newly selected or synthesized. Other allocations can give intermediate results. A slower implementation retains the same simulated control dynamics because the host waits for the action; no hard 20 ms wall-clock requirement is accepted.

## Interpretation

The reliable quantitative budget is roughly twice state/intermediate storage and +48% parameter storage. Arithmetic is the larger physical risk and can force less parallelism. There is no justified exact total-area, power or slowdown percentage yet. Fidelity32 has much stronger measured fidelity on this case, but no full-horizon population guarantee. A later mixed-precision experiment could ask whether wide state/input resolution and narrower coefficients preserve quality; the one-decision probes are not enough to accept it. No such numerical replacement is selected by this diagnosis.

Reproduce logical estimates with `experiments/row16_validation/estimate_hardware.py`; its JSON identifies assumptions and primary sources. The existing G4 decision remains open.

## Checks completed for this diagnostic request

- Exact float full-grid replay at action 101; identical observation/masks to the saved first-divergence fixture.
- Exact candidate actions 102–1150 and complete terminal grid; plant endpoint and reward replay for all three saved arms.
- Five one-decision arithmetic/input ablations; six none/single/all sensor probes; four late same-state comparisons; four history-swap sets, with every reconstructed float action checked through 1150.
- Direct two-action terminal-state counterfactual confirms the explicit-Euler one-step result.
- Diagnostic source and input-snapshot hashes validate; compileall, repository smoke/oracle firewall and unchanged accepted manifest loaders pass. No production/reference/RTL changes require rerunning the prior 105-test suite, and it is not claimed rerun here.
- Logical counts and conditional schedules regenerated separately; physical DSP/RAM facts checked in primary Altera documentation. No Quartus synthesis, FPGA measurement, numerical acceptance or resumed qualification is claimed.
