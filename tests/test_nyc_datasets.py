"""The official NYC data documentation, plus the street and permit records added to real corners."""
import copy
import math

import pytest

from cornerbrief import search
from cornerbrief.data_loader import load_corner, load_dictionary
from cornerbrief.geo import state_plane_to_lonlat
from cornerbrief.evidence import build_evidence, data_sufficient, join_report, road_owner, road_owner_assumed
from cornerbrief.llm import OfflineClient
from cornerbrief.orchestrator import analyze
from cornerbrief.review_export import approve, to_markdown
from cornerbrief.sidewalk import max_width_ft
from cornerbrief.site_visit import build_list

SURVEY = "2023-01-01"


def real(permits=None, street_segments=None, **changes):
    row = dict(the_geom=dict(type="Point", coordinates=[-73.9, 40.7]), cornerid=1, rampid=2, geocyclora=SURVEY, borough="4", stname1="VAN DAM STREET", stname2="THOMSON AVENUE",
               curb_reveal="0.2", ramp_running_slope_total="6", ramp_cross_slope="1", ramp_width="60", ramp_left_flare="60", lnd_width="60", lnd_length="60", lnd_cross_slope="1",
               gutter_slope="1", counter_slope="-2", ramp_right_flare="8", ramp_length="8")
    row.update(changes)
    corner = dict(key="real_x", label="A and B", data_kind="NYC Open Data", context=dict(inside_nyc=True, work_type="corner_ramp_row", road_control="not_recorded"),
                  locations=[row], progress=[dict(cornerid=1, construc_2="Planned Construction")], complaints=[])
    if permits is not None:
        corner["permits"] = permits
    if street_segments is not None:
        corner["street_segments"] = street_segments
    return corner


def evidence_of(corner, field=None):
    return build_evidence(corner, load_dictionary(corner), field)


def item(items, field):
    return next(e for e in items if e.field == field)


def permit(kind, end, **more):
    return dict(permitnumber="Q1", permittypedesc=kind, issuedworkstartdate="2024-01-01T00:00:00.000", issuedworkenddate=end, onstreetname="VAN DAM STREET", fromstreetname="THOMSON AVENUE", **more)


def test_official_units_are_recorded():
    fields = load_dictionary(real())["fields"]
    assert {fields[f]["unit"] for f in ("curb_reveal", "lnd_width", "lnd_length", "ramp_width", "ramp_length")} == {"in"}
    assert {fields[f]["unit"] for f in ("ramp_running_slope_total", "counter_slope", "gutter_slope", "lnd_cross_slope", "ramp_right_flare", "ramp_left_flare", "ramp_cross_slope")} == {"percent"}
    assert {f["unit_status"] for f in fields.values()} == {"documented"}


def test_positive_length_in_inches_gives_the_rise():
    rise = item(evidence_of(real()), "ramp_rise")
    assert rise.value == 3.6 and rise.unit == "in" and rise.label == "measured"


def test_negative_length_is_not_silently_made_positive():
    items = evidence_of(real(ramp_left_flare="-17.0"))
    length = item(items, "ramp_length")
    assert length.label == "assumed" and length.value == -17.0 and "negative" in length.reason
    assert not [e for e in items if e.field == "ramp_rise"]
    assert any("ramp length" in p for p in data_sufficient(real(ramp_left_flare="-17.0"), items)[1])


def test_negative_slope_is_a_direction_and_stays_measured():
    assert item(evidence_of(real()), "counter_slope").label == "measured"


def test_site_measurement_replaces_a_negative_length():
    corner = real(ramp_left_flare="-17.0")
    entry = dict(key="2:ramp_length", value=4.0, unit="ft", date="2026-11-02", by="A B")
    length = item(evidence_of(corner, [entry]), "ramp_length")
    assert length.label == "measured" and length.on_site


# A real permit point at Thomson Avenue and Van Dam Street, and a ramp about 14 m southwest of it.
PERMIT_POINT = "POINT (1002652.3247999996 210610.10690000653)"
RAMP_NEAR = dict(type="Point", coordinates=[-73.93370894345186, 40.74464324083891])
RAMP_FAR = dict(type="Point", coordinates=[-73.9300, 40.7446])


def ramp_permit(note=None, wkt=PERMIT_POINT, end="2024-04-06T23:59:59.000", number="Q1"):
    extra = {k: v for k, v in dict(permitlocationcomments=note, wkt=wkt).items() if v}
    return dict(permit("PED RAMP REPLACE/MODIFY/INSTALL GOVERNMENT", end, **extra), permitnumber=number)


