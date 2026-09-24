## Silk registers

There is no public documentation of BWT Silk softener registers. Names below come from firmware settings table analysis (Perla Silk Wi‑Fi firmware, settings name table @ `0x86880`, stride `0x2c`) plus TwinValues / community observations. Register index == `params[i]`.

Firmware / product metadata (version, gitver, productCode) is **not** in these registers — it comes from `GET /silk/status`.

If you have additional values or corrections, please open a PR or issue.

| Register | Name | Notes |
|---|---|---|
| 0 | Salt type | TwinValues / community |
| 1 | Reserved | often `-1` |
| 2 | Current hour | device clock |
| 3 | Current minute | device clock |
| 4 | Water hardness | ppm CaCO₃ |
| 5 | Device ranking | TwinValues |
| 6 | Model code | TwinValues |
| 7 | Recharge / regen hour | firmware: `RechargeTime` |
| 8 | Regen minute | |
| 9 | ? | live often `9` |
| 10 | ? | live often `8` |
| 11 | Duplex setting | firmware |
| 12 | Base model number | firmware |
| 13 | Hardness units | firmware (was previously mis-documented as turbine pulses) |
| 14 | Avg water served / day | litres/day |
| 15 | Total water served | ×100 → lifetime litres |
| 16 | Current flow rate | ×60 → L/h |
| 17 | Days in service | |
| 18 | Warranty days remaining | |
| 19 | Total regenerations | |
| 20 | Turbine pulses per litre | firmware (default `40`) |
| 21 | Recharge interval | firmware |
| 22 | Capacity scale factor | firmware (default `100`) |
| 23 | Remaining capacity | litres |
| 24 | Fill duration | minutes |
| 25 | Dwell duration | minutes |
| 26 | Brine duration | minutes |
| 27 | Backwash duration | minutes |
| 28 | Rinse duration | minutes |
| 29 | Salt alarm mode | firmware |
| 30 | Regenerativ capacity | raw units (÷10 ≈ kg) |
| 31 | Regenerativ remaining | raw units (÷10 ≈ kg) |
| 32 | Salt use per regeneration | firmware |
| 33 | Service reminder mode | |
| 34 | Days until service | |
| 35 | Recharge algorithm | |
| 36–37 | Reserved | often `-1` |
| 38 | Day of week | |
| 39 | Allow salt type change | firmware bool |
| 40 | Allow regen time change | firmware bool |
| 41 | Resin capacity | firmware |
| 42 | Daily water usage | litres today |
| 43 | ? | often `-1` |
| 44–46 | Reserved | often `-1` |
| 47 | ? | |

### Softener UART (firmware)

- `$Rsscc` — read `cc` registers from start `ss`
- `$Wassvvv` — write
- `$CRSWVN` — BOASTW3 version
- `$CIFRGN` / `$CIREGN` — regeneration
