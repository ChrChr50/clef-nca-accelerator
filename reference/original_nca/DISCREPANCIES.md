# Paper, Python, notebook, and demo discrepancies

The pinned Python implementation and shipped checkpoint manifest control raw
reference behavior. This table prevents later work from silently choosing the
paper's prose when the executable differs.

| Topic | Paper | Pinned executable evidence | Locked interpretation |
|---|---|---|---|
| Parameter count | 1,854 | 1,916 = 1,100 + 630 + 186 | 1,916; all three Conv2D layers use bias |
| Perception | 20 learned 3x3x6 filters | Conv2D 3x3, 6 to 20, full channel mixing | Learned cross-correlation, not Sobel/depthwise |
| Hidden width | 30 | 20 to 30 pointwise layer | 30 |
| Boundary | 32x32 with zeros at boundaries | first Conv2D hard-codes `padding='SAME'`; torus option does not change it | Zero padding |
| Update probability | 0.5 | uniform `<= 0.5`, one BxHxWx1 mask | Shared across six channels |
| Input cell | all but output identifier fixed; information is observation | every active input cell is fully cleared after residual update, then ch1/ch2/ch4/ch5 and ch0 observation are written | Post-update hard clamp |
| Output cell | output identifier fixed; other values evolve | ch3 is cleared/reasserted, but ch4/ch5 receive +1 every NCA step | Preserve accumulating output hidden channels |
| Activation | figure shows ReLU then ReLU then linear | checkpoint JSON confirms ReLU/ReLU/linear | ReLU/ReLU/linear |
| State bounds | overflow penalty outside [-5,5] | inference has `bound_values=False` | No clipping; penalty is training-only |
| Initial state | random grid | NumPy uniform [-0.1,0.1), cast float32 | Preserve |
| Recurrent schedule | random 50 to 60 | both NumPy and TensorFlow upper bounds are exclusive | 50 through 59 |
| Hidden persistence | same grid for whole simulation | prediction commits into grid pool; one-grid test pool persists, but test does not explicitly reset it between episodes | Persist between moves; cross-episode behavior is a harness gap |
| Input coordinates | figure/notebook use (5,12) | `NCA_DQN.py` constructor uses (5,13); notebook training and demo use (5,12), while a later visualization cell uses (5,13) | Checkpoint evaluation uses notebook/demo (5,12); discrepancy stays explicit |
| Output scaling | multiply CA output by 100 for Q | DQN divides by 0.01 | Equivalent |
| Terminal reward | -100 | environment overwrites reward with cosine value; DQN wrapper stores -100 on terminal transitions | Runtime reward and replay target are distinct |
| Episode horizon | reports mean 13,273 steps | current environment forces done after step 10,000 | Paper table cannot be regenerated from current HEAD without an undocumented historical difference |
| Noise | uniform update perturbation | adds 0.01*uniform[-1,1) to delta before cell mask | Preserve |
| Damage | random circle, inputs unaffected | pool damage happens before NCA call, so post-step input clamp repairs inputs; all channels in circle are randomized | Preserve order and all-channel replacement |
| Curriculum | mean of inputs then DQN | notebook confirms target = 4*mean of eight synthetic inputs and weight transfer | Preserve as historical procedure |
| Learning rate | decay at 1k and 10k | schedule object constructed but scalar 0.005 passed to model in notebook/DQN constructor | No evidence decay was applied in released notebook |
| JavaScript demo | not normative | clamps a different subset/order and uses `<0.5`; browser model graph is still authoritative for weights/topology | Use Python behavior; use TFJS only for topology/weights |