@pytest.mark.parametrize("permits,geometry,label", [
    ([ramp_permit("SW")], RAMP_NEAR, "assumed"),
    ([ramp_permit("sw corner")], RAMP_NEAR, "assumed"),
    ([ramp_permit()], RAMP_NEAR, "assumed"),
    ([ramp_permit("NW")], RAMP_NEAR, "assumed"),
    ([ramp_permit("NE")], RAMP_NEAR, "measured"),
    ([ramp_permit("SW")], RAMP_FAR, "measured"),
    ([ramp_permit("SW", wkt=None)], RAMP_NEAR, "measured"),
    ([ramp_permit("SW", wkt="not a point")], RAMP_NEAR, "measured"),
    ([ramp_permit("SW")], None, "measured"),
])
def test_only_a_permit_located_at_the_ramp_questions_the_measurement(permits, geometry, label):
    corner = real(permits=permits, the_geom=geometry)
    assert item(evidence_of(corner), "ramp_width").label == label


def test_exact_corner_note_beats_an_adjacent_one():
    corner = real(permits=[ramp_permit(n, number=n) for n in ("SW", "NW", "SE", "NE")], the_geom=RAMP_NEAR)
    assert "1 pedestrian ramp permit located at this ramp has" in item(evidence_of(corner), "ramp_width").reason


def test_block_ramp_permit_goes_on_the_site_visit_without_a_stop():
    corner = real(permits=[ramp_permit("SW", wkt=None)], the_geom=RAMP_NEAR)
    items = evidence_of(corner)
    assert not any("ramp permit" in p for p in data_sufficient(corner, items)[1])
    visit = [v for v in build_list(items, corner) if "pedestrian ramp permits changed" in v["action"]]
    assert visit and "doesn't tie it" in visit[0]["why"]
    assert any("Confirm this is current" not in v["action"] for v in build_list(items, corner))


def test_tied_permit_is_not_also_listed_as_block_only():
    corner = real(permits=[ramp_permit("SW")], the_geom=RAMP_NEAR)
    assert not any("pedestrian ramp permits changed" in v["action"] for v in build_list(evidence_of(corner), corner))
    assert any("Confirm this is current" in v["action"] for v in build_list(evidence_of(corner), corner))


@pytest.mark.parametrize("x,y,lon,lat", [(1002652.3248, 210610.1069, -73.93359, 40.74473), (984250.0, 0.0, -74.0, 40.16667)])
def test_state_plane_conversion(x, y, lon, lat):
    assert state_plane_to_lonlat(x, y) == pytest.approx((lon, lat), abs=0.0001)


def test_ramp_permit_before_the_survey_changes_nothing():
    corner = real(permits=[ramp_permit("SW", end="2022-04-06T23:59:59.000")], the_geom=RAMP_NEAR)
    assert item(evidence_of(corner), "ramp_width").label == "measured"
    assert any("no permit" in n for n in join_report(corner))


def test_other_permit_is_a_site_visit_item_and_not_a_stale_label():
    corner = real(permits=[permit("INSTALL TRAFFIC SIGNALS", "2024-04-06T23:59:59.000")])
    items = evidence_of(corner)
    assert item(items, "ramp_width").label == "measured"
    assert any("permits" in v["action"] for v in build_list(items, corner))
    assert any("allowed, not that it happened" in n for n in join_report(corner))


def test_site_measurement_clears_the_permit_question():
    corner = real(permits=[ramp_permit("SW")], the_geom=RAMP_NEAR)
    width = item(evidence_of(corner, [dict(key="2:ramp_width", value=60, unit="in", date="2026-11-02", by="A B")]), "ramp_width")
    assert width.label == "measured"


def test_jurisdiction_codes_never_confirm_the_road_owner():
    corner = real(street_segments=[dict(full_street_name="VAN DAM ST", streetwidth="44", rwjurisdiction="3"), dict(full_street_name="THOMSON AVE", streetwidth="40")])
    ok, problems = data_sufficient(corner, evidence_of(corner))
    assert not ok and any("road owner" in p for p in problems)
    assert any("doesn't settle the road owner" in n for n in join_report(corner))


def test_centerline_matches_abbreviated_names_and_reports_a_missing_one():
    corner = real(street_segments=[dict(full_street_name="VAN DAM ST", streetwidth="44"), dict(full_street_name="THOMSON AVE", streetwidth="40")])
    assert not any("No street within 100 m" in n for n in join_report(corner))
    corner["street_segments"] = [dict(full_street_name="VAN DAM ST", streetwidth="44")]
    assert any("THOMSON AVENUE" in n and "No street within 100 m" in n for n in join_report(corner))


