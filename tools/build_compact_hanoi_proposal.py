from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Clef_NCA_Tower_of_Hanoi_Proposal.docx"

NAVY = "17365D"
PALE_BLUE = "EDF3F8"
PALE_GRAY = "F7F7F7"
MID_GRAY = "666666"
LIGHT_BORDER = "D9D9D9"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        node = borders.find(qn(tag))
        if node is None:
            node = OxmlElement(tag)
            borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), "4")
        node.set(qn("w:space"), "0")
        node.set(qn("w:color"), LIGHT_BORDER)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_run_font(run, name="Aptos", size=None, bold=None, color=None, italic=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def add_hyperlink(paragraph, text, url, color="1F4E79"):
    part = paragraph.part
    rel_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    r_color = OxmlElement("w:color")
    r_color.set(qn("w:val"), color)
    r_pr.append(r_color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    r_pr.append(underline)
    r_fonts = OxmlElement("w:rFonts")
    r_fonts.set(qn("w:ascii"), "Aptos")
    r_fonts.set(qn("w:hAnsi"), "Aptos")
    r_pr.append(r_fonts)
    run.append(r_pr)
    text_node = OxmlElement("w:t")
    text_node.text = text
    run.append(text_node)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char1, instr_text, fld_char2])
    set_run_font(run, size=9, color=MID_GRAY)


def add_paragraph(doc, text="", style=None, bold_lead=None, keep=False):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.08
    if keep:
        p.paragraph_format.keep_with_next = True
    if bold_lead and text.startswith(bold_lead):
        r1 = p.add_run(bold_lead)
        set_run_font(r1, bold=True)
        r2 = p.add_run(text[len(bold_lead):])
        set_run_font(r2)
    else:
        r = p.add_run(text)
        set_run_font(r)
    return p


def add_bullet(doc, text, level=0):
    style = "List Bullet" if level == 0 else "List Bullet 2"
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(2.5)
    p.paragraph_format.line_spacing = 1.03
    r = p.add_run(text)
    set_run_font(r)
    return p


def add_number(doc, text):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.04
    r = p.add_run(text)
    set_run_font(r)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(11 if level == 1 else 7)
    p.paragraph_format.space_after = Pt(4)
    return p


def make_table(doc, headers, rows, widths=None, font_size=9.2):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    header = table.rows[0]
    set_repeat_table_header(header)
    for i, value in enumerate(headers):
        cell = header.cells[i]
        if widths:
            cell.width = Inches(widths[i])
        set_cell_shading(cell, NAVY)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(value)
        set_run_font(r, size=font_size, bold=True, color="FFFFFF")
    for ridx, values in enumerate(rows):
        row = table.add_row()
        cant_split = OxmlElement("w:cantSplit")
        row._tr.get_or_add_trPr().append(cant_split)
        for i, value in enumerate(values):
            cell = row.cells[i]
            if widths:
                cell.width = Inches(widths[i])
            if ridx % 2 == 1:
                set_cell_shading(cell, PALE_BLUE)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(value)
            set_run_font(r, size=font_size)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


doc = Document()
section = doc.sections[0]
section.page_width = Inches(8.5)
section.page_height = Inches(11)
section.top_margin = Inches(0.58)
section.bottom_margin = Inches(0.58)
section.left_margin = Inches(0.75)
section.right_margin = Inches(0.75)

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Aptos"
normal._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
normal.font.size = Pt(10)
normal.paragraph_format.space_after = Pt(4)

title_style = styles["Title"]
title_style.font.name = "Aptos Display"
title_style._element.rPr.rFonts.set(qn("w:ascii"), "Aptos Display")
title_style._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos Display")
title_style.font.size = Pt(25)
title_style.font.bold = True
title_style.font.color.rgb = RGBColor(0, 0, 0)
title_style.paragraph_format.space_after = Pt(5)
title_ppr = title_style._element.get_or_add_pPr()
title_pbdr = title_ppr.find(qn("w:pBdr"))
if title_pbdr is None:
    title_pbdr = OxmlElement("w:pBdr")
    title_ppr.append(title_pbdr)
