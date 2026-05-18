---
id: fig-02-data-parameters
title: Minimum Set of Key Data Parameters
source: EpiHack Arizona 2026 - Ending Pandemics Academy / University of Arizona Global Health Institute
type: data_schema
domain: one_health
tags: [data-parameters, surveillance, one-health, schema]
---

# Minimum Set of Key Data Parameters

A radial framework grouping the minimum set of data parameters required for
One Health participatory surveillance, organized into eight color-coded
parameter classes.

## Legend

| Color | Category | Description |
|---|---|---|
| Light Blue | **General** | Demographic and contact attributes of a reporter |
| Dark Blue | **Human** | Human health symptoms and clinical signs |
| (Dark Blue) | **Severity markers** | Severe-disease indicators within the human set |
| Pink/Magenta | **Exposure** | Risk-exposure events for the reporter |
| Tan/Yellow | **Auxiliary** | Supporting evidence (signals, images, lab) |
| Green | **Environmental** | Environmental incident and vector signals |
| Magenta | **Livestock** | Domestic-animal incident attributes |
| Purple | **Wildlife** | Wildlife incident attributes |

## Parameters by Category

### General
- Age
- Sex
- Email
- Unique ID
- Occupation
- Date of report
- Postal code
- Phone number
- Household member ID
- Geographical coordinates

### Human (symptoms / clinical)
- No symptoms
- Symptoms
- Date of illness
- Cough / congestion
- Nausea / vomiting
- Difficulty breathing
- Sore throat
- Rash
- Fever
- Chills
- Diarrhea
- Bleeding from body openings *(severity marker)*
- Red eyes
- Muscle or body aches and pains
- Discolored or bloody urine *(severity marker)*
- Loss of smell or taste
- Yellow skin / yellow eyes *(severity marker)*
- Absent from work
- Absent from school
- Did you seek health care or treatment

### Exposure
- Attending a recent mass gathering
- Tick or insect bite
- Animal bite
- History of travel
- Contact with live animals
- Contact with dead or sick animals
- Contact with sick individual / confirmed case

### Auxiliary
- Digital biomarker signal
- Photo
- Diagnostic / lab confirmation

### Environmental
- Date of environmental incident
- Location of vector spotting
- Unusual presence of vectors
- Density or number of vectors
- Flooding
- Water contamination

### Livestock
- Date of livestock incident
- Location of livestock incident
- Number of sick animals
- Number of dead animals
- Species

### Wildlife
- Date of wildlife incident
- Location of wildlife incident
- Species
- Number of dead animals

## Knowledge Graph Schema (entity → category)

```yaml
parameter_category:
  - id: general
    color: "#5BA3D0"
  - id: human
    color: "#1F3A93"
  - id: severity_marker
    color: "#1F3A93"
    parent: human
  - id: exposure
    color: "#E84A7A"
  - id: auxiliary
    color: "#E6C36A"
  - id: environmental
    color: "#4CAF50"
  - id: livestock
    color: "#C2185B"
  - id: wildlife
    color: "#6A1B9A"
```

## Attribution
- The University of Arizona, Mel & Enid Zuckerman College of Public Health
- Global Health Institute
- Ending Pandemics Academy
