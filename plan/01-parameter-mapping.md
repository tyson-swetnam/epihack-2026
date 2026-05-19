---
title: "Plan 01 — Mapping the Minimum Dataset to VBD and Heat"
---

# 01 — Parameter mapping

The Minimum Set of Key Data Parameters in
[Figure 2](../figures/02-minimum-key-data-parameters.html) is the
shared data contract for both verticals. This page enumerates which
parameters apply, which need vertical-specific extensions, and how
each lands in the DuckLake knowledge graph as a column or as an
edge / property on an `observation` node.

## Observation node, in one place

Every report from a community user, every record pulled from an MCP
server, and every agency case becomes a row whose canonical type is
`observation` and whose properties are drawn from the eight Figure 2
parameter classes plus the per-vertical extensions below.

```
observation.<uuid>
  ├── kind = "report" | "mcp_pull" | "agency_case"
  ├── vertical = "vbd" | "heat"
  ├── source = "mobile" | "sms" | "voice" | "vectorsurv" | "nws_heatrisk" | …
  ├── (General properties — same for both verticals)
  ├── (Human properties — vertical-specific symptom set)
  ├── (Exposure properties — vertical-specific risk factors)
  ├── (Auxiliary properties — photo / digital biomarker / lab)
  ├── (Environmental properties — vertical-specific)
  └── edges to: pathogen.*, focus.*, county.*, tribe.*, outbreak.*,
                resource.*, population.*  (existing kg nodes)
```

## Class-by-class mapping

### General class — identical contract, both verticals

| Figure 2 param | VBD use | Heat use | DuckLake landing |
|---|---|---|---|
| Age | Risk stratification (children, elderly) | Vulnerability score (65+) | `kg.property(observation.X, "age", value_num)` |
| Sex | Demographic | Demographic (81% of Maricopa heat deaths are male) | `…, "sex", value_text` |
| Email | Channel for results | Optional (anonymous-friendly) | `…, "contact_email"` |
| Unique ID | Stable identifier for follow-up | Same | `kg.node.node_id` (uuid) |
| Occupation | Outdoor work = WNV/tick risk | Outdoor work = heat risk (OSHA) | `…, "occupation"` |
| Date of report | Drives Figure 3 milestones | Same | `…, "reported_at", value_text` (ISO) |
| Postal code | County / tribe resolution | Cooling-center proximity | `…, "postal_code"` |
| Phone number | SMS fallback | 211 referral | `…, "contact_phone"` |
| Household member ID | Tick-shared-with-pet detection | "Are others in your home at risk?" | edge `observation → relatesTo → observation` |
| Geographical coordinates | Map / cluster detection | Cooling-center routing | `…, "lat"`, `…, "lon"` + edge to `county.*`, `tribe.*` |

### Human class — diverges by vertical

| Figure 2 param | VBD | Heat |
|---|---|---|
| No symptoms | ✓ (asymptomatic check-in) | ✓ ("just checking in" for unsheltered) |
| Symptoms (general) | ✓ | ✓ |
| Date of illness | ✓ — *clock starts here for Detect→Notify* | ✓ |
| Cough / congestion | ✓ (WNV neuro) | — |
| Nausea / vomiting | ✓ | ✓ (heat exhaustion) |
| Difficulty breathing | ✓ (hantavirus, severe WNV) | ✓ (heat stroke) |
| Sore throat | ✓ | — |
| Rash | ✓ (RMSF, dengue) | — |
| Fever | ✓ | ✓ (heat stroke ≥ 104 °F) |
| Chills | ✓ | — |
| Diarrhea | ✓ | — |
| **Bleeding from body openings** *(severity marker)* | ✓ | — |
| Red eyes | ✓ (dengue, leptospirosis) | — |
| Muscle / body aches | ✓ | ✓ |
| **Discolored / bloody urine** *(severity marker)* | ✓ (leptospirosis, severe RMSF) | ✓ (rhabdomyolysis) |
| Loss of smell or taste | ✓ | — |
| **Yellow skin / yellow eyes** *(severity marker)* | ✓ (leptospirosis) | — |
| Absent from work / school | ✓ | ✓ |
| Sought health care | ✓ (drives Notify / Verify) | ✓ |
| *Heat-specific additions:* | | |
| Confusion / altered mental status | — | ✓ *(critical heat-stroke indicator)* |
| Stopped sweating / hot dry skin | — | ✓ *(heat stroke)* |
| Heavy sweating | — | ✓ *(heat exhaustion)* |
| Headache | — | ✓ |
| Dizziness / fainting | — | ✓ |
| Muscle cramps | — | ✓ |
| Core body temp (if measured) | — | ✓ *(numeric)* |

### Exposure class — both extend Figure 2 differently

