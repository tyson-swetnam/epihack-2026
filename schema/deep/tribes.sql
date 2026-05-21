-- ============================================================================
-- EpiHack Arizona 2026 -- DEEP RESEARCH: Arizona Tribal Nations
--
-- 22 federally recognized tribal nations whose lands lie wholly or partly in
-- Arizona, plus their primary tribal health / HHS entities and (where
-- documented) natural-resource / wildlife / vector-control entities. Linkage
-- edges connect each tribe to ITCA-TEC (Phoenix and Tucson IHS Areas) and, for
-- the Navajo Nation, to the Navajo Epidemiology Center.
--
-- Source convention: source_fig = 'deep-tribes'.
-- Edge ID range:    11000-11999  (this agent's reserved range).
--
-- DATA SOVEREIGNTY CAVEATS
-- ------------------------
-- 1. Tribal Nations are sovereign governments. Health and natural-resource
--    data they collect (or that IHS collects on their behalf) is governed by
--    tribal law, tribal IRBs, and data-sharing agreements -- it is NOT public
--    domain even when aggregate counts appear in federal reports.
-- 2. The CDC/IHS Tribal Epidemiology Centers (TECs) are Public Health
--    Authorities under HIPAA but still bound by individual tribal data-use
--    agreements; ITCA-TEC works under MOUs with each of its 21 member tribes.
-- 3. Where a tribe operates IHS-run vs. tribally-run ("638") health programs,
--    data ownership differs. Direct Service tribes (e.g., Kaibab Paiute,
--    Havasupai, San Juan Southern Paiute) rely on IHS facilities and the
--    tribe itself may publish little; absence of a tribe-branded URL here
--    does NOT mean absence of a health program.
-- 4. Enrollment counts are approximate, point-in-time, and self-reported by
--    each Nation. Reservation-resident population (US Census) is a different
--    number and is not used here.
-- 5. URLs were verified at the time of compilation (May 2026). Tribal
--    web infrastructure changes frequently; canonical URLs only.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Tribal-nation nodes (22)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('tribe.ak_chin',
     'tribal_nation', 'Ak-Chin Indian Community',
     'Federally recognized O''odham/Piipaash community on a 22,000-acre reservation in Pinal County, ~35 miles south of Phoenix.',
     'deep-tribes'),
  ('tribe.cocopah',
     'tribal_nation', 'Cocopah Indian Tribe',
     'Yuman-speaking ''Xawitt Kwñchawaay'' nation on three non-contiguous reservations in Yuma County near the lower Colorado River.',
     'deep-tribes'),
  ('tribe.crit',
     'tribal_nation', 'Colorado River Indian Tribes',
     'Confederation of Mohave, Chemehuevi, Hopi, and Navajo members on the Colorado River Indian Reservation spanning La Paz County, AZ and San Bernardino/Riverside Counties, CA.',
     'deep-tribes'),
  ('tribe.fort_mcdowell',
     'tribal_nation', 'Fort McDowell Yavapai Nation',
     'Yavapai nation on a 40-square-mile reservation in Maricopa County northeast of Phoenix along the Verde River.',
     'deep-tribes'),
  ('tribe.fort_mojave',
     'tribal_nation', 'Fort Mojave Indian Tribe',
     'Pipa Aha Macav (Mojave) nation on lands spanning Mohave County, AZ; San Bernardino County, CA; and Clark County, NV.',
     'deep-tribes'),
  ('tribe.quechan',
     'tribal_nation', 'Fort Yuma Quechan Indian Tribe',
     'Kwatsáan nation on the Fort Yuma Indian Reservation along the lower Colorado River; lands in Imperial County, CA and Yuma County, AZ.',
     'deep-tribes'),
  ('tribe.gila_river',
     'tribal_nation', 'Gila River Indian Community',
     'Akimel O''odham and Pee-Posh nation on 372,000 acres south of Phoenix in Pinal and Maricopa Counties.',
     'deep-tribes'),
  ('tribe.havasupai',
     'tribal_nation', 'Havasupai Tribe',
     'Havsuw'' Baaja ("People of the Blue-Green Waters") nation at the base of the Grand Canyon in Coconino County; village of Supai.',
     'deep-tribes'),
  ('tribe.hopi',
     'tribal_nation', 'Hopi Tribe',
     'Hopisinom nation on a 1.5M-acre reservation of twelve villages on three mesas in Navajo and Coconino Counties.',
     'deep-tribes'),
  ('tribe.hualapai',
     'tribal_nation', 'Hualapai Tribe',
     '"People of the Tall Pines" nation on ~1M acres along 108 miles of the Grand Canyon and Colorado River in Mohave, Coconino, and Yavapai Counties.',
     'deep-tribes'),
  ('tribe.kaibab_paiute',
     'tribal_nation', 'Kaibab Band of Paiute Indians',
     'Southern Paiute band on a 121,000-acre reservation in Mohave and Coconino Counties surrounding Pipe Spring National Monument.',
     'deep-tribes'),
  ('tribe.navajo',
     'tribal_nation', 'Navajo Nation',
     'Diné nation on a ~27,000-square-mile reservation spanning Apache, Navajo, and Coconino Counties, AZ; San Juan County, UT; and McKinley/San Juan Counties, NM. Largest reservation by area and enrolled membership in the US.',
     'deep-tribes'),
  ('tribe.pascua_yaqui',
     'tribal_nation', 'Pascua Yaqui Tribe',
     'Yoeme nation; reservation in Pima County southwest of Tucson, with member communities in Maricopa and Pinal Counties.',
     'deep-tribes'),
  ('tribe.zuni',
     'tribal_nation', 'Pueblo of Zuni',
     'A:shiwi Pueblo headquartered at Zuni, NM (McKinley County); the federally recognized Zuni Heaven (Kolhu/wala:wa) parcel lies in Apache County, AZ.',
     'deep-tribes'),
  ('tribe.srpmic',
     'tribal_nation', 'Salt River Pima-Maricopa Indian Community',
     'Akimel O''odham (Pima) and Xalychidom Piipaash (Maricopa) community on 52,600 acres bordering Scottsdale, Tempe, Mesa, and Fountain Hills in Maricopa County.',
     'deep-tribes'),
  ('tribe.san_carlos_apache',
     'tribal_nation', 'San Carlos Apache Tribe',
     'Nnee (Apache) nation on 1.8M acres spanning Gila, Graham, and Pinal Counties in east-central Arizona.',
     'deep-tribes'),
  ('tribe.san_juan_southern_paiute',
     'tribal_nation', 'San Juan Southern Paiute Tribe',
     'Southern Paiute nation headquartered in Tuba City, AZ (Coconino County); members reside on lands within the Navajo Nation in Arizona and Utah.',
     'deep-tribes'),
  ('tribe.tohono_oodham',
     'tribal_nation', 'Tohono O''odham Nation',
     'O''odham nation on the 2.8M-acre Tohono O''odham Nation reservation across Pima, Pinal, and Maricopa Counties; second-largest reservation by area in the US.',
     'deep-tribes'),
  ('tribe.tonto_apache',
     'tribal_nation', 'Tonto Apache Tribe',
     'Tonto Apache nation on an 85-acre reservation adjacent to Payson in Gila County -- the smallest land base of any AZ federally recognized tribe.',
     'deep-tribes'),
  ('tribe.white_mountain_apache',
     'tribal_nation', 'White Mountain Apache Tribe',
     'Ndee (Apache) nation on the 1.67M-acre Fort Apache Reservation in Navajo, Apache, and Gila Counties; home to nine major communities and Apache trout endemic habitat.',
     'deep-tribes'),
  ('tribe.yavapai_apache',
     'tribal_nation', 'Yavapai-Apache Nation',
     'Confederation of Yavapai (Wipuhk''a''bah) and Tonto Apache (Dilzhe''e) on five communities in the Verde Valley (Yavapai County): Tunlii, Middle Verde, Rimrock, Camp Verde, Clarkdale.',
     'deep-tribes'),
  ('tribe.yavapai_prescott',
     'tribal_nation', 'Yavapai-Prescott Indian Tribe',
     'Wiikvteepaya (Yavapai) nation on a ~1,413-acre reservation in central Yavapai County adjacent to the City of Prescott.',
     'deep-tribes')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. Tribal-government top-level URLs (verified May 2026)
-- ---------------------------------------------------------------------------
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('tribe.ak_chin',                  'url', 'https://ak-chin.nsn.us/'),
  ('tribe.cocopah',                  'url', 'https://www.cocopah.com/'),
  ('tribe.crit',                     'url', 'https://crit-nsn.gov/'),
  ('tribe.fort_mcdowell',            'url', 'https://fmyn.org/'),
  ('tribe.fort_mojave',              'url', 'https://www.fortmojaveindiantribe.com/'),
  ('tribe.quechan',                  'url', 'https://quechantribe.com/'),
  ('tribe.gila_river',               'url', 'https://www.gilariver.org/'),
  ('tribe.havasupai',                'url', 'https://theofficialhavasupaitribe.com/'),
  ('tribe.hopi',                     'url', 'https://www.hopi-nsn.gov/'),
  ('tribe.hualapai',                 'url', 'https://hualapai-nsn.gov/'),
  ('tribe.kaibab_paiute',            'url', 'https://www.kaibabpaiute-nsn.gov/'),
  ('tribe.navajo',                   'url', 'https://www.navajo-nsn.gov/'),
  ('tribe.pascua_yaqui',             'url', 'https://www.pascuayaqui-nsn.gov/'),
  ('tribe.zuni',                     'url', 'https://www.ashiwi.org/'),
  ('tribe.srpmic',                   'url', 'https://srpmic-nsn.gov/'),
  ('tribe.san_carlos_apache',        'url', 'https://www.scat-nsn.gov/'),
  ('tribe.san_juan_southern_paiute', 'url', 'https://www.sanjuanpaiute-nsn.gov/'),
  ('tribe.tohono_oodham',            'url', 'https://www.tonation-nsn.gov/'),
  ('tribe.tonto_apache',             'url', 'https://tontoapache.org/'),
  ('tribe.white_mountain_apache',    'url', 'http://www.wmat.us/'),
  ('tribe.yavapai_apache',           'url', 'https://yavapai-apache.org/'),
  ('tribe.yavapai_prescott',         'url', 'https://www.ypit.com/')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. Primary Arizona county/counties of the reservation
-- ---------------------------------------------------------------------------
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('tribe.ak_chin',                  'az_county', 'Pinal'),
  ('tribe.cocopah',                  'az_county', 'Yuma'),
  ('tribe.crit',                     'az_county', 'La Paz'),
  ('tribe.fort_mcdowell',            'az_county', 'Maricopa'),
  ('tribe.fort_mojave',              'az_county', 'Mohave'),
  ('tribe.quechan',                  'az_county', 'Yuma'),
  ('tribe.gila_river',               'az_county', 'Pinal, Maricopa'),
  ('tribe.havasupai',                'az_county', 'Coconino'),
  ('tribe.hopi',                     'az_county', 'Navajo, Coconino'),
  ('tribe.hualapai',                 'az_county', 'Mohave, Coconino, Yavapai'),
  ('tribe.kaibab_paiute',            'az_county', 'Mohave, Coconino'),
  ('tribe.navajo',                   'az_county', 'Apache, Navajo, Coconino'),
  ('tribe.pascua_yaqui',             'az_county', 'Pima'),
  ('tribe.zuni',                     'az_county', 'Apache'),
  ('tribe.srpmic',                   'az_county', 'Maricopa'),
  ('tribe.san_carlos_apache',        'az_county', 'Gila, Graham, Pinal'),
  ('tribe.san_juan_southern_paiute', 'az_county', 'Coconino'),
  ('tribe.tohono_oodham',            'az_county', 'Pima, Pinal, Maricopa'),
  ('tribe.tonto_apache',             'az_county', 'Gila'),
  ('tribe.white_mountain_apache',    'az_county', 'Navajo, Apache, Gila'),
  ('tribe.yavapai_apache',           'az_county', 'Yavapai'),
  ('tribe.yavapai_prescott',         'az_county', 'Yavapai')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. Approximate enrolled membership (publicly known, point-in-time)
--    Numbers are tribal/Wikipedia/Navajo Times/ITCA-cited approximations.
-- ---------------------------------------------------------------------------
INSERT INTO kg.property (node_id, key, value_num) VALUES
  ('tribe.ak_chin',                  'enrolled_membership_approx',   1100),
  ('tribe.cocopah',                  'enrolled_membership_approx',   1000),
  ('tribe.crit',                     'enrolled_membership_approx',   4277),
  ('tribe.fort_mcdowell',            'enrolled_membership_approx',    950),
  ('tribe.fort_mojave',              'enrolled_membership_approx',   1200),
  ('tribe.quechan',                  'enrolled_membership_approx',   3500),
  ('tribe.gila_river',               'enrolled_membership_approx',  24000),
  ('tribe.havasupai',                'enrolled_membership_approx',    770),
  ('tribe.hopi',                     'enrolled_membership_approx',  14000),
  ('tribe.hualapai',                 'enrolled_membership_approx',   2300),
  ('tribe.kaibab_paiute',            'enrolled_membership_approx',    250),
  ('tribe.navajo',                   'enrolled_membership_approx', 399494),
  ('tribe.pascua_yaqui',             'enrolled_membership_approx',  22000),
  ('tribe.zuni',                     'enrolled_membership_approx',  11000),
  ('tribe.srpmic',                   'enrolled_membership_approx',  11000),
  ('tribe.san_carlos_apache',        'enrolled_membership_approx',  15393),
  ('tribe.san_juan_southern_paiute', 'enrolled_membership_approx',    260),
  ('tribe.tohono_oodham',            'enrolled_membership_approx',  34000),
  ('tribe.tonto_apache',             'enrolled_membership_approx',    140),
  ('tribe.white_mountain_apache',    'enrolled_membership_approx',  15000),
  ('tribe.yavapai_apache',           'enrolled_membership_approx',   2500),
  ('tribe.yavapai_prescott',         'enrolled_membership_approx',    160)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 5. Tribal health / HHS entities (where verified)
--    NOTE: resource.tohono_oodham_hhs is already defined in wildlife_vectors.sql
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('resource.ak_chin_hhs',
     'resource_org', 'Ak-Chin Indian Community Health & Human Services',
     'Tribal HHS coordinating community health, behavioral health, elder services for Ak-Chin members; partners with IHS Ak-Chin Clinic.',
     'deep-tribes'),
  ('resource.cocopah_hhs',
     'resource_org', 'Cocopah Tribal Health Maintenance Program',
     'Tribal health program providing health/nutrition education, wellness checks, patient advocacy, and CHR services to Cocopah elders and members.',
     'deep-tribes'),
  ('resource.crit_dhss',
     'resource_org', 'CRIT Department of Health and Social Services',
     'Tribal DHSS for the Colorado River Indian Tribes; behavioral health, CHR program, food distribution, and social services in Parker, AZ.',
     'deep-tribes'),
  ('resource.fort_mcdowell_hhs',
     'resource_org', 'Fort McDowell Yavapai Nation Health Department',
     'Tribal primary care and community health services for the Fort McDowell Yavapai Nation.',
     'deep-tribes'),
  ('resource.fort_mojave_hhs',
     'resource_org', 'Fort Mojave Indian Tribe Health Department',
     'Operates Fort Mojave Indian Health Center (FMIHC) and the Fort Mojave Wellness Center; outpatient direct medical and public-health services.',
     'deep-tribes'),
  ('resource.quechan_hhs',
     'resource_org', 'Quechan Tribal Health Department',
     'Includes Fort Yuma Health Care Center, Community Health Representative (CHR) Program, Elder/Family Services, and Wellness Center.',
     'deep-tribes'),
  ('resource.gila_river_thd',
     'resource_org', 'Gila River Indian Community Tribal Health Department',
     'GRIC THD: community health education, vet services, disease surveillance, nutrition program; partners with Gila River Health Care (HRC-operated 638 system).',
     'deep-tribes'),
  ('resource.hopi_hhs',
     'resource_org', 'Hopi Tribe Department of Health & Human Services',
     'Hopi DHHS provides community health, behavioral health, and public-health regulation across the Hopi reservation; partners with Hopi Health Care Center (IHS).',
     'deep-tribes'),
  ('resource.hualapai_hhs',
     'resource_org', 'Hualapai Health Department',
     'Tribal health department in Peach Springs offering primary care, behavioral health, WIC, CHR, and public-health services.',
     'deep-tribes'),
  ('resource.navajo_doh',
     'resource_org', 'Navajo Department of Health (NDOH)',
     'Tribal health authority created 1977; serves ~400,000 Diné through 14 programs across AZ, NM, UT; parent of Navajo Epidemiology Center.',
     'deep-tribes'),
  ('resource.pascua_yaqui_hsd',
     'resource_org', 'Pascua Yaqui Health Services Division',
     'Tribal HSD managing >$30M in federal/state/tribal/private funds; pharmacy, dental, dialysis, HIV/AIDS prevention, Centered Spirit behavioral health, wellness center.',
     'deep-tribes'),
  ('resource.srpmic_hhs',
     'resource_org', 'SRPMIC Health & Human Services (River People Health Center)',
     'Tribal HHS operating River People Health Center and SRPMIC Public Health Program (WIC, environmental health, public-health nursing, diabetes prevention, injury prevention).',
     'deep-tribes'),
  ('resource.san_carlos_dhhs',
     'resource_org', 'San Carlos Apache Department of Health & Human Services',
     'Tribal DHHS oversees 13 tribal health programs; San Carlos Apache Healthcare Corporation operates the hospital and emergency department.',
     'deep-tribes'),
  ('resource.white_mountain_hhs',
     'resource_org', 'White Mountain Apache Tribe Health & Behavioral Health',
     'Operates Apache Behavioral Health Services (ABHS); partners with IHS Whiteriver Service Unit; CDC-published RSV and pneumococcal surveillance with JHU CAIH.',
     'deep-tribes'),
  ('resource.yavapai_apache_hsd',
     'resource_org', 'Yavapai-Apache Nation Medical Center',
     'Tribal medical center in Camp Verde: primary care, behavioral health, dental, vision, optometry, nutrition, tobacco cessation telemedicine.',
     'deep-tribes'),
  ('resource.tonto_apache_clinic',
     'resource_org', 'Tonto Apache Healthcare Clinic',
     'Tribally operated clinic opened 2021 on the Tonto Apache Reservation in Payson; community-focused primary care open to tribal members and the public.',
     'deep-tribes')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.ak_chin_hhs',           'jurisdiction', 'tribal'),
  ('resource.cocopah_hhs',           'jurisdiction', 'tribal'),
  ('resource.crit_dhss',             'jurisdiction', 'tribal'),
  ('resource.fort_mcdowell_hhs',     'jurisdiction', 'tribal'),
  ('resource.fort_mojave_hhs',       'jurisdiction', 'tribal'),
  ('resource.quechan_hhs',           'jurisdiction', 'tribal'),
  ('resource.gila_river_thd',        'jurisdiction', 'tribal'),
  ('resource.hopi_hhs',              'jurisdiction', 'tribal'),
  ('resource.hualapai_hhs',          'jurisdiction', 'tribal'),
  ('resource.navajo_doh',            'jurisdiction', 'tribal'),
  ('resource.pascua_yaqui_hsd',      'jurisdiction', 'tribal'),
  ('resource.srpmic_hhs',            'jurisdiction', 'tribal'),
  ('resource.san_carlos_dhhs',       'jurisdiction', 'tribal'),
  ('resource.white_mountain_hhs',    'jurisdiction', 'tribal'),
  ('resource.yavapai_apache_hsd',    'jurisdiction', 'tribal'),
  ('resource.tonto_apache_clinic',   'jurisdiction', 'tribal')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.ak_chin_hhs',           'url', 'https://ak-chin.nsn.us/departments/'),
  ('resource.cocopah_hhs',           'url', 'https://www.cocopah.com/departments.html'),
  ('resource.crit_dhss',             'url', 'https://critdhss.org/'),
  ('resource.fort_mcdowell_hhs',     'url', 'https://fmyn.org/'),
  ('resource.fort_mojave_hhs',       'url', 'https://mojaveindiantribe.com/health-department/'),
  ('resource.quechan_hhs',           'url', 'https://quechantribe.com/departments-health.html'),
  ('resource.gila_river_thd',        'url', 'https://www.gricthd.org/'),
  ('resource.hopi_hhs',              'url', 'https://www.hopi-nsn.gov/tribal-services/department-of-community-health-services/'),
  ('resource.hualapai_hhs',          'url', 'https://hualapai-nsn.gov/services/hualapai-health-department/'),
  ('resource.navajo_doh',            'url', 'https://ndoh.navajo-nsn.gov/'),
  ('resource.pascua_yaqui_hsd',      'url', 'https://www.pascuayaqui-nsn.gov/health-services/'),
  ('resource.srpmic_hhs',            'url', 'https://srpmic-nsn.gov/community/health-center/'),
  ('resource.san_carlos_dhhs',       'url', 'https://www.scatdhhs.gov/'),
  ('resource.white_mountain_hhs',    'url', 'https://www.wmabhs.org/'),
  ('resource.yavapai_apache_hsd',    'url', 'https://yavapai-apache.org/directory/medical-center/'),
  ('resource.tonto_apache_clinic',   'url', 'https://tontoapache.org/')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6. Tribal natural-resource / wildlife / vector-control entities
--    (where a verifiable program exists; resource.navajo_fish_wildlife is
--    already defined in wildlife_vectors.sql)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('resource.crit_fish_game',
     'resource_org', 'CRIT Fish and Game Department',
     'Manages hunting and fishing on the Colorado River Indian Reservation; issues tribal permits and runs habitat programs along the lower Colorado.',
     'deep-tribes'),
  ('resource.hopi_dnr_wemp',
     'resource_org', 'Hopi Department of Natural Resources -- Wildlife & Ecosystems Management Program',
     'Manages deer, elk, furbearer, mountain-lion, and migratory-bird harvest plus golden-eagle and red-tailed-hawk conservation on Hopi lands.',
     'deep-tribes'),
  ('resource.hualapai_dnr',
     'resource_org', 'Hualapai Department of Natural Resources',
     'Primary authority over Hualapai natural resources; divisions for Air Quality, Agriculture, Environmental Services, Water Resources, Wildlife/Fisheries/Parks; ~1M acres.',
     'deep-tribes'),
  ('resource.gila_river_deq',
     'resource_org', 'Gila River Indian Community Department of Environmental Quality',
     'Established 1995; programs include air, pesticides, waste, water quality, and the Wildlife & Ecosystems Management Program; MAR-5 restoration trail.',
     'deep-tribes'),
  ('resource.srpmic_epnr',
     'resource_org', 'SRPMIC Environmental Protection & Natural Resources Division',
     'EPNR division of SRPMIC Community Development Dept; air, water, pesticides, waste, range, brownfields; manages constructed treatment wetlands as wildlife habitat.',
     'deep-tribes'),
  ('resource.tohono_oodham_nr',
     'resource_org', 'Tohono O''odham Nation Department of Natural Resources -- Wildlife and Vegetation',
     'Wildlife and Vegetation Management Program plus Soil/Water Conservation, Range, Agriculture Extension, and Animal Control across 2.8M acres.',
     'deep-tribes'),
  ('resource.san_carlos_recwild',
     'resource_org', 'San Carlos Apache Recreation & Wildlife Department',
     'Manages big-game (elk, Coues deer, antelope) lottery, javelina, game birds, and the Fish & Wildlife Conservation Stamp program on 1.8M acres.',
     'deep-tribes'),
  ('resource.white_mountain_gf',
     'resource_org', 'White Mountain Apache Tribe Game and Fish Department',
     'Manages trophy elk, Apache trout (endemic), 16 reservation lakes, hunting/fishing permits, and wildlife disease surveillance on the Fort Apache Reservation.',
     'deep-tribes')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.crit_fish_game',        'jurisdiction', 'tribal'),
  ('resource.hopi_dnr_wemp',         'jurisdiction', 'tribal'),
  ('resource.hualapai_dnr',          'jurisdiction', 'tribal'),
  ('resource.gila_river_deq',        'jurisdiction', 'tribal'),
  ('resource.srpmic_epnr',           'jurisdiction', 'tribal'),
  ('resource.tohono_oodham_nr',      'jurisdiction', 'tribal'),
  ('resource.san_carlos_recwild',    'jurisdiction', 'tribal'),
  ('resource.white_mountain_gf',     'jurisdiction', 'tribal')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.crit_fish_game',        'url', 'https://crit-nsn.gov/crit_contents/departments/'),
  ('resource.hopi_dnr_wemp',         'url', 'https://www.hopi-nsn.gov/tribal-services/department-natural-resources-2/wildlife-ecosystems/'),
  ('resource.hualapai_dnr',          'url', 'https://hualapai.us/'),
  ('resource.gila_river_deq',        'url', 'https://www.gricdeq.org/wildlife-program'),
  ('resource.srpmic_epnr',           'url', 'https://srpmic-nsn.gov/government/epnr/'),
  ('resource.tohono_oodham_nr',      'url', 'https://www.tonation-nsn.gov/natural-resources/wildlife-and-vegetation/'),
  ('resource.san_carlos_recwild',    'url', 'https://www.sancarlosrecreationwildlife.com/'),
  ('resource.white_mountain_gf',     'url', 'https://wmatgameandfish.com/')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 7. Edges -- HHS operatedBy tribe
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (11001, 'resource.ak_chin_hhs',         'operatedBy', 'tribe.ak_chin',               'deep-tribes'),
  (11002, 'resource.cocopah_hhs',         'operatedBy', 'tribe.cocopah',               'deep-tribes'),
  (11003, 'resource.crit_dhss',           'operatedBy', 'tribe.crit',                  'deep-tribes'),
  (11004, 'resource.fort_mcdowell_hhs',   'operatedBy', 'tribe.fort_mcdowell',         'deep-tribes'),
  (11005, 'resource.fort_mojave_hhs',     'operatedBy', 'tribe.fort_mojave',           'deep-tribes'),
  (11006, 'resource.quechan_hhs',         'operatedBy', 'tribe.quechan',               'deep-tribes'),
  (11007, 'resource.gila_river_thd',      'operatedBy', 'tribe.gila_river',            'deep-tribes'),
  (11008, 'resource.hopi_hhs',            'operatedBy', 'tribe.hopi',                  'deep-tribes'),
  (11009, 'resource.hualapai_hhs',        'operatedBy', 'tribe.hualapai',              'deep-tribes'),
  (11010, 'resource.navajo_doh',          'operatedBy', 'tribe.navajo',                'deep-tribes'),
  (11011, 'resource.pascua_yaqui_hsd',    'operatedBy', 'tribe.pascua_yaqui',          'deep-tribes'),
  (11012, 'resource.srpmic_hhs',          'operatedBy', 'tribe.srpmic',                'deep-tribes'),
  (11013, 'resource.san_carlos_dhhs',     'operatedBy', 'tribe.san_carlos_apache',     'deep-tribes'),
  (11014, 'resource.white_mountain_hhs',  'operatedBy', 'tribe.white_mountain_apache', 'deep-tribes'),
  (11015, 'resource.yavapai_apache_hsd',  'operatedBy', 'tribe.yavapai_apache',        'deep-tribes'),
  (11016, 'resource.tonto_apache_clinic', 'operatedBy', 'tribe.tonto_apache',          'deep-tribes'),
  (11017, 'resource.tohono_oodham_hhs',   'operatedBy', 'tribe.tohono_oodham',         'deep-tribes')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 8. Edges -- Wildlife / NR entity operatedBy tribe
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (11050, 'resource.crit_fish_game',      'operatedBy', 'tribe.crit',                  'deep-tribes'),
  (11051, 'resource.hopi_dnr_wemp',       'operatedBy', 'tribe.hopi',                  'deep-tribes'),
  (11052, 'resource.hualapai_dnr',        'operatedBy', 'tribe.hualapai',              'deep-tribes'),
  (11053, 'resource.gila_river_deq',      'operatedBy', 'tribe.gila_river',            'deep-tribes'),
  (11054, 'resource.srpmic_epnr',         'operatedBy', 'tribe.srpmic',                'deep-tribes'),
  (11055, 'resource.tohono_oodham_nr',    'operatedBy', 'tribe.tohono_oodham',         'deep-tribes'),
  (11056, 'resource.san_carlos_recwild',  'operatedBy', 'tribe.san_carlos_apache',     'deep-tribes'),
  (11057, 'resource.white_mountain_gf',   'operatedBy', 'tribe.white_mountain_apache', 'deep-tribes'),
  (11058, 'resource.navajo_fish_wildlife','operatedBy', 'tribe.navajo',                'deep-tribes')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 9. Edges -- ITCA-TEC partnership (all 21 ITCA member tribes in Phoenix and
--    Tucson IHS Areas). Per ITCA: all 22 AZ federally recognized tribes are
--    served, except San Juan Southern Paiute and Pueblo of Zuni (Zuni's
--    primary jurisdiction is in NM, served by Albuquerque IHS Area; the San
--    Juan Southern Paiute partnership is informal and historically served via
--    the Navajo system). We include the 20 ITCA member tribes here. Adjust
--    if local MOU updates change.
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (11100, 'tribe.ak_chin',                  'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11101, 'tribe.cocopah',                  'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11102, 'tribe.crit',                     'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11103, 'tribe.fort_mcdowell',            'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11104, 'tribe.fort_mojave',              'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11105, 'tribe.quechan',                  'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11106, 'tribe.gila_river',               'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11107, 'tribe.havasupai',                'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11108, 'tribe.hopi',                     'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11109, 'tribe.hualapai',                 'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11110, 'tribe.kaibab_paiute',            'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11111, 'tribe.pascua_yaqui',             'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11112, 'tribe.srpmic',                   'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11113, 'tribe.san_carlos_apache',        'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11114, 'tribe.tohono_oodham',            'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11115, 'tribe.tonto_apache',             'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11116, 'tribe.white_mountain_apache',    'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11117, 'tribe.yavapai_apache',           'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11118, 'tribe.yavapai_prescott',         'partneredWith', 'resource.itca_tec', 'deep-tribes'),
  (11119, 'tribe.san_juan_southern_paiute', 'partneredWith', 'resource.itca_tec', 'deep-tribes')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 10. Edges -- Navajo Epidemiology Center partnership (Navajo Nation only)
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (11200, 'tribe.navajo', 'partneredWith', 'resource.navajo_ec', 'deep-tribes')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 11. Edges -- tribal HHS informs Q4 of heat and wildlife-vectors groups
--     (Q4 in both groups concerns vulnerable populations / participatory
--     surveillance, both of which tribal HHS programs materially inform.)
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (11300, 'resource.ak_chin_hhs',         'informs', 'heat.q4', 'deep-tribes'),
  (11301, 'resource.ak_chin_hhs',         'informs', 'wv.q4',   'deep-tribes'),
  (11302, 'resource.cocopah_hhs',         'informs', 'heat.q4', 'deep-tribes'),
  (11303, 'resource.cocopah_hhs',         'informs', 'wv.q4',   'deep-tribes'),
  (11304, 'resource.crit_dhss',           'informs', 'heat.q4', 'deep-tribes'),
  (11305, 'resource.crit_dhss',           'informs', 'wv.q4',   'deep-tribes'),
  (11306, 'resource.fort_mcdowell_hhs',   'informs', 'heat.q4', 'deep-tribes'),
  (11307, 'resource.fort_mcdowell_hhs',   'informs', 'wv.q4',   'deep-tribes'),
  (11308, 'resource.fort_mojave_hhs',     'informs', 'heat.q4', 'deep-tribes'),
  (11309, 'resource.fort_mojave_hhs',     'informs', 'wv.q4',   'deep-tribes'),
  (11310, 'resource.quechan_hhs',         'informs', 'heat.q4', 'deep-tribes'),
  (11311, 'resource.quechan_hhs',         'informs', 'wv.q4',   'deep-tribes'),
  (11312, 'resource.gila_river_thd',      'informs', 'heat.q4', 'deep-tribes'),
  (11313, 'resource.gila_river_thd',      'informs', 'wv.q4',   'deep-tribes'),
  (11314, 'resource.hopi_hhs',            'informs', 'heat.q4', 'deep-tribes'),
  (11315, 'resource.hopi_hhs',            'informs', 'wv.q4',   'deep-tribes'),
  (11316, 'resource.hualapai_hhs',        'informs', 'heat.q4', 'deep-tribes'),
  (11317, 'resource.hualapai_hhs',        'informs', 'wv.q4',   'deep-tribes'),
  (11318, 'resource.navajo_doh',          'informs', 'heat.q4', 'deep-tribes'),
  (11319, 'resource.navajo_doh',          'informs', 'wv.q4',   'deep-tribes'),
  (11320, 'resource.pascua_yaqui_hsd',    'informs', 'heat.q4', 'deep-tribes'),
  (11321, 'resource.pascua_yaqui_hsd',    'informs', 'wv.q4',   'deep-tribes'),
  (11322, 'resource.srpmic_hhs',          'informs', 'heat.q4', 'deep-tribes'),
  (11323, 'resource.srpmic_hhs',          'informs', 'wv.q4',   'deep-tribes'),
  (11324, 'resource.san_carlos_dhhs',     'informs', 'heat.q4', 'deep-tribes'),
  (11325, 'resource.san_carlos_dhhs',     'informs', 'wv.q4',   'deep-tribes'),
  (11326, 'resource.white_mountain_hhs',  'informs', 'heat.q4', 'deep-tribes'),
  (11327, 'resource.white_mountain_hhs',  'informs', 'wv.q4',   'deep-tribes'),
  (11328, 'resource.yavapai_apache_hsd',  'informs', 'heat.q4', 'deep-tribes'),
  (11329, 'resource.yavapai_apache_hsd',  'informs', 'wv.q4',   'deep-tribes'),
  (11330, 'resource.tonto_apache_clinic', 'informs', 'heat.q4', 'deep-tribes'),
  (11331, 'resource.tonto_apache_clinic', 'informs', 'wv.q4',   'deep-tribes'),
  (11332, 'resource.tohono_oodham_hhs',   'informs', 'heat.q4', 'deep-tribes'),
  (11333, 'resource.tohono_oodham_hhs',   'informs', 'wv.q4',   'deep-tribes')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 12. Edges -- tribal NR/wildlife entity informs wv.q4
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (11400, 'resource.crit_fish_game',     'informs', 'wv.q4', 'deep-tribes'),
  (11401, 'resource.hopi_dnr_wemp',      'informs', 'wv.q4', 'deep-tribes'),
  (11402, 'resource.hualapai_dnr',       'informs', 'wv.q4', 'deep-tribes'),
  (11403, 'resource.gila_river_deq',     'informs', 'wv.q4', 'deep-tribes'),
  (11404, 'resource.srpmic_epnr',        'informs', 'wv.q4', 'deep-tribes'),
  (11405, 'resource.tohono_oodham_nr',   'informs', 'wv.q4', 'deep-tribes'),
  (11406, 'resource.san_carlos_recwild', 'informs', 'wv.q4', 'deep-tribes'),
  (11407, 'resource.white_mountain_gf',  'informs', 'wv.q4', 'deep-tribes')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- END deep-tribes
-- ============================================================================
