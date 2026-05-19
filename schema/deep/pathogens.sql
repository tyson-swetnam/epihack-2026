-- ============================================================================
-- EpiHack Arizona 2026 -- Deep dive: Pathogens (Arizona wildlife / vector-borne
-- and heat-adjacent emerging threats)
--
-- Adds:
--   * pathogen.<slug>    nodes  (15 pathogens of AZ One Health relevance)
--   * vector.<slug>      nodes  (arthropod vectors known from AZ surveillance)
--   * reservoir.<slug>   nodes  (mammalian / avian reservoir hosts)
--   * disease.<slug>     nodes  (clinical syndromes — kept distinct from the
--                                pathogen itself, e.g. plague vs Y. pestis)
--   * kg.edge rows linking each pathogen to its vectors, reservoirs, the AZ
--     surveillance resources that monitor it, and the focus areas it falls
--     under  (see header for new predicates)
--   * kg.property rows capturing scientific name, recent AZ case counts (with
--     year), primary seasonality, notifiable status, and ICD-10 code(s).
--
-- Depends on (run first):
--   schema/knowledge_graph.sql     -- kg.node / kg.edge / kg.property tables,
--                                     focus_area + resource_org seed rows
--   schema/wildlife_vectors.sql    -- focus.* and resource.* IDs referenced
--                                     below (focus.plague, focus.wnv, ...,
--                                     resource.adhs, resource.azgfd, ...)
--   schema/heat.sql                -- heat focus areas (not referenced
--                                     directly, but provides context for
--                                     "heat-adjacent" pathogens like Valley
--                                     Fever and the climate-shifted vector
--                                     range expansion edges)
--
-- New predicates (documented here so downstream readers don't need to guess):
--   transmittedBy   pathogen  -> vector       (Aedes aegypti, Xenopsylla cheopis, ...)
--   reservoirIn     pathogen  -> reservoir    (deer mouse, prairie dog, ...)
--   causes          pathogen  -> disease      (Y. pestis -> plague)
--   surveilledBy    pathogen  -> resource_org (ADHS, AZGFD, USGS NWHC, ...)
--   endemicIn       pathogen  -> geography    (encoded as value_text property
--                                              when geography node doesn't
--                                              exist yet -- see kg.property)
--   targetsFocusArea pathogen -> focus_area   (reuses existing predicate)
--
-- edge_id range: 10000 - 10999  (this agent owns this block)
-- source_fig:    'deep-pathogens' for all rows below
-- All inserts are idempotent (ON CONFLICT DO NOTHING).
--
-- Case counts are sourced from ADHS, MCDPH, CDC, and peer-reviewed reports as
-- of May 2026; see kg.property row 'count_source' for citations. Where exact
-- AZ-only counts were not separable from regional / national totals we record
-- the closest defensible figure and flag it 'approximate'.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- VECTORS  (arthropods known to transmit listed pathogens in or near AZ)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('vector.culex_tarsalis',       'vector', 'Culex tarsalis',
     'Western encephalitis mosquito; primary enzootic / bridge vector of WNV and SLEV in the AZ desert Southwest; peaks late summer.', 'deep-pathogens'),
  ('vector.culex_quinquefasciatus','vector','Culex quinquefasciatus',
     'Southern house mosquito; principal urban WNV vector in Maricopa County; also competent for SLEV.', 'deep-pathogens'),
  ('vector.aedes_aegypti',        'vector', 'Aedes aegypti',
     'Yellow-fever mosquito; established in Phoenix, Tucson, Yuma; vector of dengue, Zika, chikungunya, yellow fever.', 'deep-pathogens'),
  ('vector.aedes_albopictus',     'vector', 'Aedes albopictus',
     'Asian tiger mosquito; detected in AZ since 2015 (Maricopa); secondary dengue/Zika vector.', 'deep-pathogens'),
  ('vector.rhipicephalus_sanguineus','vector','Rhipicephalus sanguineus (brown dog tick)',
     'Brown dog tick; principal RMSF vector in AZ tribal communities (unique to AZ/NW Mexico); active year-round in/around homes.', 'deep-pathogens'),
  ('vector.ixodes_pacificus',     'vector', 'Ixodes pacificus (western black-legged tick)',
     'Western black-legged tick; documented in Mohave County Hualapai Mountains spring 2024 by Great AZ Tick Check; competent Lyme vector (no AZ Bb+ ticks yet).', 'deep-pathogens'),
  ('vector.dermacentor_andersoni','vector', 'Dermacentor andersoni (Rocky Mountain wood tick)',
     'Rocky Mountain wood tick; tularemia and Colorado tick fever vector at higher AZ elevations.', 'deep-pathogens'),
  ('vector.dermacentor_variabilis','vector','Dermacentor variabilis (American dog tick)',
     'American dog tick; minor RMSF and tularemia vector; range edge in AZ.', 'deep-pathogens'),
  ('vector.oropsylla_montana',    'vector', 'Oropsylla montana (ground-squirrel flea)',
     'Ground-squirrel flea; principal plague vector to humans in the US Southwest including northern AZ.', 'deep-pathogens'),
  ('vector.xenopsylla_cheopis',   'vector', 'Xenopsylla cheopis (oriental rat flea)',
     'Oriental rat flea; historic plague vector via commensal rats; minor role in AZ today.', 'deep-pathogens')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- RESERVOIRS  (mammalian / avian / environmental hosts in AZ)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('reservoir.passerine_birds',   'reservoir','Passerine birds (corvids, house sparrows, house finches)',
     'Amplifying hosts for WNV and SLEV; dead-corvid surveillance is an AZ early-warning tool.', 'deep-pathogens'),
  ('reservoir.deer_mouse',        'reservoir','Peromyscus maniculatus (deer mouse)',
     'Principal reservoir of Sin Nombre hantavirus across the AZ Colorado Plateau and Four Corners.', 'deep-pathogens'),
  ('reservoir.gunnisons_prairie_dog','reservoir','Gunnison''s prairie dog (Cynomys gunnisoni)',
     'Highly susceptible plague host; massive die-offs signal Y. pestis circulation on the AZ/NM plateau.', 'deep-pathogens'),
  ('reservoir.rock_squirrel',     'reservoir','Rock squirrel (Otospermophilus variegatus)',
     'Common AZ plague-positive sciurid; frequent source of human exposure via fleas.', 'deep-pathogens'),
  ('reservoir.cottontail_rabbit', 'reservoir','Desert / mountain cottontail (Sylvilagus spp.)',
     'Reservoir for tularemia and a host for RMSF-vector ticks; mortality events trigger investigations.', 'deep-pathogens'),
  ('reservoir.black_tailed_jackrabbit','reservoir','Black-tailed jackrabbit (Lepus californicus)',
     'Tularemia reservoir / amplifier in AZ rangelands.', 'deep-pathogens'),
  ('reservoir.domestic_dog',      'reservoir','Domestic dog (Canis lupus familiaris)',
     'Maintains R. sanguineus tick populations sustaining RMSF in AZ tribal communities; sentinel for canine leptospirosis.', 'deep-pathogens'),
  ('reservoir.bats',              'reservoir','Bats (multiple AZ species)',
     'Lyssavirus reservoirs; bat-strain rabies dominates AZ human exposures.', 'deep-pathogens'),
  ('reservoir.striped_skunk',     'reservoir','Striped skunk (Mephitis mephitis)',
     'AZ rabies reservoir; skunk-strain epizootics in Cochise/Coconino.', 'deep-pathogens'),
  ('reservoir.gray_fox',          'reservoir','Gray fox (Urocyon cinereoargenteus)',
     'AZ fox-strain rabies reservoir; rising 2024-2025 case counts in Navajo and southern AZ counties.', 'deep-pathogens'),
  ('reservoir.wild_waterfowl',    'reservoir','Wild waterfowl & shorebirds',
     'Natural reservoir for HPAI H5N1; AZ migratory flyway brings periodic spillovers.', 'deep-pathogens'),
  ('reservoir.dairy_cattle',      'reservoir','Dairy cattle',
     'Novel HPAI H5N1 D1.1 mammalian host; first AZ detection Maricopa County Feb 2025 (third US spillover lineage).', 'deep-pathogens'),
  ('reservoir.mule_deer_elk',     'reservoir','Mule deer and Rocky Mountain elk',
     'Cervid hosts targeted by AZGFD CWD surveillance; AZ remains CWD-free as of 2024 (n=1,543 sampled).', 'deep-pathogens'),
  ('reservoir.desert_soil',       'reservoir','Desert soil (Lower Sonoran life zone)',
     'Environmental reservoir for Coccidioides immitis/posadasii; aerosolized by wind, construction, and post-monsoon dust events.', 'deep-pathogens'),
  ('reservoir.rodents_commensal', 'reservoir','Commensal rodents (Rattus, Mus)',
     'Reservoirs/maintenance hosts for Leptospira, plague (historical), and zoonotic spillover bridges in urban AZ.', 'deep-pathogens'),
  ('reservoir.primates_human',    'reservoir','Humans (urban Aedes cycle)',
     'In urban dengue/Zika cycles, humans serve as the amplifying reservoir between Aedes aegypti bites.', 'deep-pathogens')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- DISEASES  (clinical syndromes distinct from the pathogen node)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, source_fig) VALUES
  ('disease.west_nile_fever',      'disease','West Nile fever / neuroinvasive disease',  'deep-pathogens'),
  ('disease.sle',                  'disease','St. Louis encephalitis',                   'deep-pathogens'),
  ('disease.dengue_fever',         'disease','Dengue fever / severe dengue',             'deep-pathogens'),
  ('disease.zika',                 'disease','Zika virus disease and congenital Zika',   'deep-pathogens'),
  ('disease.hps',                  'disease','Hantavirus (cardio)pulmonary syndrome',    'deep-pathogens'),
  ('disease.plague',               'disease','Plague (bubonic / septicemic / pneumonic)','deep-pathogens'),
  ('disease.tularemia',            'disease','Tularemia (rabbit fever)',                 'deep-pathogens'),
  ('disease.rmsf',                 'disease','Rocky Mountain spotted fever',             'deep-pathogens'),
  ('disease.rabies',               'disease','Rabies',                                   'deep-pathogens'),
  ('disease.avian_influenza_h5n1', 'disease','Avian influenza A(H5N1) infection',        'deep-pathogens'),
  ('disease.cwd',                  'disease','Chronic wasting disease (cervid prion disease)','deep-pathogens'),
  ('disease.valley_fever',         'disease','Coccidioidomycosis (Valley Fever)',        'deep-pathogens'),
  ('disease.lyme',                 'disease','Lyme disease',                             'deep-pathogens'),
  ('disease.anaplasmosis',         'disease','Human granulocytic anaplasmosis',          'deep-pathogens'),
  ('disease.babesiosis',           'disease','Babesiosis',                               'deep-pathogens'),
  ('disease.leptospirosis',        'disease','Leptospirosis (Weil''s disease)',          'deep-pathogens')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- PATHOGENS
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('pathogen.wnv',
     'pathogen', 'West Nile virus (WNV)',
     'Flavivirus; AZ''s leading arboviral cause of neuroinvasive disease. Maricopa County saw an unprecedented 2021 outbreak (1,487 cases, 101 deaths); 2024 statewide ~31 human cases.',
     'deep-pathogens'),
  ('pathogen.slev',
     'pathogen', 'St. Louis encephalitis virus (SLEV)',
     'Flavivirus; co-circulated with WNV in the 2015 Maricopa reemergence outbreak; sporadic AZ cases since via Culex tarsalis.',
     'deep-pathogens'),
  ('pathogen.denv',
     'pathogen', 'Dengue virus (DENV 1-4)',
     'Flavivirus; first locally acquired AZ case Maricopa Nov 2022; travel-associated cases rising 2024 nationally (+359% over 2010-2023 average).',
     'deep-pathogens'),
  ('pathogen.zikv',
     'pathogen', 'Zika virus (ZIKV)',
     'Flavivirus; all AZ cases to date travel-associated; no local transmission documented.',
     'deep-pathogens'),
  ('pathogen.snv',
     'pathogen', 'Sin Nombre virus (SNV / hantavirus)',
     'Orthohantavirus; reservoir Peromyscus maniculatus; AZ had 11 confirmed cases in 2024 (vs ~3/yr baseline) and 7 cases including 4 deaths in 2025.',
     'deep-pathogens'),
  ('pathogen.yersinia_pestis',
     'pathogen', 'Yersinia pestis',
     'Gram-negative bacterium; plague enzootic on the AZ Colorado Plateau (Coconino, Apache, Navajo). 2025 saw a fatal pneumonic case in Coconino County and an Apache County case.',
     'deep-pathogens'),
  ('pathogen.francisella_tularensis',
     'pathogen', 'Francisella tularensis',
     'Tier-1 select agent bacterium; sporadic AZ cases (typically <5/yr) from rabbits, ticks, deer flies.',
     'deep-pathogens'),
  ('pathogen.rickettsia_rickettsii',
     'pathogen', 'Rickettsia rickettsii',
     'Obligate intracellular bacterium causing RMSF; AZ tribal-community outbreak since 2003 transmitted by Rhipicephalus sanguineus; >500 cases / ~30 deaths cumulative.',
     'deep-pathogens'),
  ('pathogen.rabies_lyssavirus',
     'pathogen', 'Rabies lyssavirus',
     'Lyssavirus; AZ maintains bat, skunk, and fox strain enzootics. 2024 ADHS data shows year-over-year rises, especially in Navajo and Cochise Counties.',
     'deep-pathogens'),
  ('pathogen.hpai_h5n1',
     'pathogen', 'Highly pathogenic avian influenza A(H5N1) clade 2.3.4.4b',
     'Orthomyxovirus; first AZ dairy-cattle detection Maricopa County Feb 13 2025 (D1.1 genotype, third US wild-bird-to-cow spillover).',
     'deep-pathogens'),
  ('pathogen.cwd_prion',
     'pathogen', 'Chronic wasting disease prion (PrP^CWD)',
     'Misfolded cervid prion; not yet detected in AZ deer/elk despite 25+ years and 25,000+ samples; present in all four neighboring states.',
     'deep-pathogens'),
  ('pathogen.coccidioides',
     'pathogen', 'Coccidioides immitis / posadasii',
     'Dimorphic soil fungus endemic to AZ Lower Sonoran zone; 14,640 reported AZ cases in 2024 (most in a decade), ~986 hospitalizations and 86 deaths.',
     'deep-pathogens'),
  ('pathogen.borrelia_burgdorferi',
     'pathogen', 'Borrelia burgdorferi sensu lato',
     'Spirochete causing Lyme disease; all reported AZ human cases travel-associated. Ixodes pacificus detected in Mohave Co. Hualapai Mtns spring 2024, but no Bb+ ticks yet.',
     'deep-pathogens'),
  ('pathogen.anaplasma_phagocytophilum',
     'pathogen', 'Anaplasma phagocytophilum',
     'Tick-borne intracellular bacterium; rare in AZ — travel/exposure-associated; surveillance via ADHS notifiable list and Great AZ Tick Check.',
     'deep-pathogens'),
  ('pathogen.babesia_microti',
     'pathogen', 'Babesia microti',
     'Intra-erythrocytic protozoan; no locally acquired AZ cases documented; ADHS tracks travel-associated cases.',
     'deep-pathogens'),
  ('pathogen.leptospira',
     'pathogen', 'Leptospira interrogans (and related spp.)',
     'Spirochete; canine outbreaks in Maricopa County 2016-2017 and 2024-2025 (notifiable for dogs); human cases rare (5 statewide 2006-2023).',
     'deep-pathogens')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Pathogen scalar properties (scientific name, family, ICD-10, notifiable,
-- seasonality, recent AZ case counts with year)
-- ---------------------------------------------------------------------------
INSERT INTO kg.property (node_id, key, value_text) VALUES
  -- scientific names
  ('pathogen.wnv',                   'scientific_name','Orthoflavivirus nilense (West Nile virus)'),
  ('pathogen.slev',                  'scientific_name','Orthoflavivirus louisense (St. Louis encephalitis virus)'),
  ('pathogen.denv',                  'scientific_name','Orthoflavivirus denguei (DENV-1, -2, -3, -4)'),
  ('pathogen.zikv',                  'scientific_name','Orthoflavivirus zikaense (Zika virus)'),
  ('pathogen.snv',                   'scientific_name','Orthohantavirus sinnombreense (Sin Nombre orthohantavirus)'),
  ('pathogen.yersinia_pestis',       'scientific_name','Yersinia pestis'),
  ('pathogen.francisella_tularensis','scientific_name','Francisella tularensis (subsp. tularensis = Type A; subsp. holarctica = Type B)'),
  ('pathogen.rickettsia_rickettsii', 'scientific_name','Rickettsia rickettsii'),
  ('pathogen.rabies_lyssavirus',     'scientific_name','Lyssavirus rabies (Rabies lyssavirus)'),
  ('pathogen.hpai_h5n1',             'scientific_name','Influenza A virus subtype H5N1, clade 2.3.4.4b'),
  ('pathogen.cwd_prion',             'scientific_name','Cervid prion protein, scrapie isoform (PrP^Sc / PrP^CWD)'),
  ('pathogen.coccidioides',          'scientific_name','Coccidioides immitis; Coccidioides posadasii'),
  ('pathogen.borrelia_burgdorferi',  'scientific_name','Borrelia burgdorferi sensu lato'),
  ('pathogen.anaplasma_phagocytophilum','scientific_name','Anaplasma phagocytophilum'),
  ('pathogen.babesia_microti',       'scientific_name','Babesia microti'),
  ('pathogen.leptospira',            'scientific_name','Leptospira interrogans (sensu lato)'),
  -- taxonomic family / class
  ('pathogen.wnv',                   'pathogen_class','virus (Flaviviridae)'),
  ('pathogen.slev',                  'pathogen_class','virus (Flaviviridae)'),
  ('pathogen.denv',                  'pathogen_class','virus (Flaviviridae)'),
  ('pathogen.zikv',                  'pathogen_class','virus (Flaviviridae)'),
  ('pathogen.snv',                   'pathogen_class','virus (Hantaviridae)'),
  ('pathogen.yersinia_pestis',       'pathogen_class','bacterium (Yersiniaceae)'),
  ('pathogen.francisella_tularensis','pathogen_class','bacterium (Francisellaceae)'),
  ('pathogen.rickettsia_rickettsii', 'pathogen_class','bacterium (Rickettsiaceae)'),
  ('pathogen.rabies_lyssavirus',     'pathogen_class','virus (Rhabdoviridae)'),
  ('pathogen.hpai_h5n1',             'pathogen_class','virus (Orthomyxoviridae)'),
  ('pathogen.cwd_prion',             'pathogen_class','prion'),
  ('pathogen.coccidioides',          'pathogen_class','fungus (Onygenaceae)'),
  ('pathogen.borrelia_burgdorferi',  'pathogen_class','bacterium (Spirochaetaceae)'),
  ('pathogen.anaplasma_phagocytophilum','pathogen_class','bacterium (Anaplasmataceae)'),
  ('pathogen.babesia_microti',       'pathogen_class','protozoan (Apicomplexa)'),
  ('pathogen.leptospira',            'pathogen_class','bacterium (Leptospiraceae)'),
  -- ICD-10 codes (primary clinical code in AZ surveillance)
  ('pathogen.wnv',                   'icd10','A92.3 (West Nile virus infection)'),
  ('pathogen.slev',                  'icd10','A83.3 (St Louis encephalitis)'),
  ('pathogen.denv',                  'icd10','A90 / A91 (dengue fever / severe dengue)'),
  ('pathogen.zikv',                  'icd10','A92.5 (Zika virus disease); P35.4 congenital'),
  ('pathogen.snv',                   'icd10','B33.4 (Hantavirus cardiopulmonary syndrome)'),
  ('pathogen.yersinia_pestis',       'icd10','A20.0-A20.9 (plague forms)'),
  ('pathogen.francisella_tularensis','icd10','A21.0-A21.9 (tularemia forms)'),
  ('pathogen.rickettsia_rickettsii', 'icd10','A77.0 (RMSF)'),
  ('pathogen.rabies_lyssavirus',     'icd10','A82.0 / A82.9 (sylvatic / unspecified rabies); Z20.3 exposure'),
  ('pathogen.hpai_h5n1',             'icd10','J09.X (influenza due to identified novel A virus)'),
  ('pathogen.cwd_prion',             'icd10','none (animal disease; no human ICD-10 — surveilled under animal codes)'),
  ('pathogen.coccidioides',          'icd10','B38.0-B38.9 (coccidioidomycosis)'),
  ('pathogen.borrelia_burgdorferi',  'icd10','A69.20-A69.29 (Lyme disease)'),
  ('pathogen.anaplasma_phagocytophilum','icd10','A77.49 (other ehrlichiosis / anaplasmosis)'),
  ('pathogen.babesia_microti',       'icd10','B60.0 (babesiosis)'),
  ('pathogen.leptospira',            'icd10','A27.0 / A27.81 / A27.89 / A27.9 (leptospirosis forms)'),
  -- Seasonality (AZ-specific)
  ('pathogen.wnv',                   'seasonality_az','peak July-October; year-round low-level Aedes/Culex breeding in Phoenix metro'),
  ('pathogen.slev',                  'seasonality_az','late summer to early fall (August-October)'),
  ('pathogen.denv',                  'seasonality_az','monsoon and post-monsoon (July-November) when Aedes aegypti density peaks'),
  ('pathogen.zikv',                  'seasonality_az','travel-driven; year-round case importation'),
  ('pathogen.snv',                   'seasonality_az','spring peak (March-June) following wet winters that boost rodent populations'),
  ('pathogen.yersinia_pestis',       'seasonality_az','May-October flea activity; tied to rodent die-offs'),
  ('pathogen.francisella_tularensis','seasonality_az','May-September (tick + rabbit exposure)'),
  ('pathogen.rickettsia_rickettsii', 'seasonality_az','YEAR-ROUND in AZ tribal communities (brown dog tick lives indoors)'),
  ('pathogen.rabies_lyssavirus',     'seasonality_az','year-round; bat exposures peak summer, terrestrial peak spring'),
  ('pathogen.hpai_h5n1',             'seasonality_az','fall/winter wild-bird migration (Pacific & Central Flyways)'),
  ('pathogen.cwd_prion',             'seasonality_az','year-round; AZGFD sampling concentrated in fall hunt seasons'),
  ('pathogen.coccidioides',          'seasonality_az','bimodal: June-July and October-November dust seasons'),
  ('pathogen.borrelia_burgdorferi',  'seasonality_az','travel-acquired; vector tick active spring at higher elevations'),
  ('pathogen.anaplasma_phagocytophilum','seasonality_az','spring-summer; mostly travel-acquired'),
  ('pathogen.babesia_microti',       'seasonality_az','travel-acquired; northeast US summer source'),
  ('pathogen.leptospira',            'seasonality_az','monsoon-driven (July-September standing water); canine outbreaks have been year-round'),
  -- Notifiable status (US nationally notifiable per CDC NNDSS unless noted)
  ('pathogen.wnv',                   'notifiable','yes (NNDSS; AZ reportable within 1 working day)'),
  ('pathogen.slev',                  'notifiable','yes (NNDSS arboviral; AZ reportable)'),
  ('pathogen.denv',                  'notifiable','yes (NNDSS)'),
  ('pathogen.zikv',                  'notifiable','yes (NNDSS)'),
  ('pathogen.snv',                   'notifiable','yes (NNDSS hantavirus disease, non-Hantaan)'),
  ('pathogen.yersinia_pestis',       'notifiable','yes (NNDSS; AZ immediate report)'),
  ('pathogen.francisella_tularensis','notifiable','yes (NNDSS; select agent; AZ immediate report)'),
  ('pathogen.rickettsia_rickettsii', 'notifiable','yes (spotted fever rickettsioses, NNDSS)'),
  ('pathogen.rabies_lyssavirus',     'notifiable','yes — human cases AND animal cases reportable in AZ'),
  ('pathogen.hpai_h5n1',             'notifiable','yes (novel influenza A; immediate; reportable in animals to USDA APHIS / AZDA)'),
  ('pathogen.cwd_prion',             'notifiable','reportable in cervids to AZGFD / USDA APHIS (no human ICD)'),
  ('pathogen.coccidioides',          'notifiable','yes (AZ reportable; NNDSS since 1995)'),
  ('pathogen.borrelia_burgdorferi',  'notifiable','yes (NNDSS Lyme disease)'),
  ('pathogen.anaplasma_phagocytophilum','notifiable','yes (NNDSS ehrlichiosis/anaplasmosis)'),
  ('pathogen.babesia_microti',       'notifiable','yes (NNDSS since 2011)'),
  ('pathogen.leptospira',            'notifiable','yes (NNDSS reinstated 2013; canine cases reportable to AZ State Vet)')
