---
id: wv-q3-surveillance-technologies
title: Q3 — Technologies that could improve surveillance in this sector
group: wildlife_vectors
question_number: 3
question_text: "What technologies could improve surveillance in this sector(s)?"
domain: one_health
tags: [technology, edna, metagenomics, camera-traps, acoustic, remote-sensing, ml]
---

# Q3 — Technologies that could improve surveillance

> **What technologies could improve surveillance in this sector(s)?**

## Sampling-side technology

| Technology | What it adds | Caveats |
|---|---|---|
| **Environmental DNA (eDNA)** from water, soil, sediment | Detect host species and some pathogens without trapping individuals | False positives from degraded DNA; requires lab pipeline |
| **Pathogen metagenomics on pooled vectors** (Nanopore / Illumina) | Unbiased detection of novel arboviruses, *Rickettsia*, *Borrelia*, etc. in mosquito or tick pools | Cost, bioinformatics, reference databases |
| **Wildlife camera traps** with on-device ML | Continuous wildlife presence/absence; can flag sick-looking animals | Storage, species mis-classification |
| **Acoustic monitoring** (AudioMoth, ARUs) | Bird and bat community surveillance; can detect mosquito species by wing-beat frequency | Manual review still required |
| **Smart mosquito traps** (e.g. BG-Counter, Vectrax) | Near-real-time density telemetry vs. weekly manual counts | Capex, connectivity |
| **Satellite + drone remote sensing** | NDVI, surface water, temperature anomalies as predictors of vector population growth | Resolution, cadence |
| **Wastewater pathogen surveillance** | Catches some zoonotic spillover signals (e.g. *Leptospira*, hantavirus) at population scale | Designed for human pathogens; wildlife signals are noisy |

## Data + analytics side

- **NEON Data API** + **Arizona open-data portals** unified into one
  query layer (this is exactly what the DuckLake/DuckDB knowledge graph
  in this repository is for).
- **Knowledge-graph search** across the One Health Minimum Dataset →
  surface "what do we know about *Y. pestis* in Coconino County in the
  last 30 days?" in one query.
- **Bayesian early-warning models** combining mosquito index, WNV
  positivity, weather, and human case counts.
- **Federated learning** so tribal nations and other jurisdictions can
  contribute to models without releasing raw line-level data.
- **LLM-assisted intake** that lets a hunter, ranger, or member of the
  public submit a free-text report and have it normalized to the
  Minimum Dataset parameters automatically.

## Participatory technology

- Mobile apps with offline mode and photo upload (iNaturalist as a
  pattern, but with structured public-health prompts).
- SMS / USSD short codes for low-bandwidth areas.
- Audio reports (voice messages transcribed by an LLM) for
  literacy-independent participation.
- Geofenced push notifications when a surveillance signal exceeds a
  threshold in the user's area.

## See also

- [Resources — NEON, ADHS, AZGFD](./resources.md)
- [Q4 — Participatory Surveillance for wildlife disease](./04-participatory-surveillance.md)
