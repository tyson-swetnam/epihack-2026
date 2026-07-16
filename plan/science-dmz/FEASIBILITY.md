# Feasibility Evaluation — UNM CARC × BigByte Science DMZ

**Date:** July 2026 · **Status:** planning evaluation, not as-built
**Companion files:** [`network-concept.html`](network-concept.html) (topology diagram) · [`feasibility-evaluation.html`](feasibility-evaluation.html) (full report with risk matrix)

**Method.** 20-agent deep-research run (540 web lookups): six sourced research sweeps — hardware pricing, circuits/recurring costs, staffing benchmarks, NSF CC* precedents, HIPAA/Medical-Science-DMZ requirements, UNM-specific facts — each independently and adversarially fact-checked; four synthesis passes (risk register, SWOT, cost model, staffing model); an integrating verdict; and a completeness critique whose two critical findings were researched and folded back in.

---

## Verdict: feasible, with conditions

The engineering is sound and well-precedented: the no-inline-firewall design is ESnet's canonical Science DMZ pattern, the HIPAA VRF maps onto the peer-reviewed Medical Science DMZ (Peisert et al., *JAMIA* 25(3):267–274) running in production at Indiana, Harvard, and U Chicago, and off-campus R&E siting has a real precedent chain (UNR Pronghorn at Switch Citadel; PNWGP in Seattle's Westin Building; FRGP in Denver). Nothing discovered makes the build infeasible.

Three verified findings gate everything:

1. **Fiber.** The "LoboNet = UNM fiber at BigByte" premise is refuted; the metro span must be leased new, and the *real* bandwidth bottleneck is CARC's ~10G campus DMZ segment, not the WAN.
2. **Funding.** Corrected capex (~$614K–$1.13M) straddles the $700K CC* Area-1 ceiling, and no CC* solicitation is open as of July 2026. The plan only closes as a funding stack.
3. **Staffing.** The three open roles cannot deliver the stated service; steady state needs ~3.85 UNM FTE including two genuinely new hires, plus a pay-band fix and an honest business-hours SLO.

If the top three go/no-go conditions below cannot be satisfied, re-scope (campus or H5/505 Marquette siting; regional framing at the $1.4M ceiling) rather than proceed on current assumptions.

---

## What adversarial verification overturned

These corrections are baked into every number below and must be fixed in any external-facing concept document:

| # | Claim in concept | Verified finding |
|---|---|---|
| 1 | "LoboNet" at BigByte is UNM fiber | It is **Lobo Internet Services Ltd.** (lobo.net, AS11996), a commercial ABQ ISP. No UNM strands found at 123 Central Ave NW. Budget a new dark-fiber lease: $500–2,500/mo per pair + $2–10K NRC, 14–22 weeks provisioning (UPN/Zayo/Lumen on-net). |
| 2 | "Rio Grande GigaPoP" | No such entity. It is the **Albuquerque GigaPoP (ABQG)**, operated by UNM IT, at/near the H5 carrier hotel (505 Marquette), 3–5 blocks from BigByte. Internet2's 400G node in ABQ is upstream. |
| 3 | UNM WAN is ~10G | **UNM already has 100G** to ESnet and WRN via ABQG. The bottleneck is **CARC's ~10G campus Science-DMZ segment** (2014 CC*IIE vintage) — an explicit costed upgrade work package is required. |
| 4 | 40–60% edu discount | **16–35%** off list is what's documented (Arista TX DIR sheet: 16.00%). Deeper cuts need negotiated deal registration and cannot be assumed in a grant budget. |
| 5 | OSN pod: 1.5 PB, $10K/yr fee | ~**1.4 PB usable**; the **$10K/yr fee appears in no public OSN document** — confirm in writing. Pod: ~$90K hardware, 7U, 4.1 kW, 6-month deactivation notice. |
| 6 | NSF CC* as funding vehicle | **No open solicitation as of July 2026** (24-530 deadlines passed 2024; June-2026 announcements are FY2024-cycle awards). |
| 7 | BigByte "Tier III / 2N+1" | Self-declared; no Uptime certification found; listings show a **single 8,000-gal generator**. SOC 2 Type 2 + power diligence required before contract. |

