# Executable references

reference/original_nca/ is the immutable published-NCA operator/reproduction reference. reference/hanoi/ is the completed historical environment/oracle and must remain tested; its interface is not the new target.

The active benchmark is reference-paper CartPole (accepted ADR-0008). E01 consolidates existing original_nca plant/I/O/replay authority into separate deployment contracts; it does not duplicate physics or rewrite the immutable reference. E02/G3E accepts checkpoint/protocol before P06/P07 freeze/quantization. Custom surface and EvoGym are post-FPGA extensions with separate contracts, not current plant work.