ON CONFLICT DO NOTHING;

-- Recent AZ case counts (numeric) with the report year / source captured in
-- the companion text properties below
INSERT INTO kg.property (node_id, key, value_num) VALUES
  ('pathogen.wnv',                   'az_human_cases_2024',          31),
  ('pathogen.wnv',                   'az_human_cases_2021',        1487),
  ('pathogen.wnv',                   'az_deaths_2021',              101),
  ('pathogen.slev',                  'us_human_cases_2025',           3),
  ('pathogen.denv',                  'az_locally_acquired_cases_2022',2),
  ('pathogen.zikv',                  'az_locally_acquired_cases_total',0),
  ('pathogen.snv',                   'az_human_cases_2024',          11),
  ('pathogen.snv',                   'az_human_cases_2025',           7),
  ('pathogen.snv',                   'az_deaths_2025',                4),
  ('pathogen.yersinia_pestis',       'us_avg_human_cases_per_year',   7),
  ('pathogen.yersinia_pestis',       'az_deaths_2025',                1),
  ('pathogen.rickettsia_rickettsii', 'az_cases_cumulative_since_2003',500),
  ('pathogen.rickettsia_rickettsii', 'az_deaths_cumulative_since_2003',30),
  ('pathogen.hpai_h5n1',             'az_dairy_herds_detected_2025',  1),
  ('pathogen.cwd_prion',             'az_cervid_samples_2024',     1543),
  ('pathogen.cwd_prion',             'az_cervid_samples_since_1998',25000),
  ('pathogen.cwd_prion',             'az_cervid_positives_total',     0),
  ('pathogen.coccidioides',          'az_human_cases_2024',       14640),
  ('pathogen.coccidioides',          'az_hospitalizations_2024',    986),
  ('pathogen.coccidioides',          'az_deaths_2024',               86),
  ('pathogen.coccidioides',          'az_share_of_us_cases_pct',     66),
  ('pathogen.borrelia_burgdorferi',  'az_locally_acquired_cases_total',0),
  ('pathogen.leptospira',            'az_human_cases_2006_2023',      5)
