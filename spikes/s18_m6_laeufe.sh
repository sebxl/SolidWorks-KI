#!/bin/sh
# S18 M6 (Prüfstufe 2): Optuna-Bester aus M5 (Probe 3: T 179,725, YS 205,367, ZF −187,494) mit allen 1992 Startlagen D1
# in den drei Bedingungen der Studie, dazu die Bedingung io 0,05 rau mit halbem Zeitschritt und halber
# Kontakt-Zeitkonstante. Aufruf aus dem Repo: sh spikes/s18_m6_laeufe.sh <python> <auftrag> <aus>
PY=$1; A=$2; O=$3
SIM=spikes/s18_sortierschritt.sim.yaml
P="rutsche.yaml:YV=156.7252 rutsche.yaml:R_BN=34.7748 rutsche.yaml:ZF=-187.4937 weichenkeil.yaml:YS=205.3668"
mkdir -p $O
DT=1e-5 TC=1.5e-4 V=0.10 $PY -m spikes.s18_sim $A $SIM nio $O/m6_nio_v0.10.json --var spec --parameter $P
DT=1e-5 TC=1.5e-4 V=0.05 MU_KEIL=0.55 E_KEIL=0.55 $PY -m spikes.s18_sim $A $SIM io_fest $O/m6_io_v0.05_rau.json --var spec --parameter $P
DT=1e-5 TC=1.5e-4 V=0.15 MU_KEIL=0.55 E_KEIL=0.55 $PY -m spikes.s18_sim $A $SIM io_fest $O/m6_io_v0.15_rau.json --var spec --parameter $P
DT=5e-6 TC=7.5e-5 V=0.05 MU_KEIL=0.55 E_KEIL=0.55 $PY -m spikes.s18_sim $A $SIM io_fest $O/m6_io_v0.05_rau_dt5e-6.json --var spec --parameter $P
