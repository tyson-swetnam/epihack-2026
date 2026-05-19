-- ============================================================================
-- EpiHack Arizona 2026 -- Deep dive: Historical outbreaks (zoonotic / vector-
-- borne / heat) as kg.node rows of type 'outbreak'.
--
-- Purpose
--   Provide a structured, time-stamped corpus of notable Arizona outbreak
--   events that can be queried against the Figure 3 timeliness milestone
--   framework (predict -> prevent -> detect -> notify -> verify ->
--   lab_confirm -> respond -> public_comm -> outbreak_start -> outbreak_end
--   -> aar).  Every outbreak is linked to:
--     * the pathogen that caused it          (causedBy)
--     * the primary AZ county geography      (occurredIn)
--     * the agency that surveilled / reported it (reportedBy)
--     * the timeliness milestone(s) it illustrates (markedMilestone)
--
-- Conventions
--   * Node IDs:        outbreak.<slug>
--   * Edge ID range:   14000 .. 14999   (reserved for this seed)
--   * source_fig:      'deep-outbreaks'
--   * All inserts are idempotent (ON CONFLICT DO NOTHING).
--   * pathogen.<slug> and county.<slug> nodes are owned by sibling seeders.
--     If they have not yet run, the foreign-key references will not exist
--     in kg.node yet; DuckDB's REFERENCES enforcement and ON CONFLICT
--     DO NOTHING keep this idempotent on rerun.
--
-- Run order
--   .read schema/knowledge_graph.sql        (must run first - milestones)
--   .read schema/deep/pathogens.sql         (sibling - pathogen.* nodes)
--   .read schema/deep/counties.sql          (sibling - county.* nodes)
--   .read schema/deep/outbreaks.sql         (this file)
--
-- Date precision note
--   `start_date` and `end_date` are stored as text (ISO 8601 where known,
--   year-only where the published record is imprecise).  This lets us
--   honour the actual evidentiary precision in the literature without
--   manufacturing false certainty.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Outbreak nodes
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('outbreak.four_corners_hantavirus_1993',
     'outbreak',
     '1993 Four Corners Hantavirus Outbreak',
     'Cluster of fatal acute respiratory illness in young, previously healthy adults across the Navajo Nation and adjacent Four Corners area; investigation by CDC, IHS, NM/AZ/UT/CO health departments, and UNM led to the discovery of Sin Nombre virus and the deer mouse (Peromyscus maniculatus) reservoir.',
     'deep-outbreaks'),
  ('outbreak.az_wnv_2003',
     'outbreak',
     '2003 Arizona West Nile Virus Emergence',
     'First locally-acquired WNV human cases in Arizona; surveillance detected the virus in birds (Sept), then mosquitoes (Oct), then humans (Nov), establishing WNV as endemic in the state.',
     'deep-outbreaks'),
  ('outbreak.az_dengue_yuma_sonora_2014',
     'outbreak',
     '2014 Binational Dengue Outbreak (Yuma County / Sonora)',
     'Cross-border DENV-1 outbreak with 93 travel-associated cases in AZ residents (70 in Yuma County) and 52 locally-acquired cases in San Luis Río Colorado, Sonora; no local transmission was identified north of the border despite established Aedes aegypti and elevated Breteau indices.',
     'deep-outbreaks'),
  ('outbreak.az_chikungunya_2014',
     'outbreak',
     '2014 Arizona Chikungunya Importation',
     'Arizona''s first season of chikungunya importations following the 2013 Americas emergence; 20 travel-associated cases identified by ADHS, concentrated in Maricopa County. No autochthonous transmission detected.',
     'deep-outbreaks'),
  ('outbreak.maricopa_wnv_2021',
     'outbreak',
     '2021 Maricopa County West Nile Virus Outbreak',
     'Largest documented WNV outbreak in any U.S. county: 1,487 cases, 1,014 hospitalisations, 101 deaths. Co-circulation with St. Louis encephalitis virus complicated diagnosis. Documented in MMWR April 2023.',
     'deep-outbreaks'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',
     'outbreak',
     '2022-present HPAI H5N1 in Arizona Wild Birds and Spillover Hosts',
     'Ongoing detections of HPAI H5N1 (clade 2.3.4.4b) in AZ wild birds since 2022, escalating in 2024-2025 to include a Maricopa County backyard flock, a Pinal County commercial layer flock (~1.8M birds depopulated), wastewater positives, dairy-milk positives, zoo-animal mortality, and the state''s first human H5 cases (two Pinal County poultry workers).',
     'deep-outbreaks'),
  ('outbreak.az_hantavirus_2023',
     'outbreak',
     '2023 Arizona Hantavirus Spike',
     'Six confirmed hantavirus pulmonary syndrome cases in Arizona in 2023, concentrated in the northern counties; above the 2012-2022 baseline of 0-5 cases per year.',
     'deep-outbreaks'),
  ('outbreak.maricopa_heat_2023',
     'outbreak',
     '2023 Maricopa County Heat Mortality Season',
     'Record-shattering heat-mortality season: 645 confirmed heat-associated deaths in Maricopa County, a 52% increase over 2022. 71% occurred on Excessive Heat Warning days; 303 deaths during the July 10-25 streak when daily lows never dropped below 91°F.',
     'deep-outbreaks'),
  ('outbreak.maricopa_cooling_center_barriers_2023',
     'outbreak',
     '2023 Maricopa Cooling-Center Access Barriers Assessment',
     'Surveillance event documented in MMWR (April 2025): assessment of 944 cooling-center visitors and 1,260 general public respondents during Aug 1-Sept 15, 2023; identified lack of transportation (31% of visitors), limited evening hours, and low awareness as access barriers.',
     'deep-outbreaks'),
  ('outbreak.az_hantavirus_2024',
     'outbreak',
     '2024 Arizona Hantavirus Spike',
     'Eleven confirmed HPS cases in Arizona in 2024 (Apache, Coconino, Navajo, Maricopa, and the first-ever Pima County case); six deaths across the 2023-2024 cluster. Triggered an ADHS Health Alert Network advisory on 2024-07-08.',
     'deep-outbreaks'),
  ('outbreak.az_heat_2024',
     'outbreak',
     '2024 Arizona Record Heat Season',
     '113 consecutive days of triple-digit temperatures and 70 days at or above 110°F in Phoenix; Maricopa County recorded 602 confirmed heat-associated deaths — first year-over-year decline in a decade despite the hottest summer on record. ~50% of decedents were unhoused; 88% of indoor deaths occurred in homes with non-functioning AC.',
     'deep-outbreaks'),
  ('outbreak.coconino_plague_2025',
     'outbreak',
     '2025 Coconino County Human Pneumonic Plague Death',
     'Coconino County resident died of pneumonic plague in a Flagstaff emergency room in July 2025; first plague death in Coconino County since 2007. NAU Pathogen and Microbiome Institute (Dr. Dave Wagner) provided public commentary contextualising the rarity and the ongoing plague-vaccine research programme.',
     'deep-outbreaks'),
  ('outbreak.az_rmsf_tribal_2003_present',
     'outbreak',
     'Arizona Tribal Rocky Mountain Spotted Fever Outbreak (2003-present)',
     'Sustained RMSF epizootic-driven epidemic among American Indian communities in eastern Arizona, transmitted by the brown dog tick (Rhipicephalus sanguineus). Publicly documented on the San Carlos Apache and White Mountain Apache reservations beginning 2003; >500 cases and ~30 deaths through 2024, with an Arizona case-fatality rate (~6%) far above the U.S. average (<1%).',
     'deep-outbreaks'),
  ('outbreak.az_rmsf_rodeo_pilot_2012',
     'outbreak',
     'RMSF Rodeo Tribal Intervention Pilot (2012-2013)',
     'Two-year integrated tick-prevention pilot in a ~600-home Arizona tribal community ("Reservation B"): long-acting tick collars on all dogs, monthly environmental acaricide application, animal-care education. CDC + tribal + ADHS partnership; substantial decline in human RMSF incidence in the intervention community.',
     'deep-outbreaks')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Outbreak properties (typed scalars)
