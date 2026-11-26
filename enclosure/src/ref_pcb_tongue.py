"""ref_tongue: hardware/step/airq-tongue.step as a design (see ref_pcb)."""
from ref_pcb import stage, wrapper

DESIGN = "ref_tongue"
OUTPUT = "reference/airq-tongue.sc"
STEP = "airq-tongue.step"


def prepare():
    """Stage the canonical (LF) copy of the STEP file the script imports."""
    stage(STEP)


def build():
    return wrapper(DESIGN, STEP)
