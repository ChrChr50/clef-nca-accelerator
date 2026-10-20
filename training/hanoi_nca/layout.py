"""Load and analyze the configurable Hanoi I/O layout."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path


LAYOUT_PATH = Path(__file__).with_name("layout_v1.json")


@dataclass(frozen=True)
class Layout:
    input_coordinates: tuple[tuple[int, int], ...]
    input_names: tuple[str, ...]
    output_coordinates: tuple[tuple[int, int], ...]
    action_names: tuple[str, ...]

    def validate(self) -> None:
        if len(self.input_coordinates) != 36 or len(self.output_coordinates) != 6:
            raise ValueError("layout must contain 36 inputs and six outputs")
        all_coordinates = self.input_coordinates + self.output_coordinates
        if len(set(all_coordinates)) != 42:
            raise ValueError("input/output coordinates collide")
        if any(not (0 <= row < 32 and 0 <= column < 32) for row, column in all_coordinates):
            raise ValueError("layout coordinate is outside the 32x32 grid")


def load_layout(path: Path = LAYOUT_PATH) -> Layout:
    raw = json.loads(path.read_text(encoding="utf-8"))
    inputs = sorted(raw["input_cells"], key=lambda item: item["index"])
    outputs = sorted(raw["output_cells"], key=lambda item: item["index"])
    layout = Layout(
        input_coordinates=tuple(tuple(item["coordinate"]) for item in inputs),
        input_names=tuple(item["name"] for item in inputs),
        output_coordinates=tuple(tuple(item["coordinate"]) for item in outputs),
        action_names=tuple(item["action"] for item in outputs),
    )
    layout.validate()
    return layout


def layout_statistics(layout: Layout) -> dict[str, object]:
    distances = [
        math.dist(input_coordinate, output_coordinate)
        for input_coordinate in layout.input_coordinates
        for output_coordinate in layout.output_coordinates
    ]
    chebyshev = [
        max(abs(a[0] - b[0]), abs(a[1] - b[1]))
        for a in layout.input_coordinates
        for b in layout.output_coordinates
    ]
    input_centroid = tuple(
        sum(coordinate[axis] for coordinate in layout.input_coordinates) / 36 for axis in range(2)
    )
    output_centroid = tuple(
        sum(coordinate[axis] for coordinate in layout.output_coordinates) / 6 for axis in range(2)
    )
    per_output_mean = []
    for output in layout.output_coordinates:
        per_output_mean.append(
            sum(math.dist(input_coordinate, output) for input_coordinate in layout.input_coordinates) / 36
        )
    return {
        "collision_count": 42 - len(set(layout.input_coordinates + layout.output_coordinates)),
        "input_centroid": list(input_centroid),
        "output_centroid": list(output_centroid),
        "centroid_offset": math.dist(input_centroid, output_centroid),
        "euclidean_input_output": {
            "minimum": min(distances),
            "mean": sum(distances) / len(distances),
            "maximum": max(distances),
        },
        "chebyshev_input_output": {
            "minimum": min(chebyshev),
            "mean": sum(chebyshev) / len(chebyshev),
            "maximum": max(chebyshev),
        },
        "per_output_mean_euclidean": per_output_mean,
        "per_output_mean_spread": max(per_output_mean) - min(per_output_mean),
    }
