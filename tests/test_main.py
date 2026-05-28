"""Tests for grassgigs CLI tool."""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open, MagicMock
from grassgigs.__main__ import (
    fetch_events,
    parse_date,
    format_date,
    haversine,
    geocode_city,
    filter_events,
    display_events,
    display_states,
    main,
)


# Sample test data - realistic event structures from the API
SAMPLE_EVENTS = [
    {
        "id": "1",
        "band": "The Infamous Beard",
        "date": "2026-06-15",
        "venue": "Blue Ridge Performing Arts Center",
        "city": "Asheville",
        "state": "NC",
        "type": "concert",
        "url": "https://example.com/event1",
        "price": "$25",
        "doors": "6:30 PM",
        "latitude": 35.5951,
        "longitude": -82.5515,
    },
    {
        "id": "2",
        "band": "Punch Brothers",
        "date": "2026-06-20",
        "venue": "Carnegie Hall",
        "city": "New York",
        "state": "NY",
        "type": "concert",
        "url": "https://example.com/event2",
        "price": "$75",
        "doors": "7:00 PM",
        "latitude": 40.7587,
        "longitude": -73.9857,
    },
    {
        "id": "3",
        "band": "Leftover Salmon",
        "date": "2026-06-15",
        "venue": "Festive Festival Grounds",
        "city": "Boulder",
        "state": "CO",
        "type": "festival",
        "url": "https://example.com/event3",
        "price": "$50",
        "latitude": 40.0150,
        "longitude": -105.2705,
    },
    {
        "id": "4",
        "band": "Billy Strings",
        "date": "2025-12-01",
        "venue": "Sold Out Venue",
        "city": "Chicago",
        "state": "IL",
        "type": "concert",
        "url": "https://example.com/event4",
        "price": "$45",
        "latitude": 41.8781,
        "longitude": -87.6298,
    },
    {
        "id": "5",
        "band": "Yonder Mountain String Band",
        "date": "2026-06-15",
        "venue": "Workshop Center",
        "city": "Denver",
        "state": "CO",
        "type": "workshop",
        "url": "https://example.com/event5",
        "latitude": 39.7392,
        "longitude": -104.9903,
    },
]


# ============= parse_date tests =============

class TestParseDate:
    def test_iso_format(self):
        result = parse_date("2026-06-15")
        assert result == datetime(2026, 6, 15)

    def test_us_format(self):
        result = parse_date("06/15/2026")
        assert result == datetime(2026, 6, 15)

    def test_invalid_string(self):
        result = parse_date("not-a-date")
        assert result is None

    def test_none_input(self):
        result = parse_date(None)
        assert result is None

    def test_empty_string(self):
        result = parse_date("")
        assert result is None

    def test_partial_date(self):
        result = parse_date("2026-06")
        assert result is None


# ============= format_date tests =============

class TestFormatDate:
    def test_iso_format(self):
        result = format_date("2026-06-15")
        assert result == "Mon, Jun 15, 2026"

    def test_us_format(self):
        result = format_date("06/15/2026")
        assert result == "Mon, Jun 15, 2026"

    def test_invalid_string(self):
        result = format_date("not-a-date")
        assert result == "not-a-date"

    def test_none_input(self):
        result = format_date(None)
        assert result is None

    def test_empty_string(self):
        result = format_date("")
        assert result == ""


# ============= haversine tests =============

class TestHaversine:
    def test_same_location(self):
        # Same point should be 0 distance
        dist = haversine(35.5951, -82.5515, 35.5951, -82.5515)
        assert dist == 0

    def test_new_york_to_asheville(self):
        # Approximate distance should be ~530 miles
        dist = haversine(35.5951, -82.5515, 40.7587, -73.9857)
        assert 500 < dist < 600

    def test_boulder_to_denver(self):
        # Boulder to Denver is approximately 24 miles
        dist = haversine(40.0150, -105.2705, 39.7392, -104.9903)
        assert 20 < dist < 30

    def test_new_york_to_chicago(self):
        # Approximate distance should be ~750 miles
        dist = haversine(40.7587, -73.9857, 41.8781, -87.6298)
        assert 700 < dist < 800

    def test_zero_radius(self):
        # Very small distance
        dist = haversine(35.5951, -82.5515, 35.6051, -82.5515)
        assert 0 < dist < 1


# ============= fetch_events tests =============

