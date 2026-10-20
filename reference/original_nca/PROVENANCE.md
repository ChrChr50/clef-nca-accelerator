# Provenance and reproducibility boundary

The authoritative executable source is the local clone at
`self-organized-control/`, pinned to commit
`8c85be11b0838ea14ac51a11dac3098db43afed2` from 2022-01-13. The source URL is
`https://github.com/aVariengien/self-organized-control`. The paper supplied by
the user has SHA-256
`85d101822d2dd81fd7a2152e88f74ddce4f93ebad8159f7ffaeaf053f5375c37`.

`provenance.json` pins the source files, notebook, checkpoint archive, and three
browser-demo checkpoints. `checkpoint_hashes.json` additionally pins every
TensorFlow checkpoint member in the archive.

## Licensing gap

The repository has no `LICENSE`, `LICENCE`, `COPYING`, or `NOTICE` file. Its
`code/setup.py` contains `license='MIT'`, but a classifier string is not the
license text and the repository carries no copyright notice. Consequently this
project does not vendor or modify the upstream sources or checkpoint bytes.
The clean-room implementation is original project code; it reads checkpoints
from the user's local clone during verification. Institutional or legal review
is required before redistributing upstream artifacts.

## Environment and seed gaps

The notebook metadata identifies Python 3.8.1, and tracked bytecode filenames
identify CPython 3.8. The exported browser models identify Keras 2.2.4-tf and
TensorFlow.js Converter 3.7.0. The notebook installs TensorFlow transitively and
installs unversioned `gym`; it records no resolved TensorFlow, Gym, NumPy, CUDA,
cuDNN, or driver versions. No historical training or evaluation seeds are
present. Those values are recorded as unavailable rather than inferred.

The clean-room inference environment is separately locked and uses explicit
mask/noise/damage traces so RNG algorithms do not leak into the operator
contract.
