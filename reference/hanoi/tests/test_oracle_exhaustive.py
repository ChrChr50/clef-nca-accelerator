from __future__ import annotations

import unittest

from reference.hanoi.environment import ACTIONS, HanoiState, encode_observation, decode_observation, iter_states, transition
from reference.hanoi.oracle import encode_locations, optimal_actions, recursive_distance, reverse_graph_distances


def independent_transition(state: HanoiState, action: int) -> tuple[tuple[int, ...], bool]:
    source, destination = ACTIONS[action]
    source_stack = [disk for disk in range(state.disk_count - 1, -1, -1) if state.locations[disk] == source]
    destination_stack = [disk for disk in range(state.disk_count - 1, -1, -1) if state.locations[disk] == destination]
    if not source_stack:
        return state.locations, False
    moving = source_stack[-1]
    if destination_stack and destination_stack[-1] < moving:
        return state.locations, False
    updated = list(state.locations)
    updated[moving] = destination
    return tuple(updated), True


class ExhaustiveOracleTests(unittest.TestCase):
    def test_every_bounded_state_goal_and_action(self) -> None:
        checked_states = 0
        checked_actions = 0
        ambiguous_states = 0
        legal_actions = 0
        illegal_actions = 0
        for disk_count in range(1, 9):
            for goal in range(3):
                distances = reverse_graph_distances(disk_count, goal)
                self.assertEqual(3**disk_count, len(distances))
                self.assertEqual((1 << disk_count) - 1, max(distances))
                for state in iter_states(disk_count, goal):
                    checked_states += 1
                    code = encode_locations(state.locations)
                    distance = distances[code]
                    self.assertEqual(distance, recursive_distance(state.locations, goal))
                    self.assertEqual(state, decode_observation(encode_observation(state)))
                    selected = optimal_actions(state)
                    if len(selected) > 1:
                        ambiguous_states += 1
                    if state.terminal:
                        self.assertEqual(0, distance)
                        self.assertEqual((), selected)
                    else:
                        self.assertGreater(distance, 0)
                        self.assertGreaterEqual(len(selected), 1)
                    reducing: list[int] = []
                    for action in range(6):
                        checked_actions += 1
                        expected_locations, expected_legal = independent_transition(state, action)
                        successor, legal, _ = transition(state, action)
                        self.assertEqual(expected_legal, legal)
                        self.assertEqual(expected_locations, successor.locations)
                        if not legal:
                            illegal_actions += 1
                            self.assertIs(successor, state)
                            continue
                        legal_actions += 1
                        successor_distance = distances[encode_locations(successor.locations)]
                        self.assertLessEqual(abs(successor_distance - distance), 1)
                        reverse_action = ACTIONS.index((ACTIONS[action][1], ACTIONS[action][0]))
                        predecessor, reverse_legal, _ = transition(successor, reverse_action)
                        self.assertTrue(reverse_legal)
                        self.assertEqual(state, predecessor)
                        if successor_distance == distance - 1:
                            reducing.append(action)
                    self.assertEqual(tuple(reducing), selected)

                for source in range(3):
                    if source == goal:
                        continue
                    standard_code = encode_locations((source,) * disk_count)
                    self.assertEqual((1 << disk_count) - 1, distances[standard_code])

        self.assertEqual(3 * sum(3**n for n in range(1, 9)), checked_states)
        self.assertEqual(6 * checked_states, checked_actions)
        self.assertEqual(checked_actions, legal_actions + illegal_actions)
        # Exhaustive enumeration is itself the ambiguity check. For a fixed
        # three-peg goal tower, this bounded graph has a unique reducing action
        # at every nonterminal state; the API nevertheless returns a tuple so a
        # future contract that introduces ties cannot silently collapse them.
        self.assertEqual(0, ambiguous_states)
        print(
            "exhaustive Hanoi metrics: "
            f"states={checked_states}, actions={checked_actions}, legal={legal_actions}, "
            f"illegal={illegal_actions}, ambiguous_optimal_sets={ambiguous_states}"
        )


if __name__ == "__main__":
    unittest.main()
