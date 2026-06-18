# ──────────────────────────────────────────────────────────
# BENGALURU ROAD NETWORK DEFINITION
# ──────────────────────────────────────────────────────────

NODES = {
    "CBD":             {"lat": 12.9716, "lon": 77.5946, "name": "City Center (MG Road)"},
    "Mekhri_Circle":   {"lat": 13.0053, "lon": 77.5809, "name": "Mekhri Circle"},
    "Hebbal":          {"lat": 13.0356, "lon": 77.5971, "name": "Hebbal Flyover"},
    "Yeshwanthpura":   {"lat": 13.0209, "lon": 77.5503, "name": "Yeshwanthpura Circle"},
    "Jalahalli":       {"lat": 13.0375, "lon": 77.5177, "name": "Jalahalli Cross (SM Circle)"},
    "Kengeri":         {"lat": 12.9063, "lon": 77.4853, "name": "Kengeri"},
    "Vijayanagar":     {"lat": 12.9617, "lon": 77.5213, "name": "Vijayanagar"},
    "Jayanagar":       {"lat": 12.9299, "lon": 77.5826, "name": "Jayanagar"},
    "Silk_Board":      {"lat": 12.9173, "lon": 77.6234, "name": "Silk Board Junction"},
    "Koramangala":     {"lat": 12.9352, "lon": 77.6245, "name": "Koramangala"},
    "KR_Puram":        {"lat": 13.0068, "lon": 77.6938, "name": "KR Puram"},
    "Nagavara":        {"lat": 13.0462, "lon": 77.6173, "name": "Nagavara-ORR Junction"},
    "Yelahanka":       {"lat": 13.1006, "lon": 77.5949, "name": "Yelahanka Circle"},
    "Electronic_City": {"lat": 12.8459, "lon": 77.6601, "name": "Electronic City"},
    "Whitefield":      {"lat": 12.9698, "lon": 77.7500, "name": "Whitefield"},
    "Bannerghatta":    {"lat": 12.8663, "lon": 77.5965, "name": "Bannerghatta Junction"},
}

# (from, to, corridor_name, historical_event_count)
# Added in both directions inside build_graph()
CORRIDOR_EDGES = [
    # Mysore Road — highest density (743 events)
    ("Kengeri",       "Vijayanagar",    "Mysore Road",         743),
    ("Vijayanagar",   "CBD",            "Mysore Road",         743),

    # Magadi Road — parallel to Mysore Road, spillover absorber (245)
    ("Kengeri",       "Jayanagar",      "Magadi Road",         245),
    ("Jayanagar",     "CBD",            "Magadi Road",         245),

    # Bellary Road 1 — CBD to Hebbal (610)
    ("CBD",           "Mekhri_Circle",  "Bellary Road 1",      610),
    ("Mekhri_Circle", "Hebbal",         "Bellary Road 1",      610),

    # Bellary Road 2 — Hebbal northward to airport (379)
    ("Hebbal",        "Yelahanka",      "Bellary Road 2",      379),

    # Tumkur Road — NW corridor (458)
    ("Jalahalli",     "Yeshwanthpura",  "Tumkur Road",         458),
    ("Yeshwanthpura", "CBD",            "Tumkur Road",         458),

    # Hosur Road — SE corridor (298)
    ("CBD",           "Silk_Board",     "Hosur Road",          298),
    ("Silk_Board",    "Electronic_City","Hosur Road",          298),

    # Old Madras Road — East corridor (263)
    ("CBD",           "KR_Puram",       "Old Madras Road",     263),

    # ORR East 1 — Silk Board → KR Puram (244)
    ("Silk_Board",    "Koramangala",    "ORR East 1",          244),
    ("Koramangala",   "KR_Puram",       "ORR East 1",          244),

    # ORR East 2 — KR Puram → Nagavara (187)
    ("KR_Puram",      "Nagavara",       "ORR East 2",          187),

    # ORR North 1 — Nagavara → Hebbal (275)
    ("Nagavara",      "Hebbal",         "ORR North 1",         275),

    # ORR North 2 — Hebbal → Yelahanka via ORR (235)
    ("Hebbal",        "Yelahanka",      "ORR North 2",         235),

    # ORR West 1 — Kengeri → Yeshwanthpura (168)
    ("Kengeri",       "Yeshwanthpura",  "ORR West 1",          168),

    # West of Chord Road — inner west bypass (174)
    ("Yeshwanthpura", "Vijayanagar",    "West of Chord Road",  174),

    # Bannerghatta Road — south corridor (209)
    ("CBD",           "Jayanagar",      "Bannerghatta Road",   209),
    ("Jayanagar",     "Bannerghatta",   "Bannerghatta Road",   209),

    # Hennur Main Road — north connector (96)
    ("Nagavara",      "Yelahanka",      "Hennur Main Road",    96),

    # Varthur Road — east tech corridor (77)
    ("KR_Puram",      "Whitefield",     "Varthur Road",        77),

    # IRR Thanisandra — inner north ring (95)
    ("Nagavara",      "KR_Puram",       "IRR Thanisandra",     95),

    # Connectivity links (approximate inner-city connectors)
    ("Mekhri_Circle", "Yeshwanthpura",  "Inner Ring Road",     150),
    ("Koramangala",   "Jayanagar",      "Inner Ring Road",     100),
    ("Silk_Board",    "Jayanagar",      "Inner Ring Road",     100),
    ("Jalahalli",     "Yeshwanthpura",  "Inner Ring Road",     120),
    ("Hebbal",        "Mekhri_Circle",  "Inner Ring Road",     130),
    ("Nagavara",      "Yeshwanthpura",  "Inner Ring Road",     110),
]