title_bottom = OxmlElement("w:bottom")
title_bottom.set(qn("w:val"), "nil")
title_pbdr.append(title_bottom)

for name, size in (("Heading 1", 15), ("Heading 2", 11.5)):
    style = styles[name]
    style.font.name = "Aptos Display"
    style._element.rPr.rFonts.set(qn("w:ascii"), "Aptos Display")
    style._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos Display")
    style.font.size = Pt(size)
    style.font.bold = True
    style.font.color.rgb = RGBColor(0, 0, 0)

for list_name in ("List Bullet", "List Bullet 2", "List Number"):
    styles[list_name].font.name = "Aptos"
    styles[list_name]._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    styles[list_name]._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    styles[list_name].font.size = Pt(9.9)

footer = section.footer
fp = footer.paragraphs[0]
fp.add_run("Clef NCA Tower of Hanoi Proposal    |    ")
for run in fp.runs:
    set_run_font(run, size=8.5, color=MID_GRAY)
add_page_number(fp)

title = doc.add_paragraph(style="Title")
title.alignment = WD_ALIGN_PARAGRAPH.LEFT
run = title.add_run("Neural Cellular Automata Accelerator for Tower of Hanoi")
set_run_font(run, name="Aptos Display", size=25, bold=True, color="000000")

subtitle = doc.add_paragraph()
subtitle.paragraph_format.space_after = Pt(2)
r = subtitle.add_run("Preliminary semester project proposal")
set_run_font(r, size=12, bold=True, color=NAVY)

meta = doc.add_paragraph()
meta.paragraph_format.space_after = Pt(12)
r = meta.add_run("Prepared for advisor review  |  September 2026")
set_run_font(r, size=9.5, color=MID_GRAY)

add_paragraph(
    doc,
    "I propose to build a fixed-point FPGA and ASIC-oriented accelerator for a neural cellular automaton that learns to solve Tower of Hanoi through repeated local interactions. The implementation starts from a published and reproducible NCA controller architecture, replaces its CartPole environment with a parameterized Tower of Hanoi environment, and adds hardware features for locality, fault recovery, adaptive resource use, and causal experiments. The semester has an independent engineering deliverable even if the longer-term autopoiesis hypothesis remains unresolved.",
)

p = add_paragraph(doc, "Decision requested  Approve the staged scope in which a verified FPGA NCA engine and closed-loop Hanoi demonstration form the required deliverable, while ASIC physical design and endogenous Clef mechanisms remain successive targets.", bold_lead="Decision requested  ")
p.paragraph_format.space_after = Pt(10)

add_heading(doc, "Existing foundation and controlled extension", 1)
add_paragraph(
    doc,
    "The proposal does not assume that a new learning substrate will work without precedent. It combines documented pieces and makes the unproven step small enough to test in software before RTL is committed. The exact Tower of Hanoi NCA is new work; the cellular controller, training pattern, and hardware workflow have prior demonstrations.",
)

make_table(
    doc,
    ["Documented basis", "What it establishes", "How this project builds on it"],
    [
        (
            "Variengien et al. 2021 CartPole NCA",
            "A 32 by 32 recurrent grid with six channels per cell, a shared local neural rule, distributed inputs and outputs, Deep Q learning, persistent control, and damage tests. Public code and pretrained models are available.",
            "Reuse the cellular state model, local update operator, recurrent execution method, software training workflow, and perturbation methodology. Replace CartPole observations and actions with Hanoi state and legal moves.",
        ),
        (
            "Xu and Miikkulainen 2025 NCA for ARC AGI",
            "NCAs can be trained for precise grid transformations and evaluated for generalization beyond biological pattern growth.",
            "Supports using an NCA for a discrete structured reasoning task, while leaving Hanoi performance as an empirical question.",
        ),
        (
            "Paluch et al. 2024 FPGA neural control",
            "A documented flow from trained neural controller to quantized FPGA implementation, hardware in the loop, and latency, power, and resource reporting.",
            "Use the same engineering discipline for an NCA datapath rather than a conventional multilayer perceptron controller.",
        ),
    ],
    widths=[1.55, 2.45, 2.95],
    font_size=8.7,
)

