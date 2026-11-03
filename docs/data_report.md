# CornerBrief data report

Generated 2026-11-03 16:38 UTC.

Field matches are keyword guesses. Read the column descriptions before relying on them.

## Coverage of what the demo needs

Datasets checked: Pedestrian Ramp Locations, Pedestrian Ramp Program Progress, Pedestrian Ramp Complaints.

| Need | Possible fields |
| --- | --- |
| Location (lat/long or geometry) | Pedestrian Ramp Locations: `the_geom`; Pedestrian Ramp Program Progress: `the_geom` |
| Corner or ramp ID | Pedestrian Ramp Locations: `cornerid`; Pedestrian Ramp Locations: `rampid`; Pedestrian Ramp Program Progress: `objectid`; Pedestrian Ramp Program Progress: `cornerid`; Pedestrian Ramp Complaints: `cmt_corner_id` |
| Borough | Pedestrian Ramp Locations: `borough`; Pedestrian Ramp Program Progress: `borough`; Pedestrian Ramp Complaints: `borough` |
| Ramp type | Pedestrian Ramp Program Progress: `constructi`; Pedestrian Ramp Complaints: `temp_repair_type` |
| Running slope | Pedestrian Ramp Locations: `ramp_running_slope_total`; Pedestrian Ramp Locations: `gutter_slope`; Pedestrian Ramp Locations: `lnd_cross_slope`; Pedestrian Ramp Locations: `counter_slope`; Pedestrian Ramp Locations: `ramp_cross_slope` |
| Cross slope | Pedestrian Ramp Locations: `lnd_cross_slope`; Pedestrian Ramp Locations: `ramp_cross_slope` |
| Ramp width | Pedestrian Ramp Locations: `lnd_width`; Pedestrian Ramp Locations: `ramp_width` |
| Landing or turning space | Pedestrian Ramp Locations: `obstacles_landing` |
| Curb height or reveal | Pedestrian Ramp Locations: `curb_reveal` |
| Sidewalk width | NOT FOUND |
| Street grade | NOT FOUND |
| Detectable warning surface | Pedestrian Ramp Locations: `dws_conditions` |
| Compliance or review status | Pedestrian Ramp Program Progress: `construc_2` |
| Complaint or repair | Pedestrian Ramp Complaints: `complaint_id`; Pedestrian Ramp Complaints: `complaint_date`; Pedestrian Ramp Complaints: `temp_repair_feasible`; Pedestrian Ramp Complaints: `temp_repair_date`; Pedestrian Ramp Complaints: `temp_repair_type`; Pedestrian Ramp Complaints: `second_temp_repair_needed`; Pedestrian Ramp Complaints: `date_second_temp_repair`; Pedestrian Ramp Complaints: `bulkcomplaint` |

## Pedestrian Ramp Locations

- ID: `ufzp-rrqu`
- Rows: 217,679
- Data last updated: 2021-10-27
- Rows sampled: 1,000

### Columns

