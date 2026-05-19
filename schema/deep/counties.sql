-- ============================================================================
-- EpiHack Arizona 2026 -- Deep dive: Arizona counties
--
-- One node per Arizona county (15) plus child resource nodes for the county
-- health department and any explicit mosquito / vector control program the
-- county runs through its environmental health division.
--
-- Existing resource nodes are referenced (not redefined):
--   * resource.mcdph_mcesd      -- Maricopa Vector Control (wildlife_vectors.sql)
--   * resource.pcdh             -- Pima Vector Control     (wildlife_vectors.sql)
--   * resource.coconino_hhs     -- Coconino HHS            (wildlife_vectors.sql)
--   * heat.q1..q4, wv.q1..q4    -- focus-group questions
--
-- Edge-id range reserved for this agent: 12000..12999
-- All inserts use ON CONFLICT DO NOTHING. source_fig = 'deep-counties'.
--
-- Run AFTER schema/knowledge_graph.sql, schema/heat.sql, schema/wildlife_vectors.sql.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. County nodes  (node_type = 'county')
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('county.apache',     'county', 'Apache County',
     'Northeastern AZ; includes a large share of the Navajo Nation and Fort Apache; seat St. Johns.',
     'deep-counties'),
  ('county.cochise',    'county', 'Cochise County',
     'Southeastern AZ border county; Sierra Vista / Bisbee / Douglas; seat Bisbee.',
     'deep-counties'),
  ('county.coconino',   'county', 'Coconino County',
     'Second-largest US county by area; Flagstaff, Grand Canyon, Navajo & Hopi lands; seat Flagstaff.',
     'deep-counties'),
  ('county.gila',       'county', 'Gila County',
     'Central AZ; Globe, Payson, San Carlos Apache & Tonto Apache lands; seat Globe.',
     'deep-counties'),
  ('county.graham',     'county', 'Graham County',
     'Southeastern AZ; Safford, Mt. Graham, San Carlos Apache reservation overlap; seat Safford.',
     'deep-counties'),
  ('county.greenlee',   'county', 'Greenlee County',
     'Smallest population AZ county; Clifton / Morenci copper mining; seat Clifton.',
     'deep-counties'),
  ('county.la_paz',     'county', 'La Paz County',
     'Western AZ on the Colorado River; Parker; Colorado River Indian Tribes; seat Parker.',
     'deep-counties'),
  ('county.maricopa',   'county', 'Maricopa County',
     'Phoenix metro; most populous AZ county and 4th most populous US county; seat Phoenix.',
     'deep-counties'),
  ('county.mohave',     'county', 'Mohave County',
     'Northwestern AZ; Kingman, Bullhead City, Lake Havasu City; seat Kingman.',
     'deep-counties'),
  ('county.navajo',     'county', 'Navajo County',
     'Northern AZ; Show Low, Winslow, Holbrook; large Navajo and Hopi nation overlap; seat Holbrook.',
     'deep-counties'),
  ('county.pima',       'county', 'Pima County',
     'Tucson metro; second most populous AZ county; Tohono O''odham Nation overlap; seat Tucson.',
     'deep-counties'),
  ('county.pinal',      'county', 'Pinal County',
     'Central AZ between Phoenix and Tucson; Casa Grande, Apache Junction, Maricopa; seat Florence.',
     'deep-counties'),
  ('county.santa_cruz', 'county', 'Santa Cruz County',
     'Smallest AZ county by area; Nogales border port-of-entry; seat Nogales.',
     'deep-counties'),
  ('county.yavapai',    'county', 'Yavapai County',
     'Central-northern AZ; Prescott, Prescott Valley, Cottonwood, Sedona; seat Prescott.',
     'deep-counties'),
  ('county.yuma',       'county', 'Yuma County',
     'Southwestern AZ border / Colorado River agricultural belt; seat Yuma.',
     'deep-counties')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- County properties (population approx. 2024, county seat, FIPS)
