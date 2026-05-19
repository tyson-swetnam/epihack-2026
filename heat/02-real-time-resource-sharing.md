---
id: heat-q2-real-time-resource-sharing
title: Q2 — Do cooling centers share resources in real-time?
group: heat
question_number: 2
question_text: "Do cooling centers share resources in real-time with each other, e.g., we have no space; we are short on water?"
domain: one_health
tags: [cooling-centers, real-time, coordination, resource-sharing, logistics]
---

# Q2 — Real-time resource sharing between cooling centers

> **Do cooling centers share resources in real-time with each other,
> e.g., we have no space; we are short on water?**

## Starting context

The honest answer in 2026 is: **mostly no**, with notable exceptions.

### What already exists

- The **MAG Heat Relief Network** coordinates the network at the
  *regional* level — onboarding sites, publishing locations, and
  distributing donated supplies. MAG runs an
  [annual resource-collection drive](https://azmag.gov/Programs/Heat-Relief-Network/Resources)
  for water bottles, hats, sunscreen, electrolyte packets, and
  lightweight clothing.
- The **City of Phoenix Office of Heat Response and Mitigation**
  (OHRM / HeatReadyPHX) coordinates city-operated centers and
  partners with municipal libraries, parks and recreation, and
  community-based organizations.
- **211 Arizona** functions as a *human* router — operators see open
  centers and can refer a caller to an alternate location if their
  nearest one is full or closed.
- The **Clear Channel Outdoor + Maricopa County** digital-billboard
  partnership can update messaging within a few hours.

### What is mostly absent

- A standing **machine-readable, real-time feed** of:
  - current occupancy / available seats per center,
  - supplies on hand (water, ice, ORS packets),
  - service hours overrides (e.g. a center closed today due to a power
    outage),
  - pet-availability today,
  - cross-center transportation availability.
- A standardized **inter-center communication channel** (most
  coordination still happens via phone and email).

## Data-model sketch (for the participatory system)

A `cooling_center_status` event from a site operator could carry:

| Field | Example |
|---|---|
| `center_id` | `mag.hrn.0473` |
| `as_of` | `2026-07-18T14:05:00-07:00` |
| `is_open` | `true` |
| `seats_available` | `12` |
| `pets_ok_today` | `true` |
| `water_status` | `low` (`ok` \| `low` \| `out`) |
| `ice_status` | `out` |
| `transport_available` | `false` |
| `notes` | "AC unit struggling, room temp 82 °F" |

Aggregated and published as an open GeoJSON/Parquet feed, this would
power both the public map (Q1) and operator dashboards.

## Technology options

| Approach | Trade-off |
|---|---|
| Lightweight web form / SMS short-code for site operators to post status each shift | Easy to adopt; relies on humans remembering |
| QR-code "open-shift / close-shift" check-in for staff | Captures hours-of-operation automatically |
| IoT temperature + occupancy sensors at participating centers | Highest fidelity; capex and connectivity required |
| Federated mutual-aid app between centers | Adds peer-to-peer logistics (water transfers) |

## See also

- [Q1 — Cooling-center awareness](./01-public-awareness-cooling-centers.md)
- [Q3 — Heat-safety education](./03-heat-safety-education.md)
- [Resources — full catalog](./resources.md)
