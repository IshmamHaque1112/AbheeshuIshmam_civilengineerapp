"""One measured takeoff. Cost, crew and equipment all read from it."""
from .parts_kit import assumptions


def build_takeoff(parts: list[dict]) -> dict:
    a = assumptions()
    def area(kind):
        return sum(p["length_ft"] * p["width_ft"] for p in parts if p["kind"] == kind)
    ramp, landing, dws = area("ramp"), area("landing"), area("dws")
    slab_ft3 = sum(p["length_ft"] * p["width_ft"] * p["thickness_ft"] for p in parts if p["kind"] in ("ramp", "landing"))
    curb = sum(p["length_ft"] for p in parts if p["kind"] == "curb")
    removal = (ramp + landing) * a["removal_factor"]["value"]
    items = [
        dict(id="slab_area", label="Ramp and landing slab", qty=round(ramp + landing, 1), unit="sf"),
        dict(id="dws_area", label="Detectable warning surface", qty=round(dws, 1), unit="sf"),
        dict(id="curb_length", label="Curb", qty=round(curb, 1), unit="lf"),
        dict(id="removal_area", label="Existing surface removal", qty=round(removal, 1), unit="sf"),
        dict(id="concrete_volume", label="Slab concrete", qty=round(slab_ft3 / 27, 2), unit="cy"),
    ]
    return {"items": items, "assumptions": [{"id": k, **v} for k, v in a.items()],
            "exclusions": ["Utilities and utility relocation", "Drainage changes", "Traffic and pedestrian control",
                           "Permits and inspection", "Roadway or sidewalk work beyond the modeled parts",
                           "Base preparation and reinforcement", "Overhead, profit and escalation"]}


def qty(takeoff: dict, item_id: str) -> float:
    return next(i["qty"] for i in takeoff["items"] if i["id"] == item_id)
