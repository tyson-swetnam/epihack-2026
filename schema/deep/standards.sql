-- ============================================================================
-- EpiHack Arizona 2026 -- Interoperability Standards Knowledge Graph
--
-- Encodes the interoperability standards that matter to wildlife / vector /
-- heat surveillance and crosswalks Figure 2 Minimum Dataset parameters and
-- focus-area concepts to canonical codes inside those standards.
--
-- Run *after* schema/knowledge_graph.sql, schema/heat.sql, and
-- schema/wildlife_vectors.sql so that focus.* and param.* node references
-- resolve.
--
-- Conventions:
--   * Adds standard.<slug>, code.icd10.<dotless>, and dwc.<term> nodes.
--   * Predicates introduced here:
--       - definedIn   (code -> standard)
--       - mappedTo    (code / dwc term  ->  focus.* / param.*)
--   * edge_id range reserved for this file: 15000-15999.
--   * All inserts use ON CONFLICT DO NOTHING.
--   * source_fig = 'deep-standards' throughout.
--
-- ICD-10-CM codes below carry the dotted display form in the `code` property
-- and a dotless `node_id` suffix (e.g. T67.0XXA  ->  code.icd10.t670xxa)
-- to keep slugs URL-safe. Display codes preserve the official ICD-10-CM
-- punctuation.
--
-- Note on standards-governance drift worth flagging downstream:
--   * HL7 FHIR R5 was published 2023-03-26; the prior workhorse R4 (2019)
--     is still the version most US payer / public-health systems are
--     certified against (USCDI v3 / v4, CMS interop rules). Expect dual-
--     version mappings for years; this graph anchors on R5 but the
--     `version` property is exposed so we can fork an R4 node later.
--   * DCAT-US v3 (2024) is now the GSA / data.gov baseline, supplanting
--     DCAT-US v1.1.
--   * Darwin Core received a major Latimer-Core companion update in 2024;
--     core terms remain stable.
--   * SNOMED CT International July-2024 release added wildfire-smoke and
--     extreme-heat findings; the US Edition lags by ~6 months.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Standard nodes
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('standard.fhir_r5',
     'standard', 'HL7 FHIR R5',
     'HL7 Fast Healthcare Interoperability Resources, Release 5 (2023). RESTful clinical and public-health data exchange; key resources for surveillance include Observation, Condition, Encounter, Location, Patient, Practitioner, and the public-health resources MeasureReport and MedicinalProductDefinition.',
     'deep-standards'),
  ('standard.omop',
     'standard', 'OMOP Common Data Model',
     'OHDSI Observational Medical Outcomes Partnership CDM v5.4 / v6.0. Person-centric relational schema for population-health analytics across federated EHR / claims datasets.',
     'deep-standards'),
  ('standard.icd10',
     'standard', 'ICD-10-CM',
     'International Classification of Diseases, 10th Revision, Clinical Modification. US clinical diagnostic code set maintained jointly by CDC NCHS and CMS; FY2025 edition effective 2024-10-01.',
     'deep-standards'),
  ('standard.snomed_ct',
     'standard', 'SNOMED CT',
     'Systematized Nomenclature of Medicine -- Clinical Terms. Comprehensive multilingual clinical terminology maintained by SNOMED International; US Edition published by NLM.',
     'deep-standards'),
  ('standard.loinc',
     'standard', 'LOINC',
     'Logical Observation Identifiers Names and Codes. Universal code system for laboratory tests and clinical observations; maintained by Regenstrief Institute.',
     'deep-standards'),
  ('standard.nedss',
     'standard', 'CDC NEDSS Reportable Conditions',
     'National Electronic Disease Surveillance System Base System (NBS) and the Reportable Condition Knowledge Management System (RCKMS) -- canonical list of nationally notifiable conditions and their case-definition rules.',
     'deep-standards'),
  ('standard.dwc',
     'standard', 'Darwin Core',
     'TDWG biodiversity data standard for sharing species-occurrence records; underpins GBIF, iNaturalist, eBird, VertNet, and the Atlas of Living Australia.',
     'deep-standards'),
  ('standard.geosparql',
     'standard', 'OGC GeoSPARQL / OGC API - Features',
     'Open Geospatial Consortium standards: GeoSPARQL 1.1 (RDF + SPARQL for geospatial data) and the OGC API - Features family for serving vector geospatial features over HTTP.',
     'deep-standards'),
  ('standard.schema_org_dataset',
     'standard', 'Schema.org Dataset / DCAT-US 3',
     'Schema.org Dataset vocabulary (used by Google Dataset Search) and DCAT-US v3 (2024), the US federal profile of W3C DCAT for data.gov-compatible dataset metadata.',
     'deep-standards'),
  ('standard.w3c_prov',
     'standard', 'W3C PROV',
     'W3C PROV family (PROV-DM, PROV-O, PROV-N) for representing provenance of entities, activities, and agents; foundational for data-lineage tracking in federated surveillance.',
     'deep-standards')
