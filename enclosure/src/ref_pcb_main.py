"""ref_main: hardware/step/airq-main.step as a design (see ref_pcb)."""
from ref_pcb import wrapper

DESIGN = "ref_main"
OUTPUT = "reference/airq-main.sc"
STEP = "airq-main.step"


def build():
    return wrapper(DESIGN, STEP)