add_paragraph(
    doc,
    "This evidence de-risks the architecture, tools, and evaluation method. It does not guarantee that an NCA will discover a size-general Tower of Hanoi policy. That risk is isolated by a software feasibility gate and a training-only imitation fallback. The FPGA will contain the learned local rule, not an explicit recursive Hanoi solver.",
)

add_heading(doc, "Tower of Hanoi formulation", 1)
add_paragraph(
    doc,
    "The environment contains three pegs and a variable number of ordered disks. At each environment step, the NCA observes the current arrangement and proposes one of the six directed peg-to-peg transfers. The environment applies the proposal only if it moves the top disk and does not place a larger disk on a smaller one. Legal progress, illegal moves, completion, and delay produce the feedback used during training and evaluation.",
)

add_heading(doc, "State and action interface", 2)
add_bullet(doc, "Encode each disk and its current peg in a spatial input field, with a mask identifying which disk rows are active for the current problem size.")
add_bullet(doc, "Reserve hidden cell channels for distributed recurrent state rather than assigning intermediate cells fixed symbolic meanings.")
add_bullet(doc, "Read six action values from output cells, one for each directed source and destination peg pair.")
add_bullet(doc, "Retain the cellular state between moves so that the solution is an ongoing process rather than a fresh feed-forward inference at every state.")
add_bullet(doc, "Parameterize storage for a compiled maximum disk count. Generalization to unseen disk counts within that physical capacity is a stretch result, not a prerequisite for RTL completion.")

add_heading(doc, "Training path", 2)
add_number(doc, "Train and validate the Hanoi NCA entirely in software before freezing the hardware operator.")
add_number(doc, "Begin with legality and next-move curriculum tasks, then train the recurrent policy using reinforcement learning.")
add_number(doc, "If direct reinforcement learning is unstable, pretrain from optimal solution traces and fine-tune with reinforcement learning. The teacher is used only during training.")
add_number(doc, "Quantize the trained rule and verify long rollouts before translating it to RTL.")

add_paragraph(
    doc,
    "A completed n-disk solution necessarily emits at least 2^n - 1 moves. The project therefore will not claim sublinear total solution time against this output lower bound. Hardware claims will concern area, energy, latency per cellular update or Hanoi move, throughput, and the cost of maintaining performance under faults.",
)

add_heading(doc, "Baseline hardware architecture", 1)
add_paragraph(
    doc,
    "The first implementation is a folded cellular accelerator. The logical system remains a two-dimensional grid with local neighborhoods, while a configurable number of physical multiply-accumulate lanes processes many logical cells over time. Ping-pong state memories preserve the rule that all next-state values read the completed previous cellular state.",
)

make_table(
    doc,
    ["Block", "Baseline responsibility", "Design variable"],
    [
        ("State memory", "Stores fast cell channels in two banked buffers and preserves recurrent state across Hanoi moves.", "Grid size, bank count, word width, SRAM or block RAM mapping"),
        ("Neighborhood unit", "Builds each local window with reference-matched boundaries and optional disabled edges.", "Raster streaming, patch halos, or banked random access"),
        ("Local rule engine", "Runs perception, hidden transformation, residual update, activation, rounding, and saturation.", "MAC lane count, pipeline depth, precision, weight storage"),
        ("Update scheduler", "Generates deterministic seeded masks and sequences cells and cellular epochs.", "Dense sweep, masked skipping, patch-level elastic execution"),
        ("Hanoi interface", "Writes the state encoding, reads six action values, and exchanges legality and progress feedback with the host environment.", "Register or streaming protocol, batching, decision deadline"),
        ("Experiment plane", "Injects cell, state, edge, input, memory, and processing faults and records recovery.", "Checkpoint depth, trace bandwidth, intervention granularity"),
    ],
    widths=[1.25, 3.15, 2.55],
    font_size=8.7,
)

add_heading(doc, "Architecture innovations", 1)
add_paragraph(
    doc,
    "The novel work is not the use of philosophical terminology. Each theoretical influence must produce a concrete circuit choice, measurable tradeoff, or verification obligation.",
)

