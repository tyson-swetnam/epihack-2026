-- ============================================================================
-- EpiHack Arizona 2026 -- Deep dataset / API catalog
--
-- Adds dataset.* and api.* nodes for concrete, downloadable or queryable data
-- products relevant to AZ wildlife / vector-borne / heat surveillance. Each
-- node carries enough metadata (url, format, update_cadence, license_or_terms,
-- auth_required) to drive an actual data pull from the knowledge graph.
--
-- Schema conventions (do not redefine here):
--   * kg.node      (node_id, node_type, label, description, source_fig)
--   * kg.edge      (edge_id, subject_id, predicate, object_id, source_fig)
--   * kg.property  (node_id, key, value_text|value_num)
--
-- edge_id range reserved for this file: 13000-13999
-- source_fig: 'deep-datasets'
--
-- Run *after* schema/knowledge_graph.sql, schema/wildlife_vectors.sql,
-- schema/heat.sql.
--
-- Verification notes:
--   * NEON DP IDs confirmed via data.neonscience.org product pages and user
--     guides:
--       - DP1.10043.001 Mosquitoes sampled from CO2 traps
--       - DP1.10041.001 Mosquito-borne pathogen status
--       - DP1.10093.001 Ticks sampled using drag cloths
--       - DP1.10092.001 Tick-borne pathogen status
--       - DP1.10072.001 Small mammal box trapping
--       - DP1.10064.001 Rodent-borne pathogen status (hantavirus pre-2021,
--                       tick-borne pathogens from 2021)
--       - DP1.10003.001 Breeding landbird point counts
--     All NEON products are CC0-equivalent (NSF / Battelle public release).
--   * SRER (Santa Rita Experimental Range) is NEON Domain 14 core terrestrial
--     site with 10 mosquito CO2 trap points, 6 tick drag plots, and 12
--     bird grids.
--   * WHISPers has a public Django REST backend (USGS-WiM) at
--     whispersservices.usgs.gov; root /api/v1/ enumerated via GitHub.
--   * api.weather.gov is the canonical NWS public REST API; HeatRisk is
--     surfaced via NDFD gridpoint forecasts and digital.weather.gov XML.
--   * iNaturalist API v1/v2 base https://api.inaturalist.org
--   * eBird API 2.0 base https://api.ebird.org/v2/
--   * GBIF Occurrence API base https://api.gbif.org/v1/
--   * HRRR and RTMA distributed via NOAA Open Data on AWS
--     (s3://noaa-hrrr-pds, s3://noaa-rtma-pds).
-- ============================================================================

-- ---------------------------------------------------------------------------
-- NEON data products (wildlife / vectors)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('dataset.neon_mosquito_co2',
     'dataset', 'NEON Mosquitoes sampled from CO2 traps (DP1.10043.001)',
     'Mosquitoes identified to species and sex from CDC CO2 light traps at NEON terrestrial sites. Field collection data products for the mosquito pathogen workflow.',
     'deep-datasets'),
  ('dataset.neon_mosquito_pathogen',
     'dataset', 'NEON Mosquito-borne pathogen status (DP1.10041.001)',
     'Pooled mosquito pathogen test results (historic PCR; transitioning to RNA sequencing from late 2024 pilot) derived from DP1.10043.001 specimens.',
     'deep-datasets'),
  ('dataset.neon_tick_drag',
     'dataset', 'NEON Ticks sampled using drag cloths (DP1.10093.001)',
     'Tick abundance and diversity by species and lifestage from standardized drag/flag sampling at NEON terrestrial plots.',
     'deep-datasets'),
  ('dataset.neon_tick_pathogen',
     'dataset', 'NEON Tick-borne pathogen status (DP1.10092.001)',
     'Pathogen test results from nymphal ticks collected under DP1.10093.001 (e.g. Borrelia, Anaplasma, Ehrlichia, Babesia).',
     'deep-datasets'),
  ('dataset.neon_small_mammal',
     'dataset', 'NEON Small mammal box trapping (DP1.10072.001)',
     'Mark-recapture small mammal trapping data with species, sex, life-stage, mass, and reproductive condition.',
     'deep-datasets'),
  ('dataset.neon_rodent_pathogen',
     'dataset', 'NEON Rodent-borne pathogen status (DP1.10064.001)',
     'Rodent pathogen test results; pre-2021 records target hantavirus, 2021+ target tick-borne pathogens from rodent ear tissue.',
     'deep-datasets'),
  ('dataset.neon_bird_pointcounts',
     'dataset', 'NEON Breeding landbird point counts (DP1.10003.001)',
     '6-minute point counts of breeding landbirds at NEON Distributed Bird Grids; useful as HPAI baseline and bird community covariate.',
     'deep-datasets'),
  ('api.neon_portal',
     'api', 'NEON Data Portal API',
     'REST API for discovery and download of NEON observational and instrument data products as ZIP/CSV bundles, with monthly site-product partitions.',
     'deep-datasets')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  -- NEON mosquito CO2
  ('dataset.neon_mosquito_co2', 'url',               'https://data.neonscience.org/data-products/DP1.10043.001'),
  ('dataset.neon_mosquito_co2', 'dp_id',             'DP1.10043.001'),
  ('dataset.neon_mosquito_co2', 'format',            'csv'),
  ('dataset.neon_mosquito_co2', 'update_cadence',    'monthly'),
  ('dataset.neon_mosquito_co2', 'observation_cadence','Every 2 weeks at core sites; every 4 weeks at relocatable sites during the mosquito-active season'),
  ('dataset.neon_mosquito_co2', 'az_sites',          'SRER (10 mosquito points; AZ core terrestrial, Domain 14 Desert Southwest)'),
  ('dataset.neon_mosquito_co2', 'license_or_terms',  'CC0 / NEON open data policy'),
  ('dataset.neon_mosquito_co2', 'auth_required',     'none'),
  -- NEON mosquito pathogen
  ('dataset.neon_mosquito_pathogen', 'url',              'https://data.neonscience.org/data-products/DP1.10041.001'),
  ('dataset.neon_mosquito_pathogen', 'dp_id',            'DP1.10041.001'),
  ('dataset.neon_mosquito_pathogen', 'format',           'csv'),
  ('dataset.neon_mosquito_pathogen', 'update_cadence',   'annual'),
  ('dataset.neon_mosquito_pathogen', 'observation_cadence','Annual pooled-PCR; pilot RNA-seq protocol from 2024'),
  ('dataset.neon_mosquito_pathogen', 'az_sites',         'SRER'),
  ('dataset.neon_mosquito_pathogen', 'license_or_terms', 'CC0 / NEON open data policy'),
  ('dataset.neon_mosquito_pathogen', 'auth_required',    'none'),
  -- NEON tick drag
  ('dataset.neon_tick_drag', 'url',                   'https://data.neonscience.org/data-products/DP1.10093.001'),
  ('dataset.neon_tick_drag', 'dp_id',                 'DP1.10093.001'),
  ('dataset.neon_tick_drag', 'format',                'csv'),
  ('dataset.neon_tick_drag', 'update_cadence',        'monthly'),
  ('dataset.neon_tick_drag', 'observation_cadence',   'Every 3 weeks at sites with >5 ticks/yr; every 6 weeks elsewhere'),
  ('dataset.neon_tick_drag', 'az_sites',              'SRER (6 tick plots)'),
  ('dataset.neon_tick_drag', 'license_or_terms',      'CC0 / NEON open data policy'),
  ('dataset.neon_tick_drag', 'auth_required',         'none'),
  -- NEON tick pathogen
  ('dataset.neon_tick_pathogen', 'url',                'https://data.neonscience.org/data-products/DP1.10092.001'),
  ('dataset.neon_tick_pathogen', 'dp_id',              'DP1.10092.001'),
  ('dataset.neon_tick_pathogen', 'format',             'csv'),
  ('dataset.neon_tick_pathogen', 'update_cadence',     'annual'),
  ('dataset.neon_tick_pathogen', 'observation_cadence','Per-season pooled qPCR'),
  ('dataset.neon_tick_pathogen', 'az_sites',           'SRER'),
  ('dataset.neon_tick_pathogen', 'license_or_terms',   'CC0 / NEON open data policy'),
  ('dataset.neon_tick_pathogen', 'auth_required',      'none'),
  -- NEON small mammal
  ('dataset.neon_small_mammal', 'url',                'https://data.neonscience.org/data-products/DP1.10072.001'),
  ('dataset.neon_small_mammal', 'dp_id',              'DP1.10072.001'),
  ('dataset.neon_small_mammal', 'format',             'csv'),
  ('dataset.neon_small_mammal', 'update_cadence',     'monthly'),
  ('dataset.neon_small_mammal', 'observation_cadence','3 consecutive nights of Sherman trapping per bout, 4-6 bouts per active season'),
  ('dataset.neon_small_mammal', 'az_sites',           'SRER (8 mammal grids)'),
  ('dataset.neon_small_mammal', 'license_or_terms',   'CC0 / NEON open data policy'),
  ('dataset.neon_small_mammal', 'auth_required',      'none'),
  -- NEON rodent pathogen
  ('dataset.neon_rodent_pathogen', 'url',              'https://data.neonscience.org/data-products/DP1.10064.001'),
  ('dataset.neon_rodent_pathogen', 'dp_id',            'DP1.10064.001'),
  ('dataset.neon_rodent_pathogen', 'format',           'csv'),
  ('dataset.neon_rodent_pathogen', 'update_cadence',   'annual'),
  ('dataset.neon_rodent_pathogen', 'observation_cadence','Per-season serology / PCR on collected ear-tissue and blood; hantavirus pre-2021, tick-borne pathogens from 2021'),
  ('dataset.neon_rodent_pathogen', 'az_sites',         'SRER'),
  ('dataset.neon_rodent_pathogen', 'license_or_terms', 'CC0 / NEON open data policy'),
  ('dataset.neon_rodent_pathogen', 'auth_required',    'none'),
  -- NEON bird point counts
  ('dataset.neon_bird_pointcounts', 'url',              'https://data.neonscience.org/data-products/DP1.10003.001'),
  ('dataset.neon_bird_pointcounts', 'dp_id',            'DP1.10003.001'),
  ('dataset.neon_bird_pointcounts', 'format',           'csv'),
  ('dataset.neon_bird_pointcounts', 'update_cadence',   'annual'),
  ('dataset.neon_bird_pointcounts', 'observation_cadence','1-2 visits per breeding season per grid (6-min counts, 9 points/grid)'),
  ('dataset.neon_bird_pointcounts', 'az_sites',         'SRER (12 Distributed Bird Grids)'),
  ('dataset.neon_bird_pointcounts', 'license_or_terms', 'CC0 / NEON open data policy'),
  ('dataset.neon_bird_pointcounts', 'auth_required',    'none'),
  -- NEON portal API
  ('api.neon_portal', 'url',              'https://data.neonscience.org/data-api/'),
  ('api.neon_portal', 'format',           'json-api'),
  ('api.neon_portal', 'update_cadence',   'realtime'),
  ('api.neon_portal', 'license_or_terms', 'CC0 / NEON open data policy'),
  ('api.neon_portal', 'auth_required',    'none')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- USGS / WHISPers
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('dataset.whispers_events',
     'dataset', 'WHISPers wildlife mortality / morbidity events',
     'Public repository of historic and current wildlife mortality/morbidity events reported to USGS NWHC, with location, species, suspected etiology, and laboratory confirmation status.',
     'deep-datasets'),
  ('api.whispers_rest',
     'api',     'WHISPers REST API (whispersservices)',
     'Django REST Framework backend that powers the WHISPers web app; exposes events, locations, species, diagnoses, and contacts as JSON resources.',
     'deep-datasets')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('dataset.whispers_events', 'url',              'https://whispers.usgs.gov/'),
  ('dataset.whispers_events', 'format',           'csv'),
  ('dataset.whispers_events', 'update_cadence',   'realtime'),
  ('dataset.whispers_events', 'license_or_terms', 'public-domain (USGS)'),
  ('dataset.whispers_events', 'auth_required',    'none'),
  ('api.whispers_rest',       'url',              'https://whispersservices.usgs.gov/api/v1/'),
  ('api.whispers_rest',       'format',           'json-api'),
  ('api.whispers_rest',       'update_cadence',   'realtime'),
  ('api.whispers_rest',       'license_or_terms', 'public-domain (USGS)'),
  ('api.whispers_rest',       'auth_required',    'none')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- CDC / federal syndromic & reportable
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('dataset.nssp_essence',
     'dataset', 'CDC NSSP BioSense Platform (ESSENCE)',
     'National syndromic surveillance feed (chief complaint, triage notes, diagnosis) from participating EDs; supports heat-related illness (HRI) and arboviral syndromic queries; near-real-time (~24h latency).',
     'deep-datasets'),
  ('dataset.cdc_heat_health_tracker',
     'dataset', 'CDC Heat & Health Tracker',
     'NSSP-derived rate of ED visits associated with heat-related illness per 100,000 ED visits by HHS region; daily/weekly.',
     'deep-datasets'),
  ('api.cdc_epht',
     'api',     'CDC Environmental Public Health Tracking Network API',
     'REST API for the National Environmental Public Health Tracking Network; provides heat events, heat-related ED visits and deaths, vector-borne disease counts, and environmental indicators.',
     'deep-datasets'),
  ('dataset.rckms',
     'dataset', 'Reportable Conditions Knowledge Management System (RCKMS)',
     'CSTE/CDC authoritative registry of reportable-condition rules per jurisdiction (260 conditions; 94 nationally notifiable); decision-support service for electronic case reporting (eCR).',
     'deep-datasets'),
  ('dataset.hhs_heat_health_index',
     'dataset', 'HHS / CDC Heat and Health Index (HHI)',
     'ZIP-code-level composite vulnerability index across 25 indicators (heat exposure, HRI history, pre-existing conditions, sociodemographics, built environment).',
     'deep-datasets'),
  ('dataset.healthdata_gov',
     'dataset', 'HealthData.gov heat & vector datasets catalog',
     'HHS open-data catalog hosting numerous heat-illness, arboviral, and zoonotic-disease tabular datasets contributed by CDC, NIH, HRSA, and partners.',
     'deep-datasets')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('dataset.nssp_essence',           'url',              'https://www.cdc.gov/nssp/php/about/about-nssp-and-the-biosense-platform.html'),
  ('dataset.nssp_essence',           'format',           'json-api'),
  ('dataset.nssp_essence',           'update_cadence',   'realtime'),
  ('dataset.nssp_essence',           'license_or_terms', 'agency-terms (NSSP Data Use Agreement)'),
  ('dataset.nssp_essence',           'auth_required',    'agency-account'),
  ('dataset.cdc_heat_health_tracker','url',              'https://ephtracking.cdc.gov/Applications/heatTracker/'),
  ('dataset.cdc_heat_health_tracker','format',           'json-api'),
  ('dataset.cdc_heat_health_tracker','update_cadence',   'daily'),
  ('dataset.cdc_heat_health_tracker','license_or_terms', 'public-domain'),
  ('dataset.cdc_heat_health_tracker','auth_required',    'none'),
  ('api.cdc_epht',                   'url',              'https://ephtracking.cdc.gov/apigateway/api/v1/'),
  ('api.cdc_epht',                   'format',           'json-api'),
  ('api.cdc_epht',                   'update_cadence',   'daily'),
  ('api.cdc_epht',                   'license_or_terms', 'public-domain'),
  ('api.cdc_epht',                   'auth_required',    'none'),
  ('dataset.rckms',                  'url',              'https://www.rckms.org/'),
  ('dataset.rckms',                  'format',           'json-api'),
  ('dataset.rckms',                  'update_cadence',   'ad-hoc'),
  ('dataset.rckms',                  'license_or_terms', 'agency-terms (CSTE)'),
  ('dataset.rckms',                  'auth_required',    'agency-account'),
  ('dataset.hhs_heat_health_index',  'url',              'https://ephtracking.cdc.gov/Applications/heatTracker/HHI'),
  ('dataset.hhs_heat_health_index',  'format',           'csv'),
  ('dataset.hhs_heat_health_index',  'update_cadence',   'annual'),
  ('dataset.hhs_heat_health_index',  'license_or_terms', 'public-domain'),
  ('dataset.hhs_heat_health_index',  'auth_required',    'none'),
  ('dataset.healthdata_gov',         'url',              'https://healthdata.gov/'),
  ('dataset.healthdata_gov',         'format',           'csv'),
  ('dataset.healthdata_gov',         'update_cadence',   'ad-hoc'),
  ('dataset.healthdata_gov',         'license_or_terms', 'public-domain'),
  ('dataset.healthdata_gov',         'auth_required',    'none')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- NWS / NOAA weather APIs and gridded models
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('api.nws_weather_gov',
     'api',     'NWS api.weather.gov public REST API',
     'Canonical NWS public API: alerts, point forecasts, gridpoint forecasts (including HeatRisk where surfaced), zones, stations, and observations. OpenAPI spec at /openapi.json.',
     'deep-datasets'),
  ('dataset.nws_heatrisk',
     'dataset', 'NWS HeatRisk daily forecast',
     'Daily ZIP-code-level color-coded heat-health risk (Green/Yellow/Orange/Red/Magenta); experimental WPC product covering CONUS; ingestible as gridded GeoTIFF/GRIB or NDFD element.',
     'deep-datasets'),
  ('dataset.ndfd',
     'dataset', 'NWS National Digital Forecast Database (NDFD)',
     'Mosaic of NWS gridded forecasts (Tmax, Tmin, HeatIndex, ApparentT, HeatRisk) at ~2.5 km CONUS resolution; XML/REST and GRIB2.',
     'deep-datasets'),
  ('api.ndfd_xml',
     'api',     'NDFD XML/REST gridpoint service',
     'NDFD XML web service returning DWML/TSML for point or gridded time-series of forecast elements including HeatRisk.',
     'deep-datasets'),
  ('dataset.cpc_seasonal_outlook',
     'dataset', 'NOAA CPC seasonal temperature & precipitation outlooks',
     'Monthly-to-13-month probabilistic outlooks (above/below normal); supplied as shapefiles and rasters.',
     'deep-datasets'),
  ('dataset.hrrr',
     'dataset', 'NOAA HRRR (High-Resolution Rapid Refresh) model',
     '3 km hourly-updated convection-allowing model; surface T2m, dewpoint, wind, radiation; full CONUS coverage; key heat-wave nowcast input.',
     'deep-datasets'),
  ('dataset.rtma',
     'dataset', 'NOAA RTMA / URMA real-time mesoscale analysis',
     '2.5 km hourly near-surface analysis (T, RH, wind, sky cover, visibility) for CONUS; 30-45 min latency; URMA is the 6-h-delayed reprocessing.',
     'deep-datasets')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('api.nws_weather_gov',         'url',              'https://api.weather.gov/'),
  ('api.nws_weather_gov',         'format',           'json-api'),
  ('api.nws_weather_gov',         'update_cadence',   'realtime'),
  ('api.nws_weather_gov',         'license_or_terms', 'public-domain (NWS)'),
  ('api.nws_weather_gov',         'auth_required',    'none'),
  ('dataset.nws_heatrisk',        'url',              'https://www.wpc.ncep.noaa.gov/heatrisk/'),
  ('dataset.nws_heatrisk',        'format',           'geotiff'),
  ('dataset.nws_heatrisk',        'update_cadence',   'daily'),
  ('dataset.nws_heatrisk',        'license_or_terms', 'public-domain (NWS)'),
  ('dataset.nws_heatrisk',        'auth_required',    'none'),
  ('dataset.ndfd',                'url',              'https://www.ncei.noaa.gov/products/weather-climate-models/national-digital-forecast-database'),
  ('dataset.ndfd',                'format',           'grib2'),
  ('dataset.ndfd',                'update_cadence',   'hourly'),
  ('dataset.ndfd',                'license_or_terms', 'public-domain (NWS)'),
  ('dataset.ndfd',                'auth_required',    'none'),
  ('api.ndfd_xml',                'url',              'https://digital.weather.gov/xml/rest.php'),
  ('api.ndfd_xml',                'format',           'xml'),
  ('api.ndfd_xml',                'update_cadence',   'hourly'),
  ('api.ndfd_xml',                'license_or_terms', 'public-domain (NWS)'),
  ('api.ndfd_xml',                'auth_required',    'none'),
  ('dataset.cpc_seasonal_outlook','url',              'https://www.cpc.ncep.noaa.gov/products/GIS/GIS_DATA/us_tempprcpfcst/'),
  ('dataset.cpc_seasonal_outlook','format',           'shapefile'),
  ('dataset.cpc_seasonal_outlook','update_cadence',   'monthly'),
  ('dataset.cpc_seasonal_outlook','license_or_terms', 'public-domain (NOAA)'),
  ('dataset.cpc_seasonal_outlook','auth_required',    'none'),
  ('dataset.hrrr',                'url',              's3://noaa-hrrr-pds/'),
  ('dataset.hrrr',                'format',           'grib2'),
  ('dataset.hrrr',                'update_cadence',   'hourly'),
  ('dataset.hrrr',                'license_or_terms', 'public-domain (NOAA NODD)'),
  ('dataset.hrrr',                'auth_required',    'none'),
  ('dataset.rtma',                'url',              's3://noaa-rtma-pds/'),
  ('dataset.rtma',                'format',           'grib2'),
  ('dataset.rtma',                'update_cadence',   'hourly'),
  ('dataset.rtma',                'license_or_terms', 'public-domain (NOAA NODD)'),
  ('dataset.rtma',                'auth_required',    'none')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Citizen-science biodiversity APIs
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('api.inaturalist_v1',
     'api',     'iNaturalist API v1',
     'REST/JSON API for iNaturalist observations, taxa, places, and projects (Swagger at /v1/docs). Useful for AZ vector and reservoir-host occurrence pulls.',
     'deep-datasets'),
  ('api.inaturalist_v2',
     'api',     'iNaturalist API v2',
     'Newer Elasticsearch-backed API exposing the same resources with field-selection (?fields=) syntax; preferred for scalable pulls.',
     'deep-datasets'),
  ('api.ebird_v2',
     'api',     'eBird API 2.0',
     'Cornell Lab REST API for recent observations, hotspots, region lists, and taxonomy. Requires per-user API token (x-ebirdapitoken header).',
     'deep-datasets'),
  ('api.gbif_occurrence',
     'api',     'GBIF Occurrence API',
     'REST API for global biodiversity occurrence search and bulk downloads; aggregates iNaturalist Research-Grade, eBird, NEON, and museum records.',
     'deep-datasets')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('api.inaturalist_v1',  'url',              'https://api.inaturalist.org/v1/'),
  ('api.inaturalist_v1',  'format',           'json-api'),
  ('api.inaturalist_v1',  'update_cadence',   'realtime'),
  ('api.inaturalist_v1',  'license_or_terms', 'CC-BY-NC default; per-observation licenses vary (CC0/CC-BY also common)'),
  ('api.inaturalist_v1',  'auth_required',    'none'),
  ('api.inaturalist_v2',  'url',              'https://api.inaturalist.org/v2/'),
  ('api.inaturalist_v2',  'format',           'json-api'),
  ('api.inaturalist_v2',  'update_cadence',   'realtime'),
  ('api.inaturalist_v2',  'license_or_terms', 'CC-BY-NC default; per-observation licenses vary'),
  ('api.inaturalist_v2',  'auth_required',    'none'),
  ('api.ebird_v2',        'url',              'https://api.ebird.org/v2/'),
  ('api.ebird_v2',        'format',           'json-api'),
  ('api.ebird_v2',        'update_cadence',   'realtime'),
  ('api.ebird_v2',        'license_or_terms', 'eBird Data Access Terms of Use (free for non-commercial)'),
  ('api.ebird_v2',        'auth_required',    'api-key'),
  ('api.gbif_occurrence', 'url',              'https://api.gbif.org/v1/occurrence/search'),
  ('api.gbif_occurrence', 'format',           'json-api'),
  ('api.gbif_occurrence', 'update_cadence',   'daily'),
  ('api.gbif_occurrence', 'license_or_terms', 'CC0 / CC-BY / CC-BY-NC per dataset'),
  ('api.gbif_occurrence', 'auth_required',    'none')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- State / county / regional datasets
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('dataset.adhs_heat_mortality_report',
     'dataset', 'ADHS Heat-Caused & Heat-Related Deaths in Arizona (PDF/XLSX series)',
     'Annual statewide heat mortality surveillance report covering 2013-present; 4,320+ deaths cumulative through 2024; PDF + Excel companion tables.',
     'deep-datasets'),
  ('dataset.adhs_heat_dashboard',
     'dataset', 'ADHS Heat Mortality Surveillance dashboard',
     'Interactive dashboard surfacing heat-caused vs heat-related deaths by year, age, sex, race, and county.',
     'deep-datasets'),
  ('dataset.adhs_arbovirus_summary',
     'dataset', 'ADHS Arbovirus Surveillance Summary',
     'Annual VBZD / arbovirus surveillance summary reports (WNV, SLE, Dengue, Zika, chikungunya) from ADHS Vector-Borne & Zoonotic Diseases Program.',
     'deep-datasets'),
  ('dataset.adhs_epht_quickreports',
     'dataset', 'Arizona EPHT Quick Reports',
     'ADHS Environmental Public Health Tracking GIS Quick Reports — air quality, heat, water, vector indicators by county and ZIP.',
     'deep-datasets'),
  ('dataset.maricopa_heat_reports',
     'dataset', 'Maricopa County Heat-Associated Deaths Reports (archive)',
     'Maricopa County Department of Public Health annual and weekly heat-associated mortality reports since 2005; PDF series + season dashboard.',
     'deep-datasets'),
  ('dataset.mag_hrn_locations',
     'dataset', 'MAG Heat Relief Network site locations',
     'Open-data feature service of 200+ cooling, hydration, and respite locations active May 1 - Sep 30; refreshed daily during season.',
     'deep-datasets'),
  ('api.mag_hrn_arcgis',
     'api',     'MAG ArcGIS REST service — Heat Relief Network',
     'ArcGIS feature server exposing Cooling Center / Hydration Station / Respite Center / Donation Site layers; queryable by geometry, hours, attributes.',
     'deep-datasets'),
  ('api.azmag_opendata',
     'api',     'Maricopa Association of Governments Open Data portal',
     'ArcGIS Hub open-data site for MAG region; downloads as CSV/GeoJSON/Shapefile and ArcGIS feature services.',
     'deep-datasets')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('dataset.adhs_heat_mortality_report',  'url',              'https://pub.azdhs.gov/health-stats/report/heat/'),
  ('dataset.adhs_heat_mortality_report',  'format',           'pdf'),
  ('dataset.adhs_heat_mortality_report',  'update_cadence',   'annual'),
  ('dataset.adhs_heat_mortality_report',  'license_or_terms', 'agency-terms (ADHS public)'),
  ('dataset.adhs_heat_mortality_report',  'auth_required',    'none'),
  ('dataset.adhs_heat_dashboard',         'url',              'https://pub.azdhs.gov/health-stats/report/heat/index.php'),
  ('dataset.adhs_heat_dashboard',         'format',           'json-api'),
  ('dataset.adhs_heat_dashboard',         'update_cadence',   'annual'),
  ('dataset.adhs_heat_dashboard',         'license_or_terms', 'agency-terms (ADHS public)'),
  ('dataset.adhs_heat_dashboard',         'auth_required',    'none'),
  ('dataset.adhs_arbovirus_summary',      'url',              'https://www.azdhs.gov/preparedness/epidemiology-disease-control/infectious-disease-epidemiology/index.php'),
  ('dataset.adhs_arbovirus_summary',      'format',           'pdf'),
  ('dataset.adhs_arbovirus_summary',      'update_cadence',   'weekly'),
  ('dataset.adhs_arbovirus_summary',      'license_or_terms', 'agency-terms (ADHS public)'),
  ('dataset.adhs_arbovirus_summary',      'auth_required',    'none'),
  ('dataset.adhs_epht_quickreports',      'url',              'https://gis.azdhs.gov/ephtreports/'),
  ('dataset.adhs_epht_quickreports',      'format',           'json-api'),
  ('dataset.adhs_epht_quickreports',      'update_cadence',   'monthly'),
  ('dataset.adhs_epht_quickreports',      'license_or_terms', 'agency-terms (ADHS public)'),
  ('dataset.adhs_epht_quickreports',      'auth_required',    'none'),
  ('dataset.maricopa_heat_reports',       'url',              'https://www.maricopa.gov/Archive.aspx?AMID=103'),
  ('dataset.maricopa_heat_reports',       'format',           'pdf'),
  ('dataset.maricopa_heat_reports',       'update_cadence',   'weekly'),
  ('dataset.maricopa_heat_reports',       'license_or_terms', 'agency-terms (Maricopa County public)'),
  ('dataset.maricopa_heat_reports',       'auth_required',    'none'),
  ('dataset.mag_hrn_locations',           'url',              'https://hrn.azmag.gov/'),
  ('dataset.mag_hrn_locations',           'format',           'geojson'),
  ('dataset.mag_hrn_locations',           'update_cadence',   'daily'),
  ('dataset.mag_hrn_locations',           'license_or_terms', 'agency-terms (MAG public)'),
  ('dataset.mag_hrn_locations',           'auth_required',    'none'),
  ('api.mag_hrn_arcgis',                  'url',              'https://geo.azmag.gov/arcgis/rest/services/maps/Heat_Relief_Network/MapServer'),
  ('api.mag_hrn_arcgis',                  'format',           'json-api'),
  ('api.mag_hrn_arcgis',                  'update_cadence',   'daily'),
  ('api.mag_hrn_arcgis',                  'license_or_terms', 'agency-terms (MAG public)'),
  ('api.mag_hrn_arcgis',                  'auth_required',    'none'),
  ('api.azmag_opendata',                  'url',              'https://geodata-azmag.opendata.arcgis.com/'),
  ('api.azmag_opendata',                  'format',           'json-api'),
  ('api.azmag_opendata',                  'update_cadence',   'ad-hoc'),
  ('api.azmag_opendata',                  'license_or_terms', 'agency-terms (MAG public)'),
  ('api.azmag_opendata',                  'auth_required',    'none')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Edges: each dataset/api --operatedBy--> resource.<org>
-- (Using org node IDs from schema/wildlife_vectors.sql and schema/heat.sql.)
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 13000 + row_number() OVER (), subject_id, 'operatedBy', object_id, 'deep-datasets'
FROM (VALUES
  -- NEON
  ('dataset.neon_mosquito_co2',        'resource.neon'),
  ('dataset.neon_mosquito_pathogen',   'resource.neon'),
  ('dataset.neon_tick_drag',           'resource.neon'),
  ('dataset.neon_tick_pathogen',       'resource.neon'),
  ('dataset.neon_small_mammal',        'resource.neon'),
  ('dataset.neon_rodent_pathogen',     'resource.neon'),
  ('dataset.neon_bird_pointcounts',    'resource.neon'),
  ('api.neon_portal',                  'resource.neon'),
  -- WHISPers / USGS NWHC
  ('dataset.whispers_events',          'resource.usgs_nwhc'),
  ('api.whispers_rest',                'resource.usgs_nwhc'),
  -- CDC / federal
  ('dataset.nssp_essence',             'resource.cdc_nssp_biosense'),
  ('dataset.cdc_heat_health_tracker',  'resource.cdc_nssp_biosense'),
  ('api.cdc_epht',                     'resource.atsdr_place_health'),
  ('dataset.rckms',                    'resource.cdc_one_health'),
  ('dataset.hhs_heat_health_index',    'resource.atsdr_place_health'),
  ('dataset.healthdata_gov',           'resource.cdc_one_health'),
  -- NWS / NOAA (HeatRisk attributed to NWS Phoenix WFO as primary AZ producer;
  -- the api / gridded products are produced by NWS / NOAA broadly)
  ('api.nws_weather_gov',              'resource.nws_phoenix'),
  ('dataset.nws_heatrisk',             'resource.nws_phoenix'),
  ('dataset.ndfd',                     'resource.nws_phoenix'),
  ('api.ndfd_xml',                     'resource.nws_phoenix'),
  ('dataset.cpc_seasonal_outlook',     'resource.nihhis'),
  ('dataset.hrrr',                     'resource.nihhis'),
  ('dataset.rtma',                     'resource.nihhis'),
  -- Citizen science
  ('api.inaturalist_v1',               'resource.inaturalist'),
  ('api.inaturalist_v2',               'resource.inaturalist'),
  ('api.ebird_v2',                     'resource.ebird'),
  ('api.gbif_occurrence',              'resource.gbif'),
  -- State / county
  ('dataset.adhs_heat_mortality_report','resource.adhs_heat'),
  ('dataset.adhs_heat_dashboard',      'resource.adhs_heat'),
  ('dataset.adhs_arbovirus_summary',   'resource.adhs'),
  ('dataset.adhs_epht_quickreports',   'resource.adhs'),
  ('dataset.maricopa_heat_reports',    'resource.mcdph_heat'),
  ('dataset.mag_hrn_locations',        'resource.mag_hrn'),
  ('api.mag_hrn_arcgis',               'resource.mag_hrn'),
  ('api.azmag_opendata',               'resource.mag_hrn')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Edges: each dataset/api --informs--> wv.qN or heat.qN
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 13500 + row_number() OVER (), subject_id, 'informs', object_id, 'deep-datasets'
FROM (VALUES
  -- Wildlife / vector density (WV Q1)
  ('dataset.neon_mosquito_co2',        'wv.q1'),
  ('dataset.neon_tick_drag',           'wv.q1'),
  ('dataset.neon_small_mammal',        'wv.q1'),
  ('dataset.neon_bird_pointcounts',    'wv.q1'),
  ('api.neon_portal',                  'wv.q1'),
  ('api.inaturalist_v1',               'wv.q1'),
  ('api.inaturalist_v2',               'wv.q1'),
  ('api.ebird_v2',                     'wv.q1'),
  ('api.gbif_occurrence',              'wv.q1'),
  -- Zoonotic surveillance in wildlife / vectors (WV Q2)
  ('dataset.neon_mosquito_pathogen',   'wv.q2'),
  ('dataset.neon_tick_pathogen',       'wv.q2'),
  ('dataset.neon_rodent_pathogen',     'wv.q2'),
  ('dataset.whispers_events',          'wv.q2'),
  ('api.whispers_rest',                'wv.q2'),
  ('dataset.adhs_arbovirus_summary',   'wv.q2'),
  ('dataset.rckms',                    'wv.q2'),
  -- Technologies (WV Q3)
  ('api.neon_portal',                  'wv.q3'),
  ('api.gbif_occurrence',              'wv.q3'),
  ('api.whispers_rest',                'wv.q3'),
  -- Participatory (WV Q4)
  ('api.inaturalist_v1',               'wv.q4'),
  ('api.inaturalist_v2',               'wv.q4'),
  ('api.ebird_v2',                     'wv.q4'),
  ('dataset.whispers_events',          'wv.q4'),
  -- Heat Q1 (public awareness / cooling-center locations)
  ('dataset.mag_hrn_locations',        'heat.q1'),
  ('api.mag_hrn_arcgis',               'heat.q1'),
  ('api.azmag_opendata',               'heat.q1'),
  -- Heat Q2 (real-time coordination)
  ('api.mag_hrn_arcgis',               'heat.q2'),
  ('api.nws_weather_gov',              'heat.q2'),
  -- Heat Q3 (education / forecasting context)
  ('dataset.nws_heatrisk',             'heat.q3'),
  ('dataset.ndfd',                     'heat.q3'),
  ('api.ndfd_xml',                     'heat.q3'),
  ('dataset.cpc_seasonal_outlook',     'heat.q3'),
  ('dataset.hrrr',                     'heat.q3'),
  ('dataset.rtma',                     'heat.q3'),
  ('api.nws_weather_gov',              'heat.q3'),
  -- Heat Q4 (vulnerability / surveillance)
  ('dataset.nssp_essence',             'heat.q4'),
  ('dataset.cdc_heat_health_tracker',  'heat.q4'),
  ('api.cdc_epht',                     'heat.q4'),
  ('dataset.hhs_heat_health_index',    'heat.q4'),
  ('dataset.healthdata_gov',           'heat.q4'),
  ('dataset.adhs_heat_mortality_report','heat.q4'),
  ('dataset.adhs_heat_dashboard',      'heat.q4'),
  ('dataset.adhs_epht_quickreports',   'heat.q4'),
  ('dataset.maricopa_heat_reports',    'heat.q4')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Convenience view: every dataset / api with its metadata flattened
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_datasets_apis AS
SELECT
  n.node_id,
  n.node_type,
  n.label,
  n.description,
  MAX(CASE WHEN p.key = 'url'              THEN p.value_text END) AS url,
  MAX(CASE WHEN p.key = 'format'           THEN p.value_text END) AS format,
  MAX(CASE WHEN p.key = 'update_cadence'   THEN p.value_text END) AS update_cadence,
  MAX(CASE WHEN p.key = 'license_or_terms' THEN p.value_text END) AS license_or_terms,
  MAX(CASE WHEN p.key = 'auth_required'    THEN p.value_text END) AS auth_required,
  MAX(CASE WHEN p.key = 'dp_id'            THEN p.value_text END) AS dp_id,
  MAX(CASE WHEN p.key = 'observation_cadence' THEN p.value_text END) AS observation_cadence,
  MAX(CASE WHEN p.key = 'az_sites'         THEN p.value_text END) AS az_sites
FROM kg.node n
LEFT JOIN kg.property p ON p.node_id = n.node_id
WHERE n.node_type IN ('dataset','api')
  AND n.source_fig = 'deep-datasets'
GROUP BY n.node_id, n.node_type, n.label, n.description;