ON CONFLICT DO NOTHING;

-- Standard properties: URL, version, governing body
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('standard.fhir_r5',            'url','https://hl7.org/fhir/R5/'),
  ('standard.fhir_r5',            'version','5.0.0 (2023-03-26)'),
  ('standard.fhir_r5',            'governing_body','Health Level Seven International (HL7)'),
  ('standard.omop',               'url','https://ohdsi.github.io/CommonDataModel/'),
  ('standard.omop',               'version','5.4 (current); 6.0 in pilot'),
  ('standard.omop',               'governing_body','OHDSI (Observational Health Data Sciences and Informatics)'),
  ('standard.icd10',              'url','https://www.cdc.gov/nchs/icd/icd-10-cm/'),
  ('standard.icd10',              'version','FY2025 (effective 2024-10-01)'),
  ('standard.icd10',              'governing_body','CDC NCHS + CMS (US clinical modification of WHO ICD-10)'),
  ('standard.snomed_ct',          'url','https://www.snomed.org/'),
  ('standard.snomed_ct',          'version','International Edition July 2024; US Edition March 2025'),
  ('standard.snomed_ct',          'governing_body','SNOMED International; US Edition by NLM'),
  ('standard.loinc',              'url','https://loinc.org/'),
  ('standard.loinc',              'version','2.78 (December 2024)'),
  ('standard.loinc',              'governing_body','Regenstrief Institute'),
  ('standard.nedss',              'url','https://www.cdc.gov/nbs/'),
  ('standard.nedss',              'version','NBS 7.x; RCKMS continuously updated'),
  ('standard.nedss',              'governing_body','US Centers for Disease Control and Prevention (CDC)'),
  ('standard.dwc',                'url','https://dwc.tdwg.org/'),
  ('standard.dwc',                'version','2024-09-18 ratified revision'),
  ('standard.dwc',                'governing_body','Biodiversity Information Standards (TDWG)'),
  ('standard.geosparql',          'url','https://www.ogc.org/standards/geosparql'),
  ('standard.geosparql',          'version','GeoSPARQL 1.1 (2024); OGC API - Features Part 1 1.0.1'),
  ('standard.geosparql',          'governing_body','Open Geospatial Consortium (OGC)'),
  ('standard.schema_org_dataset', 'url','https://schema.org/Dataset'),
  ('standard.schema_org_dataset', 'version','Schema.org 27.0 (2024); DCAT-US 3 (2024)'),
  ('standard.schema_org_dataset', 'governing_body','W3C Schema.org Community Group; GSA / data.gov for DCAT-US'),
  ('standard.w3c_prov',           'url','https://www.w3.org/TR/prov-overview/'),
  ('standard.w3c_prov',           'version','PROV family Recommendation (2013, reaffirmed)'),
  ('standard.w3c_prov',           'governing_body','World Wide Web Consortium (W3C)')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. ICD-10-CM code nodes for wildlife/vector/heat surveillance
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  -- Heat (T67.*)
  ('code.icd10.t670xxa','icd10_code','T67.0XXA Heatstroke and sunstroke, initial encounter',
     'ICD-10-CM rubric covers heatstroke and sunstroke; primary code for severe heat illness ED visits.','deep-standards'),
  ('code.icd10.t671xxa','icd10_code','T67.1XXA Heat syncope, initial encounter',NULL,'deep-standards'),
  ('code.icd10.t672xxa','icd10_code','T67.2XXA Heat cramp, initial encounter',NULL,'deep-standards'),
  ('code.icd10.t673xxa','icd10_code','T67.3XXA Heat exhaustion, anhydrotic, initial encounter',NULL,'deep-standards'),
  ('code.icd10.t674xxa','icd10_code','T67.4XXA Heat exhaustion due to salt depletion, initial encounter',NULL,'deep-standards'),
  ('code.icd10.t675xxa','icd10_code','T67.5XXA Heat exhaustion, unspecified, initial encounter',NULL,'deep-standards'),
  ('code.icd10.t676xxa','icd10_code','T67.6XXA Heat fatigue, transient, initial encounter',NULL,'deep-standards'),
  ('code.icd10.t677xxa','icd10_code','T67.7XXA Heat edema, initial encounter',NULL,'deep-standards'),
  ('code.icd10.t678xxa','icd10_code','T67.8XXA Other effects of heat and light, initial encounter',NULL,'deep-standards'),
  ('code.icd10.t679xxa','icd10_code','T67.9XXA Effect of heat and light, unspecified, initial encounter',NULL,'deep-standards'),

  -- Plague (A20.*)
  ('code.icd10.a200','icd10_code','A20.0 Bubonic plague',NULL,'deep-standards'),
  ('code.icd10.a201','icd10_code','A20.1 Cellulocutaneous plague',NULL,'deep-standards'),
  ('code.icd10.a202','icd10_code','A20.2 Pneumonic plague',NULL,'deep-standards'),
  ('code.icd10.a203','icd10_code','A20.3 Plague meningitis',NULL,'deep-standards'),
  ('code.icd10.a207','icd10_code','A20.7 Septicemic plague',NULL,'deep-standards'),
  ('code.icd10.a208','icd10_code','A20.8 Other forms of plague',NULL,'deep-standards'),
  ('code.icd10.a209','icd10_code','A20.9 Plague, unspecified',NULL,'deep-standards'),

  -- Yersiniosis
  ('code.icd10.a282','icd10_code','A28.2 Extraintestinal yersiniosis',
     'Yersinia enterocolitica / pseudotuberculosis extraintestinal forms; rodent reservoir overlap with plague surveillance.','deep-standards'),

  -- Rocky Mountain spotted fever
  ('code.icd10.a770','icd10_code','A77.0 Spotted fever due to Rickettsia rickettsii',
     'Rocky Mountain spotted fever; AZ has a notable tribal-community RMSF cluster driven by brown-dog-tick transmission.','deep-standards'),

  -- Hantavirus
  ('code.icd10.b334','icd10_code','B33.4 Hantavirus (cardio-)pulmonary syndrome [HPS] [HCPS]',
     'Sin Nombre virus pulmonary syndrome in the US Southwest; surveillance entry-point for rodent-reservoir HPS clusters.','deep-standards'),

  -- Tularemia (A21.*)
  ('code.icd10.a210','icd10_code','A21.0 Ulceroglandular tularemia',NULL,'deep-standards'),
  ('code.icd10.a211','icd10_code','A21.1 Oculoglandular tularemia',NULL,'deep-standards'),
  ('code.icd10.a212','icd10_code','A21.2 Pulmonary tularemia',NULL,'deep-standards'),
  ('code.icd10.a213','icd10_code','A21.3 Gastrointestinal tularemia',NULL,'deep-standards'),
  ('code.icd10.a217','icd10_code','A21.7 Generalized tularemia',NULL,'deep-standards'),
  ('code.icd10.a218','icd10_code','A21.8 Other forms of tularemia',NULL,'deep-standards'),
  ('code.icd10.a219','icd10_code','A21.9 Tularemia, unspecified',NULL,'deep-standards'),

  -- West Nile fever
  ('code.icd10.a923','icd10_code','A92.3 West Nile virus infection',
     'Includes West Nile fever, encephalitis, and viremic infection; replaces prior A92.30/.31/.32 split which remains active as child codes.','deep-standards'),
  ('code.icd10.a9230','icd10_code','A92.30 West Nile virus infection, unspecified',NULL,'deep-standards'),
  ('code.icd10.a9231','icd10_code','A92.31 West Nile virus infection with encephalitis',NULL,'deep-standards'),
  ('code.icd10.a9232','icd10_code','A92.32 West Nile virus infection with other neurologic manifestation',NULL,'deep-standards'),
  ('code.icd10.a9239','icd10_code','A92.39 West Nile virus infection with other complications',NULL,'deep-standards'),

  -- Rabies (A82.*)
  ('code.icd10.a820','icd10_code','A82.0 Sylvatic rabies',NULL,'deep-standards'),
  ('code.icd10.a821','icd10_code','A82.1 Urban rabies',NULL,'deep-standards'),
  ('code.icd10.a829','icd10_code','A82.9 Rabies, unspecified',NULL,'deep-standards')