-- ---------------------------------------------------------------------------
-- Text properties (dates, geographies, agency notes, references)
INSERT INTO kg.property (node_id, key, value_text) VALUES
  -- 1993 Four Corners hantavirus
  ('outbreak.four_corners_hantavirus_1993', 'start_date',          '1993-03'),
  ('outbreak.four_corners_hantavirus_1993', 'end_date',            '1993-12'),
  ('outbreak.four_corners_hantavirus_1993', 'detect_date',         '1993-05'),
  ('outbreak.four_corners_hantavirus_1993', 'notify_date',         '1993-05-14'),
  ('outbreak.four_corners_hantavirus_1993', 'lab_confirm_date',    '1993-06-10'),
  ('outbreak.four_corners_hantavirus_1993', 'reservoir_confirm_date','1993-06-16'),
  ('outbreak.four_corners_hantavirus_1993', 'pathogen_id',         'pathogen.sin_nombre'),
  ('outbreak.four_corners_hantavirus_1993', 'primary_geography',   'Four Corners region (Navajo Nation; AZ Apache & Navajo Cos., NM, UT, CO)'),
  ('outbreak.four_corners_hantavirus_1993', 'reference',           'CDC MMWR 42(22):421-424 (Jun 11 1993); CDC MMWR 43(02):45-48 (Jan 21 1994).'),
  -- 2003 AZ WNV emergence
  ('outbreak.az_wnv_2003',                  'start_date',          '2003-09'),
  ('outbreak.az_wnv_2003',                  'end_date',            '2003-12'),
  ('outbreak.az_wnv_2003',                  'detect_date',         '2003-09'),
  ('outbreak.az_wnv_2003',                  'lab_confirm_date',    '2003-11'),
  ('outbreak.az_wnv_2003',                  'pathogen_id',         'pathogen.wnv'),
  ('outbreak.az_wnv_2003',                  'primary_geography',   'Maricopa County, Arizona'),
  ('outbreak.az_wnv_2003',                  'reference',           'ADHS WNV historical surveillance; first bird (Sept 2003), first mosquito pool (~Oct 2003), first human case (Nov 2003).'),
  -- 2014 binational dengue
  ('outbreak.az_dengue_yuma_sonora_2014',   'start_date',          '2014-09'),
  ('outbreak.az_dengue_yuma_sonora_2014',   'end_date',            '2014-12'),
  ('outbreak.az_dengue_yuma_sonora_2014',   'pathogen_id',         'pathogen.denv'),
  ('outbreak.az_dengue_yuma_sonora_2014',   'primary_geography',   'Yuma County, Arizona / San Luis Río Colorado, Sonora'),
  ('outbreak.az_dengue_yuma_sonora_2014',   'reference',           'CDC MMWR 65(19):495-499 (May 20 2016) -- Jones et al.'),
  -- 2014 AZ chikungunya
  ('outbreak.az_chikungunya_2014',          'start_date',          '2014'),
  ('outbreak.az_chikungunya_2014',          'end_date',            '2014'),
  ('outbreak.az_chikungunya_2014',          'pathogen_id',         'pathogen.chikv'),
  ('outbreak.az_chikungunya_2014',          'primary_geography',   'Maricopa, Yavapai, Mohave, Yuma counties (all imported)'),
  ('outbreak.az_chikungunya_2014',          'reference',           'ADHS Chikungunya/Dengue Investigation Protocol; ADHS 2015 emerging infections briefing.'),
  -- 2021 Maricopa WNV
  ('outbreak.maricopa_wnv_2021',            'start_date',          '2021-06'),
  ('outbreak.maricopa_wnv_2021',            'end_date',            '2021-12'),
  ('outbreak.maricopa_wnv_2021',            'notify_date',         '2021-09-02'),
  ('outbreak.maricopa_wnv_2021',            'vector_index_peak_date','2021-09-11'),
  ('outbreak.maricopa_wnv_2021',            'pathogen_id',         'pathogen.wnv'),
  ('outbreak.maricopa_wnv_2021',            'primary_geography',   'Maricopa County, Arizona'),
  ('outbreak.maricopa_wnv_2021',            'reference',           'Kretschmer et al., CDC MMWR 72(17):452-457 (Apr 28 2023). Largest single-county WNV outbreak in U.S. history.'),
  -- 2022+ HPAI H5N1 wild birds
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'start_date',          '2022'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'end_date',            'ongoing'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'detect_date',         '2022-11-21'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'pathogen_id',         'pathogen.h5n1'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'primary_geography',   'Statewide; Maricopa & Pinal counties most affected'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'reference',           'USDA APHIS HPAI Detections; AZDA Nov 21 2022 backyard flock confirmation; 2024-2025 Pinal layer-flock depopulation; ADHS first human H5 case announcement.'),
  -- 2023 AZ hantavirus spike
  ('outbreak.az_hantavirus_2023',           'start_date',          '2023-01'),
  ('outbreak.az_hantavirus_2023',           'end_date',            '2023-12'),
  ('outbreak.az_hantavirus_2023',           'pathogen_id',         'pathogen.sin_nombre'),
  ('outbreak.az_hantavirus_2023',           'primary_geography',   'Northern Arizona (Apache, Coconino, Navajo counties)'),
  ('outbreak.az_hantavirus_2023',           'reference',           'ADHS HAN advisory 2024-07-08; CDC hantavirus surveillance.'),
  -- 2023 Maricopa heat
  ('outbreak.maricopa_heat_2023',           'start_date',          '2023-04-11'),
  ('outbreak.maricopa_heat_2023',           'end_date',            '2023-10-31'),
  ('outbreak.maricopa_heat_2023',           'peak_window_start',   '2023-07-10'),
  ('outbreak.maricopa_heat_2023',           'peak_window_end',     '2023-07-25'),
  ('outbreak.maricopa_heat_2023',           'pathogen_id',         'pathogen.heat'),
  ('outbreak.maricopa_heat_2023',           'primary_geography',   'Maricopa County, Arizona'),
  ('outbreak.maricopa_heat_2023',           'reference',           'MCDPH 2023 Heat-Associated Deaths Report (final, Mar 2024).'),
  -- 2023 cooling-center barriers MMWR
  ('outbreak.maricopa_cooling_center_barriers_2023','start_date',  '2023-08-01'),
  ('outbreak.maricopa_cooling_center_barriers_2023','end_date',    '2023-09-15'),
  ('outbreak.maricopa_cooling_center_barriers_2023','pathogen_id', 'pathogen.heat'),
  ('outbreak.maricopa_cooling_center_barriers_2023','primary_geography','Maricopa County, Arizona'),
  ('outbreak.maricopa_cooling_center_barriers_2023','reference',   'CDC MMWR 74(14):234-235 (Apr 17 2025) -- Notes from the Field, Roach et al.'),
  -- 2024 AZ hantavirus spike
  ('outbreak.az_hantavirus_2024',           'start_date',          '2024-01'),
  ('outbreak.az_hantavirus_2024',           'end_date',            '2024-12'),
  ('outbreak.az_hantavirus_2024',           'notify_date',         '2024-07-08'),
  ('outbreak.az_hantavirus_2024',           'pathogen_id',         'pathogen.sin_nombre'),
  ('outbreak.az_hantavirus_2024',           'primary_geography',   'Apache, Coconino, Navajo, Maricopa, Pima counties'),
  ('outbreak.az_hantavirus_2024',           'reference',           'ADHS HAN advisory 2024-07-08; first Pima County HPS case ever recorded.'),
  -- 2024 record AZ heat
  ('outbreak.az_heat_2024',                 'start_date',          '2024-04'),
  ('outbreak.az_heat_2024',                 'end_date',            '2024-10'),
  ('outbreak.az_heat_2024',                 'pathogen_id',         'pathogen.heat'),
  ('outbreak.az_heat_2024',                 'primary_geography',   'Statewide; Maricopa County core'),
  ('outbreak.az_heat_2024',                 'reference',           'MCDPH 2024 Heat-Associated Deaths Report (Mar 2025); NWS Phoenix climate summaries.'),
  -- 2025 Coconino plague
  ('outbreak.coconino_plague_2025',         'start_date',          '2025-07'),
  ('outbreak.coconino_plague_2025',         'end_date',            '2025-07'),
  ('outbreak.coconino_plague_2025',         'detect_date',         '2025-07-11'),
  ('outbreak.coconino_plague_2025',         'public_comm_date',    '2025-07-11'),
  ('outbreak.coconino_plague_2025',         'pathogen_id',         'pathogen.y_pestis'),
  ('outbreak.coconino_plague_2025',         'primary_geography',   'Coconino County, Arizona'),
  ('outbreak.coconino_plague_2025',         'reference',           'Coconino County HHS press release Jul 11 2025; KNAU interview with Dr. Dave Wagner, NAU PMI (Jul 18 2025); CIDRAP coverage; Scientific American piece.'),
  -- RMSF tribal AZ (long-running)
  ('outbreak.az_rmsf_tribal_2003_present',  'start_date',          '2003'),
  ('outbreak.az_rmsf_tribal_2003_present',  'end_date',            'ongoing'),
  ('outbreak.az_rmsf_tribal_2003_present',  'pathogen_id',         'pathogen.rickettsia_rickettsii'),
  ('outbreak.az_rmsf_tribal_2003_present',  'primary_geography',   'Eastern Arizona tribal lands (publicly: San Carlos Apache, White Mountain Apache); other affected tribes have not publicly identified themselves'),
  ('outbreak.az_rmsf_tribal_2003_present',  'reference',           'Drexler et al., Risk Factors for Fatal Outcome from RMSF -- Arizona 2002-2011 (PMC4706357); Traeger et al., RMSF Characterization Arizona 2002-2011 (PMC4699465); NPR 2025 coverage.'),
  -- RMSF Rodeo pilot
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'start_date',          '2012'),
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'end_date',            '2013'),
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'pathogen_id',         'pathogen.rickettsia_rickettsii'),
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'primary_geography',   'Anonymised AZ tribal community ("Reservation B"), ~600 homes / ~10,000 residents'),
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'reference',           'Drexler et al., Community-Based Control of the Brown Dog Tick -- PLOS ONE 9(12):e112368 (2014).')
ON CONFLICT DO NOTHING;

