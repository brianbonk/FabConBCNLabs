# Sample / reference data

| File | Status | Used by |
|---|---|---|
| `stops_landmarks.csv` | **Input**, hand-authored. Landmarks around the CCIB and the city, preferred lines, search radius, polling interval. | `infra/build_stops_from_osm.py` (and `infra/resolve_stops.py`) |
| `stops.csv` | **Generated and committed** (2026-09-24) by `infra/build_stops_from_osm.py`. Columns: `StopCode,StopName,Address,Zone,Lat,Lon,Lines,IsPrimary,PollIntervalSeconds`. 18 TMB bus stops: 6 at the venue, 4 along the corridor, 8 at the interchanges. | The Function (`TMB_IBUS_STOPS`) **and** Lab 03 (`StopsDim`), Lab 06 (uploaded to `Files/reference/`) |
| `lines.csv` | **Generated and committed** alongside `stops.csv`. Columns: `LineCode,LineName,LineOrigin,LineDestination,TmbLineId`. Origins/destinations as shown on tmb.cat's line pages. | Lab 03 (`LinesDim`), Lab 04 parameter |
| `metro_stations.csv` | **Hand-built and committed** (2026-09-24). Columns: `StationCode,StationName,Lines,Zone,Lat,Lon`. Station codes read from tmb.cat's metro line pages (clicking a station navigates to `/estacion/<code>`); coordinates from Barcelona's open-data transport dataset. | The Function (`TMB_METRO_STATIONS`) and Lab 03 (`MetroStationsDim`) |
| `metro_stations_wanted.csv` | **Input** for the API-based resolver only. | `infra/resolve_stops.py` |

## Where the codes come from

TMB's own Transit API needs an app key, so the committed files were built from public sources instead:

- **Bus stop codes, names, coordinates, lines**: OpenStreetMap bus stops in Barcelona carry TMB's stop code in the
  `ref` tag. Spot-checked against tmb.cat's stop pages: 2689 "Diagonal Mar", 2265 "Pg Taulat - Diagonal Mar",
  2683 "Rambla de Prim - Metro La Pau", 1265 "Pg de Sant Joan - Còrsega" all match. Stops operated by AMB/ATM were
  excluded (TMB's iTransit endpoint serves TMB stops).
- **Line origins/destinations**: read from `tmb.cat/en/barcelona/buses/-/lineabus/<line>`.
- **Metro station codes**: `tmb.cat/en/barcelona/metro/-/lineametro/<line>`, click a station, read the code from the URL.
  Codes are per line and station (Passeig de Gràcia is 425 on L4; its L2/L3 codes differ), so the file lists one
  line per station and iTransit returns that line's trains.

## The venue stops (Zone = Venue)

| StopCode | Stop | Lines | Where |
|---|---|---|---|
| **2689** | Diagonal Mar | H16 | Av. Diagonal in front of the CCIB. **The `<VENUE_STOP_CODE>` used in Labs 02 and 05.** |
| 3477 | Pg Taulat - Pl de Llevant | H16 | Other direction, Pg. Taulat side of the CCIB |
| 3347 | Diagonal - Pl Llevant | 7 | Av. Diagonal, line 7 towards Zona Universitària |
| 2259 | Diagonal - Llull | 7 | Av. Diagonal, line 7 |
| 1090 | Metro Maresme - Fòrum | 136 | At the L4 station entrance |
| 1878 | Rambla Prim - Av. Diagonal | V31 | At the L4 station entrance |

Metro: **416 El Maresme | Fòrum (L4)** is the venue station; 415 Besòs Mar and 417 Selva de Mar are its neighbours.

## Regenerating

```bash
python3 infra/build_stops_from_osm.py            # bus stops + lines from OpenStreetMap (no key needed)
python3 infra/build_stops_from_osm.py --refresh  # ignore the cached Overpass result
```

Don't regenerate on the day: the labs quote stop names and the venue code, and the Function's `TMB_IBUS_STOPS`
must match `StopsDim`. If OpenStreetMap's `route_ref` is missing for a line at a landmark, the script says so;
add the stop by hand or widen the radius in `stops_landmarks.csv`.

Function settings derived from these files:

```
TMB_IBUS_STOPS=2689,2259,3347,1090,3477,1878,2700,662,32,2265,1297,956,3878,281,1210,1103,1282,784
TMB_METRO_STATIONS=416,415,417,422,425,126,130,523,521,518
```