make_table(
    doc,
    ["Design idea", "RTL realization", "Value now and later"],
    [
        (
            "Process preserving folding",
            "Typed sense, integrate, propose, and commit interfaces plus differential tests show that memory banking, pipeline depth, and cell ordering preserve the logical cellular transition.",
            "Applied category theory motivates compositional verification. The same contract can host later Clef rules without changing the experimental chassis.",
        ),
        (
            "Patch local topology",
            "Divide the grid into SRAM backed patches that exchange version tagged halo states through narrow neighbor links.",
            "Reduces global traffic and compares centralized raster, patch synchronous, and elastic local schedules. Dynamic links can be introduced later.",
        ),
        (
            "Local consistency",
            "Boundary versions and assertions require neighboring patch descriptions to agree before a logical epoch commits.",
            "A sheaf inspired local to global discipline supports distributed execution without claiming a clockless or autopoietic baseline.",
        ),
        (
            "Viability aware compute",
            "Economy, nominal, and recovery modes vary iteration count, active lanes, precision, and clock enables using generic urgency and convergence signals.",
            "Optimizes energy per successful Hanoi move. Later, locally distributed viability variables can replace host selected modes.",
        ),
        (
            "Multirate organization",
            "Separate fast cell state from optional slow edge, plasticity, resource, and threshold memories with independent update enables.",
            "Avoids paying fast-state bandwidth for slow variables and provides a direct path to local plasticity and maintenance experiments.",
        ),
        (
            "Degenerate remapping",
            "Map logical patches onto interchangeable processing and memory resources so surviving hardware can absorb a failed region at lower throughput.",
            "Measures graceful degradation now and supplies a control case for later endogenous role migration.",
        ),
        (
            "Causal interrogability",
            "Checkpoint state, fork normal and intervention runs, silence selected regions or links, and compare action, recovery, and viability trajectories.",
            "Improves verification and fault analysis now; later supplies the counterfactual evidence needed to distinguish activity from causal maintenance.",
        ),
    ],
    widths=[1.35, 3.05, 2.55],
    font_size=8.45,
)

add_heading(doc, "Evaluation", 1)
add_paragraph(
    doc,
    "The baseline will be compared at four levels: floating-point software, bit-accurate fixed-point software, RTL simulation, and FPGA execution. A conventional compact policy network will provide a control comparison so that FPGA acceleration is not mistaken for an NCA-specific advantage.",
)
add_bullet(doc, "Task quality: legal-move rate, solution rate, move count above optimum, generalization across start and goal states, and performance across trained and unseen disk counts.")
add_bullet(doc, "Hardware performance: cycles per cell update, cellular epoch, and Hanoi move; maximum clock frequency; throughput; area; memory; multiplier use; power; and energy per legal or successful move.")
add_bullet(doc, "Resilience: performance and recovery time after damaged state regions, disabled logical cells, broken neighbor links, missing inputs, or failed physical processing resources.")
add_bullet(doc, "Architectural value: Pareto comparisons across precision, MAC lanes, banking, patch size, update sparsity, resource modes, and fault support.")

add_heading(doc, "Semester scope and acceptance", 1)
make_table(
    doc,
    ["Stage", "Required result", "Fallback that preserves a deliverable"],
    [
        ("Weeks 1 to 3", "Software Hanoi NCA solves declared small problem sizes and exports deterministic traces.", "Use optimal-trace pretraining; if necessary, reduce the maximum training size while retaining the parameterized representation."),
        ("Weeks 4 to 5", "Fixed-point model preserves declared policy and rollout tolerances.", "Use wider or mixed precision and quantization-aware retraining."),
        ("Weeks 6 to 9", "Synthesizable NCA core matches bit-accurate one-cell, one-epoch, and multi-epoch traces.", "Use a more folded engine or smaller synthesized configuration while retaining full-size software tests."),
        ("Weeks 10 to 12", "FPGA closes the loop with the host Hanoi environment and completes repeatable episodes.", "Run the host environment at hardware pace and report compute latency separately if real-time communication is limiting."),
        ("Weeks 13 to 15", "PPA and fault study completed; core enters the available ASIC synthesis and place-and-route flow.", "Deliver timing, area, and power reports at the highest supported physical-design stage if an MPW or SRAM macro is unavailable."),
    ],
    widths=[1.05, 3.15, 2.75],
    font_size=8.55,
)

