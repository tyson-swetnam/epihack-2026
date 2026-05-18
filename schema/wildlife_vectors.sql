-- ============================================================================
-- EpiHack Arizona 2026 -- Wildlife / Vector-Borne Diseases focus group
--
-- Captures the focus group, its four guiding questions, the anchor
-- data resources (state, county, tribal, federal, academic,
-- citizen-science), and a draft system_design that applies the
-- worksheet template to wildlife disease participatory surveillance.
--
-- Run *after* schema/knowledge_graph.sql and schema/system_designs.sql.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- The focus group itself
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('group.wildlife_vectors',
     'focus_group',
     'Wildlife / Vector-Borne Diseases',
     'EpiHack Arizona 2026 focus group on wildlife and vector-borne disease participatory surveillance in Arizona.',
     'wildlife-vectors-group')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- New focus areas surfaced by this group
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, source_fig) VALUES
  ('focus.vector_borne',         'focus_area', 'Vector-borne disease',                    'wildlife-vectors-group'),
  ('focus.mosquito',             'focus_area', 'Mosquitoes',                              'wildlife-vectors-group'),
  ('focus.tick',                 'focus_area', 'Ticks',                                   'wildlife-vectors-group'),
  ('focus.flea',                 'focus_area', 'Fleas',                                   'wildlife-vectors-group'),
  ('focus.rodent',               'focus_area', 'Rodents',                                 'wildlife-vectors-group'),
  ('focus.zoonotic',             'focus_area', 'Zoonotic infections (general)',           'wildlife-vectors-group'),
  ('focus.cwd',                  'focus_area', 'Chronic wasting disease (CWD)',           'wildlife-vectors-group'),
  ('focus.hpai',                 'focus_area', 'Highly pathogenic avian influenza (HPAI)','wildlife-vectors-group'),
  ('focus.plague',               'focus_area', 'Plague (Yersinia pestis)',                'wildlife-vectors-group'),
  ('focus.hantavirus',           'focus_area', 'Hantavirus (Sin Nombre)',                 'wildlife-vectors-group'),
  ('focus.rabies',               'focus_area', 'Rabies',                                  'wildlife-vectors-group'),
  ('focus.wnv',                  'focus_area', 'West Nile virus',                         'wildlife-vectors-group'),
  ('focus.rmsf',                 'focus_area', 'Rocky Mountain spotted fever',            'wildlife-vectors-group'),
  ('focus.tularemia',            'focus_area', 'Tularemia',                               'wildlife-vectors-group')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- The four guiding questions
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('wv.q1', 'group_question', 'WV Q1 — Wildlife & vector density tracking',
     'How does Arizona track wildlife? How do they monitor the density of mosquitoes, ticks and fleas? Rodents?',
     'wv-q1-wildlife-tracking'),
  ('wv.q2', 'group_question', 'WV Q2 — Zoonotic surveillance in wildlife / vectors',
     'How does Arizona monitor wildlife and/or vectors for presence or absence of zoonotic infections?',
     'wv-q2-zoonotic-surveillance'),
  ('wv.q3', 'group_question', 'WV Q3 — Technologies to improve surveillance',
     'What technologies could improve surveillance in this sector(s)?',
     'wv-q3-surveillance-technologies'),
  ('wv.q4', 'group_question', 'WV Q4 — Participatory surveillance for wildlife disease',
     'How can wildlife diseases be better tracked using Participatory Surveillance?',
     'wv-q4-participatory-surveillance')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_num) VALUES
  ('wv.q1','question_number',1),
  ('wv.q2','question_number',2),
  ('wv.q3','question_number',3),
  ('wv.q4','question_number',4)
ON CONFLICT DO NOTHING;

