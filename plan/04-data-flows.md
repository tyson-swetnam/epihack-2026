---
title: "Plan 04 — End-to-end data flows"
---

# 04 — End-to-end data flows

Four worked scenarios, one per persona × vertical. Each shows the
Minimum-Dataset fields populated, the MCPs called, the agents
invoked, and the Figure 3 timeliness milestones triggered.

---

## Scenario A — Hiker mails in a tick

**Persona:** Recreational hiker, age 38, has a tick attached after
a weekend hike near Patagonia (Santa Cruz County).

**Channel:** Mobile app.

### Steps

1. **User opens the app.** "Submit a tick" flow.
2. Camera capture of the tick on a coin for scale. App-side
   client-side ML estimates engorgement; user enters date attached,
   approximate hours attached, location on body.
3. **Intake Agent** populates the Minimum Dataset:
   - General: age, sex, ZIP, GPS coordinates, date of report.
   - Exposure: tick bite, attached for ~6 h, leg.
   - Auxiliary: photo of tick.
4. **Geo-Enrichment Agent** resolves GPS → `county.santa_cruz`,
   not on a reservation; pulls
   `vectorsurv-mcp.agency_region_intersect` to find the responsible
   county vector-control agency.
5. **Validation Agent** photo-quality check passes; species
   tentatively identified as *Rhipicephalus sanguineus* (brown dog
   tick) but with low confidence — flagged for Walker lab.
6. **Triage Agent (VBD branch):**
   - Matches `vector.rhipicephalus_sanguineus → transmittedBy →
     pathogen.rickettsia_rickettsii (RMSF)` from
     `schema/deep/pathogens.sql`.
   - No symptoms reported; triage class = `mail-tick-to-walker-lab`
     + `self-monitor-for-14-days`.
7. **Enrichment Agent:**
   - `great-az-tick-check-mcp.create_submission(user, tick_meta)`
     returns a mailing label PDF.
   - `vectorsurv-mcp.get_pools(arthropod="tick", county=Santa Cruz,
     last 90 days)` — nothing reported nearby, so no live signal.
   - Looks up `schema/deep/outbreaks.sql` for any active RMSF
     event — historical tribal-lands cluster noted but not active
     near Patagonia.
8. **Persistence:** observation node lands with edges to
   `pathogen.rickettsia_rickettsii`, `county.santa_cruz`,
   `resource.ua_extension_tickcheck`, and `focus.rmsf`.
9. **Notification Agent:** in-app card with the mailing label, an
   ICD-10 reference (`A77.0`), a 14-day symptom watchlist, and a
   one-tap "if symptoms appear" booking link.

### Milestones triggered
- *Detect* — at step 2 (community reported a tick exposure).
- *Verify* (potential, deferred) — when Walker lab returns species
  + pathogen results, the Knowledge Update Agent ingests the
  result and edges the observation to a `lab_result` node.

---

## Scenario B — Symptomatic patient calls 211

**Persona:** Construction worker, age 52, Phoenix, fevers + severe
muscle aches for 3 days, no obvious bite memory.

**Channel:** Voice via 211 Arizona (transcribed by a downstream
voice-MCP).

### Steps

1. **211 operator** opens the worker's intake on the Sentinel
   web console; voice transcript streams in.
2. **Intake Agent** extracts:
   - General: age, sex (M), Phoenix ZIP, occupation = construction.
   - Human: fever, severe muscle aches, mild headache, 3-day onset,
     has not sought care.
   - Exposure: outdoor occupation, no remembered bite, no recent
     travel.
3. **Geo-Enrichment Agent:** `county.maricopa`.
4. **Validation Agent:** no duplicate report; flagged as "symptomatic,
   no exposure history — open differential."
5. **Triage Agent (VBD branch):**
   - Symptoms match WNV, dengue (low likelihood given no travel),
     and — importantly — **leptospirosis** (occupational exposure).
   - Calls `vectorsurv-mcp.get_pools(target_acronym="WNV",
     county=Maricopa, last 30 days)` — WNV pool positivity at
     **8.2 per 1000** in nearby ZCTAs, well above threshold.
6. **Enrichment Agent:**
   - Attaches the live WNV vector-index reading.
   - Calls `adhs-mcp.recent_cases("WNV", Maricopa)` — confirms
     uptick.
   - Calls `knowledge-graph-mcp.outbreak_check("WNV", Maricopa)` —
     edges to a fresh `outbreak.maricopa_wnv_2026` if one exists.
7. **Triage class = `urgent-care` + `clinician-alert-WNV`.**
8. **Notification Agent:**
   - Worker: "Given your symptoms and current WNV activity in
     Maricopa, please go to an urgent care or ED today. Here is
     the nearest one open now." (One-tap call + directions.)
   - 211 operator: same in real time.
   - **Agency channel:** an aggregated pin on the MCDPH analyst
     dashboard, no PII.

### Milestones triggered
- *Detect* — symptom onset 3 days ago (computed from date-of-
  illness field).
