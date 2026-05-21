// EpiHack Arizona 2026 — geospatial data for the MapLibre map.
//
// Coordinates are approximate (county-seat or reservation-centroid level);
// for production use, these should be replaced with authoritative TIGER/Line
// shapefiles for counties, BIA shapefiles for tribal lands, and verified
// addresses for agency HQs. Each feature carries `properties.kg_node_id`
// pointing back to the corresponding node in the DuckLake knowledge graph.

window.EPIHACK_MAP_DATA = {

  // -------------------------------------------------------------------
  // 15 Arizona counties — point per county seat
  // -------------------------------------------------------------------
  counties: {
    type: "FeatureCollection",
    features: [
      {type:"Feature", properties:{name:"Apache",      seat:"St. Johns", vector_control:false, kg_node_id:"county.apache",      population_approx:66000,   page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-109.36, 34.50]}},
      {type:"Feature", properties:{name:"Cochise",     seat:"Bisbee",    vector_control:true,  kg_node_id:"county.cochise",     population_approx:125000,  page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-109.93, 31.45]}},
      {type:"Feature", properties:{name:"Coconino",    seat:"Flagstaff", vector_control:true,  kg_node_id:"county.coconino",    population_approx:145000,  page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-111.65, 35.20]}},
      {type:"Feature", properties:{name:"Gila",        seat:"Globe",     vector_control:false, kg_node_id:"county.gila",        population_approx:54000,   page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-110.79, 33.39]}},
      {type:"Feature", properties:{name:"Graham",      seat:"Safford",   vector_control:false, kg_node_id:"county.graham",      population_approx:39000,   page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-109.71, 32.83]}},
      {type:"Feature", properties:{name:"Greenlee",    seat:"Clifton",   vector_control:false, kg_node_id:"county.greenlee",    population_approx:9500,    page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-109.30, 33.05]}},
      {type:"Feature", properties:{name:"La Paz",      seat:"Parker",    vector_control:false, kg_node_id:"county.la_paz",      population_approx:16500,   page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-114.29, 34.15]}},
      {type:"Feature", properties:{name:"Maricopa",    seat:"Phoenix",   vector_control:true,  kg_node_id:"county.maricopa",    population_approx:4500000, page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-112.07, 33.45]}},
      {type:"Feature", properties:{name:"Mohave",      seat:"Kingman",   vector_control:true,  kg_node_id:"county.mohave",      population_approx:215000,  page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-114.05, 35.19]}},
      {type:"Feature", properties:{name:"Navajo",      seat:"Holbrook",  vector_control:false, kg_node_id:"county.navajo",      population_approx:107000,  page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-110.16, 34.90]}},
      {type:"Feature", properties:{name:"Pima",        seat:"Tucson",    vector_control:true,  kg_node_id:"county.pima",        population_approx:1050000, page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-110.93, 32.22]}},
      {type:"Feature", properties:{name:"Pinal",       seat:"Florence",  vector_control:true,  kg_node_id:"county.pinal",       population_approx:475000,  page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-111.39, 33.03]}},
      {type:"Feature", properties:{name:"Santa Cruz",  seat:"Nogales",   vector_control:false, kg_node_id:"county.santa_cruz",  population_approx:48000,   page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-110.94, 31.34]}},
      {type:"Feature", properties:{name:"Yavapai",     seat:"Prescott",  vector_control:true,  kg_node_id:"county.yavapai",     population_approx:248000,  page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-112.47, 34.54]}},
      {type:"Feature", properties:{name:"Yuma",        seat:"Yuma",      vector_control:true,  kg_node_id:"county.yuma",        population_approx:208000,  page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-114.62, 32.69]}}
    ]
  },

  // -------------------------------------------------------------------
  // 22 federally recognized AZ tribal nations — approximate reservation
  // centroids. Polygons would be more correct but require BIA shapefiles.
  // -------------------------------------------------------------------
  tribes: {
    type: "FeatureCollection",
    features: [
      {type:"Feature", properties:{name:"Ak-Chin Indian Community",            kg_node_id:"tribe.ak_chin"},               geometry:{type:"Point", coordinates:[-112.05, 32.95]}},
      {type:"Feature", properties:{name:"Cocopah Indian Tribe",                kg_node_id:"tribe.cocopah"},               geometry:{type:"Point", coordinates:[-114.78, 32.62]}},
      {type:"Feature", properties:{name:"Colorado River Indian Tribes",        kg_node_id:"tribe.crit"},                  geometry:{type:"Point", coordinates:[-114.30, 34.05]}},
      {type:"Feature", properties:{name:"Fort McDowell Yavapai Nation",        kg_node_id:"tribe.fort_mcdowell"},         geometry:{type:"Point", coordinates:[-111.65, 33.62]}},
      {type:"Feature", properties:{name:"Fort Mojave Indian Tribe",            kg_node_id:"tribe.fort_mojave"},           geometry:{type:"Point", coordinates:[-114.60, 35.05]}},
      {type:"Feature", properties:{name:"Fort Yuma Quechan Tribe",             kg_node_id:"tribe.quechan"},               geometry:{type:"Point", coordinates:[-114.60, 32.74]}},
      {type:"Feature", properties:{name:"Gila River Indian Community",         kg_node_id:"tribe.gila_river"},            geometry:{type:"Point", coordinates:[-111.95, 33.20]}},
      {type:"Feature", properties:{name:"Havasupai Tribe",                     kg_node_id:"tribe.havasupai"},             geometry:{type:"Point", coordinates:[-112.70, 36.25]}},
      {type:"Feature", properties:{name:"Hopi Tribe",                          kg_node_id:"tribe.hopi"},                  geometry:{type:"Point", coordinates:[-110.50, 35.95]}},
      {type:"Feature", properties:{name:"Hualapai Tribe",                      kg_node_id:"tribe.hualapai"},              geometry:{type:"Point", coordinates:[-113.50, 35.55]}},
      {type:"Feature", properties:{name:"Kaibab Band of Paiute Indians",       kg_node_id:"tribe.kaibab_paiute"},         geometry:{type:"Point", coordinates:[-112.65, 36.95]}},
      {type:"Feature", properties:{name:"Navajo Nation",                       kg_node_id:"tribe.navajo"},                geometry:{type:"Point", coordinates:[-109.80, 36.30]}},
      {type:"Feature", properties:{name:"Pascua Yaqui Tribe",                  kg_node_id:"tribe.pascua_yaqui"},          geometry:{type:"Point", coordinates:[-111.05, 32.15]}},
      {type:"Feature", properties:{name:"Pueblo of Zuni (AZ parcel)",          kg_node_id:"tribe.zuni"},                  geometry:{type:"Point", coordinates:[-109.05, 34.30]}},
      {type:"Feature", properties:{name:"Salt River Pima-Maricopa Indian Community", kg_node_id:"tribe.salt_river"},      geometry:{type:"Point", coordinates:[-111.85, 33.55]}},
      {type:"Feature", properties:{name:"San Carlos Apache Tribe",             kg_node_id:"tribe.san_carlos_apache"},     geometry:{type:"Point", coordinates:[-110.10, 33.40]}},
      {type:"Feature", properties:{name:"San Juan Southern Paiute Tribe",      kg_node_id:"tribe.san_juan_southern_paiute"}, geometry:{type:"Point", coordinates:[-111.60, 36.85]}},
      {type:"Feature", properties:{name:"Tohono O'odham Nation",               kg_node_id:"tribe.tohono_oodham"},         geometry:{type:"Point", coordinates:[-111.65, 32.10]}},
      {type:"Feature", properties:{name:"Tonto Apache Tribe",                  kg_node_id:"tribe.tonto_apache"},          geometry:{type:"Point", coordinates:[-111.34, 34.21]}},
      {type:"Feature", properties:{name:"White Mountain Apache Tribe",         kg_node_id:"tribe.white_mountain_apache"}, geometry:{type:"Point", coordinates:[-110.00, 33.85]}},
      {type:"Feature", properties:{name:"Yavapai-Apache Nation",               kg_node_id:"tribe.yavapai_apache"},        geometry:{type:"Point", coordinates:[-111.85, 34.70]}},
      {type:"Feature", properties:{name:"Yavapai-Prescott Indian Tribe",       kg_node_id:"tribe.yavapai_prescott"},      geometry:{type:"Point", coordinates:[-112.50, 34.55]}}
    ]
  },

  // -------------------------------------------------------------------
  // NEON sites in Arizona (Domain 14 Desert Southwest)
  // -------------------------------------------------------------------
  neon_sites: {
    type: "FeatureCollection",
    features: [
      {type:"Feature", properties:{name:"Santa Rita Experimental Range (SRER) — NEON core terrestrial site", kg_node_id:"program.neon_srer", kind:"core_terrestrial", domain:"D14", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-110.835, 31.910]}},
      {type:"Feature", properties:{name:"Sycamore Creek (SYCA) — NEON aquatic site",                          kg_node_id:"program.neon_syca", kind:"aquatic",          domain:"D14", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-111.508, 33.751]}}
    ]
  },

  // -------------------------------------------------------------------
  // Federal / state / county / city agency HQs
  // -------------------------------------------------------------------
  agencies: {
    type: "FeatureCollection",
    features: [
      {type:"Feature", properties:{name:"Arizona Department of Health Services (ADHS)", jurisdiction:"state",    kg_node_id:"resource.adhs",        page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-112.094, 33.448]}},
      {type:"Feature", properties:{name:"Arizona Game and Fish Department (AZGFD)",     jurisdiction:"state",    kg_node_id:"resource.azgfd",       page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-112.137, 33.610]}},
      {type:"Feature", properties:{name:"Arizona Dept. of Agriculture",                 jurisdiction:"state",    kg_node_id:"resource.az_agriculture", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-112.094, 33.450]}},
      {type:"Feature", properties:{name:"Maricopa County Vector Control (MCESD)",       jurisdiction:"county",   kg_node_id:"resource.mcdph_mcesd", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-112.092, 33.460]}},
      {type:"Feature", properties:{name:"Pima County Vector Control (PCHD)",            jurisdiction:"county",   kg_node_id:"resource.pcdh",        page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-110.969, 32.221]}},
      {type:"Feature", properties:{name:"Coconino County HHS",                          jurisdiction:"county",   kg_node_id:"resource.coconino_hhs", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-111.651, 35.198]}},
      {type:"Feature", properties:{name:"MAG Heat Relief Network HQ",                   jurisdiction:"regional", kg_node_id:"resource.mag_hrn",     page:"../heat/resources.html"},     geometry:{type:"Point", coordinates:[-112.078, 33.452]}},
      {type:"Feature", properties:{name:"City of Phoenix Office of Heat Response & Mitigation (OHRM)", jurisdiction:"city", kg_node_id:"resource.phoenix_ohrm", page:"../heat/resources.html"}, geometry:{type:"Point", coordinates:[-112.077, 33.450]}},
      {type:"Feature", properties:{name:"Inter Tribal Council of Arizona — TEC",        jurisdiction:"tribal",   kg_node_id:"resource.itca_tec",    page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-112.061, 33.456]}},
      {type:"Feature", properties:{name:"Navajo Epidemiology Center (Window Rock)",     jurisdiction:"tribal",   kg_node_id:"resource.navajo_ec",   page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-109.054, 35.681]}},
      {type:"Feature", properties:{name:"UA Mel & Enid Zuckerman College of Public Health", jurisdiction:"academic", kg_node_id:"resource.ua_mezcoph", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-110.946, 32.241]}},
      {type:"Feature", properties:{name:"UA Cooperative Extension — Great Arizona Tick Check (Walker lab, Forbes 410)", jurisdiction:"academic", kg_node_id:"resource.ua_extension_tickcheck", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-110.953, 32.234]}},
      {type:"Feature", properties:{name:"Arizona Veterinary Diagnostic Laboratory (AZVDL)", jurisdiction:"academic", kg_node_id:"resource.azvdl", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-110.953, 32.270]}},
      {type:"Feature", properties:{name:"NAU Pathogen and Microbiome Institute (PMI)", jurisdiction:"academic", kg_node_id:"resource.nau_pmi", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-111.659, 35.183]}},
      {type:"Feature", properties:{name:"TGen North (Flagstaff)",                       jurisdiction:"academic", kg_node_id:"resource.tgen",        page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-111.612, 35.198]}},
      {type:"Feature", properties:{name:"ASU Biodesign Institute (Tempe)",              jurisdiction:"academic", kg_node_id:"resource.asu_biodesign", page:"../heat/resources.html"}, geometry:{type:"Point", coordinates:[-111.931, 33.420]}},
      {type:"Feature", properties:{name:"Indian Health Service — Phoenix Area Office",  jurisdiction:"federal_tribal", kg_node_id:"resource.ihs_phoenix", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-112.080, 33.508]}},
      {type:"Feature", properties:{name:"NWS Phoenix",                                   jurisdiction:"federal",  kg_node_id:"resource.nws_phoenix", page:"../heat/resources.html"},     geometry:{type:"Point", coordinates:[-112.038, 33.428]}},
      {type:"Feature", properties:{name:"NWS Tucson",                                    jurisdiction:"federal",  kg_node_id:"resource.nws_tucson",  page:"../heat/resources.html"},     geometry:{type:"Point", coordinates:[-110.956, 32.157]}}
    ]
  },

  // -------------------------------------------------------------------
  // Federal land-manager units with documented wildlife-disease activity
  // -------------------------------------------------------------------
  federal_lands: {
    type: "FeatureCollection",
    features: [
      {type:"Feature", properties:{name:"Grand Canyon National Park (zoonotic surveillance — hantavirus, plague, WNV, rabies)", agency:"NPS", kg_node_id:"resource.nps_az", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-112.140, 36.054]}},
      {type:"Feature", properties:{name:"Saguaro National Park (rabies investigation 2023)", agency:"NPS", kg_node_id:"resource.nps_az", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-110.730, 32.250]}},
      {type:"Feature", properties:{name:"Arizona Strip District (BLM AIM/TerrADat)", agency:"BLM", kg_node_id:"resource.blm_az", page:"../wildlife/resources.html"}, geometry:{type:"Point", coordinates:[-113.500, 36.700]}}
    ]
  },

  // -------------------------------------------------------------------
  // Historical outbreak locations (from schema/deep/outbreaks.sql)
  // -------------------------------------------------------------------
  outbreaks: {
    type: "FeatureCollection",
    features: [
      {type:"Feature", properties:{name:"1993 Four Corners hantavirus (Sin Nombre virus discovery)", year:1993, kg_node_id:"outbreak.four_corners_hantavirus_1993", pathogen:"Sin Nombre virus"}, geometry:{type:"Point", coordinates:[-109.045, 36.999]}},
      {type:"Feature", properties:{name:"2003 AZ West Nile virus emergence", year:2003, kg_node_id:"outbreak.az_wnv_2003", pathogen:"WNV"}, geometry:{type:"Point", coordinates:[-112.07, 33.45]}},
      {type:"Feature", properties:{name:"2014 Yuma / Sonora binational dengue outbreak", year:2014, kg_node_id:"outbreak.az_dengue_yuma_sonora_2014", pathogen:"Dengue"}, geometry:{type:"Point", coordinates:[-114.62, 32.69]}},
      {type:"Feature", properties:{name:"2021 Maricopa WNV outbreak — 1,487 cases / 101 deaths", year:2021, kg_node_id:"outbreak.maricopa_wnv_2021", pathogen:"WNV"}, geometry:{type:"Point", coordinates:[-112.07, 33.50]}},
      {type:"Feature", properties:{name:"2023 hantavirus spike (6 cases)", year:2023, kg_node_id:"outbreak.az_hantavirus_2023", pathogen:"Sin Nombre virus"}, geometry:{type:"Point", coordinates:[-110.50, 35.95]}},
      {type:"Feature", properties:{name:"2023 Maricopa heat-mortality season — 645 deaths", year:2023, kg_node_id:"outbreak.maricopa_heat_2023", pathogen:"Heat"}, geometry:{type:"Point", coordinates:[-112.07, 33.45]}},
      {type:"Feature", properties:{name:"2024 hantavirus spike (11 cases, 6 deaths)", year:2024, kg_node_id:"outbreak.az_hantavirus_2024", pathogen:"Sin Nombre virus"}, geometry:{type:"Point", coordinates:[-109.80, 36.30]}},
      {type:"Feature", properties:{name:"2024 AZ heat season — 602 deaths", year:2024, kg_node_id:"outbreak.az_heat_2024", pathogen:"Heat"}, geometry:{type:"Point", coordinates:[-112.07, 33.50]}},
      {type:"Feature", properties:{name:"2025 Coconino County human plague case", year:2025, kg_node_id:"outbreak.coconino_plague_2025", pathogen:"Y. pestis"}, geometry:{type:"Point", coordinates:[-111.65, 35.20]}},
      {type:"Feature", properties:{name:"RMSF outbreaks on tribal lands (2003–present, >500 cases)", year:2003, kg_node_id:"outbreak.az_rmsf_tribal_2003_present", pathogen:"R. rickettsii"}, geometry:{type:"Point", coordinates:[-110.10, 33.40]}}
    ]
  }
};
