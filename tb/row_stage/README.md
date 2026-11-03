# Row-stage and state-storage prototype verification

These are reversible P09/P10 comparison components under ADR-0015, not a complete controller, accepted numerical replacement, integrated in-place scheduler, or measured FPGA fit.

Run with Python 3.12 / NumPy 2.3.5 and Icarus/vvp on PATH:

```
python tb/row_stage/run.py
python tb/row_stage/memory.py
python tb/row_stage/audit_transcripts.py
```

The arithmetic bench runs 16/F10 state, 16/F12 weights, 48/F22 accumulators and the existing fidelity32 widths through eight configurations, 24 random full rows. Independent scalar Python-integer dot products establish expected outputs and accumulator/output saturation counts. It checks all output words, signed arithmetic, whole-row tags, 1080/800/720-cycle schedules, a seven-lane non-divisible tail, request input capture, seven cycles of response backpressure, incomplete configuration refusal and reset abort.

The memory bench covers every one of 6144 scalar locations at both state widths, concurrent distinct-address reads/writes, blocked same-address reads and subsequent retry, full post-write readback, response tags and reset invalidation without resetting RAM contents. A higher-level controller must enforce generation ownership and prevent external access to partially committed epochs; these tests do not prove those missing mechanisms.

Results, compiler commands, source hashes, safe synthetic fixtures and logs are under ignored `artifacts/row_stage/`. Existing P08/P09 tests remain separate regression comparators. The new stage captures a complete input row and holds its completed output under valid/ready. Its explicit 54-value-per-cell convolution test interface is a functional prototype, not the final shared-line-buffer/window implementation or a claim that such patch registers fit the board.

The stage has no update mask or I/O rewrite: those belong after the complete local delta in the recurrent controller. All stage arithmetic is evaluated, so these results establish no masked-work/power savings. Kernels/biases are loaded into prototype arrays; target ROM port mapping and technology-specific memory/DSP bindings remain unmeasured.

The 2026-10-30 transcript audit adds `audit_transcripts.py`: distinct public synthetic coefficients check the common convolution sequence across 32 lanes; continuous requests and an always-ready consumer measure accepted-request spacing. Current results are 1080 active arithmetic cycles and 1081 clock intervals per row at both widths. This is a component measurement and does not implement the missing shared-row/window frontend or prove physical ROM broadcasting. See `docs/verification/TRANSCRIPT_RTL_CONFORMANCE_AUDIT_2026_10_30.md` for the complete comparison and generation-safety limits of the write-priority memory component.