ON CONFLICT DO NOTHING;

-- Property: display code + originating system
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('code.icd10.t670xxa','code','T67.0XXA'),  ('code.icd10.t670xxa','system','ICD-10-CM'),
  ('code.icd10.t671xxa','code','T67.1XXA'),  ('code.icd10.t671xxa','system','ICD-10-CM'),
  ('code.icd10.t672xxa','code','T67.2XXA'),  ('code.icd10.t672xxa','system','ICD-10-CM'),
  ('code.icd10.t673xxa','code','T67.3XXA'),  ('code.icd10.t673xxa','system','ICD-10-CM'),
  ('code.icd10.t674xxa','code','T67.4XXA'),  ('code.icd10.t674xxa','system','ICD-10-CM'),
  ('code.icd10.t675xxa','code','T67.5XXA'),  ('code.icd10.t675xxa','system','ICD-10-CM'),
  ('code.icd10.t676xxa','code','T67.6XXA'),  ('code.icd10.t676xxa','system','ICD-10-CM'),
  ('code.icd10.t677xxa','code','T67.7XXA'),  ('code.icd10.t677xxa','system','ICD-10-CM'),
  ('code.icd10.t678xxa','code','T67.8XXA'),  ('code.icd10.t678xxa','system','ICD-10-CM'),
  ('code.icd10.t679xxa','code','T67.9XXA'),  ('code.icd10.t679xxa','system','ICD-10-CM'),
  ('code.icd10.a200','code','A20.0'),        ('code.icd10.a200','system','ICD-10-CM'),
  ('code.icd10.a201','code','A20.1'),        ('code.icd10.a201','system','ICD-10-CM'),
  ('code.icd10.a202','code','A20.2'),        ('code.icd10.a202','system','ICD-10-CM'),
  ('code.icd10.a203','code','A20.3'),        ('code.icd10.a203','system','ICD-10-CM'),
  ('code.icd10.a207','code','A20.7'),        ('code.icd10.a207','system','ICD-10-CM'),
  ('code.icd10.a208','code','A20.8'),        ('code.icd10.a208','system','ICD-10-CM'),
  ('code.icd10.a209','code','A20.9'),        ('code.icd10.a209','system','ICD-10-CM'),
  ('code.icd10.a282','code','A28.2'),        ('code.icd10.a282','system','ICD-10-CM'),
  ('code.icd10.a770','code','A77.0'),        ('code.icd10.a770','system','ICD-10-CM'),
  ('code.icd10.b334','code','B33.4'),        ('code.icd10.b334','system','ICD-10-CM'),
  ('code.icd10.a210','code','A21.0'),        ('code.icd10.a210','system','ICD-10-CM'),
  ('code.icd10.a211','code','A21.1'),        ('code.icd10.a211','system','ICD-10-CM'),
  ('code.icd10.a212','code','A21.2'),        ('code.icd10.a212','system','ICD-10-CM'),
  ('code.icd10.a213','code','A21.3'),        ('code.icd10.a213','system','ICD-10-CM'),
  ('code.icd10.a217','code','A21.7'),        ('code.icd10.a217','system','ICD-10-CM'),
  ('code.icd10.a218','code','A21.8'),        ('code.icd10.a218','system','ICD-10-CM'),
  ('code.icd10.a219','code','A21.9'),        ('code.icd10.a219','system','ICD-10-CM'),
  ('code.icd10.a923','code','A92.3'),        ('code.icd10.a923','system','ICD-10-CM'),
  ('code.icd10.a9230','code','A92.30'),      ('code.icd10.a9230','system','ICD-10-CM'),
  ('code.icd10.a9231','code','A92.31'),      ('code.icd10.a9231','system','ICD-10-CM'),
  ('code.icd10.a9232','code','A92.32'),      ('code.icd10.a9232','system','ICD-10-CM'),
  ('code.icd10.a9239','code','A92.39'),      ('code.icd10.a9239','system','ICD-10-CM'),
  ('code.icd10.a820','code','A82.0'),        ('code.icd10.a820','system','ICD-10-CM'),
  ('code.icd10.a821','code','A82.1'),        ('code.icd10.a821','system','ICD-10-CM'),
  ('code.icd10.a829','code','A82.9'),        ('code.icd10.a829','system','ICD-10-CM')
