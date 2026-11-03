# Current CartPole NCA epoch core

The portable core advances one 32 × 32 × 6 grid by one epoch. The caller supplies the cell update mask and scaled observations. The default format uses 32-bit state, 24-bit weights and 62-bit accumulators.

## Datapath

```mermaid
flowchart LR
    Host["Host grid load and readback"] <-->|"Four cells per beat"| Grid["Four-bank persistent grid"]
    Grid -->|"Old rows"| Window["Three tagged old-row buffers"]
    Window -->|"Zero-padded 3 × 3 neighborhood terms"| Conv["Convolution · 54 → 20<br/>32 MAC lanes · ReLU"]
    Conv -->|"Row features"| D1["Dense 1 · 20 → 30<br/>24 MAC lanes · ReLU"]
    D1 -->|"Row features"| D2["Dense 2 · 30 → 6<br/>8 MAC lanes"]
    Weights["Host-loaded kernel and bias tables"] --> Conv & D1 & D2
    D2 --> Delta["Pending delta row"]
    Grid -->|"Released old center row"| WB["Masked residual add and saturation<br/>Source clears, markers and input rewrite"]
    Delta --> WB
    Inputs["Latched mask and observations"] --> WB
    Inputs -->|"Mask carried with row through stages"| Conv
    WB -->|"Commit four cells per beat"| Grid
```

Each arithmetic stage adds bias and uses nearest-even rounding and signed saturation at its output. Ready/valid transfers carry the row, epoch tag and mask. Convolution, Dense 1 and Dense 2 can operate on different rows concurrently. Masked cells skip learned MAC work while the mandatory source rewrites still execute.

## Control

```mermaid
flowchart TB
    Idle["Idle · host loads grid and configures all three layers"]
    Idle -->|"start_valid and start_ready"| Start["Latch mask and observations<br/>Set busy and clear epoch bookkeeping"]
    Start --> Fill["Fetch rows 0 and 1<br/>Then fetch each newly needed old row"]
    Fill --> Launch["Launch convolution when window and stage are ready"]
    Launch --> Wait["Wait for matching convolution row result"]
    Wait -->|"Rows 0–29 complete · fetch row r+2"| Fill
    Wait -->|"Row 30 complete · row 31 window ready"| Launch
    Wait -->|"Row 31 complete"| FetchDone["All rows fetched"]
    Wait -->|"Row r completes · release old row r−1<br/>Final row also releases itself"| Release["Old-row release bitmap"]
    Launch -->|"Results hand off through both dense stages"| Capture["Capture Dense 2 delta row and tag"]
    Capture --> Hold["Wait for target old row release"]
    Release --> Hold
    Hold --> Read["Read eight old-center-row beats"]
    Read --> Commit["Rewrite and commit eight beats<br/>Pulse row_commit"]
    Commit -->|"Writeback slot available"| Capture
    Commit --> Barrier["32 rows committed · writeback idle · all result slots empty"]
    FetchDone --> Barrier
    Barrier -->|"Pulse done and clear busy"| Idle
```

The grid read arbiter gives writeback priority over window fill. The memory defers a read that collides with a write to the same address. The release bitmap protects old-generation data until convolution has finished reading it. The host can load or read the grid while idle. G5 physical mapping and action-level integration remain pending.

See the [RTL inventory](../../rtl/core/README.md) and [epoch-core interface and ownership notes](ROW_PIPELINE_EPOCH_CORE.md).