-- ---------------------------------------------------------------------------
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('county.apache',     'county_seat', 'St. Johns'),
  ('county.cochise',    'county_seat', 'Bisbee'),
  ('county.coconino',   'county_seat', 'Flagstaff'),
  ('county.gila',       'county_seat', 'Globe'),
  ('county.graham',     'county_seat', 'Safford'),
  ('county.greenlee',   'county_seat', 'Clifton'),
  ('county.la_paz',     'county_seat', 'Parker'),
  ('county.maricopa',   'county_seat', 'Phoenix'),
  ('county.mohave',     'county_seat', 'Kingman'),
  ('county.navajo',     'county_seat', 'Holbrook'),
  ('county.pima',       'county_seat', 'Tucson'),
  ('county.pinal',      'county_seat', 'Florence'),
  ('county.santa_cruz', 'county_seat', 'Nogales'),
  ('county.yavapai',    'county_seat', 'Prescott'),
  ('county.yuma',       'county_seat', 'Yuma'),
  ('county.apache',     'fips', '04001'),
  ('county.cochise',    'fips', '04003'),
  ('county.coconino',   'fips', '04005'),
  ('county.gila',       'fips', '04007'),
  ('county.graham',     'fips', '04009'),
  ('county.greenlee',   'fips', '04011'),
  ('county.la_paz',     'fips', '04012'),
  ('county.maricopa',   'fips', '04013'),
  ('county.mohave',     'fips', '04015'),
  ('county.navajo',     'fips', '04017'),
  ('county.pima',       'fips', '04019'),
  ('county.pinal',      'fips', '04021'),
  ('county.santa_cruz', 'fips', '04023'),
  ('county.yavapai',    'fips', '04025'),
  ('county.yuma',       'fips', '04027')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_num) VALUES
  ('county.apache',     'population_approx',    66000),
  ('county.cochise',    'population_approx',   125000),
  ('county.coconino',   'population_approx',   145000),
  ('county.gila',       'population_approx',    53000),
  ('county.graham',     'population_approx',    39000),
  ('county.greenlee',   'population_approx',     9500),
  ('county.la_paz',     'population_approx',    16700),
  ('county.maricopa',   'population_approx',  4585000),
  ('county.mohave',     'population_approx',   220000),
  ('county.navajo',     'population_approx',   107000),
  ('county.pima',       'population_approx',  1075000),
  ('county.pinal',      'population_approx',   513000),
  ('county.santa_cruz', 'population_approx',    47700),
  ('county.yavapai',    'population_approx',   254000),
  ('county.yuma',       'population_approx',   217000)
ON CONFLICT DO NOTHING;

-- County top-level health-department-page URLs (verified May 2026)
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('county.apache',     'health_dept_url', 'https://www.apachecountyaz.gov/Public-Health-Services'),
  ('county.cochise',    'health_dept_url', 'https://www.cochise.az.gov/372/Health-Social-Services'),
  ('county.coconino',   'health_dept_url', 'https://www.coconino.az.gov/2124/Health-and-Human-Services'),
  ('county.gila',       'health_dept_url', 'https://www.gilacountyaz.gov/government/health_and_emergency_services/health_services/index.php'),
  ('county.graham',     'health_dept_url', 'https://www.graham.az.gov/263/Public-Health'),
  ('county.greenlee',   'health_dept_url', 'https://greenlee.az.gov/ova_dep/health-and-county-services/'),
  ('county.la_paz',     'health_dept_url', 'https://www.lapaz.gov/644'),
  ('county.maricopa',   'health_dept_url', 'https://www.maricopa.gov/5388/Public-Health'),
  ('county.mohave',     'health_dept_url', 'https://www.mohave.gov/departments/public-health/'),
  ('county.navajo',     'health_dept_url', 'https://www.navajocountyaz.gov/309/Public-Health-Services'),
  ('county.pima',       'health_dept_url', 'https://www.pima.gov/95/Health'),
  ('county.pinal',      'health_dept_url', 'https://www.pinal.gov/151/Public-Health'),
  ('county.santa_cruz', 'health_dept_url', 'https://www.santacruzcountyaz.gov/153/Public-Health'),
  ('county.yavapai',    'health_dept_url', 'https://www.yavapaihealth.com/'),
  ('county.yuma',       'health_dept_url', 'https://www.yumacountyaz.gov/government/health-district')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. County health department resource nodes