-- Question -> group
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (7000, 'wv.q1', 'partOf', 'group.wildlife_vectors', 'wildlife-vectors-group'),
  (7001, 'wv.q2', 'partOf', 'group.wildlife_vectors', 'wildlife-vectors-group'),
  (7002, 'wv.q3', 'partOf', 'group.wildlife_vectors', 'wildlife-vectors-group'),
  (7003, 'wv.q4', 'partOf', 'group.wildlife_vectors', 'wildlife-vectors-group')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Data resources / programs
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  -- State
  ('resource.adhs',                'resource_org', 'Arizona Department of Health Services (ADHS)',
     'Statewide public-health authority; operates the Vector-Borne & Zoonotic Diseases program and Arizona State Public Health Laboratory.', 'wv-resources'),
  ('program.adhs_vbzd',            'program',      'ADHS Vector-Borne & Zoonotic Diseases',
     'WNV, SLE, dengue, Zika, hantavirus, plague, tularemia, rabies, RMSF surveillance; arboviral syndromic surveillance.', 'wv-resources'),
  ('resource.azgfd',               'resource_org', 'Arizona Game and Fish Department (AZGFD)',
     'Wildlife data authority for Arizona; Wildlife Health Program; CWD and HPAI surveillance; public mortality reporting.', 'wv-resources'),
  ('program.azgfd_wildlife_health','program',      'AZGFD Wildlife Health Program',
     'Investigates wildlife morbidity and mortality; runs CWD surveillance (>25,000 samples since 1998) and HPAI wild-bird monitoring.', 'wv-resources'),
  ('resource.az_agriculture',      'resource_org', 'Arizona Department of Agriculture', NULL, 'wv-resources'),
  ('initiative.arizona_one_health','initiative',   'Arizona One Health',
     'Multi-agency initiative coordinating ADHS, AZGFD, AZ Agriculture, USDA APHIS, AZVDL, CDC, and UA on zoonotic disease.', 'wv-resources'),

  -- County
  ('resource.mcdph_mcesd',         'resource_org', 'Maricopa County (MCDPH + MCESD Vector Control)',
     'Operates 800+ vector traps county-wide; weekly Vector Index for WNV and SLE; Fight the Bite Maricopa public site.', 'wv-resources'),
  ('resource.pcdh',                'resource_org', 'Pima County Health Department — Vector Control',
     'Mosquito surveillance May–November; Culex tarsalis / Culex quinquefasciatus focus; free Gila topminnow biological control program.', 'wv-resources'),
  ('resource.coconino_hhs',        'resource_org', 'Coconino County Health and Human Services',
     'Northern AZ surveillance for hantavirus, plague, WNV, and rabies; partners with NPS at Grand Canyon.', 'wv-resources'),

  -- Tribal
  ('resource.navajo_ec',           'resource_org', 'Navajo Epidemiology Center',
     'Established 2005; manages Navajo Nation public-health information systems; Navajo Nation Health Survey (BRFSS adaptation).', 'wv-resources'),
  ('resource.itca_tec',            'resource_org', 'Inter Tribal Council of Arizona — Tribal Epidemiology Center (ITCA-TEC)',
     'Builds tribally-driven public-health and epidemiologic capacity across Phoenix and Tucson IHS Areas.', 'wv-resources'),
  ('resource.navajo_fish_wildlife','resource_org', 'Navajo Nation Department of Fish and Wildlife',
     'Wildlife authority for the largest U.S. reservation; plague is endemic and locally tracked.', 'wv-resources'),
  ('resource.tohono_oodham_hhs',   'resource_org', 'Tohono O''odham Nation Health and Human Services',
     'Tribal HHS for ~28,000 members across 2.8M acres in southwestern Arizona; Sells Indian Hospital.', 'wv-resources'),
  ('resource.ihs_phoenix',         'resource_org', 'Indian Health Service — Phoenix Area',
     'Covers AZ, NV, UT for ~180,000 AI/AN users.', 'wv-resources'),
  ('resource.ihs_tucson',          'resource_org', 'Indian Health Service — Tucson Area', NULL, 'wv-resources'),

  -- Federal
  ('resource.cdc_one_health',      'resource_org', 'CDC One Health Office',
     'Federal coordination on One Health; co-author of the 2023 National One Health Framework with USDA and DOI.', 'wv-resources'),
  ('resource.usda_aphis_ws',       'resource_org', 'USDA APHIS Wildlife Services (Arizona program)',
     'Predation management, urban coyotes, endangered species, zoonotic diseases (plague, rabies).', 'wv-resources'),
  ('program.aphis_sers',           'program',      'USDA APHIS Surveillance and Emergency Response System (SERS)',
     'Nationally coordinated wildlife disease monitoring infrastructure.', 'wv-resources'),
  ('resource.usda_aphis_vs',       'resource_org', 'USDA APHIS Veterinary Services', NULL, 'wv-resources'),
  ('resource.usgs_nwhc',           'resource_org', 'USGS National Wildlife Health Center (NWHC)',
     'Federal wildlife disease center; maintains the National Wildlife Disease Database and WHISPers event-reporting system.', 'wv-resources'),
  ('program.whispers',             'program',      'WHISPers (Wildlife Health Information Sharing Partnership)',
     'Web repository of historic and current wildlife mortality/morbidity events; portal for NWHC diagnostic services.', 'wv-resources'),
  ('resource.usfws_az',            'resource_org', 'U.S. Fish and Wildlife Service — Arizona Offices',
     'Administers ~1.8M acres in AZ via refuges and hatcheries; coordinates HPAI surveillance and ARPA Zoonotic Disease Grant for AZ ($134,320).', 'wv-resources'),
  ('resource.nps_az',              'resource_org', 'National Park Service (Arizona units)',
     'Grand Canyon, Saguaro, and other AZ NPS units; partners with county HHS on hantavirus, plague, WNV, rabies.', 'wv-resources'),
  ('resource.blm_az',              'resource_org', 'Bureau of Land Management (Arizona)',
     'AIM TerrADat rangeland vegetation indicators useful as vector-habitat covariates.', 'wv-resources'),
  ('resource.usfs_az',             'resource_org', 'U.S. Forest Service (Arizona national forests)', NULL, 'wv-resources'),

  -- Academic / research
  ('resource.neon',                'resource_org', 'National Ecological Observatory Network (NEON)',
     'NSF-funded, Battelle-operated 30-year continental ecological observatory; standardized mosquito, tick, rodent, bird data.', 'wv-resources'),
  ('program.neon_srer',            'program',      'NEON Santa Rita Experimental Range (SRER) site',
     'Arizona NEON core terrestrial site in Domain 14 Desert Southwest; six tick plots and ten mosquito points.', 'wv-resources'),
  ('program.neon_biorepository',   'program',      'NEON Biorepository at ASU',
     'Hosted at Arizona State University; voucher specimens of carabids and mosquitoes plus DNA extracts.', 'wv-resources'),
  ('resource.ua_mezcoph',          'resource_org', 'UA Mel & Enid Zuckerman College of Public Health — One Health Initiative',
     'Bridges ~10 UA colleges and 20+ departments on One Health research and education.', 'wv-resources'),
  ('resource.ua_extension_tickcheck','resource_org','UA Cooperative Extension — Great Arizona Tick Check',
     'Statewide participatory tick surveillance led by Dr. Kathleen Walker (UA Entomology) with ADHS and MEZCOPH; ~$1M CDC grant.', 'wv-resources'),
  ('resource.azvdl',               'resource_org', 'Arizona Veterinary Diagnostic Laboratory (AZVDL)',
     'UA College of Veterinary Medicine; AAVLD-accredited; NAHLN Level 2; ~13,000 tests/year including HPAI surveillance.', 'wv-resources'),
  ('resource.nau_pmi',             'resource_org', 'NAU Pathogen and Microbiome Institute',
     'Plague (Y. pestis) genomic surveillance under Dr. Dave Wagner; partner with TGen North.', 'wv-resources'),
  ('resource.tgen',                'resource_org', 'Translational Genomics Research Institute (TGen)',
     'Phoenix-based genomics institute; pathogen sequencing partner for AZ.', 'wv-resources'),
  ('resource.asu_biodesign',       'resource_org', 'ASU Biodesign Institute',
     'Wastewater-based epidemiology research (Halden lab); hosts NEON Biorepository.', 'wv-resources'),

  -- Participatory / citizen science
  ('resource.inaturalist',         'resource_org', 'iNaturalist',
     'Global citizen-science platform for biodiversity observations; 200M+ observations; data published to GBIF.', 'wv-resources'),
  ('resource.ebird',               'resource_org', 'eBird (Cornell Lab of Ornithology)',
     'Dominant bird-observation citizen-science platform; complementary to iNaturalist for HPAI early warning.', 'wv-resources'),
  ('resource.gbif',                'resource_org', 'Global Biodiversity Information Facility (GBIF)',
     'International aggregator of biodiversity observation data including iNaturalist and eBird feeds.', 'wv-resources'),
  ('resource.fightthebite',        'resource_org', 'Fight the Bite Maricopa',
     'Public-facing communication and trap-location hub from Maricopa County Vector Control.', 'wv-resources')