| Field | Type | Filled in sample | Distinct in sample | Example | Description |
| --- | --- | --- | --- | --- | --- |
| `the_geom` | point | 100% | 1000 | {"type": "Point", "coordinates": [-73.89718748103968, 40.83794631113792]} | Each ramp is represented by a point in the dataset  |
| `cornerid` | number | 100% | 995 | 1370422 | Unique identifier assigned to the corner by the surveyor for the street corner |
| `rampid` | number | 100% | 1000 | 340375 | Unique identifier assigned to the ramp by the surveyor for the ramp |
| `ramp_onstr` | text | 100% | 666 | Crotona Ave | Street(s) for where the ramp is facing/serving |
| `geocyclora` | calendar_date | 100% | 99 | 2019-10-19T00:00:00.000 | The date the data was captured by the surveyor |
| `borough` | number | 100% | 5 | 2 | Borough of the ramp location |
| `stname1` | text | 100% | 639 | CROTONA AVENUE | Street name one at intersection |
| `stname2` | text | 100% | 679 | 86 AVENUE | Street name two at intersection |
| `curb_reveal` | number | 100% | 28 | 999.0 | Maximum height of lip at dropped curb |
| `ramp_running_slope_total` | number | 100% | 171 | 5.5 | Longitudinal slope of ramp's entire extent |
| `dws_conditions` | text | 100% | 4 | Good Condition | Detectable Warning Surface condition |
| `gutter_slope` | number | 100% | 128 | 1.2 | Slope measured along the roadway gutter line |
| `lnd_width` | number | 100% | 322 | 60.0 | Width of top landing (perpendicular to ramp)  |
| `lnd_length` | number | 100% | 194 | 48.0 | Length of top landing (in direction of ramp)  |
| `lnd_cross_slope` | number | 100% | 146 | 2.2 | Slope of top landing (perpendicular to direction of ramp)  |
| `counter_slope` | number | 100% | 195 | 4.9 | Slope of adjacent street at ramp interface (roadway grade)  |
| `ramp_width` | number | 100% | 323 | 60.0 | Width of ramp  |
| `ramp_right_flare` | number | 100% | 295 | 8.8 | Max slope of right flare (from the frontal view of ramp)  |
| `ramp_left_flare` | number | 100% | 337 | 60.0 | Max slope of left flare (from the frontal view of ramp)  |
| `ramp_length` | number | 100% | 306 | 3.3 | Length of ramp  |
| `ramp_cross_slope` | number | 100% | 135 | 4.3 | Cross slope of ramp  |
| `ponding` | text | 100% | 2 | No | Is there pooling of water at the base of ramp?  |
| `obstacles_ramp` | text | 100% | 6 | None | List of infrastructure/permanent street furniture within pedestrian access route: ramp area.  |
| `obstacles_landing` | text | 100% | 7 | None | List of infrastructure/permanent street furniture within pedestrian access route: area behind ramp(s... |

### Value breakdowns (sample)

- `borough`: 3 (311), 4 (307), 2 (226), 1 (85), 5 (71)
- `dws_conditions`: Missing (660), Good Condition (320), Defective (19), Not Applicable (1)
- `ponding`: No (814), Yes (186)
- `obstacles_ramp`: None (984), Utility access (11), Utility Vault (2), Wooden Utility Pole (1), Catch Basin (1), Wooden Utility Pole,Metal Light Pole (1)
- `obstacles_landing`: None (932), Utility access (57), Utility Vault (7), Wooden Utility Pole (1), Wooden Utility pole,Wooden Traffic pole,Wooden Light pole (1), Bollard,Utility access (1), FDNY Call Box (1)

## Pedestrian Ramp Program Progress

- ID: `e7gc-ub6z`
- Rows: 187,749
- Data last updated: 2026-11-01
- Rows sampled: 1,000

### Columns

| Field | Type | Filled in sample | Distinct in sample | Example | Description |
| --- | --- | --- | --- | --- | --- |
| `the_geom` | point | 100% | 1000 | {"type": "Point", "coordinates": [-73.92534282712704, 40.767801184811006]} | Geometry column used for mapping |
| `objectid` | number | 100% | 1000 | 50078 | A system-managed value that uniquely identifies a record or feature |
| `cornerid` | number | 100% | 1000 | 1057583 | Unique numeric identifier assigned to a corner point. A corner may contain more than one ramp.  |
| `street_nam` | text | 100% | 487 | CRESCENT STREET | The first street name where the corner is located. |
| `street_n_1` | text | 100% | 439 | 30 ROAD | The second street name where the corner is located. |
| `borough` | text | 100% | 3 | QUEENS | Borough where the corner is located. |
| `constructi` | text | 62% | 2 | Upgrade | If the construction type is a pedestrian ramp upgrade or new installation. |
| `construc_1` | text | 36% | 311 | 2026/10/14 | The date the corner construction was completed. |
| `construc_2` | text | 100% | 6 | Complex Planned Construction | The status for the corner.  |

### Value breakdowns (sample)

- `borough`: QUEENS (995), BRONX (3), BROOKLYN (2)
- `constructi`: Upgrade (555), New Install (65)
- `construc_2`: Constructed (322), Planned Construction (291), Not Assigned (200), Not Required (103), Complex Planned Construction (50), Complex Constructed (34)

## Pedestrian Ramp Complaints

- ID: `jagj-gttd`
- Rows: 6,571
- Data last updated: 2026-11-01
- Rows sampled: 1,000

### Columns

| Field | Type | Filled in sample | Distinct in sample | Example | Description |
| --- | --- | --- | --- | --- | --- |
| `cmt_corner_id` | number | 100% | 993 | 1068314 | Unique numeric identifier assigned to a corner point. A corner may contain more than one ramp.  |
| `street_name1` | text | 100% | 425 | 78 AVENUE | The first street name where the corner is located. |
| `street_name2` | text | 100% | 510 | 153 STREET | The second street name where the corner is located. |
| `borough` | text | 100% | 5 | QUEENS | Borough where the corner is located. |
| `community_district` | number | 100% | 63 | 408 | The three digit community district number to identify the community district the corner is located i... |
| `block` | number | 100% | 805 | 6710 | Tax Block identification number adjacent to the corner. |
| `lot` | number | 100% | 149 | 2 | Tax Lot identification number adjacent to the corner. |
| `complaint_id` | text | 100% | 733 | 311-23925250 | Unique identification number for each complaint record. |
| `complaint_date` | calendar_date | 100% | 337 | 2025-08-05T00:00:00.000 | The date the complaint was made. |
| `temp_repair_feasible` | text | 100% | 3 | No | If a temporary repair is feasible.  |
| `temp_repair_date` | calendar_date | 28% | 86 | 2019-06-26T00:00:00.000 | The date the temporary repair was completed. |
| `temp_repair_type` | text | 28% | 2 | Other | What type of temporary repair was done on the corner or pedestrian ramp. |
| `second_temp_repair_needed` | text | 100% | 1 | No | If a second temporary repair is needed for a corner or pedestrian ramp. |
| `date_second_temp_repair` | calendar_date | 0% | 0 |  | The date of the second temporary repair. |
| `bulkcomplaint` | text | 80% | 2 | No | If the complaint involves multiple corners. |

### Value breakdowns (sample)

- `borough`: QUEENS (363), BROOKLYN (250), MANHATTAN (248), BRONX (89), STATEN ISLAND (50)
- `temp_repair_feasible`: No (719), Yes (280), Pending Determination (1)
- `temp_repair_type`: Other (278), Asphalt Ramp (2)
- `bulkcomplaint`: No (788), Yes (16)
