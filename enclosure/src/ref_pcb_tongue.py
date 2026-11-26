"""ref_tongue: hardware/step/airq-tongue.step as a design (see ref_pcb)."""
from ref_pcb import wrapper

DESIGN = "ref_tongue"
OUTPUT = "reference/airq-tongue.sc"
STEP = "airq-tongue.step"


def build():
    return wrapper(DESIGN, STEP)