-- Numeric properties (cases, deaths, hospitalisations, magnitudes)
INSERT INTO kg.property (node_id, key, value_num) VALUES
  -- 1993 Four Corners hantavirus
  ('outbreak.four_corners_hantavirus_1993', 'total_cases',           24),    -- April-May 1993 CDC count; expanded by year-end
  ('outbreak.four_corners_hantavirus_1993', 'total_deaths',          12),
  ('outbreak.four_corners_hantavirus_1993', 'case_fatality_rate_pct',50),
  -- 2003 AZ WNV emergence
  ('outbreak.az_wnv_2003',                  'total_cases',           13),    -- 12-13 in the published record
  ('outbreak.az_wnv_2003',                  'total_deaths',           1),
  -- 2014 dengue Yuma/Sonora
  ('outbreak.az_dengue_yuma_sonora_2014',   'total_cases_az',         93),
  ('outbreak.az_dengue_yuma_sonora_2014',   'total_cases_yuma',       70),
  ('outbreak.az_dengue_yuma_sonora_2014',   'total_cases_sonora_local',52),
  ('outbreak.az_dengue_yuma_sonora_2014',   'total_deaths',            0),
  -- 2014 chikungunya AZ
  ('outbreak.az_chikungunya_2014',          'total_cases',            20),
  ('outbreak.az_chikungunya_2014',          'cases_maricopa',         15),
  ('outbreak.az_chikungunya_2014',          'cases_yavapai',           3),
  ('outbreak.az_chikungunya_2014',          'cases_mohave',            1),
  ('outbreak.az_chikungunya_2014',          'cases_yuma',              1),
  ('outbreak.az_chikungunya_2014',          'total_deaths',            0),
  -- 2021 Maricopa WNV
  ('outbreak.maricopa_wnv_2021',            'total_cases',          1487),
  ('outbreak.maricopa_wnv_2021',            'hospitalisations',     1014),
  ('outbreak.maricopa_wnv_2021',            'total_deaths',          101),
  ('outbreak.maricopa_wnv_2021',            'vector_index_peak',   53.61),
  -- 2022+ HPAI H5N1
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'human_cases_az',          2),   -- two Pinal poultry workers, both H5
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'human_deaths_az',         0),
  -- 2023 AZ hantavirus
  ('outbreak.az_hantavirus_2023',           'total_cases',             6),
  -- 2023 Maricopa heat
  ('outbreak.maricopa_heat_2023',           'total_deaths',          645),
  ('outbreak.maricopa_heat_2023',           'pct_change_vs_prior_yr',  52),
  ('outbreak.maricopa_heat_2023',           'deaths_july_10_25',     303),
  ('outbreak.maricopa_heat_2023',           'pct_on_ehw_days',         71),
  -- 2023 cooling-center barriers
  ('outbreak.maricopa_cooling_center_barriers_2023','visitors_surveyed',944),
  ('outbreak.maricopa_cooling_center_barriers_2023','public_surveyed',1260),
  ('outbreak.maricopa_cooling_center_barriers_2023','pct_no_transport',31),
  ('outbreak.maricopa_cooling_center_barriers_2023','cooling_centers',112),
  -- 2024 AZ hantavirus
  ('outbreak.az_hantavirus_2024',           'total_cases',            11),
  ('outbreak.az_hantavirus_2024',           'total_deaths_2023_2024_combined',6),
  -- 2024 heat
  ('outbreak.az_heat_2024',                 'total_deaths_maricopa', 602),
  ('outbreak.az_heat_2024',                 'days_110plus_phoenix',   70),
  ('outbreak.az_heat_2024',                 'consecutive_100_days',  113),
  -- 2025 Coconino plague
  ('outbreak.coconino_plague_2025',         'total_cases',             1),
  ('outbreak.coconino_plague_2025',         'total_deaths',            1),
  ('outbreak.coconino_plague_2025',         'years_since_prior_coconino_death',18),
  -- RMSF tribal AZ
  ('outbreak.az_rmsf_tribal_2003_present',  'total_cases_through_2024',500),
  ('outbreak.az_rmsf_tribal_2003_present',  'total_deaths_through_2024',30),
  ('outbreak.az_rmsf_tribal_2003_present',  'case_fatality_rate_pct',  6),
  -- RMSF Rodeo
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'homes_enrolled',        600),
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'community_population',10000)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Edges: outbreak --causedBy--> pathogen
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 14000 + row_number() OVER (), subject_id, 'causedBy', object_id, 'deep-outbreaks'
FROM (VALUES
  ('outbreak.four_corners_hantavirus_1993',          'pathogen.sin_nombre'),
  ('outbreak.az_wnv_2003',                           'pathogen.wnv'),
  ('outbreak.az_dengue_yuma_sonora_2014',            'pathogen.denv'),
  ('outbreak.az_chikungunya_2014',                   'pathogen.chikv'),
  ('outbreak.maricopa_wnv_2021',                     'pathogen.wnv'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',            'pathogen.h5n1'),
  ('outbreak.az_hantavirus_2023',                    'pathogen.sin_nombre'),
  ('outbreak.maricopa_heat_2023',                    'pathogen.heat'),
  ('outbreak.maricopa_cooling_center_barriers_2023', 'pathogen.heat'),
  ('outbreak.az_hantavirus_2024',                    'pathogen.sin_nombre'),
  ('outbreak.az_heat_2024',                          'pathogen.heat'),
  ('outbreak.coconino_plague_2025',                  'pathogen.y_pestis'),
  ('outbreak.az_rmsf_tribal_2003_present',           'pathogen.rickettsia_rickettsii'),
  ('outbreak.az_rmsf_rodeo_pilot_2012',              'pathogen.rickettsia_rickettsii')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Edges: outbreak --occurredIn--> county
-- (Multiple counties allowed per outbreak; only seed where the county node
-- slug is the obvious AZ county. The sibling counties seeder owns
-- county.* nodes; if not yet present the FK will reject and ON CONFLICT
-- DO NOTHING keeps idempotency on re-run.)
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 14100 + row_number() OVER (), subject_id, 'occurredIn', object_id, 'deep-outbreaks'
FROM (VALUES
  -- 1993 Four Corners hantavirus
  ('outbreak.four_corners_hantavirus_1993', 'county.apache'),
  ('outbreak.four_corners_hantavirus_1993', 'county.navajo'),
  -- 2003 WNV
  ('outbreak.az_wnv_2003',                  'county.maricopa'),
  -- 2014 dengue
  ('outbreak.az_dengue_yuma_sonora_2014',   'county.yuma'),
  -- 2014 chikungunya
  ('outbreak.az_chikungunya_2014',          'county.maricopa'),
  ('outbreak.az_chikungunya_2014',          'county.yavapai'),
  ('outbreak.az_chikungunya_2014',          'county.mohave'),
  ('outbreak.az_chikungunya_2014',          'county.yuma'),
  -- 2021 Maricopa WNV
  ('outbreak.maricopa_wnv_2021',            'county.maricopa'),
  -- HPAI H5N1
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'county.maricopa'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'county.pinal'),
  -- 2023 hantavirus
  ('outbreak.az_hantavirus_2023',           'county.apache'),
  ('outbreak.az_hantavirus_2023',           'county.coconino'),
  ('outbreak.az_hantavirus_2023',           'county.navajo'),
  -- 2023 Maricopa heat
  ('outbreak.maricopa_heat_2023',           'county.maricopa'),
  -- 2023 cooling-center barriers
  ('outbreak.maricopa_cooling_center_barriers_2023','county.maricopa'),
  -- 2024 hantavirus
  ('outbreak.az_hantavirus_2024',           'county.apache'),
  ('outbreak.az_hantavirus_2024',           'county.coconino'),
  ('outbreak.az_hantavirus_2024',           'county.navajo'),
  ('outbreak.az_hantavirus_2024',           'county.maricopa'),
  ('outbreak.az_hantavirus_2024',           'county.pima'),
  -- 2024 record heat
  ('outbreak.az_heat_2024',                 'county.maricopa'),
  -- 2025 Coconino plague
  ('outbreak.coconino_plague_2025',         'county.coconino'),
  -- RMSF tribal (the publicly-named affected tribes occupy these counties)
  ('outbreak.az_rmsf_tribal_2003_present',  'county.gila'),
  ('outbreak.az_rmsf_tribal_2003_present',  'county.graham'),
  ('outbreak.az_rmsf_tribal_2003_present',  'county.navajo'),
  ('outbreak.az_rmsf_tribal_2003_present',  'county.apache'),
  -- RMSF Rodeo (anonymised reservation; same general region)
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'county.gila')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Edges: outbreak --reportedBy--> resource.<agency>
-- (Resources are seeded in schema/wildlife_vectors.sql and schema/heat.sql.)
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 14300 + row_number() OVER (), subject_id, 'reportedBy', object_id, 'deep-outbreaks'
FROM (VALUES
  -- 1993 Four Corners -- IHS + state HDs + CDC; we have CDC One Health resource
  ('outbreak.four_corners_hantavirus_1993', 'resource.cdc_one_health'),
  ('outbreak.four_corners_hantavirus_1993', 'resource.navajo_ec'),
  ('outbreak.four_corners_hantavirus_1993', 'resource.ihs_phoenix'),
  -- 2003 WNV
  ('outbreak.az_wnv_2003',                  'resource.adhs'),
  ('outbreak.az_wnv_2003',                  'resource.mcdph_mcesd'),
  -- 2014 dengue
  ('outbreak.az_dengue_yuma_sonora_2014',   'resource.adhs'),
  ('outbreak.az_dengue_yuma_sonora_2014',   'resource.cdc_one_health'),
  -- 2014 chikungunya
  ('outbreak.az_chikungunya_2014',          'resource.adhs'),
  ('outbreak.az_chikungunya_2014',          'resource.mcdph_mcesd'),
  -- 2021 Maricopa WNV
  ('outbreak.maricopa_wnv_2021',            'resource.mcdph_mcesd'),
  ('outbreak.maricopa_wnv_2021',            'resource.adhs'),
  ('outbreak.maricopa_wnv_2021',            'resource.cdc_one_health'),
  -- HPAI H5N1
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'resource.usda_aphis_vs'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'resource.usgs_nwhc'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'resource.azgfd'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'resource.az_agriculture'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'resource.adhs'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'resource.azvdl'),
  -- 2023 hantavirus
  ('outbreak.az_hantavirus_2023',           'resource.adhs'),
  ('outbreak.az_hantavirus_2023',           'resource.coconino_hhs'),
  -- 2023 Maricopa heat
  ('outbreak.maricopa_heat_2023',           'resource.mcdph_heat'),
  ('outbreak.maricopa_heat_2023',           'resource.adhs_heat'),
  -- 2023 cooling-center barriers MMWR
  ('outbreak.maricopa_cooling_center_barriers_2023', 'resource.mcdph_heat'),
  ('outbreak.maricopa_cooling_center_barriers_2023', 'resource.mag_hrn'),
  ('outbreak.maricopa_cooling_center_barriers_2023', 'resource.cdc_one_health'),
  -- 2024 hantavirus
  ('outbreak.az_hantavirus_2024',           'resource.adhs'),
  ('outbreak.az_hantavirus_2024',           'resource.coconino_hhs'),
  -- 2024 heat
  ('outbreak.az_heat_2024',                 'resource.mcdph_heat'),
  ('outbreak.az_heat_2024',                 'resource.adhs_heat'),
  ('outbreak.az_heat_2024',                 'resource.phoenix_ohrm'),
  -- 2025 Coconino plague
  ('outbreak.coconino_plague_2025',         'resource.coconino_hhs'),
  ('outbreak.coconino_plague_2025',         'resource.adhs'),
  ('outbreak.coconino_plague_2025',         'resource.nau_pmi'),
  -- RMSF tribal
  ('outbreak.az_rmsf_tribal_2003_present',  'resource.adhs'),
  ('outbreak.az_rmsf_tribal_2003_present',  'resource.cdc_one_health'),
  ('outbreak.az_rmsf_tribal_2003_present',  'resource.ihs_phoenix'),
  -- RMSF Rodeo
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'resource.cdc_one_health'),
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'resource.adhs'),
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'resource.ihs_phoenix')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Edges: outbreak --markedMilestone--> milestone.*
-- Each outbreak illustrates one or more Figure-3 timeliness milestones,
-- whether the milestone represented a success (clean timeline) or a
-- documented gap (e.g., delayed Notify in 2021 Maricopa WNV).
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 14500 + row_number() OVER (), subject_id, 'markedMilestone', object_id, 'deep-outbreaks'
FROM (VALUES
  -- 1993 Four Corners hantavirus: textbook Detect -> Notify -> Verify ->
  -- Lab confirm timeline, but discovery of a brand-new pathogen.
  ('outbreak.four_corners_hantavirus_1993', 'milestone.detect'),
  ('outbreak.four_corners_hantavirus_1993', 'milestone.notify'),
  ('outbreak.four_corners_hantavirus_1993', 'milestone.verify'),
  ('outbreak.four_corners_hantavirus_1993', 'milestone.lab_confirm'),
  ('outbreak.four_corners_hantavirus_1993', 'milestone.respond'),
  ('outbreak.four_corners_hantavirus_1993', 'milestone.public_comm'),
  -- 2003 WNV: clean bird-then-mosquito-then-human Predict -> Detect chain
  ('outbreak.az_wnv_2003',                  'milestone.predict'),
  ('outbreak.az_wnv_2003',                  'milestone.detect'),
  ('outbreak.az_wnv_2003',                  'milestone.lab_confirm'),
  -- 2014 dengue Yuma/Sonora: cross-border Detect + Notify; Prevent success
  -- (no autochthonous AZ cases despite vector presence)
  ('outbreak.az_dengue_yuma_sonora_2014',   'milestone.detect'),
  ('outbreak.az_dengue_yuma_sonora_2014',   'milestone.notify'),
  ('outbreak.az_dengue_yuma_sonora_2014',   'milestone.prevent'),
  -- 2014 chikungunya: travel screening / Detect milestone
  ('outbreak.az_chikungunya_2014',          'milestone.detect'),
  ('outbreak.az_chikungunya_2014',          'milestone.lab_confirm'),
  -- 2021 Maricopa WNV: famously delayed Notify -- 100 cases already on the
  -- books by the time Vector Control issued the formal alert on 2021-09-02
  ('outbreak.maricopa_wnv_2021',            'milestone.detect'),
  ('outbreak.maricopa_wnv_2021',            'milestone.notify'),
  ('outbreak.maricopa_wnv_2021',            'milestone.respond'),
  ('outbreak.maricopa_wnv_2021',            'milestone.public_comm'),
  ('outbreak.maricopa_wnv_2021',            'milestone.aar'),
  -- HPAI H5N1 ongoing: Predict (wild-bird sentinel) -> Detect -> Notify
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'milestone.predict'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'milestone.detect'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'milestone.notify'),
  ('outbreak.az_hpai_h5n1_wildbird_2022',   'milestone.respond'),
  -- 2023 hantavirus: Detect + Notify (HAN advisory)
  ('outbreak.az_hantavirus_2023',           'milestone.detect'),
  ('outbreak.az_hantavirus_2023',           'milestone.notify'),
  -- 2023 Maricopa heat: end-to-end timeline with documented Respond /
  -- Public Comm; AAR published Mar 2024
  ('outbreak.maricopa_heat_2023',           'milestone.detect'),
  ('outbreak.maricopa_heat_2023',           'milestone.respond'),
  ('outbreak.maricopa_heat_2023',           'milestone.public_comm'),
  ('outbreak.maricopa_heat_2023',           'milestone.outbreak_end'),
  ('outbreak.maricopa_heat_2023',           'milestone.aar'),
  -- 2023 cooling-center barriers MMWR: Prevent + Respond evaluation
  ('outbreak.maricopa_cooling_center_barriers_2023','milestone.prevent'),
  ('outbreak.maricopa_cooling_center_barriers_2023','milestone.respond'),
  ('outbreak.maricopa_cooling_center_barriers_2023','milestone.aar'),
  -- 2024 hantavirus: HAN-advisory Notify is the clearest milestone
  ('outbreak.az_hantavirus_2024',           'milestone.detect'),
  ('outbreak.az_hantavirus_2024',           'milestone.notify'),
  ('outbreak.az_hantavirus_2024',           'milestone.public_comm'),
  -- 2024 record heat
  ('outbreak.az_heat_2024',                 'milestone.predict'),
  ('outbreak.az_heat_2024',                 'milestone.prevent'),
  ('outbreak.az_heat_2024',                 'milestone.respond'),
  ('outbreak.az_heat_2024',                 'milestone.public_comm'),
  ('outbreak.az_heat_2024',                 'milestone.aar'),
  -- 2025 Coconino plague: rapid Detect -> Public Comm same-day
  ('outbreak.coconino_plague_2025',         'milestone.detect'),
  ('outbreak.coconino_plague_2025',         'milestone.lab_confirm'),
  ('outbreak.coconino_plague_2025',         'milestone.public_comm'),
  -- RMSF tribal (long-running): persistent gaps in Detect (children
  -- presenting too late) and Respond (resource constraints)
  ('outbreak.az_rmsf_tribal_2003_present',  'milestone.detect'),
  ('outbreak.az_rmsf_tribal_2003_present',  'milestone.respond'),
  ('outbreak.az_rmsf_tribal_2003_present',  'milestone.public_comm'),
  -- RMSF Rodeo: Prevent (one-shot intervention) + AAR (published in PLOS ONE)
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'milestone.prevent'),
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'milestone.respond'),
  ('outbreak.az_rmsf_rodeo_pilot_2012',     'milestone.aar')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Convenience view: timeline-ready outbreak summary
