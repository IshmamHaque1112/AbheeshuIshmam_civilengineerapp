"""Likely equipment types only. This never selects a crane or a crane position."""


def build_equipment(takeoff: dict) -> list[dict]:
    return [
        {"type": "Concrete saw", "use": "Cut the existing surface and curb"},
        {"type": "Compact excavator or skid steer", "use": "Remove material and move base"},
        {"type": "Plate compactor", "use": "Compact the base"},
        {"type": "Concrete delivery truck", "use": "Deliver slab and curb concrete"},
        {"type": "Dump truck", "use": "Haul removed material"},
    ]