ON CONFLICT DO NOTHING;

-- Jurisdiction property
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.adhs',                'jurisdiction', 'state'),
  ('resource.azgfd',               'jurisdiction', 'state'),
  ('resource.az_agriculture',      'jurisdiction', 'state'),
  ('resource.mcdph_mcesd',         'jurisdiction', 'county'),
  ('resource.pcdh',                'jurisdiction', 'county'),
  ('resource.coconino_hhs',        'jurisdiction', 'county'),
  ('resource.navajo_ec',           'jurisdiction', 'tribal'),
  ('resource.itca_tec',            'jurisdiction', 'tribal'),
  ('resource.navajo_fish_wildlife','jurisdiction', 'tribal'),
  ('resource.tohono_oodham_hhs',   'jurisdiction', 'tribal'),
  ('resource.ihs_phoenix',         'jurisdiction', 'federal_tribal'),
  ('resource.ihs_tucson',          'jurisdiction', 'federal_tribal'),
  ('resource.cdc_one_health',      'jurisdiction', 'federal'),
  ('resource.usda_aphis_ws',       'jurisdiction', 'federal'),
  ('resource.usda_aphis_vs',       'jurisdiction', 'federal'),
  ('resource.usgs_nwhc',           'jurisdiction', 'federal'),
  ('resource.usfws_az',            'jurisdiction', 'federal'),
  ('resource.nps_az',              'jurisdiction', 'federal'),
  ('resource.blm_az',              'jurisdiction', 'federal'),
  ('resource.usfs_az',             'jurisdiction', 'federal'),
  ('resource.neon',                'jurisdiction', 'federal_funded_research'),
  ('resource.ua_mezcoph',          'jurisdiction', 'academic'),
  ('resource.ua_extension_tickcheck','jurisdiction','academic'),
  ('resource.azvdl',               'jurisdiction', 'academic'),
  ('resource.nau_pmi',             'jurisdiction', 'academic'),
  ('resource.tgen',                'jurisdiction', 'academic'),
  ('resource.asu_biodesign',       'jurisdiction', 'academic'),
  ('resource.inaturalist',         'jurisdiction', 'citizen_science'),
  ('resource.ebird',               'jurisdiction', 'citizen_science'),
  ('resource.gbif',                'jurisdiction', 'international'),
  ('resource.fightthebite',        'jurisdiction', 'county')