--    (Maricopa, Pima, Coconino are referenced not redefined.)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('resource.apache_hd',     'resource_org', 'Apache County Public Health Services District',
     'Five-division county PHSD with clinics in St. Johns, Springerville, Round Valley, Chinle; serves a population that is majority AI/AN; rural with limited infrastructure.',
     'deep-counties'),
  ('resource.cochise_hd',    'resource_org', 'Cochise County Health and Social Services',
     'Border-county HD; Environmental Health Services Division covers food, vector and zoonotic surveillance; routinely posts WNV detections via "Fight the Bite" updates.',
     'deep-counties'),
  ('resource.gila_hd',       'resource_org', 'Gila County Public Health & Community Services',
     'Globe-based county HD with offices in Globe and Payson; communicable disease, immunizations, vital records, HIV care, school health.',
     'deep-counties'),
  ('resource.graham_hd',     'resource_org', 'Graham County Department of Health & Human Services',
     'Safford-based rural HD; communicable disease, WIC, immunizations, environmental health; partners with San Carlos Apache HD.',
     'deep-counties'),
  ('resource.greenlee_hd',   'resource_org', 'Greenlee County Health Department',
     'Smallest AZ county HD (Clifton); provides core clinical and environmental health services to ~9.5k residents.',
     'deep-counties'),
  ('resource.la_paz_hd',     'resource_org', 'La Paz County Health Department',
     'Parker-based rural HD; communicable disease, immunizations, environmental health; Healthy La Paz coalition partner.',
     'deep-counties'),
  ('resource.mohave_hd',     'resource_org', 'Mohave County Department of Public Health',
     'Kingman-based HD with branches in Bullhead City and Lake Havasu City; Environmental Health Division runs mosquito surveillance and fogging response.',
     'deep-counties'),
  ('resource.navajo_hd',     'resource_org', 'Navajo County Public Health Services District',
     'Holbrook-based HD; environmental health handles fly / vector / septic complaints and distributes ADHS mosquito materials.',
     'deep-counties'),
  ('resource.pinal_hd',      'resource_org', 'Pinal County Public Health Services District',
     'Florence-based HD; Environmental Health Division operates the Pinal Vector Control Program for WNV-competent mosquito surveillance.',
     'deep-counties'),
  ('resource.santa_cruz_hd', 'resource_org', 'Santa Cruz County Health Services',
     'Nogales-based border HD; binational coordination with Sonora; runs communicable disease, WIC, environmental health, and the Mariposa CHC FQHC referral network.',
     'deep-counties'),
  ('resource.yavapai_hd',    'resource_org', 'Yavapai County Community Health Services',
     'Prescott-based HD with offices in Prescott, Prescott Valley, Cottonwood; Environmental Disease Control program covers WNV, rabies, bed bugs, rodents.',
     'deep-counties'),
  ('resource.yuma_hd',       'resource_org', 'Yuma County Public Health Services District (Health District)',
     'Yuma-based border HD; Environmental Health Services Division operates Yuma Vector Control (mosquito trapping, identification, fogging).',
     'deep-counties')
ON CONFLICT DO NOTHING;

