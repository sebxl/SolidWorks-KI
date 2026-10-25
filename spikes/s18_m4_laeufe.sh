#!/bin/sh
# S18 M4: Sortierschritt mit Geometrie aus den Specs, drei Vergleichsfälle gegen die Handmodell-Rohdaten
# (simulation/sortierschritt-2026-10-18/daten). Aufruf aus dem Repo: sh spikes/s18_m4_laeufe.sh <python> <auftrag> <aus>
PY=$1; A=$2; O=$3
SIM=spikes/s18_sortierschritt.sim.yaml
mkdir -p $O
export DT=1e-5 TC=1.5e-4
# 1 G1c (freigegeben), rauer Keil µ 0,55 / e 0,55, Weiche i.O. (Keil bleibt draußen), 0,10 m/s – Hand: 100 %
MU_KEIL=0.55 E_KEIL=0.55 V=0.10 $PY -m spikes.s18_sim $A $SIM io_fest $O/m4_g1c_keil0.55_io_fest_v0.10.json
# 2 G1b = G1c ohne Keilwangen, Stahlkeil µ 0,55 / e 0,60, i.O., 0,10 m/s – Hand: 88,6 %
MU_KEIL=0.55 E_KEIL=0.60 V=0.10 $PY -m spikes.s18_sim $A $SIM io_fest $O/m4_g1b_stahl_io_fest_v0.10.json \
  --var G1b --ohne weichenkeil.yaml:wange_mx,wange_px
# 3 Ist v5 (vor G1c): Rutsche YV 170,5 / R_BN 21 ohne Fangwand, Keil YS 218,5 ohne Wangen; n.i.O., 0,10 m/s – Hand: 25,8 % falsch
V=0.10 $PY -m spikes.s18_sim $A $SIM nio $O/m4_ist_nio_v0.10.json --var ist \
  --parameter rutsche.yaml:YV=170.5 rutsche.yaml:R_BN=21 weichenkeil.yaml:YS=218.5 \
  --ohne rutsche.yaml:fw weichenkeil.yaml:wange_mx,wange_px
