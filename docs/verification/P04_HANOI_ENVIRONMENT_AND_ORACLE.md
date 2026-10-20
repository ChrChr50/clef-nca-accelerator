# P04 deterministic Hanoi environment and oracle evidence

## Outcome

P04 implements and exhaustively verifies the accepted `N_MAX=8` Tower of
Hanoi environment contract. The transition environment is deterministic,
reward-free, and independent of the training/evaluation-only shortest-path
oracle. No training, Hanoi NCA adapter, model export, or RTL behavior was added.

The executable authorities are:

- `reference/hanoi/environment.py` for state, observation, transition, reset,
  terminal, move-budget, serialization, and hashing semantics;
- `reference/hanoi/environment_manifest.json` for the machine-readable contract;
- `reference/hanoi/oracle.py` for training/evaluation-only distances and complete
  optimal-action sets;
- `scripts/check_oracle_firewall.py` for the deployable/import boundary.

## Locked environment contract

- State is a tuple of peg indices in smallest-to-largest disk order. Since disk
  order is implicit, every one of the `3^n` location assignments is canonical
  and legal for `1 <= n <= 8`.
- The observation contains 36 values. Indices `4*d..4*d+3` encode disk slot
  `d` as `[peg0, peg1, peg2, present]`; indices 32--34 are the goal-peg one-hot;
  index 35 is `n/8`. Absent disk slots are exactly zero.
- Actions remain unmasked and ordered `0->1`, `0->2`, `1->0`, `1->2`, `2->0`,
  `2->1`. An illegal action is an exact no-op with `legal=false` and no moved
  disk. Every attempted action consumes one move-budget unit.
- The caller supplies a positive move budget. Its policy value remains a G3
  decision. Terminal completion takes precedence over budget truncation on the
  final action, and stepping after either condition requires reset.
- Seeded reset uses a specified SHA-256 counter mapping, not a runtime PRNG.
  Standard-source and explicit-location resets are also supported.
- State and complete episode snapshots use sorted, compact UTF-8 JSON and
  SHA-256. Strict deserialization rejects missing, unknown, or inconsistent
  fields.
- Reward, imitation target, illegal-action penalty, and action masking are not
  transition semantics and remain outside P04 for G3.

## Independent oracle

`reverse_graph_distances` performs a breadth-first traversal from the terminal
tower through reversible legal transitions. Its complete tables are generated
in memory and are not committed or exported. A structurally independent
largest-disk recurrence checks every table entry:

1. If the largest disk is already on the goal, solve the smaller configuration
   for the same goal.
2. Otherwise, solve the smaller configuration onto the auxiliary peg, move the
   largest disk, then account for the known `2^(n-1)-1` transfer.

The optimal-action API returns every action whose successor distance is exactly
one smaller. Exhaustive enumeration found zero tied optimal-action sets for a
fixed three-peg terminal tower across this bounded contract. This is a measured
graph property, not an API assumption: results remain tuples and the test
derives the full reducing set independently for every state.

The generated eight-disk distance-table hashes are:

| Goal peg | SHA-256 of distance bytes |
|---:|---|
| 0 | `b5f54bf7dee40bbdeacfac85fd410df9288b1a19886e9d257ce21d08d3c2202c` |
| 1 | `5566a50884e1560cd232c5f5e3e7befccdfd5d79345cc2671076387266ecc6f7` |
| 2 | `0447f9b5d11db1fa19e4308be0f377e6929e76d70f1642595f627a5262e83d8e` |

## Exhaustive verification

The test visits disk counts 1 through 8, all three goals, all canonical states,
and all six actions. It compares transition legality and successors to a second
stack-based implementation, checks every legal edge's inverse, verifies the BFS
distance against the recurrence, derives the complete optimal-action set,
checks that an edge changes distance by at most one, and confirms every
standard source-to-distinct-goal distance is `2^n-1`.

Observed exhaustive totals:

- 29,520 state/goal combinations;
- 177,120 action attempts;
- 88,488 legal transitions and 88,632 illegal no-ops;
- zero ambiguous optimal-action sets;
- 6,561 eight-disk assignments per goal and every smaller projection covered.

## Oracle import/build firewall

The public `reference.hanoi` package exports only environment symbols. The
firewall scans `model_export/`, `rtl/`, `boards/`, and `flows/`, plus the public
environment package boundary, for oracle imports, APIs, table artifacts, and
known distance/optimal-action identifiers. Its negative tests construct a
contaminated model-export import, an indirect package import, and an RTL
distance table and prove they are rejected. The repository smoke gate and
hosted workflow run the firewall.

## Commands and observed results

| Command | Observed result |
|---|---|
| `python -m unittest discover -s reference/hanoi/tests -v` | Pass: 11 tests; exhaustive totals above |
| `python scripts/check_oracle_firewall.py` | Pass: deployable trees and public package boundary clean |
| `python scripts/run_smoke.py` | Pass: scaffold, seven governance hashes, locked environment, and oracle firewall |
| `python -m unittest discover -s reference/original_nca/tests -v` | Pass: 17 immutable P03 tests |

On the Windows host, `python` in these command labels denotes the repository's
bundled Python runtime path. GitHub Actions uses Python 3.12 via `setup-python`.

## Deferred boundary

P04 supplies labels for later training but does not expose them to a deployed
model. G3/P05 must choose the actual move budget, observation/target scaling,
reward and illegal-action treatment, coordinates, recurrence schedule, and
training design. P05 has not begun.