-- Jurisdiction + URL properties for new HD nodes
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.apache_hd',     'jurisdiction', 'county'),
  ('resource.cochise_hd',    'jurisdiction', 'county'),
  ('resource.gila_hd',       'jurisdiction', 'county'),
  ('resource.graham_hd',     'jurisdiction', 'county'),
  ('resource.greenlee_hd',   'jurisdiction', 'county'),
  ('resource.la_paz_hd',     'jurisdiction', 'county'),
  ('resource.mohave_hd',     'jurisdiction', 'county'),
  ('resource.navajo_hd',     'jurisdiction', 'county'),
  ('resource.pinal_hd',      'jurisdiction', 'county'),
  ('resource.santa_cruz_hd', 'jurisdiction', 'county'),
  ('resource.yavapai_hd',    'jurisdiction', 'county'),
  ('resource.yuma_hd',       'jurisdiction', 'county'),
  ('resource.apache_hd',     'url', 'https://www.apachecountyaz.gov/Public-Health-Services'),
  ('resource.cochise_hd',    'url', 'https://www.cochise.az.gov/372/Health-Social-Services'),
  ('resource.gila_hd',       'url', 'https://www.gilacountyaz.gov/government/health_and_emergency_services/health_services/index.php'),
  ('resource.graham_hd',     'url', 'https://www.graham.az.gov/263/Public-Health'),
  ('resource.greenlee_hd',   'url', 'https://greenlee.az.gov/ova_dep/health-and-county-services/'),
  ('resource.la_paz_hd',     'url', 'https://www.lapaz.gov/644'),
  ('resource.mohave_hd',     'url', 'https://www.mohave.gov/departments/public-health/'),
  ('resource.navajo_hd',     'url', 'https://www.navajocountyaz.gov/309/Public-Health-Services'),
  ('resource.pinal_hd',      'url', 'https://www.pinal.gov/151/Public-Health'),
  ('resource.santa_cruz_hd', 'url', 'https://www.santacruzcountyaz.gov/153/Public-Health'),
  ('resource.yavapai_hd',    'url', 'https://www.yavapaihealth.com/'),
  ('resource.yuma_hd',       'url', 'https://www.yumacountyaz.gov/government/health-district')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. Explicit vector-control program nodes (where one exists)
