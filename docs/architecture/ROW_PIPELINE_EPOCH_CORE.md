# Shared-row epoch pipeline — 2026-10-30

Readability cleanup: the five active modules remain in `rtl/core/`, with an
explicit `files.f` source list. Comments were removed and abbreviated internal
signals were renamed; public interfaces, arithmetic and scheduling are unchanged.
The old folded engine and standalone primitives are historical test fixtures in
`tb/legacy_rtl/`. See `docs/verification/RTL_CLEANUP_RENAME_MAP.json` for old/new
names and `docs/verification/RTL_CLEANUP_2026_10_30.md` for current source checks.

ADR-0017 authorizes the transcript recommendations independently of row16's
unaccepted numerical replacement. The default core arithmetic is fidelity32.
The earlier audit describes the files before this implementation; it remains a
dated record, not the current completeness claim.

## RTL ownership and connections

```
                               cfg_layer / coefficient load
                                           |
four-bank persistent grid --> three old rows --> convolution (32 MAC lanes)
        ^                    nca_row_window       nca_row_stage, STREAM_INPUT
        |                                            | row/tag/mask
        |                                       Dense 1 (24 lanes)
        |                                            | row/tag/mask
        |                                       Dense 2 (8 lanes)
        |                                            |
        +-- source postwrites <-- owned delta row <--+
             and residual       + old-row reread
```

`rtl/core/nca_epoch_core.sv` connects the existing banked memory, new
`nca_row_window.sv`, and three instances of `nca_row_stage.sv`. The convolution
generate branch contains no captured 32×54 input patch array. It consumes shared
row-window scalar selections throughout its computation. Dense stages retain
ordinary captured input rows; completed producer output rows remain owned until
the corresponding handshake. There are no additional transfer FIFO pairs.

The common term order is kernel row, kernel column, then channel. Boundary
neighbors are constant zero. The frontend initially reads rows 0/1, then fetches
only one new row as the window advances, for 256 four-cell reads per epoch.
Tags/valid bits distinguish three physical row slots from logical row numbers.

The lane mapping remains `destination=lane*ceil(32*outputs/lanes)+slot`.
Convolution broadcasts one kernel/bias address across 32 columns. Dense 1 has
three groups with output indices `(slot+10*group)%30`, shared by eight lanes
each. Dense 2 broadcasts one address across its eight lanes. The arithmetic
work lengths remain 1080/800/720 enabled clocks; frontend/capture/drain and
arbitration overhead mean those figures are not epoch timing or achieved Fmax.

## Generation safety

After convolution row r+1 completes, old row r is released for overwrite. Row 31
is released after its own convolution completes. A completed Dense 2 row waits
for this release, rereads its old central row from the single grid, computes
masked residuals and source postwrites, then writes eight beats. The shared row
snapshot retains any old values still needed by active convolution. Assertions
reject un-released writes, old-generation reads of committed rows, and mismatched
epoch tags. All 32 rows must commit and all stages drain before the next epoch.

Writeback has bounded read priority. Already-issued RAM responses are captured
even while `step_enable=0`; new requests, computation and handshakes pause.
The backing memory's write-priority collision retry is retained, but it is not
the generation-safety mechanism. The release scheduler is that mechanism.

Current completed replay results are in
`docs/verification/ROW_PIPELINE_EPOCH_RTL_2026_10_30.md`: all six configurations
pass, totaling 18 epochs. Source/tool/generated-input identities are bound in
the ignored local `artifacts/row_pipeline/evidence.json`.

## Host seam and numerical behavior

Load all 256 grid beats after reset and all 1,916 coefficients/biases, committing
each layer's configuration. Only then does `start_ready` assert. Initialize or
read back with one host operation per beat while `host_ready`; do not assert
host read and write together. Readback is a synchronous response with no
backpressure; the host must capture it. Accepted start captures all mask/observation
bits. `done` is a one-clock pulse after full commit, not a ready/valid response.
`busy` stays high throughout a partial generation. `row_commit` is debug telemetry.

The eight observation words must already follow the source float32 scale,
duplication and declared integer quantization boundary. There is no observation
preload into the grid. Delta/residual/postwrite order matches the existing golden.
Input sites become `[obs,1,1,0,1,1]`; output channels 4/5 add one even under zero
masks. Guarded residual and marker saturations have separate counters. Mask skip
suppresses only learned work; neighbors still consume all old cell values.

`issued_macs` counts executed scalar products, not cycles, energy, or physical
DSP operations. With skipping off it is 1,904,640 per epoch; with skipping on it
is `1860*active_cells`. Arithmetic saturation counters cover executed work only:
skipping an inactive cell can remove irrelevant intermediate saturations without
changing the final grid. Frontend/writeback read and write counts exclude idle
host traffic. Counters reset at each accepted start. Reset invalidates all work
and requires configuration/grid reloading; no implicit source grid is invented.

The 16-bit epoch tag is modulo 65,536 and protects the sole in-flight generation;
it is not a lifetime-unique trace ID. Per-epoch 32-bit counters are adequate for
the tested bounded transactions. Lifetime/overflow accounting for indefinitely
paused service belongs to the later complete controller and remains a G5/P11
integration obligation.

## Verification and remaining gates

`tb/row_pipeline/run.py` compares every stage output and final grid against the
unchanged P07 integer golden under mixed/zero/full masks, changing observations,
persistent epochs, signed extrema and deterministic global stalls. It also
checks all row commits, transfer/MAC/postwrite counters, real stage overlap and
reset invalidation. `--restricted` repeats locally with hash-checked model2.
Exact observed outcomes are recorded in the ledger and verification report.

This is an epoch engine. It is not a complete P11 deployment controller, G5
physical acceptance, an autonomous source RNG, or a board demonstration. No
measured fit/Fmax/power or improved CartPole performance is claimed. See the G5
packet for the stop and next evidence obligations.
