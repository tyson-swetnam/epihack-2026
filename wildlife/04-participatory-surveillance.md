---
id: wv-q4-participatory-surveillance
title: Q4 — How can wildlife diseases be better tracked using Participatory Surveillance?
group: wildlife_vectors
question_number: 4
question_text: "How can wildlife diseases be better tracked using Participatory Surveillance?"
domain: one_health
tags: [participatory-surveillance, wildlife, citizen-science, design]
relates_to: [fig-04-design-launch, fig-05-design-worksheet-template]
---

# Q4 — How can wildlife diseases be better tracked using Participatory Surveillance?

> **How can wildlife diseases be better tracked using Participatory
> Surveillance?**

A draft design that applies the
[12-step lifecycle](../figures/04-designing-launching-participatory-surveillance.md)
and the [worksheet template](../figures/05-design-worksheet-template.md)
to wildlife and vector-borne disease in Arizona.

## 1. Purpose

Capture community reports of (a) sick or dead wildlife, (b) unusual vector
abundance or biting activity, and (c) suspected zoonotic exposures, and
fuse them with **AZGFD** wildlife-health data, **ADHS** zoonotic case
data, and **NEON** longitudinal ecological data to shorten the
*Detect → Verify* interval for spillover events.

## 2. Target populations

- Hunters, anglers, trappers (already report to AZGFD).
- Hikers, birders, photographers (iNaturalist / eBird overlap).
- Ranchers and hobby farmers at the urban-wildlife interface
  (see also the [Desert Wildlife Interface design](../worksheets/02-desert-wildlife-interface.md)).
- Tribal community members and tribal natural-resource staff.
- Public-land managers (NPS, USFS, BLM, AZ State Parks).
- Veterinarians and wildlife rehabilitators.

## 3. What we give back (bi-directionality)

- Real-time map of confirmed wildlife mortality and arbovirus activity
  in the user's county (privacy-preserving — aggregated to ZCTA or
  county).
- "Is this a reportable species/disease?" decision support.
- Push notifications when a signal in the user's area crosses an
  agency-defined threshold.
- Educational content tailored to species and pathogen.

## 4. Parameters (delta vs. Minimum Dataset)

**Keep:** date of incident, geographical coordinates, species, number of
sick/dead animals, photo, contact-with-animal exposure parameters.

**Add for this focus:**
- Species confidence (self-reported / photo-verified / lab-confirmed).
- Behavior at time of observation (e.g. ataxia, blindness, no flight
  response) — useful for CWD, rabies, avian influenza screening.
- Carcass condition (fresh / scavenged / decomposed) — affects lab
  utility.
- Vector activity at site (mosquitoes biting now? tick on observer?).
- Land-cover context (riparian, prairie-dog colony, peri-urban).

**De-emphasize:** human clinical-symptom parameters (handled in human
surveillance designs).

## 5. Access

- iOS / Android app with offline capture and photo upload.
- SMS short code for low-connectivity rural and tribal areas.
- 1-800 voice line that routes to AZGFD's existing report channel.
- Web form for power users (rehabbers, vets, agency staff).
- Multi-lingual UI (Spanish, Navajo / Diné Bizaad, Tohono O'odham).

## 6. Frequency

"See something, report something." No required cadence — but a monthly
nudge to active reporters keeps engagement.

## 7. Time per report

~2 minutes for a photo + tap-through; up to 10 minutes for a structured
mortality investigation by a power user.

## 8. Key partners

- **Arizona Game and Fish Department** — wildlife data authority and
  enforcement; the existing report-a-mortality channel.
- **Arizona Department of Health Services** — zoonotic disease and
  arbovirus authority; lab.
- **NEON** — standardized longitudinal vector/rodent baseline for the
  Desert Southwest domain.
- County vector-control programs (Maricopa, Pima, Yuma, Coconino,
  Pinal).
- University of Arizona (Mel & Enid Zuckerman College of Public Health;
  School of Natural Resources and the Environment; College of
  Veterinary Medicine).
- USDA APHIS Wildlife Services.
- Tribal natural-resource departments.
- iNaturalist / eBird (data partners for species ID).

## 9. Validation

- Photo + geolocation cross-check against species range.
- Cluster detection: flag spatial-temporal anomalies for AZGFD or ADHS
  review.
- Trusted-reporter weighting (vets, rehabbers, agency staff get higher
  initial confidence).
- Lab confirmation feedback loop closes the report.

## 10. Elevator pitch

> Arizona's wildlife and vector surveillance lives in silos — AZGFD
> watches game, ADHS watches arboviruses, NEON watches the ecology, and
> the people closest to the land have nowhere to send what they see. We
> are building a participatory-surveillance front door for wildlife and
> vector-borne disease in Arizona that lets hunters, hikers, ranchers,
> tribal members, and rehabbers report sick or dead wildlife and unusual
> vector activity in two minutes, routes the report to the right
> agency, and gives the community back a live map of what is happening
> in their county. Built on the One Health Minimum Dataset and a
> DuckLake knowledge graph that fuses agency, research, and community
> data.

## See also

- [Resources — NEON, ADHS, AZGFD](./resources.md)
- [Designing & Launching Participatory Surveillance (Figure 4)](../figures/04-designing-launching-participatory-surveillance.md)
- [Minimum Set of Key Data Parameters (Figure 2)](../figures/02-minimum-key-data-parameters.md)