ON CONFLICT DO NOTHING;

-- Companion text properties describing the source/year context for each count
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('pathogen.wnv',                   'count_source','CDC/ADHS arboviral surveillance, 2024 final; 2021 MMWR 72(17)'),
  ('pathogen.slev',                  'count_source','CDC arboviral current-year data, 2025 (US; AZ-specific not separable)'),
  ('pathogen.denv',                  'count_source','MMWR 72(11) and CIDRAP, locally acquired 2022 Maricopa; 2024 ADHS reports remain travel-associated'),
  ('pathogen.zikv',                  'count_source','Maricopa County Zika dashboard; no local cases ever'),
  ('pathogen.snv',                   'count_source','ADHS HPS protocol 7/16/2025; KJZZ/AZPM reporting 2024-2025 (approximate)'),
  ('pathogen.yersinia_pestis',       'count_source','CDC plague maps & 2025 Coconino/Apache county press releases'),
  ('pathogen.francisella_tularensis','count_source','AZ historical typically <5/yr (ADHS investigation manual); 2024 AZ-specific count not published'),
  ('pathogen.rickettsia_rickettsii', 'count_source','ADHS RMSF handbook (cumulative since 2003 tribal-community outbreak)'),
  ('pathogen.rabies_lyssavirus',     'count_source','ADHS 2024 Rabies in Arizona report (1/1/2024-1/28/2025)'),
  ('pathogen.hpai_h5n1',             'count_source','USDA APHIS announcement Feb 13 2025; Arizona Dept of Agriculture'),
  ('pathogen.cwd_prion',             'count_source','AZGFD CWD surveillance press release March 2024'),
  ('pathogen.coccidioides',          'count_source','ADHS Valley Fever annual data release 2024'),
  ('pathogen.borrelia_burgdorferi',  'count_source','ADHS / Axios Phoenix 8/2025; UA Great AZ Tick Check spring 2024'),
  ('pathogen.anaplasma_phagocytophilum','count_source','ADHS notifiable disease summaries; AZ counts dominated by travel exposure'),
  ('pathogen.babesia_microti',       'count_source','ADHS babesiosis protocol 6/2025 — no locally acquired AZ cases ever documented'),
  ('pathogen.leptospira',            'count_source','ADHS Director''s Blog 2024; canine outbreaks Maricopa Co. 2016-17 and 2024-25')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- EDGES (range 10000-10999)
