"""Reproducible bit counts and explicit hypothetical schedules, not synthesis."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from model_export.cartpole.accepted_arithmetic import accepted_format
from model_export.cartpole.row16_candidate import candidate_format


def main():
    result={"scope":"Logical counts/conditional timing only; no Quartus mapping, Fmax or power measurements", "formats":{}}
    for fmt in (candidate_format(),accepted_format()):
        bits={"one_grid":6144*fmt.state_bits,"three_old_rows":3*32*6*fmt.state_bits,
              "two_slots_at_each_activation_boundary":2*32*(20+30)*fmt.state_bits,
              "kernels":1860*fmt.weight_bits,"biases":56*fmt.accumulator_bits}
        result["formats"][fmt.name]={"state_bits":fmt.state_bits,"state_fraction":fmt.state_fraction,
            "weight_bits":fmt.weight_bits,"weight_fraction":fmt.weight_fraction,"accumulator_bits":fmt.accumulator_bits,
            "bytes":{k:v//8 for k,v in bits.items()},"sum_of_listed_bytes":sum(bits.values())//8,
            "state_m10k_width_packing_estimate":4*((6*fmt.state_bits+39)//40),
            "state_quantum":2**(-fmt.state_fraction),"weight_quantum":2**(-fmt.weight_fraction)}
    result["schedule_examples"]=[]
    for lanes in ((32,24,8),(16,12,4)):
        lengths=[54*((640+lanes[0]-1)//lanes[0]),20*((960+lanes[1]-1)//lanes[1]),30*((192+lanes[2]-1)//lanes[2])]
        epoch=31*max(lengths)+sum(lengths)
        result["schedule_examples"].append({"lanes":lanes,"enabled_stage_cycles":lengths,"ideal_epoch_cycles":epoch,
            "55_epoch_action_ms_at_50MHz":epoch*55/50000,
            "assumptions":"One MAC/lane/cycle, same clock, enough ports/registers, no refill/writeback/transport overhead"})
    result["excluded_storage"]="Delta holds, pipeline sums, replication/port padding, mask/RNG/UART, metadata/debug and wrappers"
    result["sources"]={
        "dsp_multipliers":"https://docs.altera.com/r/docs/683375/current/cyclone-v-device-handbook-volume-1-device-interfaces-and-integration/multipliers",
        "accumulator_restrictions":"https://docs.altera.com/r/docs/683375/current/cyclone-v-device-handbook-volume-1-device-interfaces-and-integration/accumulator-and-chainout-adder",
        "device_resources":"https://docs.altera.com/r/docs/683375/current/cyclone-v-device-handbook-volume-1-device-interfaces-and-integration/resources",
        "m10k_modes":"https://docs.altera.com/r/docs/683375/current/cyclone-v-device-handbook-volume-1-device-interfaces-and-integration/m10k-blocks-mixed-width-configurations"}
    output=Path(__file__).with_name("hardware_tradeoff.json")
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