ON CONFLICT DO NOTHING;

-- definedIn edges: every code is defined in standard.icd10 (15000-15099)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 15000 + row_number() OVER (), subject_id, 'definedIn', 'standard.icd10', 'deep-standards'
FROM (VALUES
  ('code.icd10.t670xxa'),('code.icd10.t671xxa'),('code.icd10.t672xxa'),
  ('code.icd10.t673xxa'),('code.icd10.t674xxa'),('code.icd10.t675xxa'),
  ('code.icd10.t676xxa'),('code.icd10.t677xxa'),('code.icd10.t678xxa'),
  ('code.icd10.t679xxa'),
  ('code.icd10.a200'),('code.icd10.a201'),('code.icd10.a202'),('code.icd10.a203'),
  ('code.icd10.a207'),('code.icd10.a208'),('code.icd10.a209'),
  ('code.icd10.a282'),
  ('code.icd10.a770'),
  ('code.icd10.b334'),
  ('code.icd10.a210'),('code.icd10.a211'),('code.icd10.a212'),('code.icd10.a213'),
  ('code.icd10.a217'),('code.icd10.a218'),('code.icd10.a219'),
  ('code.icd10.a923'),('code.icd10.a9230'),('code.icd10.a9231'),
  ('code.icd10.a9232'),('code.icd10.a9239'),
  ('code.icd10.a820'),('code.icd10.a821'),('code.icd10.a829')
) AS t(subject_id)
ON CONFLICT DO NOTHING;