-- ---------------------------------------------------------------------------

-- pathogen -> disease  (causes)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 10000 + row_number() OVER (), subject_id, 'causes', object_id, 'deep-pathogens'
FROM (VALUES
  ('pathogen.wnv',                    'disease.west_nile_fever'),
  ('pathogen.slev',                   'disease.sle'),
  ('pathogen.denv',                   'disease.dengue_fever'),
  ('pathogen.zikv',                   'disease.zika'),
  ('pathogen.snv',                    'disease.hps'),
  ('pathogen.yersinia_pestis',        'disease.plague'),
  ('pathogen.francisella_tularensis', 'disease.tularemia'),
  ('pathogen.rickettsia_rickettsii',  'disease.rmsf'),
  ('pathogen.rabies_lyssavirus',      'disease.rabies'),
  ('pathogen.hpai_h5n1',              'disease.avian_influenza_h5n1'),
  ('pathogen.cwd_prion',              'disease.cwd'),
  ('pathogen.coccidioides',           'disease.valley_fever'),
  ('pathogen.borrelia_burgdorferi',   'disease.lyme'),
  ('pathogen.anaplasma_phagocytophilum','disease.anaplasmosis'),
  ('pathogen.babesia_microti',        'disease.babesiosis'),
  ('pathogen.leptospira',             'disease.leptospirosis')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- pathogen -> vector  (transmittedBy)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 10050 + row_number() OVER (), subject_id, 'transmittedBy', object_id, 'deep-pathogens'
FROM (VALUES
  ('pathogen.wnv',                    'vector.culex_tarsalis'),
  ('pathogen.wnv',                    'vector.culex_quinquefasciatus'),
  ('pathogen.slev',                   'vector.culex_tarsalis'),
  ('pathogen.slev',                   'vector.culex_quinquefasciatus'),
  ('pathogen.denv',                   'vector.aedes_aegypti'),
  ('pathogen.denv',                   'vector.aedes_albopictus'),
  ('pathogen.zikv',                   'vector.aedes_aegypti'),
  ('pathogen.zikv',                   'vector.aedes_albopictus'),
  ('pathogen.yersinia_pestis',        'vector.oropsylla_montana'),
  ('pathogen.yersinia_pestis',        'vector.xenopsylla_cheopis'),
  ('pathogen.francisella_tularensis', 'vector.dermacentor_andersoni'),
  ('pathogen.francisella_tularensis', 'vector.dermacentor_variabilis'),
  ('pathogen.rickettsia_rickettsii',  'vector.rhipicephalus_sanguineus'),
  ('pathogen.rickettsia_rickettsii',  'vector.dermacentor_variabilis'),
  ('pathogen.borrelia_burgdorferi',   'vector.ixodes_pacificus'),
  ('pathogen.anaplasma_phagocytophilum','vector.ixodes_pacificus'),
  ('pathogen.babesia_microti',        'vector.ixodes_pacificus')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- pathogen -> reservoir  (reservoirIn)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 10150 + row_number() OVER (), subject_id, 'reservoirIn', object_id, 'deep-pathogens'
FROM (VALUES
  ('pathogen.wnv',                    'reservoir.passerine_birds'),
  ('pathogen.slev',                   'reservoir.passerine_birds'),
  ('pathogen.denv',                   'reservoir.primates_human'),
  ('pathogen.zikv',                   'reservoir.primates_human'),
  ('pathogen.snv',                    'reservoir.deer_mouse'),
  ('pathogen.yersinia_pestis',        'reservoir.gunnisons_prairie_dog'),
  ('pathogen.yersinia_pestis',        'reservoir.rock_squirrel'),
  ('pathogen.yersinia_pestis',        'reservoir.rodents_commensal'),
  ('pathogen.francisella_tularensis', 'reservoir.cottontail_rabbit'),
  ('pathogen.francisella_tularensis', 'reservoir.black_tailed_jackrabbit'),
  ('pathogen.rickettsia_rickettsii',  'reservoir.domestic_dog'),
  ('pathogen.rabies_lyssavirus',      'reservoir.bats'),
  ('pathogen.rabies_lyssavirus',      'reservoir.striped_skunk'),
  ('pathogen.rabies_lyssavirus',      'reservoir.gray_fox'),
  ('pathogen.hpai_h5n1',              'reservoir.wild_waterfowl'),
  ('pathogen.hpai_h5n1',              'reservoir.dairy_cattle'),
  ('pathogen.cwd_prion',              'reservoir.mule_deer_elk'),
  ('pathogen.coccidioides',           'reservoir.desert_soil'),
  ('pathogen.borrelia_burgdorferi',   'reservoir.deer_mouse'),
  ('pathogen.anaplasma_phagocytophilum','reservoir.deer_mouse'),
  ('pathogen.babesia_microti',        'reservoir.deer_mouse'),
  ('pathogen.leptospira',             'reservoir.rodents_commensal'),
  ('pathogen.leptospira',             'reservoir.domestic_dog')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- pathogen -> surveillance resource  (surveilledBy)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 10300 + row_number() OVER (), subject_id, 'surveilledBy', object_id, 'deep-pathogens'
FROM (VALUES
  -- WNV
  ('pathogen.wnv',                    'resource.adhs'),
  ('pathogen.wnv',                    'resource.mcdph_mcesd'),
  ('pathogen.wnv',                    'resource.pcdh'),
  ('pathogen.wnv',                    'resource.coconino_hhs'),
  ('pathogen.wnv',                    'resource.azgfd'),
  -- SLEV
  ('pathogen.slev',                   'resource.adhs'),
  ('pathogen.slev',                   'resource.mcdph_mcesd'),
  ('pathogen.slev',                   'resource.pcdh'),
  -- Dengue
  ('pathogen.denv',                   'resource.adhs'),
  ('pathogen.denv',                   'resource.mcdph_mcesd'),
  ('pathogen.denv',                   'resource.pcdh'),
  -- Zika
  ('pathogen.zikv',                   'resource.adhs'),
  ('pathogen.zikv',                   'resource.mcdph_mcesd'),
  -- Hantavirus
  ('pathogen.snv',                    'resource.adhs'),
  ('pathogen.snv',                    'resource.coconino_hhs'),
  ('pathogen.snv',                    'resource.usgs_nwhc'),
  ('pathogen.snv',                    'resource.azgfd'),
  -- Plague
  ('pathogen.yersinia_pestis',        'resource.adhs'),
  ('pathogen.yersinia_pestis',        'resource.coconino_hhs'),
  ('pathogen.yersinia_pestis',        'resource.azgfd'),
  ('pathogen.yersinia_pestis',        'resource.usda_aphis_ws'),
  ('pathogen.yersinia_pestis',        'resource.usgs_nwhc'),
  ('pathogen.yersinia_pestis',        'resource.nau_pmi'),
  -- Tularemia
  ('pathogen.francisella_tularensis', 'resource.adhs'),
  ('pathogen.francisella_tularensis', 'resource.azgfd'),
  ('pathogen.francisella_tularensis', 'resource.usgs_nwhc'),
  ('pathogen.francisella_tularensis', 'resource.azvdl'),
  -- RMSF
  ('pathogen.rickettsia_rickettsii',  'resource.adhs'),
  ('pathogen.rickettsia_rickettsii',  'resource.mcdph_mcesd'),
  ('pathogen.rickettsia_rickettsii',  'resource.ua_extension_tickcheck'),
  -- Rabies
  ('pathogen.rabies_lyssavirus',      'resource.adhs'),
  ('pathogen.rabies_lyssavirus',      'resource.azgfd'),
  ('pathogen.rabies_lyssavirus',      'resource.coconino_hhs'),
  ('pathogen.rabies_lyssavirus',      'resource.azvdl'),
  ('pathogen.rabies_lyssavirus',      'resource.usda_aphis_ws'),
  -- HPAI
  ('pathogen.hpai_h5n1',              'resource.adhs'),
  ('pathogen.hpai_h5n1',              'resource.azgfd'),
  ('pathogen.hpai_h5n1',              'resource.azvdl'),
  ('pathogen.hpai_h5n1',              'resource.usda_aphis_ws'),
  ('pathogen.hpai_h5n1',              'resource.usgs_nwhc'),
  -- CWD
  ('pathogen.cwd_prion',              'resource.azgfd'),
  ('pathogen.cwd_prion',              'resource.azvdl'),
  ('pathogen.cwd_prion',              'resource.usgs_nwhc'),
  -- Valley Fever
  ('pathogen.coccidioides',           'resource.adhs'),
  ('pathogen.coccidioides',           'resource.mcdph_mcesd'),
  ('pathogen.coccidioides',           'resource.pcdh'),
  -- Lyme / Anaplasma / Babesia
  ('pathogen.borrelia_burgdorferi',   'resource.adhs'),
  ('pathogen.borrelia_burgdorferi',   'resource.ua_extension_tickcheck'),
  ('pathogen.anaplasma_phagocytophilum','resource.adhs'),
  ('pathogen.anaplasma_phagocytophilum','resource.ua_extension_tickcheck'),
  ('pathogen.babesia_microti',        'resource.adhs'),
  -- Leptospirosis
  ('pathogen.leptospira',             'resource.adhs'),
  ('pathogen.leptospira',             'resource.azvdl'),
  ('pathogen.leptospira',             'resource.mcdph_mcesd')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- pathogen -> focus_area  (targetsFocusArea)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 10500 + row_number() OVER (), subject_id, 'targetsFocusArea', object_id, 'deep-pathogens'
FROM (VALUES
  ('pathogen.wnv',                    'focus.wnv'),
  ('pathogen.wnv',                    'focus.mosquito'),
  ('pathogen.wnv',                    'focus.vector_borne'),
  ('pathogen.slev',                   'focus.mosquito'),
  ('pathogen.slev',                   'focus.vector_borne'),
  ('pathogen.denv',                   'focus.mosquito'),
  ('pathogen.denv',                   'focus.vector_borne'),
  ('pathogen.zikv',                   'focus.mosquito'),
  ('pathogen.zikv',                   'focus.vector_borne'),
  ('pathogen.snv',                    'focus.hantavirus'),
  ('pathogen.snv',                    'focus.rodent'),
  ('pathogen.snv',                    'focus.zoonotic'),
  ('pathogen.yersinia_pestis',        'focus.plague'),
  ('pathogen.yersinia_pestis',        'focus.flea'),
  ('pathogen.yersinia_pestis',        'focus.rodent'),
  ('pathogen.yersinia_pestis',        'focus.zoonotic'),
  ('pathogen.yersinia_pestis',        'focus.vector_borne'),
  ('pathogen.francisella_tularensis', 'focus.tularemia'),
  ('pathogen.francisella_tularensis', 'focus.tick'),
  ('pathogen.francisella_tularensis', 'focus.zoonotic'),
  ('pathogen.rickettsia_rickettsii',  'focus.rmsf'),
  ('pathogen.rickettsia_rickettsii',  'focus.tick'),
  ('pathogen.rickettsia_rickettsii',  'focus.vector_borne'),
  ('pathogen.rickettsia_rickettsii',  'focus.zoonotic'),
  ('pathogen.rabies_lyssavirus',      'focus.rabies'),
  ('pathogen.rabies_lyssavirus',      'focus.zoonotic'),
  ('pathogen.hpai_h5n1',              'focus.hpai'),
  ('pathogen.hpai_h5n1',              'focus.zoonotic'),
  ('pathogen.cwd_prion',              'focus.cwd'),
  ('pathogen.coccidioides',           'focus.zoonotic'),  -- environmental but tracked alongside zoonoses
  ('pathogen.borrelia_burgdorferi',   'focus.tick'),
  ('pathogen.borrelia_burgdorferi',   'focus.vector_borne'),
  ('pathogen.anaplasma_phagocytophilum','focus.tick'),
  ('pathogen.anaplasma_phagocytophilum','focus.vector_borne'),
  ('pathogen.babesia_microti',        'focus.tick'),
  ('pathogen.babesia_microti',        'focus.vector_borne'),
  ('pathogen.leptospira',             'focus.zoonotic')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- pathogen -> geography  (endemicIn) -- stored as a property since we don't
-- yet have geography nodes for all AZ regions. Use value_text to record the
-- specific AZ region where each pathogen is endemic or emerging.
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('pathogen.wnv',                   'endemic_in_az','statewide; highest incidence Maricopa, Maricopa-adjacent counties'),
  ('pathogen.slev',                  'endemic_in_az','Maricopa County urban/peri-urban; sporadic statewide'),
  ('pathogen.denv',                  'endemic_in_az','emerging in low-elevation southern AZ (Maricopa, Pima, Yuma) — first local case 2022'),
  ('pathogen.zikv',                  'endemic_in_az','not endemic — travel-associated only'),
  ('pathogen.snv',                   'endemic_in_az','Colorado Plateau (Apache, Coconino, Navajo); Four Corners region'),
  ('pathogen.yersinia_pestis',       'endemic_in_az','northern AZ plateau (Coconino, Apache, Navajo); enzootic in prairie dog colonies'),
  ('pathogen.francisella_tularensis','endemic_in_az','statewide rangeland but rare; higher in northern AZ'),
  ('pathogen.rickettsia_rickettsii', 'endemic_in_az','tribal communities (Navajo, Pinal, Gila, Maricopa peri-urban); brown-dog-tick associated'),
  ('pathogen.rabies_lyssavirus',     'endemic_in_az','statewide enzootic in bats, skunks, foxes; concentrated in Cochise/Coconino/Navajo'),
  ('pathogen.hpai_h5n1',             'endemic_in_az','migratory wild birds statewide; first AZ dairy detection Maricopa County 2025'),
  ('pathogen.cwd_prion',             'endemic_in_az','NOT detected in AZ as of 2024 — present in CA, UT, NM, CO neighbors'),
  ('pathogen.coccidioides',          'endemic_in_az','Lower Sonoran life zone — endemic throughout Maricopa, Pima, Pinal, Yuma'),
  ('pathogen.borrelia_burgdorferi',  'endemic_in_az','not established — competent vector tick Ixodes pacificus found Mohave Co Hualapai Mtns 2024 but no Bb+ ticks'),
  ('pathogen.anaplasma_phagocytophilum','endemic_in_az','not established — travel-associated'),
  ('pathogen.babesia_microti',       'endemic_in_az','not established — travel-associated'),
  ('pathogen.leptospira',            'endemic_in_az','sporadic; canine clusters in Maricopa County metro')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Convenience view: a flat pathogen "card" combining the core metadata
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_pathogen_card AS
SELECT
  p.node_id                                AS pathogen_id,
  p.label                                  AS pathogen,
  p.description,
  sn.value_text                            AS scientific_name,
  pc.value_text                            AS pathogen_class,
  icd.value_text                           AS icd10,
  nf.value_text                            AS notifiable,
  s.value_text                             AS seasonality_az,
  e.value_text                             AS endemic_in_az,
  cs.value_text                            AS count_source
FROM kg.node p
LEFT JOIN kg.property sn  ON sn.node_id  = p.node_id AND sn.key  = 'scientific_name'
LEFT JOIN kg.property pc  ON pc.node_id  = p.node_id AND pc.key  = 'pathogen_class'
LEFT JOIN kg.property icd ON icd.node_id = p.node_id AND icd.key = 'icd10'
LEFT JOIN kg.property nf  ON nf.node_id  = p.node_id AND nf.key  = 'notifiable'
LEFT JOIN kg.property s   ON s.node_id   = p.node_id AND s.key   = 'seasonality_az'
LEFT JOIN kg.property e   ON e.node_id   = p.node_id AND e.key   = 'endemic_in_az'
LEFT JOIN kg.property cs  ON cs.node_id  = p.node_id AND cs.key  = 'count_source'
WHERE p.node_type = 'pathogen';