ON CONFLICT DO NOTHING;

-- URLs
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.adhs',                'url','https://www.azdhs.gov/'),
  ('resource.azgfd',               'url','https://www.azgfd.com/'),
  ('resource.az_agriculture',      'url','https://agriculture.az.gov/'),
  ('resource.mcdph_mcesd',         'url','https://www.maricopa.gov/632/Vector-Control'),
  ('resource.pcdh',                'url','https://www.pima.gov/2296/Vector-Control-Program'),
  ('resource.navajo_ec',           'url','https://nec.navajo-nsn.gov/'),
  ('resource.itca_tec',            'url','https://itcaonline.com/programs/research-and-evaluation/epidemiology/'),
  ('resource.tohono_oodham_hhs',   'url','https://www.tonation-nsn.gov/health-human-services/'),
  ('resource.ihs_phoenix',         'url','https://www.ihs.gov/phoenix/'),
  ('resource.cdc_one_health',      'url','https://www.cdc.gov/one-health/'),
  ('resource.usda_aphis_ws',       'url','https://www.aphis.usda.gov/wildlife-services'),
  ('resource.usgs_nwhc',           'url','https://www.usgs.gov/centers/nwhc'),
  ('program.whispers',             'url','https://whispers.usgs.gov/'),
  ('resource.usfws_az',            'url','https://www.fws.gov/office/arizona-ecological-services'),
  ('resource.nps_az',              'url','https://www.nps.gov/grca/learn/nature/zoonotic_diseases.htm'),
  ('resource.blm_az',              'url','https://www.blm.gov/aim'),
  ('resource.neon',                'url','https://www.neonscience.org/'),
  ('resource.ua_mezcoph',          'url','https://publichealth.arizona.edu/one-health-initiative'),
  ('resource.ua_extension_tickcheck','url','https://extension.arizona.edu/programs/great-arizona-tick-check'),
  ('resource.azvdl',               'url','https://azvdl.arizona.edu/'),
  ('resource.nau_pmi',             'url','https://in.nau.edu/pmi/'),
  ('resource.tgen',                'url','https://www.tgen.org/'),
  ('resource.asu_biodesign',       'url','https://biodesign.asu.edu/'),
  ('resource.inaturalist',         'url','https://www.inaturalist.org/'),
  ('resource.ebird',               'url','https://ebird.org/'),
  ('resource.gbif',                'url','https://www.gbif.org/'),
  ('resource.fightthebite',        'url','https://fightthebitemaricopa.org/')