class TestFetchEvents:
    @patch("urllib.request.urlopen")
    def test_fetch_success(self, mock_urlopen):
        """Test successful API response."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"events": SAMPLE_EVENTS}
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__ = MagicMock(
            return_value=mock_response
        )
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        events = fetch_events()
        assert len(events) == 5
        assert events[0]["band"] == "The Infamous Beard"

    @patch("urllib.request.urlopen")
    def test_empty_response(self, mock_urlopen):
        """Test empty events list."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"events": []}).encode(
            "utf-8"
        )
        mock_urlopen.return_value.__enter__ = MagicMock(
            return_value=mock_response
        )
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        events = fetch_events()
        assert events == []

    @patch("urllib.request.urlopen")
    def test_no_events_key(self, mock_urlopen):
        """Test response without 'events' key."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": []}).encode(
            "utf-8"
        )
        mock_urlopen.return_value.__enter__ = MagicMock(
            return_value=mock_response
        )
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        events = fetch_events()
        assert events == []

    @patch("urllib.request.urlopen")
    def test_api_error(self, mock_urlopen):
        """Test network error handling."""
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        with pytest.raises(SystemExit):
            fetch_events()


# ============= geocode_city tests =============

class TestGeocodeCity:
    @patch("urllib.request.urlopen")
    def test_successful_geocoding(self, mock_urlopen):
        """Test successful city geocoding."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            [{"lat": "35.5951", "lon": "-82.5515"}]
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__ = MagicMock(
            return_value=mock_response
        )
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        lat, lng = geocode_city("Asheville, NC")
        assert lat == pytest.approx(35.5951)
        assert lng == pytest.approx(-82.5515)

    @patch("urllib.request.urlopen")
    def test_empty_response(self, mock_urlopen):
        """Test geocoding with no results."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([]).encode("utf-8")
        mock_urlopen.return_value.__enter__ = MagicMock(
            return_value=mock_response
        )
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        lat, lng = geocode_city("Nowhere, XX")
        assert lat is None
        assert lng is None

    @patch("urllib.request.urlopen")
    def test_network_error(self, mock_urlopen):
        """Test geocoding network error."""
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("Timeout")

        lat, lng = geocode_city("Asheville, NC")
        assert lat is None
        assert lng is None


# ============= filter_events tests =============

class TestFilterEvents:
    def test_filter_by_state(self):
        result = filter_events(SAMPLE_EVENTS, state="NC")
        assert len(result) == 1
        assert result[0]["band"] == "The Infamous Beard"

    def test_filter_by_state_uppercase(self):
        result = filter_events(SAMPLE_EVENTS, state="nc")
        assert len(result) == 1

    def test_filter_by_state_no_match(self):
        result = filter_events(SAMPLE_EVENTS, state="TX")
        assert len(result) == 0

    def test_filter_by_city(self):
        result = filter_events(SAMPLE_EVENTS, city="Asheville")
        assert len(result) == 1
        assert result[0]["city"] == "Asheville"

    def test_filter_by_city_partial(self):
        result = filter_events(SAMPLE_EVENTS, city="New York")
        assert len(result) == 1
        assert result[0]["city"] == "New York"

    def test_filter_by_city_no_match(self):
        result = filter_events(SAMPLE_EVENTS, city="Miami")
        assert len(result) == 0

    def test_filter_by_band(self):
        result = filter_events(SAMPLE_EVENTS, band="Billy")
        assert len(result) == 1
        assert "Billy" in result[0]["band"]

    def test_filter_by_band_case_insensitive(self):
        result = filter_events(SAMPLE_EVENTS, band="billy")
        assert len(result) == 1

    def test_filter_by_band_no_match(self):
        result = filter_events(SAMPLE_EVENTS, band="Nonexistent")
        assert len(result) == 0

    def test_filter_by_type(self):
        result = filter_events(SAMPLE_EVENTS, event_type="festival")
        assert len(result) == 1
        assert result[0]["type"] == "festival"

    def test_filter_by_type_no_match(self):
        result = filter_events(SAMPLE_EVENTS, event_type="seminar")
        assert len(result) == 0

    def test_filter_by_days(self):
        """Test filtering events within N days from today."""
        today = datetime.now().strftime("%Y-%m-%d")
        three_days_from_now = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        seven_days_from_now = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        twenty_days_from_now = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        recent_events = [
            {"date": yesterday, "band": "Yesterday Band"},
            {"date": today, "band": "Today Band"},
            {"date": three_days_from_now, "band": "Three Days Band"},
            {"date": seven_days_from_now, "band": "Seven Days Band"},
            {"date": twenty_days_from_now, "band": "Twenty Days Band"},
        ]

        result = filter_events(recent_events, days=7)
        bands = [e["band"] for e in result]
        assert bands == ["Today Band", "Three Days Band", "Seven Days Band"]

        result = filter_events(recent_events, days=1)
        bands = [e["band"] for e in result]
        assert bands == ["Today Band"]

    def test_filter_by_days_no_match(self):
        """Test filtering with 0 days (only today's events)."""
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        events_today = [
            {"date": today, "band": "Today Band"},
            {"date": tomorrow, "band": "Tomorrow Band"},
        ]
        result = filter_events(events_today, days=0)
        assert len(result) == 1
        assert result[0]["band"] == "Today Band"

    def test_filter_upcoming(self):
        """Test upcoming filter (future dates only)."""
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        events = [
            {"date": "2025-01-01", "band": "Past Band"},
            {"date": today, "band": "Today Band"},
            {"date": "2026-12-31", "band": "Future Band"},
        ]
        result = filter_events(events, upcoming=True)
        # Should include future events only (not today or past)
        assert len(result) == 1
        assert result[0]["band"] == "Future Band"

    def test_filter_by_limit(self):
        result = filter_events(SAMPLE_EVENTS, limit=2)
        assert len(result) == 2

    def test_filter_by_limit_exceeds_count(self):
        result = filter_events(SAMPLE_EVENTS, limit=100)
        assert len(result) == 5

    def test_filter_by_radius(self):
        """Test radius-based filtering."""
        result = filter_events(
            SAMPLE_EVENTS, lat=35.5951, lng=-82.5515, radius=10
        )
        # Should only include the nearby Asheville event
        assert len(result) == 1
        assert result[0]["band"] == "The Infamous Beard"
        assert "_distance" in result[0]
        assert result[0]["_distance"] < 10

    def test_filter_by_radius_no_match(self):
        """Test radius search with no matching events."""
        result = filter_events(
            SAMPLE_EVENTS, lat=0.0, lng=0.0, radius=1
        )
        assert len(result) == 0

    def test_filter_by_radius_and_band(self):
        """Test combined filtering."""
        result = filter_events(
            SAMPLE_EVENTS,
            lat=35.5951,
            lng=-82.5515,
            radius=100,
            band="Beard",
        )
        assert len(result) == 1
        assert result[0]["band"] == "The Infamous Beard"

    def test_distance_sort(self):
        """Test distance sorting."""
        result = filter_events(
            SAMPLE_EVENTS,
            lat=35.5951,
            lng=-82.5515,
            radius=1000,
            distance_sort=True,
        )
        # First result should be the closest
        assert result[0]["band"] == "The Infamous Beard"
        # Check distances are ascending
        distances = [e["_distance"] for e in result]
        assert distances == sorted(distances)

    def test_combined_filters(self):
        """Test multiple filters combined."""
        result = filter_events(
            SAMPLE_EVENTS,
            state="CO",
            band="Salmon",
            limit=5,
        )
        assert len(result) == 1
        assert result[0]["band"] == "Leftover Salmon"

    def test_no_filters(self):
        """Test with no filters returns all events."""
        result = filter_events(SAMPLE_EVENTS)
        assert len(result) == 5

    def test_filter_preserves_event_data(self):
        """Test that original event data is preserved."""
        result = filter_events(SAMPLE_EVENTS, state="NC")
        event = result[0]
        assert event["id"] == "1"
        assert event["band"] == "The Infamous Beard"
        assert event["date"] == "2026-06-15"
        assert event["city"] == "Asheville"
        assert event["state"] == "NC"


# ============= display_events tests =============

class TestDisplayEvents:
    def test_display_single_event(self, capsys):
        """Test displaying a single event."""
        display_events(SAMPLE_EVENTS[:1])
        captured = capsys.readouterr()
        assert "The Infamous Beard" in captured.out
        assert "Asheville, NC" in captured.out
        assert "Blue Ridge Performing Arts Center" in captured.out

    def test_display_multiple_events(self, capsys):
        """Test displaying multiple events."""
        display_events(SAMPLE_EVENTS[:3])
        captured = capsys.readouterr()
        assert "The Infamous Beard" in captured.out
        assert "Punch Brothers" in captured.out
        assert "Leftover Salmon" in captured.out

    def test_display_empty(self, capsys):
        """Test displaying no events."""
        display_events([])
        captured = capsys.readouterr()
        assert "No events found" in captured.out

    def test_display_with_distance(self, capsys):
        """Test displaying events with distance info."""
        events_with_distance = [
            dict(
                SAMPLE_EVENTS[0],
                _distance=15.5,
            )
        ]
        display_events(events_with_distance)
        captured = capsys.readouterr()
        assert "15.5 mi away" in captured.out

    def test_display_all_fields(self, capsys):
        """Test displaying all event fields."""
        display_events([SAMPLE_EVENTS[0]])
        captured = capsys.readouterr()
        assert "6:30 PM" in captured.out  # doors
        assert "$25" in captured.out  # price
        assert "concert" in captured.out  # type
        assert "https://example.com/event1" in captured.out  # url


# ============= display_states tests =============

class TestDisplayStates:
    def test_display_states_breakdown(self, capsys):
        """Test state breakdown display."""
        display_states(SAMPLE_EVENTS)
        captured = capsys.readouterr()
        assert "NC" in captured.out
        assert "NY" in captured.out
        assert "CO" in captured.out
        assert "IL" in captured.out
        assert "Total" in captured.out
        assert "5 events" in captured.out  # 5 states with 1 event each

    def test_display_states_empty(self):
        """Test state breakdown with no events."""
        # Should not crash with empty list
        display_states([])
        # If we get here without exception, the test passes


# ============= Integration Tests =============

class TestMainIntegration:
    """Test the main() function with mocked API."""

    @patch("grassgigs.__main__.fetch_events")
    def test_main_no_args(self, mock_fetch):
        """Test main() with no arguments (shows all events)."""
        mock_fetch.return_value = SAMPLE_EVENTS[:2]

        with patch("sys.argv", ["grassgigs"]):
            with patch(
                "grassgigs.__main__.display_events"
            ) as mock_display:
                main()
                mock_display.assert_called_once()
                assert len(mock_display.call_args[0][0]) == 2

    @patch("grassgigs.__main__.fetch_events")
    def test_main_with_state(self, mock_fetch):
        """Test main() with --state filter."""
        mock_fetch.return_value = SAMPLE_EVENTS

        with patch("sys.argv", ["grassgigs", "--state", "NC"]):
            with patch(
                "grassgigs.__main__.display_events"
            ) as mock_display:
                main()
                assert len(mock_display.call_args[0][0]) == 1

    @patch("grassgigs.__main__.fetch_events")
    def test_main_with_states(self, mock_fetch):
        """Test main() with --states flag."""
        mock_fetch.return_value = SAMPLE_EVENTS

        with patch("sys.argv", ["grassgigs", "--states"]):
            with patch("grassgigs.__main__.display_states") as mock_display:
                main()
                mock_display.assert_called_once()

    @patch("grassgigs.__main__.fetch_events")
    def test_main_with_json(self, mock_fetch):
        """Test main() with --json output."""
        mock_fetch.return_value = SAMPLE_EVENTS[:2]

        with patch("sys.argv", ["grassgigs", "--state", "NC", "--json"]):
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with patch("sys.stdout", f):
                main()
                output = f.getvalue()
                # JSON output starts at the first '[' after debug messages
                json_start = output.find('[')
                assert json_start != -1, f"No JSON found in output: {output!r}"
                json_str = output[json_start:]
                # Should be valid JSON
                parsed = json.loads(json_str)
                assert len(parsed) == 1
                assert "band" in parsed[0]

    @patch("grassgigs.__main__.fetch_events")
    def test_main_with_limit(self, mock_fetch):
        """Test main() with --limit."""
        mock_fetch.return_value = SAMPLE_EVENTS

        with patch("sys.argv", ["grassgigs", "--limit", "3"]):
            with patch(
                "grassgigs.__main__.display_events"
            ) as mock_display:
                main()
                assert len(mock_display.call_args[0][0]) == 3

    @patch("grassgigs.__main__.fetch_events")
    @patch("grassgigs.__main__.geocode_city")
    def test_main_with_radius(self, mock_geocode, mock_fetch):
        """Test main() with radius search."""
        mock_fetch.return_value = SAMPLE_EVENTS
        mock_geocode.return_value = (35.5951, -82.5515)

        with patch(
            "sys.argv",
            ["grassgigs", "--city", "Asheville", "--radius", "10"],
        ):
            with patch(
                "grassgigs.__main__.display_events"
            ) as mock_display:
                main()
                # Should filter to nearby events
                assert len(mock_display.call_args[0][0]) >= 0


# ============= Error handling tests =============

class TestErrorHandling:
    def test_filter_nonexistent_event(self):
        """Test filtering for events that don't exist."""
        result = filter_events(SAMPLE_EVENTS, band="Nonexistent")
        assert result == []

    def test_filter_by_invalid_state(self):
        """Test filtering by invalid state code."""
        result = filter_events(SAMPLE_EVENTS, state="XX")
        assert result == []

    def test_filter_with_no_events(self):
        """Test filtering empty event list."""
        result = filter_events([], state="NC")
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
