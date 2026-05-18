---
id: fig-03-timeliness
title: Outbreak Timeliness Metrics
source: EpiHack Arizona 2026 - Ending Pandemics Academy / University of Arizona Global Health Institute
type: metric_framework
domain: one_health
tags: [timeliness, milestones, outbreak-response, one-health, metrics]
---

# Outbreak Timeliness Metrics

> Timeliness metrics are the time intervals measured between two respective
> outbreak milestones. Each milestone represents the date of key outbreak
> activities. Milestones can apply to individual sectors or to a coordinated
> One Health approach, integrating environmental, animal, and human health.

## Outbreak Milestones

| # | Milestone | Definition |
|---|---|---|
| 1 | **Predict** | Date a reliable and valid predictive alert of a potential outbreak is available (e.g. increased rainfall leading to greater density of mosquitoes capable of disease transmission). |
| 2 | **Prevent** | Date enhanced surveillance or other intervention is initiated in response to a predictive alert (e.g. mass vaccination in livestock; mosquito abatement). |
| 3 | **Detect** | Date symptom onset, death, or other evidence of pathogen circulation is observed or suspected in human(s) or animal(s). |
| 4 | **Notify** | Date an outbreak in humans or animals is officially reported to relevant authorities (e.g. local to national; national to international; cross-sector). |
| 5 | **Verify** | Date outbreak is confirmed by field investigation or other valid method. |
| 6 | **Diagnostic Test / Lab Confirmation** | Date outbreak is confirmed by diagnostic or laboratory test in an epidemiologically-linked human or animal. |
| 7 | **Respond** | Date an intervention to control or manage the outbreak is initiated by a responsible authority (e.g. mass vaccination; quarantine). |
| 8 | **Public Communication** | Date of official release of information to the public by a responsible authority. |
| 9 | **Outbreak Start** | Date symptom onset or death occurs in the earliest epidemiologically-linked human or animal (most often identified retrospectively or estimated based on available evidence). |
| 10 | **Outbreak End** | Date outbreak is declared closed by a responsible authority. |
| 11 | **After Action Review** | Date after action review is jointly conducted by relevant One Health authorities. |

## Notes

- The sequence of the milestones may vary by outbreak. In some cases a single
  action may represent more than one milestone — for example, the date of lab
  confirmation may be the date of verification. Similarly, public communication
  may be the first intervention in response to an outbreak. The definition of
  an outbreak may vary by disease, geography, or sector.
- The After Action Review milestone is included to inspire the necessary
  collaborations among sectors for operationalizing One Health.

## Knowledge Graph Triples

| subject | predicate | object |
|---|---|---|
| Outbreak | hasMilestone | Predict |
| Outbreak | hasMilestone | Prevent |
| Outbreak | hasMilestone | Detect |
| Outbreak | hasMilestone | Notify |
| Outbreak | hasMilestone | Verify |
| Outbreak | hasMilestone | LabConfirmation |
| Outbreak | hasMilestone | Respond |
| Outbreak | hasMilestone | PublicCommunication |
| Outbreak | hasMilestone | OutbreakStart |
| Outbreak | hasMilestone | OutbreakEnd |
| Outbreak | hasMilestone | AfterActionReview |
| TimelinessMetric | measures | IntervalBetweenMilestones |
| TimelinessMetric | appliesTo | HumanHealthSector |
| TimelinessMetric | appliesTo | AnimalHealthSector |
| TimelinessMetric | appliesTo | EnvironmentalHealthSector |
| TimelinessMetric | appliesTo | OneHealthCoordinatedResponse |

## Attribution
- Ending Pandemics Academy
- The University of Arizona, Mel & Enid Zuckerman College of Public Health
- Global Health Institute