def test_permit_keeps_only_a_point_and_corner_note():
    kept = search.fetch.trim_permit(dict(permitnumber="Q1", permitlocationcomments="SW", wkt=PERMIT_POINT))
    assert kept == dict(permitnumber="Q1", permitlocationcomments="SW", wkt=PERMIT_POINT)
    kept = search.fetch.trim_permit(dict(permitnumber="Q2", permitlocationcomments="31-28 Example Ave", wkt="LINESTRING (1 2, 3 4)"))
    assert kept == dict(permitnumber="Q2")


def test_filters_escape_street_names():
    corner = real(stname1="O'BRIEN% STREET")
    where = search.fetch.permits_where(corner["locations"])
    assert "O''BRIEN STREET" in where and "%O''BRIEN STREET%" in where and "permittee" not in where
    assert "within_circle(the_geom,40.7,-73.9,100)" == search.fetch.centerline_where(corner["locations"])
    assert "permittee" not in search.fetch.PERMIT_FIELDS


@pytest.mark.parametrize("changes", [dict(stname2=None), dict(geocyclora=None), dict(borough="9")])
def test_permit_filter_is_skipped_when_it_would_be_unbounded(changes):
    assert search.fetch.permits_where(real(**changes)["locations"]) is None


def fake_portal(fail=()):
    def get(url):
        for dataset in fail:
            if dataset in url:
                raise OSError("portal unavailable")
        if search.fetch.LOC in url:
            return real()["locations"]
        if search.fetch.CENTERLINE in url:
            return [dict(full_street_name="VAN DAM ST", streetwidth="44")]
        if search.fetch.PERMITS in url:
            return [permit("INSTALL TRAFFIC SIGNALS", "2024-04-06T23:59:59.000")]
        if search.fetch.OLD_PERMITS in url:
            return [dict(permit("INSTALL TRAFFIC SIGNALS", "2020-04-06T23:59:59.000"), permitnumber="Q0")]
        if search.fetch.SIDEWALK in url:
            return [dict(the_geom=dict(coordinates=[[[[-73.9005, 40.6995], [-73.8995, 40.6995], [-73.8995, 40.7005], [-73.9005, 40.7005], [-73.9005, 40.6995]]]]), source_id="1")]
        if "CMT_SURVEY" in url:
            return dict(features=[dict(attributes=dict(RAMPID=2, COMPLIANCY_STATUS="Pending", RAMP_TYPE="Ramp", RAMP_LENGTH=60, RAMP_LEFT_FLARE=8, SDW_APP_WIDTH1=999, SDW_APP_WIDTH2=170))])
        if "RoadwayData" in url:
            return dict(features=[dict(attributes=dict(Roadway_Name="VAN DAM ST", Owning_Jurisdiction="04-City or village", Maintenance_Jurisdiction="04-City or village"))])
        return []
    return get


def use_folder(tmp_path, monkeypatch, get):
    from cornerbrief.paths import DATA
    monkeypatch.setattr(search, "DATA", tmp_path)
    monkeypatch.setattr("cornerbrief.data_loader.DATA", tmp_path)
    (tmp_path / "data_dictionary.yaml").write_text((DATA / "data_dictionary.yaml").read_text())
    monkeypatch.setattr(search.fetch, "get", get)


def test_pull_keeps_street_and_permit_records(tmp_path, monkeypatch):
    use_folder(tmp_path, monkeypatch, fake_portal())
    key = search.pull("1")
    corner = load_corner(key)
    assert len(corner["source_provenance"]) == 9 and corner["sidewalk_map"]["max_width_ft"] and "the_geom" not in corner["sidewalk_map"] and "nearby_not_checked" not in corner
    assert corner["street_segments"] and len(corner["permits"]) == 2 and corner["dot_survey"] and corner["road_inventory"]
    assert corner["context"]["road_control"] == "city" and corner["context"]["road_control_basis"] == "assumed"
    assert search.pull("1") == key


def test_failed_lookup_keeps_the_packet_and_says_so(tmp_path, monkeypatch):
    use_folder(tmp_path, monkeypatch, fake_portal(fail=[search.fetch.PERMITS, search.fetch.OLD_PERMITS, search.fetch.SIDEWALK, "CMT_SURVEY", "RoadwayData"]))
    corner = load_corner(search.pull("1"))
    assert "permits" not in corner and corner["nearby_not_checked"] == ["Street Construction Permits", "Street Construction Permits 2013-2021", "NYC Planimetric Sidewalk", "NYC DOT survey map", "NYSDOT Roadway Inventory"]
    assert any("wasn't checked" in n for n in join_report(corner))


