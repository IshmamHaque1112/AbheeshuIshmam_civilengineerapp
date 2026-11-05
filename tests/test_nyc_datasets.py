"""The official NYC data documentation, plus the street and permit records added to real corners."""
import copy

import pytest

from cornerbrief import search
from cornerbrief.data_loader import load_corner, load_dictionary
from cornerbrief.evidence import build_evidence, data_sufficient, join_report, road_owner
from cornerbrief.llm import OfflineClient
from cornerbrief.orchestrator import analyze
from cornerbrief.review_export import approve, to_markdown
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


def test_ramp_permit_after_the_survey_questions_the_measurement():
    corner = real(permits=[permit("PED RAMP REPLACE/MODIFY/INSTALL GOVERNMENT", "2024-04-06T23:59:59.000")])
    items = evidence_of(corner)
    assert item(items, "ramp_width").label == "assumed" and "1 pedestrian ramp permit for this block has" in item(items, "ramp_width").reason
    assert any("Confirm this is current" in v["action"] for v in build_list(items, corner))


def test_ramp_permit_before_the_survey_changes_nothing():
    corner = real(permits=[permit("PED RAMP REPLACE/MODIFY/INSTALL GOVERNMENT", "2022-04-06T23:59:59.000")])
    assert item(evidence_of(corner), "ramp_width").label == "measured"
    assert any("no permit" in n for n in join_report(corner))


def test_other_permit_is_a_site_visit_item_and_not_a_stale_label():
    corner = real(permits=[permit("INSTALL TRAFFIC SIGNALS", "2024-04-06T23:59:59.000")])
    items = evidence_of(corner)
    assert item(items, "ramp_width").label == "measured"
    assert any("permits" in v["action"] for v in build_list(items, corner))
    assert any("allowed, not that it happened" in n for n in join_report(corner))


def test_site_measurement_clears_the_permit_question():
    corner = real(permits=[permit("PED RAMP REPLACE", "2024-04-06T23:59:59.000")])
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
    assert len(corner["source_provenance"]) == 8 and "nearby_not_checked" not in corner
    assert corner["street_segments"] and len(corner["permits"]) == 2 and corner["dot_survey"] and corner["road_inventory"]
    assert corner["context"]["road_control"] == "not_recorded"
    assert search.pull("1") == key


def test_failed_lookup_keeps_the_packet_and_says_so(tmp_path, monkeypatch):
    use_folder(tmp_path, monkeypatch, fake_portal(fail=[search.fetch.PERMITS, search.fetch.OLD_PERMITS, "CMT_SURVEY", "RoadwayData"]))
    corner = load_corner(search.pull("1"))
    assert "permits" not in corner and corner["nearby_not_checked"] == ["Street Construction Permits", "Street Construction Permits 2013-2021", "NYC DOT survey map", "NYSDOT Roadway Inventory"]
    assert any("wasn't checked" in n for n in join_report(corner))


def test_saved_real_corner_shows_the_new_evidence():
    run = analyze(load_corner("real_test"), client=OfflineClient(), save=False)
    assert run["state"].startswith("stop") and len(run["permits"]) == 43 and len(run["street_segments"]) == 12
    assert all(o["result"] in ("unknown", "not applicable") for o in run["rule_results"])
    assert not any("units" in p for p in run["problems"]) and any("road owner" in p for p in run["problems"])
    assert not any("negative" in p for p in run["problems"]) and any("pedestrian ramp permits" in p for p in run["problems"])
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
    ([("VAN DAM ST", CITY, CITY)], None),
    ([("QUEENS BLVD", CITY, CITY)], None),
    ([("VAN DAM ST", STATE, STATE), ("THOMSON AVE", CITY, CITY)], "state"),
    ([("VAN DAM ST", CITY, STATE), ("THOMSON AVE", CITY, CITY)], "state"),
    ([("VAN DAM ST", "25-Other local agencies", CITY), ("THOMSON AVE", CITY, CITY)], None),
    ([], None),
])
def test_road_owner_needs_every_street_listed(rows, expected):
    corner = real()
    corner["road_inventory"] = inventory(*rows)
    assert road_owner(corner) == expected


def test_inventory_note_says_what_it_does_not_list():
    corner = real()
    corner["road_inventory"] = inventory(("QUEENS BLVD", CITY, CITY))
    notes = " ".join(join_report(corner))
    assert "QUEENS BLVD, owned by City or village" in notes and "doesn't list THOMSON AVENUE, VAN DAM STREET" in notes


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