-- Pulls the most-relevant scalar properties into a single row per outbreak
-- so analysts can run interval / lag arithmetic without unpivoting the
-- property bag by hand.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_outbreak_timeline AS
SELECT
    n.node_id                                                AS outbreak_id,
    n.label                                                  AS outbreak,
    n.description                                            AS description,
    MAX(CASE WHEN p.key = 'start_date'         THEN p.value_text END) AS start_date,
    MAX(CASE WHEN p.key = 'end_date'           THEN p.value_text END) AS end_date,
    MAX(CASE WHEN p.key = 'detect_date'        THEN p.value_text END) AS detect_date,
    MAX(CASE WHEN p.key = 'notify_date'        THEN p.value_text END) AS notify_date,
    MAX(CASE WHEN p.key = 'lab_confirm_date'   THEN p.value_text END) AS lab_confirm_date,
    MAX(CASE WHEN p.key = 'public_comm_date'   THEN p.value_text END) AS public_comm_date,
    MAX(CASE WHEN p.key = 'pathogen_id'        THEN p.value_text END) AS pathogen_id,
    MAX(CASE WHEN p.key = 'primary_geography'  THEN p.value_text END) AS primary_geography,
    MAX(CASE WHEN p.key = 'total_cases'        THEN p.value_num  END) AS total_cases,
    MAX(CASE WHEN p.key = 'total_deaths'       THEN p.value_num  END) AS total_deaths,
    MAX(CASE WHEN p.key = 'reference'          THEN p.value_text END) AS reference
FROM kg.node n
LEFT JOIN kg.property p ON p.node_id = n.node_id
WHERE n.node_type = 'outbreak'
GROUP BY n.node_id, n.label, n.description;