--    Maricopa + Pima already have resource.mcdph_mcesd / resource.pcdh.
--    Coconino HHS does its own surveillance via resource.coconino_hhs.
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('resource.cochise_vector_control',  'resource_org', 'Cochise County Environmental Health -- Vector Control',
     'EH Services Division activity: insect/animal surveillance, posts WNV detections under "Fight the Bite Cochise"; lighter footprint than Maricopa/Pima.',
     'deep-counties'),
  ('resource.mohave_vector_control',   'resource_org', 'Mohave County Environmental Health -- Vector Surveillance & Mitigation',
     'May-September mosquito surveillance across Mohave County; nine local Culex/Aedes species tracked; CDC matrix triggers MasterLine Kontrol 4-4 (pyrethrin) fogging.',
     'deep-counties'),
  ('resource.pinal_vector_control',    'resource_org', 'Pinal County Vector Control Program',
     'Pinal PHSD Environmental Health; trap-based surveillance for WNV/SLE-competent Culex spp.; resident reporting, source-reduction guidance, biological control.',
     'deep-counties'),
  ('resource.yavapai_vector_control',  'resource_org', 'Yavapai CHS -- Environmental Disease Control',
     'Yavapai CHS program covering mosquitoes, rodents, rabies surveillance, bed bugs, and West Nile virus across Prescott / Prescott Valley / Cottonwood / Sedona.',
     'deep-counties'),
  ('resource.yuma_vector_control',     'resource_org', 'Yuma County Vector Control (Mosquito Control and Prevention)',
     'Yuma Health District Environmental Health Services Division; mosquito trapping/identification, site treatment, routine fogging on request; Lower Colorado agricultural-belt focus.',
     'deep-counties')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.cochise_vector_control',  'jurisdiction', 'county'),
  ('resource.mohave_vector_control',   'jurisdiction', 'county'),
  ('resource.pinal_vector_control',    'jurisdiction', 'county'),
  ('resource.yavapai_vector_control',  'jurisdiction', 'county'),
  ('resource.yuma_vector_control',     'jurisdiction', 'county'),
  ('resource.cochise_vector_control',  'url', 'https://www.cochise.az.gov/460/Environmental-Health-Services-Division'),
  ('resource.mohave_vector_control',   'url', 'https://www.mohave.gov/departments/public-health/environmental-health/'),
  ('resource.pinal_vector_control',    'url', 'https://www.pinal.gov/962/Vector-Control-Program'),
  ('resource.yavapai_vector_control',  'url', 'https://www.yavapaiaz.gov/Resident-Services/Environmental-Safety/Environmental-Disease-Control'),
  ('resource.yuma_vector_control',     'url', 'https://www.yumacountyaz.gov/government/health-district/divisions/environmental-health-services/vector-control-mosquito-control-and-prevention')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. Edges: county --hasResource--> health department / vector control
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  -- county -> health department
  (12001, 'county.apache',     'hasResource', 'resource.apache_hd',     'deep-counties'),
  (12002, 'county.cochise',    'hasResource', 'resource.cochise_hd',    'deep-counties'),
  (12003, 'county.coconino',   'hasResource', 'resource.coconino_hhs',  'deep-counties'),
  (12004, 'county.gila',       'hasResource', 'resource.gila_hd',       'deep-counties'),
  (12005, 'county.graham',     'hasResource', 'resource.graham_hd',     'deep-counties'),
  (12006, 'county.greenlee',   'hasResource', 'resource.greenlee_hd',   'deep-counties'),
  (12007, 'county.la_paz',     'hasResource', 'resource.la_paz_hd',     'deep-counties'),
  (12008, 'county.maricopa',   'hasResource', 'resource.mcdph_mcesd',   'deep-counties'),
  (12009, 'county.mohave',     'hasResource', 'resource.mohave_hd',     'deep-counties'),
  (12010, 'county.navajo',     'hasResource', 'resource.navajo_hd',     'deep-counties'),
  (12011, 'county.pima',       'hasResource', 'resource.pcdh',          'deep-counties'),
  (12012, 'county.pinal',      'hasResource', 'resource.pinal_hd',      'deep-counties'),
  (12013, 'county.santa_cruz', 'hasResource', 'resource.santa_cruz_hd', 'deep-counties'),
  (12014, 'county.yavapai',    'hasResource', 'resource.yavapai_hd',    'deep-counties'),
  (12015, 'county.yuma',       'hasResource', 'resource.yuma_hd',       'deep-counties'),
  -- county -> vector control (only where a distinct program exists)
  (12101, 'county.cochise',    'hasResource', 'resource.cochise_vector_control', 'deep-counties'),
  (12102, 'county.coconino',   'hasResource', 'resource.coconino_hhs',           'deep-counties'),
  (12103, 'county.maricopa',   'hasResource', 'resource.mcdph_mcesd',            'deep-counties'),
  (12104, 'county.mohave',     'hasResource', 'resource.mohave_vector_control',  'deep-counties'),
  (12105, 'county.pima',       'hasResource', 'resource.pcdh',                   'deep-counties'),
  (12106, 'county.pinal',      'hasResource', 'resource.pinal_vector_control',   'deep-counties'),
  (12107, 'county.yavapai',    'hasResource', 'resource.yavapai_vector_control', 'deep-counties'),
  (12108, 'county.yuma',       'hasResource', 'resource.yuma_vector_control',    'deep-counties')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 5. Edges: vector-control resources --informs--> wv.q1 and wv.q2
