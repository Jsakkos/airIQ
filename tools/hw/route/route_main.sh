#!/usr/bin/env bash
# Main board routing pipeline: how hardware/kicad/main/airq-main.kicad_pcb was routed. NOT part of the
# build (tools/hw/build.py never runs it); run it only to route the main board again from scratch.
#
#   bash tools/hw/route/route_main.sh            # from the repository root; takes a few minutes
#
# unroute (cleanup.py) -> rebuild -> rule areas + hand-routed critical nets (main_preroute.py) -> rebuild
# -> Freerouting (GND ignored) -> SES import -> clean-up -> second Freerouting pass for what is left
# -> hand fixes (main_postfix.py) -> GND pours + stitching vias (main_pour.py, stitch.py) -> rebuild.
#
# Needs: KiCad 10 (kicad_env.py finds it), uv, Java, and the Freerouting 2.5.0 release JAR at
# build/tools/freerouting-2.5.0/freerouting-2.5.0.jar (hardware/README.md, "Install").
# main_preroute.py hard-codes the current placement: after moving parts, redraw its lines first.
# Freerouting's result depends on its whole input (any pre-route change re-rolls it) and its
# multi-threaded optimiser adds small run-to-run differences: a re-run gives an equivalent board, check
# it (DRC, tests) before committing. The SES import rewrites the KiCad project file (pcbnew's save), so
# the script puts the generated one back.
set -eo pipefail
cd "$(dirname "$0")/../../.."
R=tools/hw/route
KP="$(uv run python -I -c 'import sys; sys.path.insert(0, "tools/hw"); from kicad_env import kicad_python; print(kicad_python())')"
FR="java -jar tools/freerouting-2.5.0/freerouting-2.5.0.jar"   # relative to build/
PCB=hardware/kicad/main/airq-main.kicad_pcb
PRO=hardware/kicad/main/airq-main.kicad_pro

build() {
  uv run --with pyyaml python tools/hw/build.py main >build/route-build.log 2>&1 || true
  grep "^DRC" build/route-build.log || true
}
clean_dangling() {   # Freerouting leaves a few vias / stubs connected on one side only
  for _ in 1 2 3 4 5; do
    n=$(uv run python -I $R/cleanup.py dangling "$PCB" build/main-drc.json); echo "cleanup: $n removed"
    [ "$n" = "0" ] && break
    build
  done
}
route_pass() {   # $1 = session name, $2 = fr_prep.py options, rest = extra Freerouting options
  local name=$1 prep=$2; shift 2
  uv run python -I $R/fr_prep.py $prep build/main.dsn build/fr-main.dsn GND >/dev/null
  (cd build && $FR -de fr-main.dsn -do "$name.ses" -mp 100 -inc Poured --gui.enabled=false "$@" >"$name.log" 2>&1) || true
  sed -n "/could not be routed/,/Auto-routing stage/p" "build/$name.log" | grep "Net '" | grep -v "'GND'" || true
  cp "$PRO" build/route-pro.bak
  "$KP" -I tools/hw/kicad_dsn.py --import-ses "$PCB" "build/$name.ses"
  cp build/route-pro.bak "$PRO"
  build
  clean_dangling
}

uv run python -I $R/cleanup.py unroute "$PCB"
build
uv run python -I $R/main_preroute.py "$PCB"
build
route_pass fr-main ""
uv run python -I $R/cleanup.py narrow "$PCB" 0.15      # drop neck-downs below the board minimum
build
n=$(uv run python -I $R/cleanup.py unrouted build/main-drc.json); echo "signal connections left after pass 1: $n"
if [ "$n" != "0" ]; then
  route_pass fr-main2 "--signal-width 150" --router.automatic_neckdown=false
  echo "signal connections left after pass 2: $(uv run python -I $R/cleanup.py unrouted build/main-drc.json)"
fi
uv run python -I $R/main_postfix.py "$PCB"            # hand fixes on the routed result
build
uv run python -I $R/main_pour.py "$PCB" >/dev/null
build
"$KP" -I $R/stitch.py "$PCB" 0.5 2.5 >build/stitch.txt 2>build/stitch.err || true
uv run python -I $R/main_pour.py "$PCB" $(cat build/stitch.txt) >/dev/null
build
uv run python -I $R/cleanup.py drop-dangling-vias build/main-drc.json build/stitch.txt
uv run python -I $R/main_pour.py "$PCB" $(cat build/stitch.txt) >/dev/null
build
# one more via in every pour fragment that has none (on the filled board)
"$KP" -I $R/stitch.py "$PCB" 0.25 2.5 islands >build/stitch2.txt 2>>build/stitch.err || true
echo "island vias: $(wc -w <build/stitch2.txt)"
uv run python -I $R/main_pour.py "$PCB" $(cat build/stitch.txt) $(cat build/stitch2.txt) >/dev/null
build