-- mappedTo edges: code -> focus area (15100-15199)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 15100 + row_number() OVER (), subject_id, 'mappedTo', object_id, 'deep-standards'
FROM (VALUES
  -- Heat morbidity: all T67.*
  ('code.icd10.t670xxa','focus.heat_morbidity'),
  ('code.icd10.t671xxa','focus.heat_morbidity'),
  ('code.icd10.t672xxa','focus.heat_morbidity'),
  ('code.icd10.t673xxa','focus.heat_morbidity'),
  ('code.icd10.t674xxa','focus.heat_morbidity'),
  ('code.icd10.t675xxa','focus.heat_morbidity'),
  ('code.icd10.t676xxa','focus.heat_morbidity'),
  ('code.icd10.t677xxa','focus.heat_morbidity'),
  ('code.icd10.t678xxa','focus.heat_morbidity'),
  ('code.icd10.t679xxa','focus.heat_morbidity'),
  -- Heatstroke is the canonical mortality code too
  ('code.icd10.t670xxa','focus.heat_mortality'),
  -- Plague: A20.* + A28.2 (extraintestinal yersiniosis is on the rodent
  -- reservoir adjacent line)
  ('code.icd10.a200','focus.plague'),
  ('code.icd10.a201','focus.plague'),
  ('code.icd10.a202','focus.plague'),
  ('code.icd10.a203','focus.plague'),
  ('code.icd10.a207','focus.plague'),
  ('code.icd10.a208','focus.plague'),
  ('code.icd10.a209','focus.plague'),
  ('code.icd10.a282','focus.zoonotic'),
  -- RMSF
  ('code.icd10.a770','focus.rmsf'),
  -- Hantavirus
  ('code.icd10.b334','focus.hantavirus'),
  -- Tularemia
  ('code.icd10.a210','focus.tularemia'),
  ('code.icd10.a211','focus.tularemia'),
  ('code.icd10.a212','focus.tularemia'),
  ('code.icd10.a213','focus.tularemia'),
  ('code.icd10.a217','focus.tularemia'),
  ('code.icd10.a218','focus.tularemia'),
  ('code.icd10.a219','focus.tularemia'),
  -- West Nile
  ('code.icd10.a923','focus.wnv'),
  ('code.icd10.a9230','focus.wnv'),
  ('code.icd10.a9231','focus.wnv'),
  ('code.icd10.a9232','focus.wnv'),
  ('code.icd10.a9239','focus.wnv'),
  -- Rabies
  ('code.icd10.a820','focus.rabies'),
  ('code.icd10.a821','focus.rabies'),
  ('code.icd10.a829','focus.rabies')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. Darwin Core term nodes (most useful for wildlife / vector observations)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('dwc.eventdate',          'dwc_term', 'dwc:eventDate',
     'ISO-8601 date(-range) on which an Event occurred. Clean crosswalk for any "date of incident" Figure-2 parameter.','deep-standards'),
  ('dwc.decimallatitude',    'dwc_term', 'dwc:decimalLatitude',
     'Geographic latitude (in decimal degrees, WGS84) of the geographic centre of a Location.','deep-standards'),
  ('dwc.decimallongitude',   'dwc_term', 'dwc:decimalLongitude',
     'Geographic longitude (in decimal degrees, WGS84) of the geographic centre of a Location.','deep-standards'),
  ('dwc.geodeticdatum',      'dwc_term', 'dwc:geodeticDatum',
     'Ellipsoid, geodetic datum, or spatial reference system on which the coordinates are based; typically EPSG:4326.','deep-standards'),
  ('dwc.coordinateuncertaintyinmeters','dwc_term','dwc:coordinateUncertaintyInMeters',
     'Horizontal distance (m) from the given coordinates within which the actual location is reasonably expected to lie.','deep-standards'),
  ('dwc.scientificname',     'dwc_term', 'dwc:scientificName',
     'Full scientific name with authorship; the canonical biodiversity species identifier.','deep-standards'),
  ('dwc.vernacularname',     'dwc_term', 'dwc:vernacularName',
     'Common (non-scientific) name; useful for participatory wildlife reporting.','deep-standards'),
  ('dwc.taxonid',            'dwc_term', 'dwc:taxonID',
     'Identifier for the taxon (e.g. GBIF taxonKey, ITIS TSN).','deep-standards'),
  ('dwc.individualcount',    'dwc_term', 'dwc:individualCount',
     'Number of individuals present at the time of the Occurrence.','deep-standards'),
  ('dwc.organismquantity',   'dwc_term', 'dwc:organismQuantity',
     'Numeric value for the quantity of organisms (paired with organismQuantityType for density/biomass).','deep-standards'),
  ('dwc.organismquantitytype','dwc_term','dwc:organismQuantityType',
     'Type of quantification system used for organismQuantity (e.g. individuals, traps/night, %cover).','deep-standards'),
  ('dwc.vitality',           'dwc_term', 'dwc:vitality',
     'Whether the organism was alive or dead at the time of observation (controlled: alive | dead | uncertain).','deep-standards'),
  ('dwc.occurrencestatus',   'dwc_term', 'dwc:occurrenceStatus',
     'Statement of presence or absence of the taxon at a Location.','deep-standards'),
  ('dwc.locality',           'dwc_term', 'dwc:locality',
     'Specific human-readable description of the place.','deep-standards'),
  ('dwc.recordedby',         'dwc_term', 'dwc:recordedBy',
     'Person(s), group(s), or organization(s) responsible for recording the original Occurrence; maps to citizen-science contributors.','deep-standards'),
  ('dwc.associatedmedia',    'dwc_term', 'dwc:associatedMedia',
     'Identifiers (URIs) of media associated with the Occurrence (photo, audio, video).','deep-standards'),
  ('dwc.samplingprotocol',   'dwc_term', 'dwc:samplingProtocol',
     'Names, references, or descriptions of the method or protocol used during the Event (e.g. CDC light trap, ovitrap).','deep-standards')
ON CONFLICT DO NOTHING;

-- Properties: term URI + governing namespace
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('dwc.eventdate',                     'uri','http://rs.tdwg.org/dwc/terms/eventDate'),
  ('dwc.decimallatitude',               'uri','http://rs.tdwg.org/dwc/terms/decimalLatitude'),
  ('dwc.decimallongitude',              'uri','http://rs.tdwg.org/dwc/terms/decimalLongitude'),
  ('dwc.geodeticdatum',                 'uri','http://rs.tdwg.org/dwc/terms/geodeticDatum'),
  ('dwc.coordinateuncertaintyinmeters', 'uri','http://rs.tdwg.org/dwc/terms/coordinateUncertaintyInMeters'),
  ('dwc.scientificname',                'uri','http://rs.tdwg.org/dwc/terms/scientificName'),
  ('dwc.vernacularname',                'uri','http://rs.tdwg.org/dwc/terms/vernacularName'),
  ('dwc.taxonid',                       'uri','http://rs.tdwg.org/dwc/terms/taxonID'),
  ('dwc.individualcount',               'uri','http://rs.tdwg.org/dwc/terms/individualCount'),
  ('dwc.organismquantity',              'uri','http://rs.tdwg.org/dwc/terms/organismQuantity'),
  ('dwc.organismquantitytype',          'uri','http://rs.tdwg.org/dwc/terms/organismQuantityType'),
  ('dwc.vitality',                      'uri','http://rs.tdwg.org/dwc/terms/vitality'),
  ('dwc.occurrencestatus',              'uri','http://rs.tdwg.org/dwc/terms/occurrenceStatus'),
  ('dwc.locality',                      'uri','http://rs.tdwg.org/dwc/terms/locality'),
  ('dwc.recordedby',                    'uri','http://rs.tdwg.org/dwc/terms/recordedBy'),
  ('dwc.associatedmedia',               'uri','http://rs.tdwg.org/dwc/terms/associatedMedia'),
  ('dwc.samplingprotocol',              'uri','http://rs.tdwg.org/dwc/terms/samplingProtocol')
ON CONFLICT DO NOTHING;

-- definedIn for Darwin Core terms (15200-15299)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 15200 + row_number() OVER (), subject_id, 'definedIn', 'standard.dwc', 'deep-standards'
FROM (VALUES
  ('dwc.eventdate'),('dwc.decimallatitude'),('dwc.decimallongitude'),
  ('dwc.geodeticdatum'),('dwc.coordinateuncertaintyinmeters'),
  ('dwc.scientificname'),('dwc.vernacularname'),('dwc.taxonid'),
  ('dwc.individualcount'),('dwc.organismquantity'),('dwc.organismquantitytype'),
  ('dwc.vitality'),('dwc.occurrencestatus'),('dwc.locality'),
  ('dwc.recordedby'),('dwc.associatedmedia'),('dwc.samplingprotocol')
) AS t(subject_id)
ON CONFLICT DO NOTHING;

-- mappedTo: Figure-2 parameter  ->  Darwin Core term  (15300-15399)
-- Note: edge direction is param --mappedTo--> dwc.<term> so a JOIN from a
-- param.* node can find its canonical biodiversity expression.
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 15300 + row_number() OVER (), subject_id, 'mappedTo', object_id, 'deep-standards'
FROM (VALUES
  -- Date of incident (env / wildlife / livestock) -> eventDate
  ('param.date_env_incident',           'dwc.eventdate'),
  ('param.date_wildlife_incident',      'dwc.eventdate'),
  ('param.date_livestock_incident',     'dwc.eventdate'),
  ('param.date_of_report',              'dwc.eventdate'),
  ('param.date_of_illness',             'dwc.eventdate'),
  -- Coordinates -> decimalLatitude + decimalLongitude (Darwin Core splits)
  ('param.geographical_coordinates',    'dwc.decimallatitude'),
  ('param.geographical_coordinates',    'dwc.decimallongitude'),
  ('param.geographical_coordinates',    'dwc.geodeticdatum'),
  ('param.location_vector_spotting',    'dwc.decimallatitude'),
  ('param.location_vector_spotting',    'dwc.decimallongitude'),
  ('param.location_vector_spotting',    'dwc.locality'),
  ('param.location_wildlife_incident',  'dwc.decimallatitude'),
  ('param.location_wildlife_incident',  'dwc.decimallongitude'),
  ('param.location_wildlife_incident',  'dwc.locality'),
  ('param.location_livestock_incident', 'dwc.decimallatitude'),
  ('param.location_livestock_incident', 'dwc.decimallongitude'),
  ('param.location_livestock_incident', 'dwc.locality'),
  -- Species
  ('param.wildlife_species',            'dwc.scientificname'),
  ('param.wildlife_species',            'dwc.vernacularname'),
  ('param.wildlife_species',            'dwc.taxonid'),
  ('param.livestock_species',           'dwc.scientificname'),
  ('param.livestock_species',           'dwc.vernacularname'),
  -- Counts
  ('param.wildlife_dead_count',         'dwc.individualcount'),
  ('param.wildlife_dead_count',         'dwc.vitality'),
  ('param.livestock_dead_count',        'dwc.individualcount'),
  ('param.livestock_dead_count',        'dwc.vitality'),
  ('param.livestock_sick_count',        'dwc.individualcount'),
  -- Vector ecology
  ('param.unusual_vectors',             'dwc.occurrencestatus'),
  ('param.unusual_vectors',             'dwc.scientificname'),
  ('param.vector_density',              'dwc.organismquantity'),
  ('param.vector_density',              'dwc.organismquantitytype'),
  ('param.vector_density',              'dwc.samplingprotocol'),
  -- Photos
  ('param.photo',                       'dwc.associatedmedia')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. Cross-standard concept mappings (focus areas -> other standards)
-- Lightweight crosswalk hints; the heavy lifting (full ValueSets) belongs
-- in a code-system service downstream. Range 15400-15499.
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('code.loinc.heat_exposure_panel','loinc_code','LOINC heat-exposure / environmental panels',
     'Placeholder anchor for LOINC environmental-exposure panels (e.g. heat-index, WBGT) referenced by occupational-health observations.','deep-standards'),
  ('code.snomed.heatstroke','snomed_concept','SNOMED CT 39579001 Heatstroke (disorder)',NULL,'deep-standards'),
  ('code.snomed.plague','snomed_concept','SNOMED CT 58750007 Plague (disorder)',NULL,'deep-standards'),
  ('code.snomed.rmsf','snomed_concept','SNOMED CT 186772009 Rocky Mountain spotted fever (disorder)',NULL,'deep-standards'),
  ('code.snomed.hantavirus','snomed_concept','SNOMED CT 47523006 Hantavirus pulmonary syndrome (disorder)',NULL,'deep-standards'),
  ('code.snomed.tularemia','snomed_concept','SNOMED CT 19265001 Tularemia (disorder)',NULL,'deep-standards'),
  ('code.snomed.wnv','snomed_concept','SNOMED CT 230145002 West Nile virus infection (disorder)',NULL,'deep-standards'),
  ('code.snomed.rabies','snomed_concept','SNOMED CT 14168008 Rabies (disorder)',NULL,'deep-standards'),
  ('code.nedss.plague','nedss_condition','NNDSS Plague',NULL,'deep-standards'),
  ('code.nedss.rmsf','nedss_condition','NNDSS Spotted Fever Rickettsiosis (incl. RMSF)',NULL,'deep-standards'),
  ('code.nedss.hantavirus','nedss_condition','NNDSS Hantavirus Infection, non-Hantavirus Pulmonary Syndrome and HPS',NULL,'deep-standards'),
  ('code.nedss.tularemia','nedss_condition','NNDSS Tularemia',NULL,'deep-standards'),
  ('code.nedss.wnv','nedss_condition','NNDSS West Nile Virus Disease (Arboviral Diseases, neuroinvasive and non-neuroinvasive)',NULL,'deep-standards'),
  ('code.nedss.rabies_human','nedss_condition','NNDSS Rabies, Human',NULL,'deep-standards'),
  ('code.nedss.rabies_animal','nedss_condition','NNDSS Rabies, Animal',NULL,'deep-standards')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('code.snomed.heatstroke',  'code','39579001'),  ('code.snomed.heatstroke', 'system','SNOMED CT'),
  ('code.snomed.plague',      'code','58750007'),  ('code.snomed.plague',     'system','SNOMED CT'),
  ('code.snomed.rmsf',        'code','186772009'), ('code.snomed.rmsf',       'system','SNOMED CT'),
  ('code.snomed.hantavirus',  'code','47523006'),  ('code.snomed.hantavirus', 'system','SNOMED CT'),
  ('code.snomed.tularemia',   'code','19265001'),  ('code.snomed.tularemia',  'system','SNOMED CT'),
  ('code.snomed.wnv',         'code','230145002'), ('code.snomed.wnv',        'system','SNOMED CT'),
  ('code.snomed.rabies',      'code','14168008'),  ('code.snomed.rabies',     'system','SNOMED CT'),
  ('code.nedss.plague',          'system','CDC NNDSS'),
  ('code.nedss.rmsf',            'system','CDC NNDSS'),
  ('code.nedss.hantavirus',      'system','CDC NNDSS'),
  ('code.nedss.tularemia',       'system','CDC NNDSS'),
  ('code.nedss.wnv',             'system','CDC NNDSS'),
  ('code.nedss.rabies_human',    'system','CDC NNDSS'),
  ('code.nedss.rabies_animal',   'system','CDC NNDSS')
ON CONFLICT DO NOTHING;

-- definedIn for SNOMED / LOINC / NEDSS crosswalk anchors (15400-15449)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 15400 + row_number() OVER (), subject_id, 'definedIn', object_id, 'deep-standards'
FROM (VALUES
  ('code.loinc.heat_exposure_panel','standard.loinc'),
  ('code.snomed.heatstroke',        'standard.snomed_ct'),
  ('code.snomed.plague',            'standard.snomed_ct'),
  ('code.snomed.rmsf',              'standard.snomed_ct'),
  ('code.snomed.hantavirus',        'standard.snomed_ct'),
  ('code.snomed.tularemia',         'standard.snomed_ct'),
  ('code.snomed.wnv',               'standard.snomed_ct'),
  ('code.snomed.rabies',            'standard.snomed_ct'),
  ('code.nedss.plague',             'standard.nedss'),
  ('code.nedss.rmsf',               'standard.nedss'),
  ('code.nedss.hantavirus',         'standard.nedss'),
  ('code.nedss.tularemia',          'standard.nedss'),
  ('code.nedss.wnv',                'standard.nedss'),
  ('code.nedss.rabies_human',       'standard.nedss'),
  ('code.nedss.rabies_animal',      'standard.nedss')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- mappedTo for SNOMED / NEDSS / LOINC crosswalks  -> focus.* (15450-15499)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 15450 + row_number() OVER (), subject_id, 'mappedTo', object_id, 'deep-standards'
FROM (VALUES
  ('code.loinc.heat_exposure_panel','focus.heat_morbidity'),
  ('code.snomed.heatstroke',        'focus.heat_mortality'),
  ('code.snomed.heatstroke',        'focus.heat_morbidity'),
  ('code.snomed.plague',            'focus.plague'),
  ('code.snomed.rmsf',              'focus.rmsf'),
  ('code.snomed.hantavirus',        'focus.hantavirus'),
  ('code.snomed.tularemia',         'focus.tularemia'),
  ('code.snomed.wnv',               'focus.wnv'),
  ('code.snomed.rabies',            'focus.rabies'),
  ('code.nedss.plague',             'focus.plague'),
  ('code.nedss.rmsf',               'focus.rmsf'),
  ('code.nedss.hantavirus',         'focus.hantavirus'),
  ('code.nedss.tularemia',          'focus.tularemia'),
  ('code.nedss.wnv',                'focus.wnv'),
  ('code.nedss.rabies_human',       'focus.rabies'),
  ('code.nedss.rabies_animal',      'focus.rabies')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 5. Convenience views
-- ---------------------------------------------------------------------------

-- View: every Figure-2 parameter together with its Darwin Core term(s)
CREATE OR REPLACE VIEW kg.v_param_to_dwc AS
SELECT
  p.node_id           AS param_id,
  p.label             AS parameter,
  d.node_id           AS dwc_id,
  d.label             AS dwc_term,
  u.value_text        AS dwc_uri
FROM kg.node p
JOIN kg.edge e
  ON e.subject_id = p.node_id
 AND e.predicate  = 'mappedTo'
JOIN kg.node d
  ON d.node_id = e.object_id
 AND d.node_type = 'dwc_term'
LEFT JOIN kg.property u
  ON u.node_id = d.node_id
 AND u.key = 'uri'
WHERE p.node_type = 'parameter';

-- View: every focus area together with the codes that map to it
CREATE OR REPLACE VIEW kg.v_focus_to_codes AS
SELECT
  f.node_id     AS focus_id,
  f.label       AS focus,
  c.node_id     AS code_id,
  c.label       AS code_label,
  cp.value_text AS code,
  sp.value_text AS code_system,
  s.label       AS standard
FROM kg.node f
JOIN kg.edge me
  ON me.object_id = f.node_id
 AND me.predicate = 'mappedTo'
JOIN kg.node c
  ON c.node_id = me.subject_id
LEFT JOIN kg.property cp
  ON cp.node_id = c.node_id AND cp.key = 'code'
LEFT JOIN kg.property sp
  ON sp.node_id = c.node_id AND sp.key = 'system'
LEFT JOIN kg.edge de
  ON de.subject_id = c.node_id AND de.predicate = 'definedIn'
LEFT JOIN kg.node s
  ON s.node_id = de.object_id AND s.node_type = 'standard'
WHERE f.node_type = 'focus_area'
  AND c.node_type IN ('icd10_code','snomed_concept','loinc_code','nedss_condition');