--    (Maricopa, Pima, Coconino already wired to wv.q1/wv.q2 in wildlife_vectors.sql)
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 12200 + row_number() OVER (), subject_id, 'informs', object_id, 'deep-counties'
FROM (VALUES
  ('resource.cochise_vector_control', 'wv.q1'),
  ('resource.cochise_vector_control', 'wv.q2'),
  ('resource.mohave_vector_control',  'wv.q1'),
  ('resource.mohave_vector_control',  'wv.q2'),
  ('resource.pinal_vector_control',   'wv.q1'),
  ('resource.pinal_vector_control',   'wv.q2'),
  ('resource.yavapai_vector_control', 'wv.q1'),
  ('resource.yavapai_vector_control', 'wv.q2'),
  ('resource.yuma_vector_control',    'wv.q1'),
  ('resource.yuma_vector_control',    'wv.q2')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6. Edges: each county HD --informs--> heat.q4 (vulnerable populations)
--                                      --informs--> wv.q2 (zoonotic)
--    Includes the three pre-existing HD/vector nodes (mcdph_mcesd, pcdh,
--    coconino_hhs) for consistency.
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 12300 + row_number() OVER (), subject_id, 'informs', object_id, 'deep-counties'
FROM (VALUES
  -- heat.q4 (vulnerable populations)
  ('resource.apache_hd',     'heat.q4'),
  ('resource.cochise_hd',    'heat.q4'),
  ('resource.coconino_hhs',  'heat.q4'),
  ('resource.gila_hd',       'heat.q4'),
  ('resource.graham_hd',     'heat.q4'),
  ('resource.greenlee_hd',   'heat.q4'),
  ('resource.la_paz_hd',     'heat.q4'),
  ('resource.mcdph_mcesd',   'heat.q4'),
  ('resource.mohave_hd',     'heat.q4'),
  ('resource.navajo_hd',     'heat.q4'),
  ('resource.pcdh',          'heat.q4'),
  ('resource.pinal_hd',      'heat.q4'),
  ('resource.santa_cruz_hd', 'heat.q4'),
  ('resource.yavapai_hd',    'heat.q4'),
  ('resource.yuma_hd',       'heat.q4'),
  -- wv.q2 (zoonotic surveillance)
  ('resource.apache_hd',     'wv.q2'),
  ('resource.cochise_hd',    'wv.q2'),
  ('resource.coconino_hhs',  'wv.q2'),
  ('resource.gila_hd',       'wv.q2'),
  ('resource.graham_hd',     'wv.q2'),
  ('resource.greenlee_hd',   'wv.q2'),
  ('resource.la_paz_hd',     'wv.q2'),
  ('resource.mcdph_mcesd',   'wv.q2'),
  ('resource.mohave_hd',     'wv.q2'),
  ('resource.navajo_hd',     'wv.q2'),
  ('resource.pcdh',          'wv.q2'),
  ('resource.pinal_hd',      'wv.q2'),
  ('resource.santa_cruz_hd', 'wv.q2'),
  ('resource.yavapai_hd',    'wv.q2'),
  ('resource.yuma_hd',       'wv.q2')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 7. Convenience view: counties with their HD + vector-control resources
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_county_resources AS
SELECT
  c.node_id      AS county_id,
  c.label        AS county,
  seat.value_text AS county_seat,
  pop.value_num   AS population_approx,
  hd_url.value_text AS health_dept_url,
  string_agg(DISTINCT r.label, '; ' ORDER BY r.label) AS resources
FROM kg.node c
LEFT JOIN kg.property seat   ON seat.node_id   = c.node_id AND seat.key   = 'county_seat'
LEFT JOIN kg.property pop    ON pop.node_id    = c.node_id AND pop.key    = 'population_approx'
LEFT JOIN kg.property hd_url ON hd_url.node_id = c.node_id AND hd_url.key = 'health_dept_url'
LEFT JOIN kg.edge   e ON e.subject_id = c.node_id AND e.predicate = 'hasResource'
LEFT JOIN kg.node   r ON r.node_id = e.object_id
WHERE c.node_type = 'county'
GROUP BY c.node_id, c.label, seat.value_text, pop.value_num, hd_url.value_text;