def test_saved_real_corner_shows_the_new_evidence():
    run = analyze(load_corner("real_test"), client=OfflineClient(), save=False)
    assert run["state"].startswith("stop") and len(run["permits"]) == 43 and len(run["street_segments"]) == 12
    assert all(o["result"] in ("unknown", "not applicable") for o in run["rule_results"])
    assert not any("units" in p or "road owner" in p for p in run["problems"])
    assert item_of(run, "corner:road_control")["label"] == "assumed" and item_of(run, "corner:sidewalk_width")["value"] == 14.11
    assert not any("negative" in p for p in run["problems"]) and any("1 pedestrian ramp permit located at this ramp" in p for p in run["problems"])
    assert item_of(run, "116256:ramp_length")["value"] == 39.6 and item_of(run, "116256:ramp_left_flare")["value"] == -17.0
    assert any("Non-Compliant" in x for x in run["dot_survey"]) and not any("Compliant" in n for n in run["join_notes"])
    assert not any("permitteename" in p for p in run["permits"])
    text = to_markdown(approve(run, "R"))
    assert "Q042024071A05" in text and "nycpedramps.info/survey" in text and "THOMSON AVE (40 ft paved)" in text


def item_of(run, key):
    return next(e for e in run["evidence"] if e["key"] == key)


def inventory(*rows):
    return [dict(Roadway_Name=n, Owning_Jurisdiction=o, Maintenance_Jurisdiction=m) for n, o, m in rows]


CITY, STATE = "04-City or village", "01-NYSDOT"


@pytest.mark.parametrize("rows,expected", [
    ([("VAN DAM ST", CITY, CITY), ("THOMSON AVE", CITY, CITY)], "city"),
    ([("VAN DAM ST", CITY, CITY)], "city"),
    ([("QUEENS BLVD", CITY, CITY)], "city"),
    ([("VAN DAM ST", STATE, STATE), ("THOMSON AVE", CITY, CITY)], "state"),
    ([("VAN DAM ST", CITY, STATE), ("THOMSON AVE", CITY, CITY)], "state"),
    ([("VAN DAM ST", "25-Other local agencies", CITY), ("THOMSON AVE", CITY, CITY)], None),
    ([], "city"),
])
def test_road_owner_needs_every_street_listed(rows, expected):
    corner = real()
    corner["road_inventory"] = inventory(*rows)
    assert road_owner(corner) == expected
    assert road_owner_assumed(corner) == (expected == "city" and len(rows) < 2 or rows == [])


def test_road_owner_stays_unknown_when_the_inventory_was_not_checked():
    assert road_owner(real()) is None and not road_owner_assumed(real())


def assumed_corner():
    corner = real()
    corner["context"].update(road_control="city", road_control_basis="assumed")
    corner["road_inventory"] = []
    return corner


def test_assumed_owner_is_shown_and_listed_for_the_site_visit():
    corner = assumed_corner()
    items = evidence_of(corner)
    owner = item(items, "road_control")
    assert owner.label == "assumed" and owner.value == "city" and "No record confirms" in owner.reason
    assert any("Confirm that the city" in v["action"] for v in build_list(items, corner))
    assert not any("road owner" in p for p in data_sufficient(corner, items)[1])


def test_assumed_owner_can_never_turn_on_a_label(monkeypatch):
    monkeypatch.setenv("SHOW_LABELS_AND_PLANS", "true")
    run = analyze(assumed_corner(), client=OfflineClient(), save=False)
    assert run["label"] is None and run["planning"] is None
    assert all(o["result"] in ("unknown", "not applicable") for o in run["rule_results"])


def test_site_entry_replaces_the_assumed_owner():
    entry = dict(key="corner:road_control", field="road_control", value="state", unit=None, date="2026-11-02", by="A B", photo=None)
    run = analyze(assumed_corner(), client=OfflineClient(), field=[entry], save=False)
    assert run["context"]["road_control"] == "state" and "road_control_basis" not in run["context"]
    assert any("road owner" in p for p in run["problems"])


def test_dot_width_is_read_as_inches_and_labeled_assumed():
    corner = real()
    corner["dot_survey"] = [dict(RAMPID=2, SDW_APP_WIDTH1=999, SDW_APP_WIDTH2=169.34)]
    corner["sidewalk_map"] = dict(max_width_ft=20.0, shapes=5)
    width = item(evidence_of(corner), "sidewalk_width")
    assert width.value == 14.11 and width.unit == "ft" and width.label == "assumed" and "about 20.0 ft" in width.reason
    assert any("Confirm this is current" in v["action"] and "no documented unit" in v["why"] for v in build_list(evidence_of(corner), corner))