| Figure 2 param | VBD | Heat |
|---|---|---|
| Attending a recent mass gathering | ✓ | ✓ *(also: stadium / outdoor concert in heat)* |
| Tick or insect bite | ✓ *(when, how many, where on body, attached duration)* | — |
| Animal bite | ✓ *(rabies)* | — |
| History of travel | ✓ *(dengue / Zika importation)* | ✓ *(arrived from cooler climate?)* |
| Contact with live animals | ✓ | — |
| Contact with dead or sick animals | ✓ *(plague, tularemia, HPAI)* | — |
| Contact with sick individual / confirmed case | ✓ | — |
| *Heat-specific additions:* | | |
| Time spent outdoors in last 24 h | — | ✓ |
| Access to working AC at home | — | ✓ *(no AC = elevated risk)* |
| Energy / utility security (any disconnect notices?) | — | ✓ |
| Currently sheltered? | — | ✓ *(unsheltered = top risk cohort)* |
| Vehicle access for transport | — | ✓ |
| Occupational heat exposure today | — | ✓ |
| On medications affecting thermoregulation | — | ✓ *(antipsychotics, diuretics, anticholinergics)* |

### Auxiliary class — overlapping but the photo subject is different

| Figure 2 param | VBD | Heat |
|---|---|---|
| Digital biomarker signal | Pulse, body temp from wearable | **Critical:** wearable skin-temp, heart-rate variability, sweat rate |
| Photo | Tick / mosquito / sick animal / rash | Optional (e.g. unsafe heat environment) |
| Diagnostic / lab confirmation | Lab result reference (LOINC) | ED diagnosis code (ICD-10 T67.*) |

The digital-biomarker slot is the single biggest unlock for the
Heat vertical — wearable data crosses the gap between "checking in"
and "you need transport to a cooling center now."

### Environmental class — both heavily extend

| Figure 2 param | VBD | Heat |
|---|---|---|
| Date of environmental incident | ✓ | ✓ |
| Location of vector spotting | ✓ | — |
| Unusual presence of vectors | ✓ | — |
| Density or number of vectors | ✓ | — |
| Flooding | ✓ *(mosquito habitat)* | — |
| Water contamination | ✓ *(leptospirosis)* | — |
| *Heat-specific additions:* | | |
| Ambient temperature (°F) | — | ✓ *(NWS HeatRisk MCP)* |
| Humidity | — | ✓ |
| Heat index | — | ✓ *(computed)* |
| NWS HeatRisk level (Green/Yellow/Orange/Red/Magenta) | — | ✓ |
| Urban-heat-island intensity at user's block | — | ✓ |
| Active extreme-heat watch/warning | — | ✓ |
| *VBD-specific additions:* | | |
| Standing water within X meters | ✓ | — |
| Recent rainfall (mm, last 7 days) | ✓ | — |

### Livestock + Wildlife classes — VBD only

The Livestock and Wildlife classes from Figure 2 are first-class for
VBD (sick / dead animal reports drive zoonotic surveillance) and
silent for Heat. They map to existing edges:

```
observation.X --reportsAbout--> reservoir.deer_mouse
observation.X --reportsAbout--> species.<from kg.deep/pathogens>
observation.X --reportsAbout--> outbreak.<if matches a known event>
```

## Suppression rules

To avoid surveillance creep, the app **does not collect** certain
Figure 2 parameters in some flows:

- **Anonymous heat check-ins** (unsheltered outreach) suppress
  Email, Occupation, Household member ID, and "absent from work /
  school" by default.
- **Tick mail-in** suppresses Human symptom fields unless the
  submitter has been bitten.
- **Wearable-only heat alerts** record only the digital biomarker
  parameter and a coarse geo (ZIP), not name or contact.

Suppression is enforced by the Intake Agent (see
[03-agentic-architecture](./03-agentic-architecture.html)) and
audited via a `consent_profile` property on every observation.

## Knowledge-graph deltas required

Adding the application means seeding a small set of new node types
into `schema/deep/`:

- `node_type = "observation"` (the per-report record).
- `node_type = "symptom"` for the heat-specific symptoms not in
  Figure 2 (confusion, hot-dry-skin, etc.) so they can be mapped to
  SNOMED CT and ICD-10 via the existing `standards.sql` crosswalks.
- `node_type = "exposure_factor"` for the heat-specific exposures
  (AC access, energy insecurity, sheltered status) and VBD-specific
  ones (bite location on body, attachment duration).
- `node_type = "consent_profile"` describing what fields are and
  aren't collected per flow.
- `node_type = "wearable_metric"` for digital-biomarker codes
  (skin_temp_c, hrv_ms, sweat_rate_g_h, etc.).

These additions are documented under
[`05-roadmap.md` Phase 0](./05-roadmap.html).
