# Deterministic Hanoi reference environment

> Historical-scope notice (2026-10-06): retained for provenance, not the active forward implementation plan. ADR-0007 and docs/architecture/EMBODIED_NCA_VISION.md supersede task-specific choices. Original-reference evidence and dated experimental decisions remain preserved; no new embodied acceptance or model freeze is implied.

This package implements the accepted G2 Hanoi environment contract for one to
eight disks and any of the three goal pegs. `environment.py` is the deployable,
reward-free transition authority. `oracle.py` is an independent reverse-graph
shortest-path reference allowed only in training, evaluation, and tests.

The six action logits are never masked. An illegal action is an exact state
no-op, reports `legal=False`, and consumes one attempted move. Rewards, target
construction, loss functions, and curriculum choices are deferred to G3/P05.

Run the bounded exhaustive verification with:

```text
python -m unittest discover -s reference/hanoi/tests -v
python scripts/check_oracle_firewall.py
```