- *Notify* — the agency dashboard pin is the local Notify event;
  Maricopa Vector Control is paged if cluster threshold reached.
- The interval *Detect → Notify* lands in the `agent_run` audit
  table; this is the headline metric.

---

## Scenario C — Unsheltered resident heat check-in

**Persona:** Unsheltered resident, no phone, downtown Phoenix on a
115 °F Magenta-HeatRisk day. CHW is doing block-by-block outreach
with a tablet.

**Channel:** CHW-mediated, on the CHW's tablet.

### Steps

1. **CHW** opens the Sentinel field app; "Heat check-in" flow.
2. CHW enters: approximate age, sex, currently unsheltered,
   sweating profusely but mentation intact, no chronic medications
   reported, last drank water ~3 h ago, current GPS.
3. **Intake Agent** suppresses Email, Phone, Household member ID
   per the anonymous-outreach consent profile.
4. **Geo-Enrichment Agent:** ZCTA 85003.
5. **Validation Agent:** accepts; flags as
   "high-risk-population observation."
6. **Triage Agent (Heat branch):**
   - Computes vulnerability score: unsheltered (+3),
     outdoor-exposure (+2), no AC (+2), Magenta HeatRisk (+3),
     symptomatic (heat exhaustion: heavy sweat + headache, +2).
     Total = **12** (max ~15).
   - Calls `nws-heatrisk-mcp.heatrisk(lat,lon,today)` =
     **Magenta** (highest level).
7. **Enrichment Agent:**
   - `mag-hrn-mcp.search_centers(lat, lon, radius=2km,
     open_now=true, pets_ok=false)` → 4 results.
   - `211-az-mcp.transport_to_cooling_center(zip, urgency="high")`
     → ride dispatch available.
8. **Triage class = `go-to-cooling-center` + `dispatch-CHW-transport`.**
9. **Notification Agent:**
   - CHW: card with the nearest center + a one-tap "request
     transport" button.
   - Center operator: a heads-up message via `mag-hrn-mcp`
     (peer-to-peer between operators).
   - Aggregated: observation lands in the Cluster Detection
     Agent's stream — five unsheltered heat-exhaustion check-ins
     in the same ZCTA in 2 h triggers a county heat-emergency
     alert.

### Milestones triggered
- *Predict* — the Magenta HeatRisk forecast 24 h prior was the
  predictive alert.
- *Prevent* — the CHW outreach happening in response to the
  Magenta forecast is itself the Prevent action.
- *Detect → Respond* interval is what this scenario optimizes.

---

## Scenario D — Agency-side cluster review

**Persona:** ADHS Vector-Borne & Zoonotic Diseases epidemiologist,
end of week.

**Channel:** Agency web dashboard.

### Steps

1. The **Cluster Detection Agent** ran nightly and flagged a
   small but unusual cluster: 4 hantavirus-compatible observations
   in Coconino County over the last 10 days, mostly from CHW
   check-ins in tribal communities.
2. **Notification Agent** wrote a row to the ADHS analyst queue
   (no PHI exposed to the wider system).
3. **Epi opens the dashboard** — sees the cluster overlaid on
   the [MapLibre map](../map/) (every pin carries
   `kg_node_id`; clicking opens the underlying observation
   with its source MCP receipts).
4. Dashboard queries (plain SQL against the kg):

```sql
-- Co-located WHISPers wildlife mortality events
SELECT w.label, w.description, p.value_text AS event_date
FROM   kg.node w
JOIN   kg.property p ON p.node_id = w.node_id AND p.key = 'event_date'
WHERE  w.node_type = 'whispers_event'
  AND  w.node_id IN (
    SELECT object_id FROM kg.edge
    WHERE subject_id IN (SELECT node_id FROM cluster_observations)
      AND predicate = 'colocatedWith'
  );

-- Recent NEON small-mammal data near the cluster
SELECT * FROM kg.v_datasets_apis
WHERE  resource_id = 'program.neon_srer'
  AND  informs_questions LIKE '%hantavirus%';
```

5. Epi clicks "open Verify workflow" — the Knowledge Update Agent
   pulls the latest ADHS hantavirus-case report via `adhs-mcp` and
   the latest NEON rodent-pathogen testing via a future
   `neon-mcp`, both edged to the cluster.
6. **Decision:** field investigation dispatched. The dispatch is
   itself a `Verify` milestone event, written back to the kg via
   `knowledge-graph-mcp`.
7. The **Figure 3 timeliness clock** for this potential outbreak
   now has Detect (community check-in), Notify (agency queue), and
   Verify (field dispatch) timestamps. *Lab Confirmation* and
   *Respond* will follow.

### Why this is a "living database" scenario

Nothing in this flow was bespoke. The cluster detector ran on the
same `observation` table community reports land in; the dashboard
queries were the same recursive-CTE patterns used by the
[knowledge-graph viewer](../graph/); the MCP pulls were the same
ones the Intake Agent uses live. The agency epi got an end-to-end
investigative workspace without anyone writing a new ETL job.
