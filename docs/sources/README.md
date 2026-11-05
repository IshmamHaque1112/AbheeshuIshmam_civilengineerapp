# Source documents

## H-1011 Pedestrian Ramps

NYC DOT Standard Details of Construction, published June 1, 2022, as listed by the [NYC Street Design Manual](https://www.nycstreetdesign.info/specifications?keysspec=&field_specification_name_value=Pedestrian+Ramps) on November 5, 2026.

| Sheet | Title |
| --- | --- |
| [H-1011-1](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-1.pdf) | Index of Drawings, Slope Limits, Legend, Glossary, General Notes (saved here) |
| [H-1011-2](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-2.pdf) | Corner Cases, Perpendicular |
| [H-1011-3](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-3.pdf) | Corner Cases, Parallel |
| [H-1011-4](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-4.pdf) | Corner Cases, Approval Requested |
| [H-1011-5](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-5.pdf) | Midblock Cases |
| [H-1011-6](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-6.pdf) | Island Cases |
| [H-1011-7](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-7.pdf) | Temporary Cases |
| [H-1011-8](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-8.pdf) | Miscellaneous Details and Examples |
| [H-1011-9](https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-9.pdf) | Detectable Warning Surfaces |

Sheets 2 to 9 aren't saved or transcribed yet. To save them, run this in PowerShell from the project folder:

```powershell
2..9 | ForEach-Object { Invoke-WebRequest "https://www.nycstreetdesign.info/sites/default/files/specs/H-1011-$_.pdf" -OutFile "docs\sources\H-1011-$_.pdf" }
```

## 2010 ADA Standards

The ADA rules quote [ada.gov's 2010 Standards page](https://www.ada.gov/law-and-regs/design-standards/2010-stds/), read on November 5, 2026.
