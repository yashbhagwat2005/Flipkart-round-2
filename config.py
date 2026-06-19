DATA_FILE = "Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"

CBD_LAT = 12.9716
CBD_LON = 77.5946

# Police Protocol Thresholds (Congestion Level -> Recommended Action)
PROTOCOL_THRESHOLDS = {
    "Low": {
        "action": "Monitor only",
        "reason": "Congestion is within normal capacity. No active intervention required.",
        "requires_action": False
    },
    "Medium": {
        "action": "Increase manpower",
        "reason": "Traffic flow is slowing down. Additional officers required at key junctions to maintain flow.",
        "requires_action": True
    },
    "High": {
        "action": "Deploy barricades",
        "reason": "Congestion nearing critical levels. Restrict entry points to prevent gridlock.",
        "requires_action": True
    },
    "Critical": {
        "action": "Active diversion",
        "reason": "Severe bottleneck detected. Immediately divert incoming traffic via alternate routes.",
        "requires_action": True
    }
}