ON CONFLICT DO NOTHING;

-- Programs belonging to parent resources
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 7100 + row_number() OVER (), subject_id, 'operatedBy', object_id, 'wv-resources'
FROM (VALUES
  ('program.adhs_vbzd',            'resource.adhs'),
  ('program.azgfd_wildlife_health','resource.azgfd'),
  ('program.aphis_sers',           'resource.usda_aphis_ws'),
  ('program.whispers',             'resource.usgs_nwhc'),
  ('program.neon_srer',            'resource.neon'),
  ('program.neon_biorepository',   'resource.neon')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- Resources informing each guiding question (most resources inform Q1 and Q2;
-- the participatory ones inform Q4)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 7200 + row_number() OVER (), subject_id, 'informs', object_id, 'wv-resources'
FROM (VALUES
  -- Q1 (density tracking)
  ('resource.mcdph_mcesd',         'wv.q1'),
  ('resource.pcdh',                'wv.q1'),
  ('resource.azgfd',               'wv.q1'),
  ('resource.neon',                'wv.q1'),
  ('resource.blm_az',              'wv.q1'),
  ('resource.ua_extension_tickcheck','wv.q1'),
  -- Q2 (zoonotic surveillance)
  ('resource.adhs',                'wv.q2'),
  ('resource.azgfd',               'wv.q2'),
  ('resource.usgs_nwhc',           'wv.q2'),
  ('resource.usda_aphis_ws',       'wv.q2'),
  ('resource.usfws_az',            'wv.q2'),
  ('resource.azvdl',               'wv.q2'),
  ('resource.nau_pmi',             'wv.q2'),
  ('resource.tgen',                'wv.q2'),
  ('resource.neon',                'wv.q2'),
  -- Q3 (technologies) — research labs are the principal informers
  ('resource.asu_biodesign',       'wv.q3'),
  ('resource.nau_pmi',             'wv.q3'),
  ('resource.tgen',                'wv.q3'),
  ('resource.ua_mezcoph',          'wv.q3'),
  -- Q4 (participatory)
  ('resource.ua_extension_tickcheck','wv.q4'),
  ('resource.inaturalist',         'wv.q4'),
  ('resource.ebird',               'wv.q4'),
  ('resource.fightthebite',        'wv.q4'),
  ('resource.azgfd',               'wv.q4'),
  ('resource.navajo_ec',           'wv.q4'),
  ('resource.itca_tec',            'wv.q4'),
  ('resource.tohono_oodham_hhs',   'wv.q4'),
  ('resource.navajo_fish_wildlife','wv.q4')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- The draft participatory-surveillance system design for wildlife disease
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('design.wildlife_vectors_az',
     'system_design',
     'Arizona Wildlife & Vector-Borne Disease Participatory Surveillance (draft)',
     'A draft participatory-surveillance system for AZ wildlife / vectors that fuses AZGFD, ADHS, NEON, and tribal data with community reports.',
     'wv-q4-participatory-surveillance')
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (7300, 'design.wildlife_vectors_az', 'addressesQuestion', 'wv.q4',                  'wv-q4-participatory-surveillance'),
  (7301, 'design.wildlife_vectors_az', 'instantiates',      'template.worksheet_v1',  'wv-q4-participatory-surveillance')
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 7310 + row_number() OVER (), 'design.wildlife_vectors_az', 'targetsFocusArea', object_id, 'wv-q4-participatory-surveillance'
FROM (VALUES
  ('focus.wildlife'),
  ('focus.urban_wildlife_interface'),
  ('focus.vector_borne'),
  ('focus.mosquito'),
  ('focus.tick'),
  ('focus.flea'),
  ('focus.rodent'),
  ('focus.zoonotic'),
  ('focus.hpai'),
  ('focus.plague'),
  ('focus.wnv'),
  ('focus.hantavirus'),
  ('focus.rmsf')
) AS t(object_id)
ON CONFLICT DO NOTHING;

-- The design uses each resource
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 7400 + row_number() OVER (), 'design.wildlife_vectors_az', 'usesResource', object_id, 'wv-q4-participatory-surveillance'
FROM (VALUES
  ('resource.azgfd'),
  ('resource.adhs'),
  ('resource.neon'),
  ('resource.ua_extension_tickcheck'),
  ('resource.usgs_nwhc'),
  ('resource.usda_aphis_ws'),
  ('resource.usfws_az'),
  ('resource.mcdph_mcesd'),
  ('resource.pcdh'),
  ('resource.coconino_hhs'),
  ('resource.navajo_ec'),
  ('resource.itca_tec'),
  ('resource.inaturalist'),
  ('resource.ebird'),
  ('resource.azvdl'),
  ('resource.nau_pmi'),
  ('resource.ua_mezcoph')
) AS t(object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Convenience view: resources grouped by jurisdiction with linked questions
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_wildlife_resources AS
SELECT
  r.node_id     AS resource_id,
  r.label       AS resource,
  j.value_text  AS jurisdiction,
  u.value_text  AS url,
  r.description AS description,
  string_agg(DISTINCT q.label, '; ') AS informs_questions
FROM kg.node r
LEFT JOIN kg.property j ON j.node_id = r.node_id AND j.key = 'jurisdiction'
LEFT JOIN kg.property u ON u.node_id = r.node_id AND u.key = 'url'
LEFT JOIN kg.edge   e   ON e.subject_id = r.node_id AND e.predicate = 'informs'
LEFT JOIN kg.node   q   ON q.node_id = e.object_id
WHERE r.node_type = 'resource_org'
GROUP BY r.node_id, r.label, j.value_text, u.value_text, r.description;
