-- ============================================================================
-- EpiHack Arizona 2026 -- Heat focus group
--
-- Captures the focus group, its four guiding questions, anchor heat data
-- resources (state, county/city, tribal, federal, academic, participatory),
-- and the vulnerability profile.
--
-- Run *after* schema/knowledge_graph.sql and schema/system_designs.sql.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Focus group
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('group.heat',
     'focus_group',
     'Heat',
     'EpiHack Arizona 2026 focus group on extreme-heat surveillance, cooling-center coordination, education, and protection of vulnerable populations.',
     'heat-group')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Focus areas
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, source_fig) VALUES
  ('focus.heat_mortality',         'focus_area', 'Heat-related mortality',                'heat-group'),
  ('focus.heat_morbidity',         'focus_area', 'Heat-related illness (ED visits)',      'heat-group'),
  ('focus.cooling_centers',        'focus_area', 'Cooling centers / heat-relief network', 'heat-group'),
  ('focus.urban_heat_island',      'focus_area', 'Urban heat island',                     'heat-group'),
  ('focus.outdoor_workers',        'focus_area', 'Outdoor workers',                       'heat-group'),
  ('focus.older_adults',           'focus_area', 'Older adults (65+)',                    'heat-group'),
  ('focus.vehicular_heatstroke',   'focus_area', 'Vehicular heatstroke',                  'heat-group'),
  ('focus.energy_insecurity',      'focus_area', 'Energy insecurity / AC affordability',  'heat-group'),
  ('focus.tribal_heat',            'focus_area', 'Tribal heat resilience',                'heat-group'),
  ('focus.border_migrants',        'focus_area', 'Border migrants and asylum-seekers',    'heat-group')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Four guiding questions
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('heat.q1', 'group_question', 'Heat Q1 — Cooling-center awareness',
     'How do you inform the public about the location of cooling centers? Are there interactive tools for the public to use?',
     'heat-q1-cooling-center-awareness'),
  ('heat.q2', 'group_question', 'Heat Q2 — Real-time resource sharing',
     'Do cooling centers share resources in real-time with each other, e.g., we have no space; we are short on water?',
     'heat-q2-real-time-resource-sharing'),
  ('heat.q3', 'group_question', 'Heat Q3 — Severe-heat education',
     'What do you provide for education on severe heat and what to do?',
     'heat-q3-education'),
  ('heat.q4', 'group_question', 'Heat Q4 — Vulnerable populations',
     'Who are most vulnerable to heat in AZ?',
     'heat-q4-vulnerable-populations')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_num) VALUES
  ('heat.q1','question_number',1),
  ('heat.q2','question_number',2),
  ('heat.q3','question_number',3),
  ('heat.q4','question_number',4)
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (8000, 'heat.q1', 'partOf', 'group.heat', 'heat-group'),
  (8001, 'heat.q2', 'partOf', 'group.heat', 'heat-group'),
  (8002, 'heat.q3', 'partOf', 'group.heat', 'heat-group'),
  (8003, 'heat.q4', 'partOf', 'group.heat', 'heat-group')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Vulnerable-population nodes (Q4)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('pop.unsheltered',          'population', 'Unsheltered residents (homeless)',
     'Largest single factor in the post-2010 rise in Maricopa heat deaths; ~36% share in 2016 and elevated since.', 'heat-q4-vulnerable-populations'),
  ('pop.older_adults',         'population', 'Older adults (65+)',
     'Disproportionate share of indoor heat deaths, often linked to AC failure or unaffordability.', 'heat-q4-vulnerable-populations'),
  ('pop.ai_an',                'population', 'American Indian / Alaska Native (Maricopa)',
     'Highest heat-associated death rate per 100,000 in MCDPH data alongside African American residents.', 'heat-q4-vulnerable-populations'),
  ('pop.african_american',     'population', 'African American (Maricopa)',
     'Highest heat-associated death rate per 100,000 in MCDPH data alongside AI/AN residents.', 'heat-q4-vulnerable-populations'),
  ('pop.males',                'population', 'Males',
     '81% of heat-associated deaths in Maricopa County.', 'heat-q4-vulnerable-populations'),
  ('pop.outdoor_workers',      'population', 'Outdoor workers',
     'Landscape, construction, agriculture, roofing, delivery, warehouse; OSHA-recognized occupational exposure.', 'heat-q4-vulnerable-populations'),
  ('pop.sud_smi',              'population', 'People with substance-use disorders or serious mental illness',
     'Frequent overlap with unsheltered homelessness; can blunt physiological heat response.', 'heat-q4-vulnerable-populations'),
  ('pop.children',             'population', 'Infants and young children',
     'Vehicular-heatstroke deaths; AZ has multiple per year.', 'heat-q4-vulnerable-populations'),
  ('pop.electric_medical_dep', 'population', 'People dependent on electric medical equipment',
     'Power outages during heat waves are double jeopardy.', 'heat-q4-vulnerable-populations'),
  ('pop.no_ac_renters',        'population', 'Renters in older housing without working AC',
     'Indoor AC-out deaths are documented in MCDPH data.', 'heat-q4-vulnerable-populations'),
  ('pop.tribal_rural',         'population', 'Tribal community members, especially rural',
     'Compounded by housing-quality gaps and limited cooling-center proximity.', 'heat-q4-vulnerable-populations'),
  ('pop.border_migrants',      'population', 'Migrants and asylum-seekers in border regions',
     'Documented heat-mortality clusters in Pima, Yuma, and Cochise counties.', 'heat-q4-vulnerable-populations')
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 8100 + row_number() OVER (), subject_id, 'identifiedBy', 'heat.q4', 'heat-q4-vulnerable-populations'
FROM (VALUES
  ('pop.unsheltered'),('pop.older_adults'),('pop.ai_an'),('pop.african_american'),
  ('pop.males'),('pop.outdoor_workers'),('pop.sud_smi'),('pop.children'),
  ('pop.electric_medical_dep'),('pop.no_ac_renters'),('pop.tribal_rural'),
  ('pop.border_migrants')
) AS t(subject_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Heat resources / programs
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  -- State
  ('resource.adhs_heat',             'resource_org', 'ADHS Heat Safety & Climate & Health Program',
     'Statewide heat-preparedness; CDC BRACE grantee since 2013; produces annual heat-mortality reports and the Heat Preparedness Network ArcGIS map.', 'heat-resources'),
  ('program.adhs_brace',             'program',      'ADHS Climate & Health (CDC BRACE)',
     'Climate-and-health profile, vulnerability assessments, intervention assessments, adaptation plans.', 'heat-resources'),
  ('tool.adhs_heat_map',             'interactive_tool', 'ADHS Heat Preparedness Network map',
     'ArcGIS Experience map of statewide Heat Preparedness Network locations.', 'heat-resources'),
  ('tool.adhs_heat_mortality_dash',  'dataset',      'ADHS Heat Mortality Surveillance Report',
     'Heat-caused and heat-related deaths report covering 2012-2023+; updated annually.', 'heat-resources'),
  ('initiative.governor_heat_plan',  'initiative',   'Arizona Governor''s Extreme Heat Preparedness Plan',
     'Annual statewide heat-preparedness plan launched May 1.', 'heat-resources'),
  ('resource.ades',                  'resource_org', 'Arizona Department of Economic Security (ADES)',
     'Administers federal LIHEAP utility assistance through community action agencies; critical for AC-bill relief during heat season.', 'heat-resources'),

  -- County / City
  ('resource.mcdph_heat',            'resource_org', 'Maricopa County Department of Public Health — Heat Surveillance',
     'Heat-associated mortality surveillance since 2005/2006; annual Heat-Associated Deaths report; real-time dashboard during season.', 'heat-resources'),
  ('resource.mag_hrn',               'resource_org', 'Maricopa Association of Governments — Heat Relief Network',
     'Regional cooling/hydration/respite network of 200+ sites May 1 to September 30 since 2005.', 'heat-resources'),
  ('tool.mag_hrn_map',               'interactive_tool', 'MAG Heat Relief Network map (hrn.azmag.gov)',
     'Public interactive map with filters by services, hours, and pet-friendly.', 'heat-resources'),
  ('resource.phoenix_ohrm',          'resource_org', 'City of Phoenix Office of Heat Response and Mitigation (HeatReadyPHX)',
     'First publicly-funded municipal heat office in the U.S. (2021); director Dr. David Hondula (ASU).', 'heat-resources'),
  ('resource.pcdh_heat',             'resource_org', 'Pima County Health Department — Cooling Centers',
     'About 36 cooling centers and hydration stations across Pima County.', 'heat-resources'),
  ('resource.tempe_heat_relief',     'resource_org', 'City of Tempe — Heat Relief',
     'Heat relief integrated with homelessness services.', 'heat-resources'),

  -- Tribal
  ('resource.climas',                'resource_org', 'CLIMAS (Climate Assessment for the Southwest)',
     'NOAA-funded UA + ITCA + NMSU partnership since 1998; explicit rural / border / tribal heat-resilience focus.', 'heat-resources'),
  ('resource.itca_tec_heat',         'resource_org', 'Inter Tribal Council of Arizona — Tribal Epidemiology Center (heat work)',
     'Builds tribally-driven epidemiologic capacity across Phoenix and Tucson IHS Areas; CLIMAS partner.', 'heat-resources'),

  -- Federal
  ('resource.cdc_brace',             'resource_org', 'CDC Climate-Ready States & Cities (BRACE)',
     'Federal framework supporting state and local climate-and-health programs; AZ is one of 16 states / 2 cities in the program.', 'heat-resources'),
  ('resource.cdc_nssp_biosense',     'resource_org', 'CDC National Syndromic Surveillance Program (BioSense)',
     'Federal syndromic surveillance backbone; AZ heat-illness ED data flows here.', 'heat-resources'),
  ('resource.atsdr_place_health',    'resource_org', 'CDC ATSDR Place and Health — Extreme Heat Adaptation', NULL, 'heat-resources'),
  ('resource.nws_phoenix',           'resource_org', 'NWS Phoenix',
     'Issues HeatRisk forecasts and Extreme Heat Watch/Warning products for central and southwestern AZ.', 'heat-resources'),
  ('resource.nws_tucson',            'resource_org', 'NWS Tucson',
     'HeatRisk and Extreme Heat products for southeastern AZ.', 'heat-resources'),
  ('tool.nws_heatrisk',              'interactive_tool', 'NWS HeatRisk',
     'Daily ZIP-code-level color-coded heat-health risk forecast (Green/Yellow/Orange/Red/Magenta).', 'heat-resources'),
  ('resource.nihhis',                'resource_org', 'NIHHIS (National Integrated Heat Health Information System)',
     'NOAA + HHS federal cross-agency coordination on heat health; funds UA-led Center for Heat Resilient Communities.', 'heat-resources'),
  ('resource.doe_swifl',             'resource_org', 'DOE Southwest Urban Corridor Integrated Field Laboratory (SW-IFL)',
     'DOE-funded heat/climate field lab anchored in the Phoenix-Tucson urban corridor.', 'heat-resources'),
  ('resource.hud_coc',               'resource_org', 'HUD Continuum of Care (CoC)',
     'Sheltered/unsheltered population data; relevant for the unsheltered cohort bearing the heaviest heat-mortality burden.', 'heat-resources'),

  -- Academic
  ('resource.ua_heat_initiative',    'resource_org', 'UA Heat Resilience Initiative',
     'Umbrella coordinating DOE SW-IFL, NIHHIS Center for Heat Resilient Communities, NOAA CLIMAS, CDC BRACE, NIH SCORCH.', 'heat-resources'),
  ('resource.ua_scorch',             'resource_org', 'UA Southwest Center on Resilience for Climate Change and Health (SCORCH)',
     'NIH-funded; cross-disciplinary research with community partners on climate-driven health threats.', 'heat-resources'),
  ('resource.ua_crh_map',            'resource_org', 'UA Center for Rural Health — AZ Cooling Centers Map',
     'Statewide rural-emphasis cooling-center map.', 'heat-resources'),
  ('resource.ua_climate_health',     'resource_org', 'UA Arizona Climate & Health',
     'Patient-facing materials and clinical resources.', 'heat-resources'),
  ('resource.asu_ker',               'resource_org', 'ASU Knowledge Exchange for Resilience',
     'Co-leads Arizona Heat Resilience Workgroup; informed Governor''s Extreme Heat Preparedness Plan.', 'heat-resources'),
  ('resource.asu_hue',               'resource_org', 'ASU Healthy Urban Environments (legacy)',
     'Heat-mitigation R&D incubator at Global Futures Laboratory; operations wound down with related work continuing in other units.', 'heat-resources'),

  -- Participatory / public-facing
  ('resource.211_az',                'resource_org', '211 Arizona — Heat Relief',
     'Live operators English/Spanish for cooling-center referrals, transportation, utility assistance, emergency AC repair.', 'heat-resources'),
  ('resource.chw_heat',              'program',      'Community Health Workers — heat-risk assessments',
     'CHWs perform in-home heat-risk assessments; called out in the World Café Q4 Heat card as a high-impact tactic.', 'heat-resources'),
  ('resource.train_the_trainer_r9',  'program',      'Western Regional Public Health Train-the-Trainer (HHS Region 9)',
     '12-year-old train-the-trainer program; identified in the World Café Q4 Heat card.', 'heat-resources'),
  ('resource.clear_channel_partner', 'program',      'Clear Channel Outdoor + Maricopa County billboard partnership',
     'Donated digital-billboard inventory displays heat-relief resources during the season.', 'heat-resources')
ON CONFLICT DO NOTHING;

-- Jurisdiction property
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.adhs_heat',             'jurisdiction','state'),
  ('resource.ades',                  'jurisdiction','state'),
  ('resource.mcdph_heat',            'jurisdiction','county'),
  ('resource.mag_hrn',               'jurisdiction','regional'),
  ('resource.phoenix_ohrm',          'jurisdiction','city'),
  ('resource.pcdh_heat',             'jurisdiction','county'),
  ('resource.tempe_heat_relief',     'jurisdiction','city'),
  ('resource.climas',                'jurisdiction','academic_tribal_partnership'),
  ('resource.itca_tec_heat',         'jurisdiction','tribal'),
  ('resource.cdc_brace',             'jurisdiction','federal'),
  ('resource.cdc_nssp_biosense',     'jurisdiction','federal'),
  ('resource.atsdr_place_health',    'jurisdiction','federal'),
  ('resource.nws_phoenix',           'jurisdiction','federal'),
  ('resource.nws_tucson',            'jurisdiction','federal'),
  ('resource.nihhis',                'jurisdiction','federal'),
  ('resource.doe_swifl',             'jurisdiction','federal'),
  ('resource.hud_coc',               'jurisdiction','federal'),
  ('resource.ua_heat_initiative',    'jurisdiction','academic'),
  ('resource.ua_scorch',             'jurisdiction','academic'),
  ('resource.ua_crh_map',            'jurisdiction','academic'),
  ('resource.ua_climate_health',     'jurisdiction','academic'),
  ('resource.asu_ker',               'jurisdiction','academic'),
  ('resource.asu_hue',               'jurisdiction','academic'),
  ('resource.211_az',                'jurisdiction','nonprofit'),
  ('resource.clear_channel_partner', 'jurisdiction','public_private_partnership')
ON CONFLICT DO NOTHING;

-- URLs
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.adhs_heat',             'url','https://www.azdhs.gov/preparedness/epidemiology-disease-control/extreme-weather/heat-safety/heat-preparedness/index.php'),
  ('tool.adhs_heat_map',             'url','https://experience.arcgis.com/experience/c5bdf9ab90894e1baa5860c450dedb3b'),
  ('tool.adhs_heat_mortality_dash',  'url','https://pub.azdhs.gov/health-stats/report/heat/'),
  ('resource.mcdph_heat',            'url','https://www.maricopa.gov/1858/Heat-Surveillance'),
  ('resource.mag_hrn',               'url','https://azmag.gov/Programs/Heat-Relief-Network'),
  ('tool.mag_hrn_map',               'url','https://hrn.azmag.gov/'),
  ('resource.phoenix_ohrm',          'url','https://www.phoenix.gov/heat'),
  ('resource.pcdh_heat',             'url','https://www.pima.gov/2307/Cooling-Centers'),
  ('resource.tempe_heat_relief',     'url','https://www.tempe.gov/government/community-health-and-human-services/housing-services/ending-homelessness/heat-relief'),
  ('resource.climas',                'url','https://climas.arizona.edu/'),
  ('resource.itca_tec_heat',         'url','https://itcaonline.com/programs/research-and-evaluation/epidemiology/'),
  ('resource.atsdr_place_health',    'url','https://www.atsdr.cdc.gov/place-health/share/extreme-heat-adaptation.html'),
  ('resource.nws_phoenix',           'url','https://www.weather.gov/psr/heat'),
  ('resource.nws_tucson',            'url','https://www.weather.gov/twc/'),
  ('resource.ua_heat_initiative',    'url','https://heat.arizona.edu/'),
  ('resource.ua_crh_map',            'url','https://azhealthtxt.arizona.edu/resources/az-cooling-centers-map'),
  ('resource.ua_climate_health',     'url','https://azclimatehealth.arizona.edu/resources/patients'),
  ('resource.asu_ker',               'url','https://resilience.asu.edu/'),
  ('resource.211_az',                'url','https://211arizona.org/crisis/heat-relief/')
ON CONFLICT DO NOTHING;

-- Programs / tools belonging to parent resources
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (8200, 'program.adhs_brace',            'operatedBy','resource.adhs_heat',       'heat-resources'),
  (8201, 'tool.adhs_heat_map',            'operatedBy','resource.adhs_heat',       'heat-resources'),
  (8202, 'tool.adhs_heat_mortality_dash', 'operatedBy','resource.adhs_heat',       'heat-resources'),
  (8203, 'tool.mag_hrn_map',              'operatedBy','resource.mag_hrn',         'heat-resources'),
  (8204, 'tool.nws_heatrisk',             'operatedBy','resource.nws_phoenix',     'heat-resources'),
  (8205, 'resource.chw_heat',             'mentionedBy','wc.q4.heat',              'note-wc-q4-heat'),
  (8206, 'resource.train_the_trainer_r9', 'mentionedBy','wc.q4.heat',              'note-wc-q4-heat')
ON CONFLICT DO NOTHING;

-- Resource -> question (which question this resource informs)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 8300 + row_number() OVER (), subject_id, 'informs', object_id, 'heat-resources'
FROM (VALUES
  -- Q1: public awareness / interactive tools
  ('tool.adhs_heat_map',             'heat.q1'),
  ('tool.mag_hrn_map',               'heat.q1'),
  ('resource.mag_hrn',               'heat.q1'),
  ('resource.pcdh_heat',             'heat.q1'),
  ('resource.ua_crh_map',            'heat.q1'),
  ('resource.211_az',                'heat.q1'),
  ('resource.clear_channel_partner', 'heat.q1'),
  -- Q2: real-time inter-center coordination
  ('resource.mag_hrn',               'heat.q2'),
  ('resource.phoenix_ohrm',          'heat.q2'),
  ('resource.211_az',                'heat.q2'),
  -- Q3: education
  ('resource.adhs_heat',             'heat.q3'),
  ('program.adhs_brace',             'heat.q3'),
  ('resource.cdc_brace',             'heat.q3'),
  ('resource.atsdr_place_health',    'heat.q3'),
  ('resource.ua_heat_initiative',    'heat.q3'),
  ('resource.ua_scorch',             'heat.q3'),
  ('resource.ua_climate_health',     'heat.q3'),
  ('resource.asu_ker',               'heat.q3'),
  ('tool.nws_heatrisk',              'heat.q3'),
  ('resource.nihhis',                'heat.q3'),
  ('resource.chw_heat',              'heat.q3'),
  ('resource.train_the_trainer_r9',  'heat.q3'),
  -- Q4: vulnerability
  ('resource.mcdph_heat',            'heat.q4'),
  ('resource.adhs_heat',             'heat.q4'),
  ('tool.adhs_heat_mortality_dash',  'heat.q4'),
  ('resource.cdc_nssp_biosense',     'heat.q4'),
  ('resource.hud_coc',               'heat.q4'),
  ('resource.climas',                'heat.q4'),
  ('resource.itca_tec_heat',         'heat.q4'),
  ('resource.doe_swifl',             'heat.q4')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Burden statistics
-- ---------------------------------------------------------------------------
INSERT INTO kg.property (node_id, key, value_num) VALUES
  ('group.heat', 'az_heat_deaths_2013_2024',  4320),
  ('group.heat', 'az_heat_deaths_2023',        990),
  ('group.heat', 'az_heat_er_visits_per_year',4298),
  ('group.heat', 'maricopa_surveillance_start_year', 2005),
  ('group.heat', 'mag_hrn_sites',              200),
  ('group.heat', 'maricopa_unsheltered_share_2016_pct', 36),
  ('group.heat', 'maricopa_male_share_pct',    81)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Convenience view: heat resources by jurisdiction with informed questions
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_heat_resources AS
SELECT
  r.node_id     AS resource_id,
  r.label       AS resource,
  r.node_type   AS resource_type,
  j.value_text  AS jurisdiction,
  u.value_text  AS url,
  r.description AS description,
  string_agg(DISTINCT q.label, '; ') AS informs_questions
FROM kg.node r
LEFT JOIN kg.property j ON j.node_id = r.node_id AND j.key = 'jurisdiction'
LEFT JOIN kg.property u ON u.node_id = r.node_id AND u.key = 'url'
LEFT JOIN kg.edge   e   ON e.subject_id = r.node_id AND e.predicate = 'informs'
LEFT JOIN kg.node   q   ON q.node_id = e.object_id
WHERE r.node_type IN ('resource_org','program','interactive_tool','dataset','initiative')
  AND (j.value_text IS NOT NULL OR e.object_id LIKE 'heat.q%')
GROUP BY r.node_id, r.label, r.node_type, j.value_text, u.value_text, r.description;
