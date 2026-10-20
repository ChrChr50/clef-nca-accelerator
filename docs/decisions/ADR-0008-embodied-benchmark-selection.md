# ADR-0008: CartPole baseline and post-FPGA extension benchmarks

- Status: Accepted for benchmark and sequencing
- Proposed: 2026-10-06
- Accepted: 2026-10-07
- Decider: User
- Stage/gate: E00/G2E benchmark choice complete; G3E readiness/protocol remains open
- Evidence: E00 comparison packet; user comparison/selection exchanges; P03 reference/reports
- Supersedes: ADR-0007's initial distributed-plant-first scope where inconsistent; original-reference and Clef distinctions retained

## Context and proposal history

The original packet compared modular soft-robot locomotion, EvoGym Balancer-v0 and event-camera following, recommending EvoGym but leaving selection unaccepted. The user subsequently requested comparison with the custom surface and CartPole, then selected CartPole rather than that recommendation. The source packet remains historical; recommendations are not user decisions.

## Accepted decision

Make the same CartPole task as the original reference paper/executable the primary benchmark for the one-semester FPGA baseline. Keep the original shared neural rule and source-aligned plant as normative references, with existing paper/source discrepancies explicitly preserved.

Make the custom balancing surface and EvoGym Balancer-v0 post-FPGA test extensions. Their local sensing/actuation, model learning, physics and event variants are implemented later under separate manifests/acceptance. They do not gate the first CartPole hardware demonstration. No order between the two extensions or exact plant/body/model is selected here.

E00 benchmark selection is complete. Resume E01 to consolidate existing CartPole deployment/environment/replay contracts, then E02 to assess existing checkpoint readiness and prepare G3E. Do not repeat P03 from scratch, restart old Hanoi P05, or freeze a checkpoint from benchmark choice alone. Retraining is not presumed necessary; justify it and obtain authorization if required.

## Consequences

The first FPGA endpoint may be a verified folded implementation of the reference controller. Preserve event-capable scheduling/local-state/transducer accommodations and measured exact-preserving work avoidance where justified. A behavior-changing event-gated NCA is a distinct variant, not “the same paper controller” by assertion. G3E must explicitly bound any event-variant commitment; CartPole alone does not establish body-wide event locality/scaling.

This is an explicit sequencing change to the earlier distributed/event benchmark-first floor, not a claim that the new CartPole endpoint satisfies all long-term robotic hypotheses. The future spatial/event objective and actual Clef ambition remain.

One semester, FPGA with host-simulated physics, no physical robot required. Exact calendar remains unspecified. ASIC fabrication and full Clef are separately authorized extensions. X01/X02 begin after the verified baseline FPGA design/loop, without waiting for ASIC fabrication.

## Remaining gates and provenance

G3E decides checkpoint identity, episode-grid reset discrepancy, released versus diagnostic horizon, control thresholds, allowed reference-preserving work skipping and any separately proposed behavior variant. P06 requires that acceptance; G4/G5 decide numerical and hardware contracts.

Upstream checkpoint redistribution remains subject to the existing rights/provenance review. Local ignored-clone verification does not authorize committing or distributing weight tensors. No task-solving host policy or teacher/oracle leakage is accepted.

## Validation

Selection changes planning/routing only. Tests actually run and limitations are in the dated implementation status entry. No new environment, training, model freeze, FPGA design, synthesis or closure result follows from this ADR.