@pytest.mark.parametrize("value", [999, 3, 984.88, None])
def test_unbelievable_dot_width_is_ignored(value):
    corner = real()
    corner["dot_survey"] = [dict(RAMPID=2, SDW_APP_WIDTH1=value, SDW_APP_WIDTH2=value)]
    assert item(evidence_of(corner), "sidewalk_width").label == "missing"


def test_sidewalk_estimate_from_a_strip():
    lon, lat = -73.9, 40.7
    east, north = 1 / (math.cos(math.radians(lat)) * 111320), 1 / 110540
    strip = [[lon + x * east, lat + y * north] for x, y in ((-60, -5), (60, -5), (60, 5), (-60, 5), (-60, -5))]
    assert max_width_ft([dict(the_geom=dict(coordinates=[[strip]]))], lon, lat) == pytest.approx(32.8, abs=0.5)
    assert max_width_ft([], lon, lat) is None


def test_inventory_note_says_what_it_does_not_list():
    corner = real()
    corner["road_inventory"] = inventory(("QUEENS BLVD", CITY, CITY))
    notes = " ".join(join_report(corner))
    assert "QUEENS BLVD, owned by City or village" in notes and "doesn't list THOMSON AVENUE, VAN DAM STREET" in notes and "assumed city-owned" in notes


def test_column_check_reports_a_length_that_disagrees():
    corner = real()
    corner["dot_survey"] = [dict(RAMPID=2, RAMP_LENGTH=50)]
    assert any("Check ramp 2's length" in n for n in join_report(corner))
    corner["dot_survey"] = [dict(RAMPID=2, RAMP_LENGTH=60)]
    assert not any("Check ramp" in n for n in join_report(corner))


def test_ada_rules_quote_ada_gov_and_stay_unreviewed():
    from cornerbrief.rules import load_rules
    rules = [r for r in load_rules() if r["id"].startswith("ADA-")]
    assert len(rules) == 7 and all("ada.gov" in r["url"] and r["status"] == "unreviewed" and not r["reviewed_by"] for r in rules)


def test_sample_corners_do_not_change():
    assert not [n for n in join_report(copy.deepcopy(load_corner("standard"))) if "Centerline" in n or "Permits" in n]


def test_old_site_measurement_stays_stale():
    corner = real(permits=[ramp_permit("SW")], the_geom=RAMP_NEAR)
    for when, words in (("2020-01-01", "before work under a pedestrian ramp permit"), ("2022-12-31", "before the 2023-01-01 survey")):
        width = item(evidence_of(corner if "permit" in words else real(), [dict(key="2:ramp_width", value=60, unit="in", date=when, by="A B")]), "ramp_width")
        assert width.label == "stale" and words in width.reason
    width = item(evidence_of(corner, [dict(key="2:ramp_width", value=60, unit="in", date="2024-05-01", by="A B")]), "ramp_width")
    assert width.label == "measured" and width.reason == "Measured on site."


def test_map_service_sources_are_named():
    get = search.fetch.get
    try:
        search.fetch.get = lambda url: {"features": []}
        assert search.esri_rows(search.fetch.DOT_SURVEY, {"f": "json"})[1]["dataset"] == "CMT_SURVEY_COMPLIANCY_TOLERANCE_PROD"
        assert search.esri_rows(search.fetch.ROAD_INVENTORY, {"f": "json"})[1]["dataset"] == "RoadwayData"
    finally:
        search.fetch.get = get


def test_saved_responses_expire_but_cover_an_outage(tmp_path, monkeypatch):
    import os, time
    monkeypatch.setattr(search.fetch, "ROOT", tmp_path)
    calls = []
    def download(url):
        calls.append(url)
        if len(calls) > 1:
            raise OSError("offline")
        return [1]
    monkeypatch.setattr(search.fetch, "_download", download)
    assert search.fetch.get("u") == [1] and search.fetch.get("u") == [1] and len(calls) == 1
    path = next((tmp_path / "cache" / "nyc").iterdir())
    old = time.time() - 8 * 86400
    os.utime(path, (old, old))
    assert search.fetch.get("u") == [1] and len(calls) == 2


def test_field_errors_use_plain_names():
    from cornerbrief.field import _value
    with pytest.raises(ValueError, match="running slope"):
        _value("ramp_running_slope_total", "abc")