---

## Networking hardware cost estimate

Education pricing at 16–35% off list, 2026 USD. Excludes the OSN pod (~$90K, externally funded), the CyVerse K8s cluster (CyVerse-funded), and salaries. **Includes the campus-side MACsec terminator the original design was missing** (MACsec is hop-by-hop; the completeness critique found both MACsec routers at BigByte with nothing to terminate the HIPAA VRF at the campus end — the 7050X3-class extension switch cannot do it).

### Capital expenditure

| Item | Qty | Low | High | Notes |
|---|---:|---:|---:|---|
| Border router pair, deep-buffer + MACsec (Arista 7280CR3MK-32D4S class) | 2 | $132,000 | $174,000 | List ~$103K ea (TX DIR); collapses border BGP + deep buffers + MACsec |
| DMZ aggregation switch (7280SR3-48YC8 class) | 1 | $15,000 | $25,000 | Deep buffers non-negotiable (ESnet 0.0046%-loss failure mode) |
| CARC campus DMZ extension switch (7050X3 class) | 1 | $12,000 | $20,000 | Open VRF only — no MACsec capability |
| **Campus-side MACsec terminator (3rd 7280CR3MK)** — *added by critique* | 1 | $67,000 | $87,000 | GCM-AES-XPN-256 wire-speed at 100G verified on Arista datasheet |
| MACsec enablement licenses (LIC-FIX-x-MACSEC × 3 devices) | 3 | $12,000 | $54,000 | Quote-only; est. $4–18K net/device |
| 100G gray optics (CWDM4 $209 / LR4 $399) + ~20% spares | 30 | $6,270 | $11,970 | FS.com verified |
| 100G DWDM QSFP28 contingency (only if fiber pairs scarce) | 4 | $12,000 | $26,200 | Drop if 2 dark pairs secured; mux/OADM unpriced |
| Data Transfer Nodes (EPYC/NVMe/CX-7, Globus) | 3 | $90,000 | $189,000 | ESnet reference ≈$63K (May 2026); CC* caps DTNs <15% of budget |
| perfSONAR nodes, 100G-capable (BigByte + CARC) | 2 | $10,000 | $16,000 | The instrument that catches soft failures |
| Zeek IDS workers (flow-shunting architecture) | 3 | $45,000 | $90,000 | Naive 100G needs 4,000+ cores; shunting is mandatory |
| 100G capture NICs (Napatech class + license) | 3 | $24,000 | $45,000 | Quote-only; 30% contingency advised |
| Optical taps / packet broker | 1 | $3,000 | $24,000 | 100G broker ports need HC3-class or used TapAgg |
| HIPAA enclave firewalls (HSC enclave + BigByte cage) | 2 | $80,000 | $160,000 | FG-1800F $40K street (check end-of-order); natural HSC-funded line |
| OOB management (Opengear + LTE, both sites) | 2 | $7,600 | $10,000 | CDW verified |
| Racks, PDUs, cabling at BigByte | 3 | $19,500 | $27,000 | |
| **Hardware subtotal** | | **$535,400** | **$959,200** | |
| Spares pool (~10%) | 1 | $53,500 | $96,000 | 2026 supply: optics ~30% over supply, 12-mo lead times |
| Integration / install / turn-up PS | 1 | $25,000 | $75,000 | Deployment only — CC* discourages consulting for production ops; use EPOC |
| **Total capex** | | **≈ $614,000** | **≈ $1,130,000** | Pre-critique baseline was $526K–$1.03M |

### Annual recurring (non-staff)

