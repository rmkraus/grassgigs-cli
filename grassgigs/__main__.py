#!/usr/bin/env python3
"""
grassgigs - Bluegrass & grassroots concert lookup CLI tool.

Queries the GrassGigs public API (AWS endpoint) to search concerts,
festivals, church services, and workshops across the US.

Usage:
    grassgigs --state NC --days 7 --limit 5
    grassgigs --band "Jerry Douglas" --limit 3
    grassgigs --upcoming --type festival --limit 5
    grassgigs --states              # list all states with event counts
    grassgigs --state VA --city "Richmond" --limit 10
    grassgigs --json --state PA --limit 20
    grassgigs --city "Nashville, TN" --radius 50 --days 14  # 50mi radius
    grassgigs --lat 36.1627 --lng -86.7816 --radius 25
    grassgigs --city "Asheville, NC" --radius 100 --distance-sort
"""

import argparse
import json
import math
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from collections import Counter

API_URL = "https://bmbn5a7v4c.execute-api.us-east-1.amazonaws.com/Prod/events"


def fetch_events():
    """Fetch all events from the GrassGigs API."""
    req = urllib.request.Request(
        API_URL,
        headers={"User-Agent": "grassgigs-cli/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("events", [])
    except urllib.error.URLError as e:
        print(f"Error: Failed to fetch events from API: {e}", file=sys.stderr)
        sys.exit(1)


def parse_date(date_str):
    """Parse event date string into a datetime object."""
    try:
        # Try multiple formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
    except (TypeError, AttributeError):
        pass
    return None


def format_date(date_str):
    """Format date string for display."""
    dt = parse_date(date_str)
    if dt:
        return dt.strftime("%a, %b %d, %Y")
    return date_str


def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on Earth (miles)."""
    R = 3958.8  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def geocode_city(city_name):
    """Look up lat/lng for a city name using OpenStreetMap Nominatim (free, no API key)."""
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(city_name)}&limit=1"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "grassgigs-cli/1.0 (github.com/rmkraus/grassgigs-cli)"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None


def filter_events(events, state=None, city=None, band=None, days=None,
                  event_type=None, upcoming=None, limit=None,
                  lat=None, lng=None, radius=None, distance_sort=False,
                  center_city=None):
    """Filter events based on search criteria."""
    filtered = events
    distances = {}

    if state:
        state = state.upper()
        filtered = [e for e in filtered if e.get("state", "").upper() == state]

    if city and lat is None and lng is None:
        city_lower = city.lower()
        filtered = [e for e in filtered if city_lower in e.get("city", "").lower()]

    if band:
        band_lower = band.lower()
        filtered = [e for e in filtered if band_lower in e.get("band", "").lower()]

    if event_type:
        filtered = [e for e in filtered if event_type in e.get("type", "")]

    if days:
        cutoff = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        filtered = [e for e in filtered if e.get("date", "") >= cutoff]

    if upcoming:
        today = datetime.now().strftime("%Y-%m-%d")
        filtered = [e for e in filtered if e.get("date", "") > today]

    # Radius search: requires lat/lng and radius in miles
    if lat is not None and lng is not None and radius:
        center_label = ""
        if center_city:
            center_label = f" ({center_city})"

        radius_events = []
        for e in filtered:
            elat = e.get("latitude")
            elng = e.get("longitude")
            if elat is not None and elng is not None:
                dist = haversine(lat, lng, float(elat), float(elng))
                if dist <= radius:
                    e["_distance"] = round(dist, 1)
                    radius_events.append(e)
                    distances[id(e)] = dist

        filtered = radius_events
        print(f"\n📍 Found {len(filtered)} events within {radius} miles{center_label}")
    else:
        print(f"\n🎵 Found {len(filtered)} event(s)")

    if distance_sort and filtered:
        filtered.sort(key=lambda e: e.get("_distance", 0))

    if limit:
        filtered = filtered[:limit]

    return filtered


def display_events(events, include_state=True):
    """Pretty-print a list of events."""
    if not events:
        print("No events found matching your criteria.")
        return

    print(f"\n🎵 Found {len(events)} event(s)\n" + "=" * 60)

    for i, event in enumerate(events, 1):
        band = event.get("band", "Unknown")
        date = format_date(event.get("date", ""))
        venue = event.get("venue", "TBA")
        city = event.get("city", "")
        state = event.get("state", "")
        event_type = event.get("type", "concert")
        url = event.get("url", "")
        price = event.get("price", "")
        doors = event.get("doors", "")
        distance = event.get("_distance", None)

        distance_str = f"  {distance} mi away" if distance is not None else ""

        print(f"\n{i}. {band}")
        print(f"   📅 {date}")
        print(f"   📍 {venue}")
        if city and state:
            print(f"   🗺️  {city}, {state}")
        elif city:
            print(f"   🗺️  {city}")
        if distance_str:
            print(f"   📏 {distance_str}")
        if doors:
            print(f"   🚪 Doors: {doors}")
        if price:
            print(f"   💰 {price}")
        print(f"   🎶 {event_type}")
        if url:
            print(f"   🔗 {url}")
        print()

    print("=" * 60)


def display_states(events):
    """Display event count breakdown by state."""
    if not events:
        print("\n🗺️  Event count by state (0 total events):\n")
        print("   No events to display.\n")
        return
    
    state_counts = Counter(e.get("state", "Unknown") for e in events)
    sorted_states = sorted(state_counts.items(), key=lambda x: x[1], reverse=True)

    total = sum(count for _, count in sorted_states)
    print(f"\n🗺️  Event count by state ({total} total events):\n")

    max_state = max(len(s) for s, _ in sorted_states)
    max_count = max(count for _, count in sorted_states)
    bar_width = 30

    for state, count in sorted_states:
        bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
        bar = "█" * bar_len
        print(f"   {state:<{max_state}} | {bar} {count:>4}  ({count/total*100:.1f}%)")

    print(f"\n   {'─' * (max_state + bar_width + 12)}")
    print(f"   Total: {total} events from {len(sorted_states)} states\n")


def main():
    parser = argparse.ArgumentParser(
        description="🎵 grassgigs - Bluegrass & grassroots concert lookup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --state NC --days 7 --limit 5        # Next 7 days in NC, 5 events
  %(prog)s --band "Jerry Douglas" --limit 3     # Shows by Jerry Douglas
  %(prog)s --upcoming --type festival --limit 5  # Festivals coming up
  %(prog)s --states                               # List states with counts
  %(prog)s --state VA --city "Richmond" --limit 10
  %(prog)s --json --state PA --limit 20          # JSON output
        """
    )

    parser.add_argument("--state", "-s", help="Filter by US state code (e.g., NC, VA, PA)")
    parser.add_argument("--city", "-c", help="Filter by city name")
    parser.add_argument("--band", "-b", help="Filter by band/artist name")
    parser.add_argument("--type", "-t", help="Filter by event type (concert, festival, church_service, workshop)")
    parser.add_argument("--days", "-d", type=int, help="Show events within N days from today")
    parser.add_argument("--upcoming", action="store_true", help="Show only upcoming events (future dates)")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Maximum number of events to return (default: 10)")
    parser.add_argument("--states", action="store_true", help="Show event count breakdown by state")
    parser.add_argument("--json", "-j", action="store_true", dest="json_output", help="Output in JSON format")
    parser.add_argument("--verbose", "-v", action="store_true", help="Include all event fields in JSON output")

    # Radius search args
    parser.add_argument("--lat", type=float, help="Latitude for radius search")
    parser.add_argument("--lng", type=float, help="Longitude for radius search")
    parser.add_argument("--radius", type=int, help="Search radius in miles (requires --lat/--lng or --city with --radius)")
    parser.add_argument("--distance-sort", action="store_true", help="Sort results by distance from center point")

    args = parser.parse_args()

    # Handle radius search geocoding
    lat = args.lat
    lng = args.lng
    center_city = None

    if args.radius and (lat is None or lng is None):
        if args.city:
            lat, lng = geocode_city(args.city)
            if lat is None:
                print(f"Error: Could not find coordinates for '{args.city}'. "
                      f"Try --lat and --lng directly, or a more specific city name.",
                      file=sys.stderr)
                sys.exit(1)
            center_city = args.city
        else:
            print("Error: --radius requires either --city or both --lat and --lng.",
                  file=sys.stderr)
            sys.exit(1)

    if args.radius and lat is not None and lng is not None and args.distance_sort:
        if not center_city and args.city:
            center_city = args.city
        elif not center_city:
            center_city = f"{lat:.2f},{lng:.2f}"

    # Fetch all events
    print("Fetching events from GrassGigs API...")
    events = fetch_events()
    print(f"Loaded {len(events)} events.\n")

    # Show states breakdown if requested
    if args.states:
        display_states(events)
        return

    # Filter events
    filtered = filter_events(
        events,
        state=args.state,
        city=args.city,
        band=args.band,
        days=args.days,
        event_type=args.type,
        upcoming=args.upcoming,
        limit=args.limit,
        lat=lat,
        lng=lng,
        radius=args.radius,
        distance_sort=args.distance_sort,
        center_city=center_city,
    )

    # Output
    if args.json_output:
        if args.verbose:
            print(json.dumps(filtered, indent=2))
        else:
            # Compact JSON with key fields
            compact = []
            for e in filtered:
                compact.append({
                    "band": e.get("band"),
                    "date": e.get("date"),
                    "venue": e.get("venue"),
                    "city": e.get("city"),
                    "state": e.get("state"),
                    "type": e.get("type"),
                    "url": e.get("url"),
                    "price": e.get("price"),
                })
            print(json.dumps(compact, indent=2))
    else:
        display_events(filtered)


if __name__ == "__main__":
    main()
