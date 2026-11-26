"""ref_main: hardware/step/airq-main.step as a design (see ref_pcb)."""
from ref_pcb import stage, wrapper

DESIGN = "ref_main"
OUTPUT = "reference/airq-main.sc"
STEP = "airq-main.step"


def prepare():
    """Stage the canonical (LF) copy of the STEP file the script imports."""
    stage(STEP)


def build():
    return wrapper(DESIGN, STEP)