| Item | Low/yr | High/yr | Notes |
|---|---:|---:|---|
| Internet2 membership/port delta | $0 | $0 | Sustaining Contribution already paid; no separate 100G port fee |
| ABQG connection / cost-share | $0 | $10,000 | Unverified placeholder — internal UNM cost-share, get a quote |
| Metro dark fiber, BigByte ↔ campus (1–2 pairs) | $6,000 | $60,000 | + one-time NRC $2–10K |
| Cross-connects at BigByte (4–8) | $2,000 | $11,000 | $50–300/mo each |
| Colo rack + power (2–4 racks, 10–20 kW incl. OSN pod) | $24,000 | $60,000 | $150–250/kW/mo planning range; BigByte quote-only |
| Hardware maintenance (10–15% of list) | $40,000 | $90,000 | High end = 24×7×4 on border pair |
| Firewall subscriptions (20–40% of firewall capex) | $16,000 | $64,000 | Natural HSC line |
| OSN fee + pod disk replacements | $10,500 | $12,000 | Fee unverified; disks $400–980 in 2026 HDD shortage |
| Optics refresh + OOB LTE | $3,000 | $7,000 | |
| **Total modeled opex** | **≈ $102,000** | **≈ $314,000** | |

**Known unpriced items:** Globus subscription tier for the S3 connector (check whether OSN's covers UNM-operated endpoints); annual pen test + semi-annual vuln scans for the PHI scope ($15–50K/yr); Zeek log storage + SIEM ingest licensing; the ABQG↔BigByte 2×100G span itself (505 Marquette cross-connects, any DWDM mux); campus inside-plant fiber (demarc → CARC, demarc → HSC MACsec endpoint); DDoS mitigation via ABQG/Internet2.

**Funding fit:** both capex ends bracket the $700K CC* Area-1 ceiling; even stripped of the HSC tier, ~$790K+ remains at worst-case pricing — phasing is asserted but not yet demonstrated numerically. Realistic architecture: CC* successor (open-DMZ core) + HSC institutional funds (HIPAA tier, outside the grant — 24-530 prohibits voluntary cost sharing) + RIO-NM EPSCoR CI Core + signed multi-year O&M commitment. Regional framing with NMSU/NM Tech unlocks the $1.4M ceiling.

---

## FTE staffing estimate — CARC, HSC, Central Campus IT

Steady-state (year 2+) fractions; build phase (year 0–1) runs ~25% hotter (≈4.8–5.25 FTE; the two model figures disagree by ~0.45 FTE — reconcile). Fringe: 46.79% main campus FY26 (→ ~48.6% FY28); ~40% HSC (verify against the HSC fringe memo).

| Org | Role | FTE | Salary (FT) | Loaded/yr | Maps to |
|---|---|---:|---:|---:|---|
| CARC | IT Manager — service owner, contracts, procurement, grant reporting | 0.25 | $105–140K | $39–51K | IT Manager (open) |
| CARC | **Senior Network Engineer** — BGP/ABQG, fabric, MACsec rollover, perfSONAR | 0.75 | $95–130K | $105–143K | **NEW HIRE** — Grade-14 band is 20–45% under market; reclass required |
| CARC | HPC Engineer — DTN/Globus, extension switch, HPC↔S3 path | 0.50 | $100–135K | $73–99K | HPC Engineer (open) |
| CARC | DevOps/Security — Zeek shunting + triage, ACL change mgmt | 0.50 | $85–115K | $62–84K | DevOps/Sec split (open) |
| CARC | Ops technician — remote-hands coordination, OSN disk swaps | 0.10 | $58.5–84K | $7–11K | Existing staff |
| Central IT | DevOps/Security — SOC integration, IR, vuln mgmt (⚠ possible double-count of the single split role — resolve in MOU) | 0.50 | $85–115K | $62–84K | DevOps/Sec split (open) |
| Central IT | Network engineer (ABQG) — handoff, fiber procurement/acceptance | 0.25 | $85–120K | $31–44K | Existing staff |
| HSC | **Secure-enclave systems/firewall engineer** — MACsec endpoint, NGFW pair, cage | 0.75 | $102–150K | $107–158K | **NEW HIRE** (HSC-funded; matches HSC's own HPC Cloud Engineer posting) |
| HSC | HIPAA compliance analyst — risk analysis, access reviews, BAA lifecycle (steps to ~0.5 FTE at NPRM finalization ~2027) | 0.25 | $85–115K | $30–40K | Existing staff (pooled) |
| **UNM total** | | **3.85** | | **≈ $515–715K** | **2 new hires required** |

*Context (not UNM payroll):* CyVerse RSE team (2 FTE + 4–6 grant RSEs) operates the K8s cluster — soft-money continuity risk; OSN DevOps operates the Ceph pod remotely.

**Coverage gaps to own honestly:** 24/7 is unstaffable (SRE math needs ≥8 in rotation vs ~2.6 open-side FTE) — declare a business-hours SLO; bus factor 1 on BGP/MACsec and on Globus internals; recruiting at UNM's classified band is the single most likely failure mode; Zeek triage is business-hours only — route alerts to Central IT's 24/7 SOC; HSC compliance under-water from 2027 (NPRM cadences, pen-test procurement unfunded); EPOC and CyVerse RSEs are grant-contingent. Incremental cash for the two new hires: **≈ $212–301K/yr loaded**.

---

## Risk register (23 risks, sorted by score)

L = likelihood, I = impact (1–5), S = L×I. R-23 added by the completeness critique.

| ID | Cat | Risk (mitigation summary) | L | I | S | Owner |
|---|---|---|--:|--:|--:|---|
| R-01 | network | "LoboNet at BigByte" is not UNM fiber → new dark-fiber lease, +14–22 wks. *(Written confirmation in 30 days; budget UPN/Zayo/Lumen pair; RFP month 1.)* | 5 | 4 | 20 | Central IT |
| R-02 | network | CARC's ~10G campus segment voids the line-rate premise. *(Explicit costed 100G work package, sequenced first; perfSONAR-validate end-to-end.)* | 4 | 4 | 16 | Joint |
| R-08 | funding | No open CC* solicitation. *(Monthly OAC watch; submission-ready proposal; RIO-NM/HSC/institutional bridge; PO conversation.)* | 4 | 4 | 16 | CARC |
| R-12 | staffing | Pay bands can't recruit 100G-DMZ talent. *(Reclass/market exception before recruiting; grant-funded yrs 1–2 with written pickup.)* | 4 | 4 | 16 | CARC |
| R-21 | governance | Three-org seams + two external operators, no operating agreement. *(Three-party MOU with device-class RACI, key custody, cost allocation, before ordering; governance board.)* | 4 | 4 | 16 | Joint |
| R-23 | security | CyVerse K8s on the firewall-free fabric contradicts the minimized-attack-surface argument. *(Own VRF + dedicated ACLs; NRP-style in-cluster enforcement — Calico default-deny, egress allowlists, admission control, Falco → SOC; NIST 800-53 compensating controls; orphaned-tenant clause.)* | 4 | 4 | 16 | Joint |
| R-13 | staffing | 3-person team can't do 24/7. *(Business-hours SLO in service definition and tenant agreements; after-hours pages → BigByte remote hands; HSC funds its own tier if it needs 24/7.)* | 5 | 3 | 15 | IT Manager |
| R-15 | compliance | No PHI at BigByte before an executed BAA (conduit exception closed; 6–8+ wks). *(Start negotiation in parallel; hard gate = BAA + SOC 2; sequence open DMZ first.)* | 3 | 5 | 15 | HSC |
| R-09 | funding | BOM exceeds CC* ceiling at real discounts; DTNs capped <15%. *(Phase: CC* open core, HSC tier outside grant; demonstrate the phased budget numerically.)* | 4 | 3 | 12 | Joint |
| R-11 | funding | Recurring costs not CC*-fundable — reconciled ~$102–314K/yr + staff. *(Signed multi-year CIO+HSC O&M commitment in the Campus CI Plan, ≈$315–615K/yr incl. net-new staff.)* | 4 | 3 | 12 | Joint |
| R-16 | compliance | HIPAA NPRM makes addressable controls mandatory (~Jul 2027). *(Design to NPRM now; budget scan/pen-test/restore cadences from year one.)* | 4 | 3 | 12 | HSC |
| R-20 | schedule | Stacked lead times → 12–18 months. *(RFPs month 1; cooperative contracts; order long-lead optics first + spares; 10–15% contingency.)* | 4 | 3 | 12 | IT Manager |
| R-18 | security | CISO/HSC-ISO veto of no-inline-firewall. *(Engage before costing; present Medical Science DMZ + NIST 800-66r2 + compensating controls; written sign-off; resolve R-23 first.)* | 3 | 4 | 12 | Joint |
| R-17 | compliance | Hybrid-entity mis-designation / enclave isolation failure (UMass $650K pattern). *(Formal designation pre-go-live; technically enforced no-route; pen test + quarterly audits; 6-yr retention.)* | 2 | 5 | 10 | HSC |
| R-03 | network | Soft failures silently kill throughput (ESnet 1-in-22,000-loss case). *(perfSONAR meshes + alerting day one; deep buffers end-to-end; EPOC enrollment.)* | 3 | 3 | 9 | CARC |
| R-10 | funding | Commercial-colo siting is a novel CC* reading. *(Argue on merits + precedents; cover in PO conversation; campus fallback; consider regional $1.4M.)* | 3 | 3 | 9 | CARC |
| R-14 | staffing | 50/50 security split erodes. *(Signed MOU with named person/duties; quarterly utilization review; backfill trigger.)* | 3 | 3 | 9 | Joint |
| R-19 | security | Zeek only viable with flow shunting; least-priced subsystem. *(Firm quotes + 30% contingency; documented shunting policy in the risk analysis; alerts → SIEM.)* | 3 | 3 | 9 | IT Manager |
| R-05 | facility | BigByte resilience unproven (single generator listed; PNM outages rising). *(SOC 2 Type 2 + power diligence before signing; SLA credits; H5 as DR option.)* | 2 | 4 | 8 | Joint |
| R-06 | vendor | Single-facility small-business dependency. *(Disclosure, 12-mo notice, assignment protections, remote-hands SLAs; rehearsed lift-and-shift runbook.)* | 2 | 4 | 8 | IT Manager |
| R-07 | vendor | OSN terms partly unverified ($10K fee; 1.4 PB; 6-mo deactivation). *(Written agreement; disk budget with shortage buffer; fallback plan.)* | 3 | 2 | 6 | CARC |
| R-22 | security | MACsec traps: XPN-256 mandatory at 100G; license-gated platforms; wire-only coverage. *(7280CR3MK-class with MACsec in PHY; scripted CAK rollover; at-rest encryption as separate control.)* | 3 | 2 | 6 | HSC |
| R-04 | network | ABQG handoff capacity/cost-share unpriced. *(Internal negotiation early, cost-share in writing; brief Internet2/WRN on the 10 PiB/mo profile.)* | 2 | 3 | 6 | Central IT |

---

## SWOT

**Strengths.** Proven ESnet + Medical Science DMZ patterns (citable, production-tested) · UNM operates ABQG and already has 100G WAN · repeat CC* awardee (CC*IIE 2014 ~$498K built the first DMZ; CC*DNI; SAMPRA) · storage/platform layers offloaded to OSN and CyVerse · HSC cost-share with NPRM-ready VRF separation · colo footprint trivially fits BigByte's 15,000 sqft / 3 MW plant.

**Weaknesses.** LoboNet fiber premise wrong (span must be leased) · staffing can't deliver the implied SLO (2 new hires; pay bands under market; 24/7 impossible) · capex likely exceeds the CC* ceiling at verified discounts · concept doc contains verified errors (credibility risk) · campus 10G segment undermines the line-rate pitch · 46.79%→49.5% fringe inflates every FTE.

**Opportunities.** CC* text explicitly permits centralized/aggregated Science DMZs — the hook for colo siting, possibly first-mover regional at $1.4M · RIO-NM EPSCoR ($8M, UNM-led, CI Core) as funding-stack partner · EPOC free operational depth (~0.25 FTE offset) · strong precedent cluster (UNR/Switch, PNWGP/Westin, FRGP/Denver, ASU $494K, LSU HSC medical DMZ) · downtown interconnect density (H5 3–5 blocks; ABQIX on-site; $50–300/mo cross-connects) · Internet2 costs sunk.

**Threats.** No open CC* solicitation · BigByte single-vendor fragility (1–10 employees, one facility, one listed generator) · supply chain + NM procurement stack to 12–18 months · HIPAA rules tighten ~2027 (OCR history: UMass $650K, OSU-CHS $875K, URMC $3M) · real discounts half the assumption · downtown grid/seismic exposure with everything in one facility, DR unpriced.

---

## Go/no-go conditions (priority order)

1. Secure the funding stack (PO conversation on CC* successor timing; HSC funds the HIPAA tier outside the grant; RIO-NM alignment) before any procurement.
2. Resolve the metro fiber question in writing within 30 days; budget the commercial lease and start its RFP immediately on award.
3. Signed multi-year CIO + HSC O&M and staffing commitment (~$315–615K/yr incl. net-new staff) in the mandatory Campus CI Plan.
4. Fix staffing pre-submission: network-engineer reclass; both new hires committed; 50/50 split as signed MOU; business-hours SLO declared.
5. CARC campus-side 100G upgrade as an explicit costed work package.
6. Gate all PHI work on: executed BAA, SOC 2 Type 2 + power diligence, hybrid-entity designation, written CISO + HSC ISO sign-off.
7. Re-baseline at 16–35% off list; firm quotes for all quote-only items; OSN fee in writing.
8. Harden the BigByte contract (disclosure, notice, assignment, SLAs, H5 relocation path).
9. Three-party operating MOU executed before equipment is ordered.
10. Correct the concept document's verified errors before external use.

## Critical path (≈12–18 months from award to full service)

1. Fiber + CARC uplink confirmation in writing — 2–4 wks
2. NSF OAC program-officer conversation — 4–8 wks, start now
3. CISO + HSC ISO engagement on compensating controls — 6–10 wks, parallel
4. Firm quotes + re-baselined budget — 6–8 wks, parallel
5. Executive commitments (O&M MOU, governance MOU, reclass) — 8–12 wks
6. Submission-ready proposal, held for the solicitation — 4–6 wks + unknown wait
7. Award month 1: fiber-lease RFP + switch/optics procurement (3–6 mo competition; 6–12 mo lead times — long-lead first, with spares)
8. Parallel: fiber provisioning 14–22 wks; BAA + diligence 6–10 wks; recruiting 3–6 mo
9. Open DMZ + CARC 100G segment build; perfSONAR mesh validation + EPOC enrollment before declaring service — 2–3 mo after hardware/fiber
10. HSC HIPAA tier second: cage fit-out, MACsec turn-up, enclave firewalls, designation, pen test — +3–6 mo after BAA

## Kill criteria

- No usable metro fiber path at ≤ ~$5K/mo → re-site to H5 or campus.
- BigByte refuses the BAA or fails SOC 2/power diligence → kill the HSC cage there even if the open DMZ proceeds.
- CISO/HSC ISO mandate an inline stateful firewall on the science path → redesign or stop.
- No CC* successor within ~12 months and no bridge funding → shelve.
- CIO/HSC decline the multi-year O&M commitment → stop.
- Network engineer unhireable at market after two cycles → do not go live at bus-factor zero.
- Re-verified capex > ~$1.0M with no phasing path under $700K → rescope regional or shrink to a campus-anchored single-router design.
- ABQG/Internet2 cannot absorb the 10 PiB/month profile without unbudgeted augmentation → re-scope tenant commitments.

---

## Caveats

Quote-only items (capture NICs, taps/broker, BigByte rack rates, ABQG cost-shares, MACsec licenses) are derived estimates. The staffing model's build-phase total has a ~0.45 FTE internal inconsistency to reconcile. The Central-IT half of the security split may be double-counted vs the concept's single split role. HSC's ~40% fringe needs verification. Enclave firewalls (10–40G) vs the 100G VRF is an unacknowledged sizing decision pending an HSC workload analysis. All figures 2026 USD, no out-year escalation.

**Key primary sources:** ESnet fasterdata (DTN reference ≈$63K May 2026; Science DMZ security model); NSF 24-530 (ceilings, DTN <15% guidance, cost-share prohibition); Arista TX-DIR price sheet + 7280R3-MACsec datasheet; OSN hosting guidelines; HHS OCR enforcement records; NRP/Nautilus admin documentation; NSA/CISA Kubernetes Hardening Guide; UNM OSP fringe memos; NMSA 13-1-125.
