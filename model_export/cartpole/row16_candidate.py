"""Unaccepted 16-bit candidate, kept outside hash-bound accepted arithmetic."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np

from model_export.cartpole.fixed_point import FixedNCA, Format
from model_export.cartpole.freeze import ROOT, load_frozen, sha256
from reference.original_nca.core import load_tfjs_weights

PROTOCOL = ROOT / "experiments/row16_validation/protocol.v1.json"
EXPECTED = Format("row16", 16, 10, 16, 12, 48)


def candidate_format() -> Format:
    value = json.loads(PROTOCOL.read_text())
    fmt = Format(**value["candidate"])
    if fmt != EXPECTED:
        raise ValueError("candidate protocol changed; requires a new version")
    return fmt


def load_candidate() -> FixedNCA:
    frozen = load_frozen()
    base = ROOT / frozen["weights"]["source"]
    blob = base / "group1-shard1of1.bin"
    if sha256(blob) != frozen["weights"]["blob_sha256"]:
        raise ValueError("frozen checkpoint hash mismatch")
    return FixedNCA(load_tfjs_weights(base / "model.json", blob), candidate_format())


def output_major_images(model: FixedNCA) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Explicit spec ROM layout W[out, flattened input], signed words."""
    kernels = [np.ascontiguousarray(k.reshape(-1, k.shape[-1]).T) for k in model.kernels]
    return kernels, [bias.copy() for bias in model.biases]


def recover_input_major(images: list[np.ndarray], shapes: list[tuple]) -> list[np.ndarray]:
    if len(images) != 3 or len(shapes) != 3:
        raise ValueError("three layers required")
    result = []
    for image, shape in zip(images, shapes, strict=True):
        expected = (shape[-1], int(np.prod(shape[:-1])))
        if np.asarray(image).shape != expected:
            raise ValueError("ROM shape differs from declared graph")
        result.append(np.ascontiguousarray(image.T.reshape(shape)))
    return result


def write_local_images(directory: Path, model: FixedNCA) -> dict:
    # Prevent accidental publication of learned tensor encodings outside ignored artifacts.
    directory = directory.resolve()
    if not directory.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("learned images must stay under ignored artifacts/")
    directory.mkdir(parents=True, exist_ok=True)
    kernels, biases = output_major_images(model)
    recovered = recover_input_major(kernels, [k.shape for k in model.kernels])
    if any(not np.array_equal(a, b) for a, b in zip(recovered, model.kernels, strict=True)):
        raise AssertionError("ROM repacking changed weights")
    files = []
    for layer, (kernel, bias) in enumerate(zip(kernels, biases, strict=True)):
        for kind, values, width in (("kernel", kernel, model.fmt.weight_bits),
                                    ("bias", bias, model.fmt.accumulator_bits)):
            path = directory / f"layer{layer}_{kind}.hex"
            path.write_text("".join(f"{int(v) & ((1 << width)-1):0{(width+3)//4}x}\n"
                                    for v in values.flat), encoding="ascii")
            files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                          "words": int(values.size), "bits": width, "kind": kind, "layer": layer})
    return {"status": "candidate-not-accepted", "format": model.fmt.manifest(),
            "layout": "output major, input minor; layer0 input=(dr,dc,ch)", "files": files}
