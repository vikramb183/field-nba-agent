"""Synthetic field-service knowledge graph.

This is made-up sample data for a demo. It is not taken from any real
company's systems.

Graph model:
    (:Symptom)-[:INDICATES {weight}]->(:Cause)-[:AFFECTS]->(:DeviceType)
    (:Cause)-[:RESOLVED_BY {success_rate}]->(:Action)
"""

DEVICE_TYPES = [
    {"id": "ont", "name": "Optical Network Terminal"},
    {"id": "router", "name": "Home Router"},
    {"id": "small_cell", "name": "Small Cell Radio"},
]

SYMPTOMS = [
    {"id": "no_internet", "name": "No internet connection",
     "keywords": ["no internet", "offline", "no connection", "internet down", "not connecting"]},
    {"id": "slow_speed", "name": "Slow speeds",
     "keywords": ["slow", "speed", "lag", "buffering", "latency"]},
    {"id": "wifi_drops", "name": "Wi-Fi keeps dropping",
     "keywords": ["drop", "dropping", "dropped", "disconnect", "intermittent"]},
    {"id": "los_light", "name": "Red LOS light",
     "keywords": ["los", "red light", "loss of signal", "optical"]},
    {"id": "overheating", "name": "Device overheating",
     "keywords": ["hot", "overheat", "temperature", "fan"]},
    {"id": "no_power", "name": "No power",
     "keywords": ["no power", "dead", "won't turn on", "wont turn on", "no lights"]},
]

CAUSES = [
    {"id": "fiber_damage", "name": "Damaged or dirty fiber", "affects": ["ont"]},
    {"id": "ont_firmware", "name": "Outdated ONT firmware", "affects": ["ont"]},
    {"id": "power_supply_fault", "name": "Faulty power supply", "affects": ["ont", "router", "small_cell"]},
    {"id": "wifi_interference", "name": "Wi-Fi channel interference", "affects": ["router"]},
    {"id": "router_config", "name": "Bad router configuration", "affects": ["router"]},
    {"id": "backhaul_congestion", "name": "Backhaul congestion", "affects": ["small_cell"]},
    {"id": "thermal_shutdown", "name": "Thermal throttling or shutdown", "affects": ["small_cell", "router"]},
]

INDICATES = [
    ("no_internet", "fiber_damage", 0.6),
    ("no_internet", "ont_firmware", 0.4),
    ("no_internet", "router_config", 0.5),
    ("no_internet", "power_supply_fault", 0.3),
    ("no_internet", "backhaul_congestion", 0.4),
    ("slow_speed", "wifi_interference", 0.7),
    ("slow_speed", "backhaul_congestion", 0.7),
    ("slow_speed", "ont_firmware", 0.3),
    ("slow_speed", "router_config", 0.3),
    ("wifi_drops", "wifi_interference", 0.8),
    ("wifi_drops", "router_config", 0.4),
    ("wifi_drops", "thermal_shutdown", 0.3),
    ("los_light", "fiber_damage", 0.9),
    ("overheating", "thermal_shutdown", 0.9),
    ("no_power", "power_supply_fault", 0.9),
]

ACTIONS = [
    {"id": "clean_inspect_fiber", "name": "Clean and inspect fiber connectors",
     "steps": "Inspect and clean fiber connectors, then test light levels with an optical power meter.",
     "est_minutes": 30, "requires_escalation": False},
    {"id": "replace_fiber_patch", "name": "Replace fiber patch cord",
     "steps": "Replace the fiber patch cord and re-test light levels.",
     "est_minutes": 45, "requires_escalation": False},
    {"id": "update_ont_firmware", "name": "Update ONT firmware",
     "steps": "Push the latest approved firmware and reboot the ONT.",
     "est_minutes": 20, "requires_escalation": False},
    {"id": "replace_power_adapter", "name": "Replace power adapter",
     "steps": "Swap the power adapter with a known-good unit and confirm the power LED.",
     "est_minutes": 15, "requires_escalation": False},
    {"id": "change_wifi_channel", "name": "Move to a cleaner Wi-Fi channel",
     "steps": "Run a Wi-Fi scan and move the router to the least congested channel.",
     "est_minutes": 10, "requires_escalation": False},
    {"id": "add_mesh_extender", "name": "Add a mesh extender",
     "steps": "Install a mesh extender near the weak-signal area and re-test coverage.",
     "est_minutes": 40, "requires_escalation": False},
    {"id": "reset_router_config", "name": "Restore a known-good router config",
     "steps": "Back up settings, factory reset, and restore a known-good configuration.",
     "est_minutes": 25, "requires_escalation": False},
    {"id": "reroute_backhaul", "name": "Rebalance backhaul capacity",
     "steps": "Open a ticket with the network operations center to rebalance backhaul capacity.",
     "est_minutes": 60, "requires_escalation": True},
    {"id": "improve_ventilation", "name": "Improve ventilation",
     "steps": "Clear the vents, check the fan, and relocate the unit away from heat sources.",
     "est_minutes": 20, "requires_escalation": False},
]

RESOLVED_BY = [
    ("fiber_damage", "clean_inspect_fiber", 0.70),
    ("fiber_damage", "replace_fiber_patch", 0.85),
    ("ont_firmware", "update_ont_firmware", 0.80),
    ("power_supply_fault", "replace_power_adapter", 0.90),
    ("wifi_interference", "change_wifi_channel", 0.70),
    ("wifi_interference", "add_mesh_extender", 0.80),
    ("router_config", "reset_router_config", 0.75),
    ("backhaul_congestion", "reroute_backhaul", 0.70),
    ("thermal_shutdown", "improve_ventilation", 0.75),
]