add_paragraph(
    doc,
    "The guaranteed semester floor is a verified, synthesizable, fixed-point cellular accelerator demonstrated on FPGA with a host-connected Hanoi environment. A tapeout-ready RTL-to-GDSII macro is the target. Fabrication depends on foundry access, funding, and shuttle dates.",
)

add_heading(doc, "Research trajectory toward Clef", 1)
make_table(
    doc,
    ["Mode", "Added capability", "Claim permitted"],
    [
        ("Zero", "Fixed shared NCA rule, fixed topology, externally trained weights, retained state, fault injection", "Distributed recurrence, emergence, and measured recovery"),
        ("One", "Locally updated edge weights and eligibility traces", "Online adaptation if behavior changes under new Hanoi mappings"),
        ("Two", "Viability dependent link and state maintenance with resource decay", "Candidate self-maintaining organization if interventions show reciprocal dependence"),
        ("Three", "Recruitment of idle cells, role migration, and locally changing connectivity", "Candidate closure to efficient cause only if causal capacities maintain one another without a hidden external maintainer"),
        ("Four", "Frozen functional models tested against historically changing roles while microstate execution remains deterministic", "Evidence relevant to Medium Rosen, never a proof of noncomputability from finite experiments"),
    ],
    widths=[0.65, 3.35, 2.95],
    font_size=8.55,
)

add_paragraph(
    doc,
    "Mode Zero remains an externally specified NCA, not an autopoietic system. It establishes the silicon substrate and intervention controls needed for stronger tests. Any later Medium Rosen interpretation will be checked against the relevant Louie, Cardenas, Hofmeyr, and Vega arguments rather than inferred from conventional computability assumptions alone.",
)

add_heading(doc, "Expected contribution", 1)
add_paragraph(
    doc,
    "The safe contribution claim is a parameterized, fault-injectable FPGA and ASIC architecture for recurrent neural cellular computation on Tower of Hanoi. Candidate novelty lies in process-preserving folding, patch-local execution, adaptive compute budgets, fault remapping, and built-in counterfactual experiments. A formal prior-art review remains necessary before claiming priority.",
)

add_paragraph(
    doc,
    "Independent of the theoretical outcome, the work demonstrates fixed-point analysis, memory and stencil dataflow, parallel arithmetic, SystemVerilog verification, FPGA integration, fault testing, PPA exploration, and ASIC physical design.",
)

add_heading(doc, "References", 1)

p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(3)
r = p.add_run("1. Variengien et al., Towards Self-organized Control, 2021. ")
set_run_font(r, size=9.2)
add_hyperlink(p, "Paper", "https://arxiv.org/abs/2106.15240")
r = p.add_run("  |  ")
set_run_font(r, size=9.2)
add_hyperlink(p, "Code", "https://github.com/aVariengien/self-organized-control")

p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(3)
r = p.add_run("2. Xu and Miikkulainen, Neural Cellular Automata for ARC AGI, 2025. ")
set_run_font(r, size=9.2)
add_hyperlink(p, "Paper", "https://arxiv.org/abs/2506.15746")

p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(3)
r = p.add_run("3. Paluch et al., FPGA Hardware Neural Control, 2024. ")
set_run_font(r, size=9.2)
add_hyperlink(p, "Paper", "https://arxiv.org/abs/2407.08681")
r = p.add_run("  |  ")
set_run_font(r, size=9.2)
add_hyperlink(p, "Code", "https://github.com/SensorsINI/Neural-Control-Tools")

p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(3)
r = p.add_run("4. Louie, More Than Life Itself, 2009, with the linked Cardenas, Hofmeyr, and Vega works for later Clef stages.")
set_run_font(r, size=9.2)

doc.core_properties.title = "Neural Cellular Automata Accelerator for Tower of Hanoi"
doc.core_properties.subject = "Preliminary semester project proposal"
doc.core_properties.keywords = "neural cellular automata, FPGA, ASIC, Tower of Hanoi, Clef, autopoiesis"

doc.save(OUT)
print(OUT)
