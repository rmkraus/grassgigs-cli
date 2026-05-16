---
name: grassgigs-concerts
description: Query bluegrass & grassroots concerts from grassgigs.com — search by state, city, band, date, or geographic radius.
---

# GrassGigs Concert Lookup CLI Tool

Query bluegrass & grassroots concerts from grassgigs.com via their public AWS API.

## What it is
A Python CLI tool that connects to the GrassGigs public API to search and filter bluegrass concerts, festivals, and events. See `references/api-reference.md` for full API schema.

## Install

### From GitHub
```bash
git clone https://github.com/rmkraus/grassgigs-cli
cd grassgigs-cli
chmod +x grassgigs/__main__.py
```

### Make globally available
```bash
sudo ln -s "$(pwd)/grassgigs/__main__.py" /usr/local/bin/grassgigs
```

## Usage

### Basic queries
```bash
# All upcoming concerts
grassgigs

# Concerts in a specific state (next 7 days)
grassgigs --state NC --days 7

# Concerts in a city
grassgigs --city "Asheville"

# Search by band name
grassgigs --band "Jerry Douglas"

# Festivals only (next 30 days)
grassgigs --upcoming --type festival

# Limit results
grassgigs --state TN --limit 5
```

### Radius search
```bash
# Within 50 miles of Nashville, next 14 days, sorted closest first
grassgigs --city "Nashville, TN" --radius 50 --days 14 --distance-sort

# Near Asheville, NC, 100-mile radius
grassgigs --city "Asheville, NC" --radius 100 --limit 20

# Raw coordinates, 25-mile radius
grassgigs --lat 35.2271 --lng -80.8431 --radius 25 --band "Bluegrass"
```

### JSON output
```bash
grassgigs --state NC --days 7 --json
```

### Info commands
```bash
# Concerts by state breakdown
grassgigs --states
```

## All flags
| Flag | Description | Example |
|------|-------------|---------|
| `--state`, `-s` | Filter by state code | `--state VA` |
| `--city`, `-c` | Filter by city (partial match) | `--city Asheville` |
| `--band`, `-b` | Search band name (partial match) | `--band "Punch Brothers"` |
| `--days`, `-d` | N days from today | `--days 14` |
| `--upcoming` | Next 30 days only | `--upcoming` |
| `--type`, `-t` | Event type filter | `--type festival` |
| `--limit`, `-l` | Max results (default: 10) | `--limit 10` |
| `--json`, `-j` | Raw JSON output | `--json` |
| `--states` | State breakdown view | `--states` |
| `--lat` | Latitude for radius search | `--lat 36.16` |
| `--lng` | Longitude for radius search | `--lng -86.78` |
| `--radius` | Search radius in miles (requires --lat/--lng or --city) | `--radius 50` |
| `--distance-sort` | Sort results by distance closest-first | `--distance-sort` |

## Event types
- `concert` — Regular live show
- `festival` — Multi-band festival event
- `church_service` — Church performance
- `workshop` — Workshop/masterclass

## Common use cases
1. **Find local concerts**: `grassgigs --state <CODE> --days 7`
2. **Festival hunting**: `grassgigs --upcoming --type festival`
3. **Band tracking**: `grassgigs --band "<name>"`
4. **Radius search**: `grassgigs --city "<city>" --radius <mi>`
5. **JSON for automation**: Add `--json` flag

## Error handling
- Network errors: script exits with error message to stderr
- Empty results: prints "No concerts found matching your criteria"
- Radius search with bad city: exits with clear error suggesting `--lat`/`--lng` alternative
- Progress output goes to stderr, clean results go to stdout (good for piping)

## Pitfalls
- **`band` field is either string OR list**: The API returns a string for single-band events but a list of dicts for multi-band events. Never assume `band` is always a string — use `isinstance(band, list)` guard before accessing `.name` attribute.
- **State field is two-letter abbreviation**: The `state` field in event objects returns "VA", "NC", etc. NOT "Virginia" or "North Carolina". When cross-referencing with state names, use a lookup table or abbreviate accordingly.
- **Progress output goes to stderr**: The CLI prints progress/emoji to stderr and data to stdout. If parsing output, capture stdout only — stderr will contain human-readable progress indicators.

## Reference
- `references/api-reference.md` — Full API endpoint schema, request/response types, and the `band` field type quirk

## Repository
- **GitHub**: `https://github.com/rmkraus/grassgigs-cli`
- **License**: MIT
