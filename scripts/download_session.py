#!/usr/bin/env python
"""
Session downloader CLI.

Downloads all data for a race session from OpenF1 and caches it locally
for offline replay and backtesting.

Usage:
    python scripts/download_session.py --year 2023 --round 1 --session Race
    python scripts/download_session.py --session-key 9158
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rsw.ingest import OpenF1Client


async def download_session(
    client: OpenF1Client,
    session_key: int,
    output_dir: Path,
) -> Path:
    """
    Download all data for a session.
    
    Returns path to saved JSON file.
    """
    print(f"\n📥 Downloading session {session_key}...")
    
    # Fetch all data
    print("  Fetching drivers...", end="", flush=True)
    drivers = await client.get_drivers(session_key)
    print(f" ✓ ({len(drivers)} drivers)")
    
    print("  Fetching laps...", end="", flush=True)
    laps = await client.get_laps(session_key)
    print(f" ✓ ({len(laps)} laps)")
    
    print("  Fetching stints...", end="", flush=True)
    stints = await client.get_stints(session_key)
    print(f" ✓ ({len(stints)} stints)")
    
    print("  Fetching pit stops...", end="", flush=True)
    pits = await client.get_pits(session_key)
    print(f" ✓ ({len(pits)} pits)")
    
    print("  Fetching race control...", end="", flush=True)
    race_control = await client.get_race_control(session_key)
    print(f" ✓ ({len(race_control)} messages)")
    
    # Get session info
    print("  Fetching session info...", end="", flush=True)
    sessions = await client.get_sessions(year=datetime.now().year)
    session_info = next((s for s in sessions if s.session_key == session_key), None)
    print(" ✓")
    
    # Build data structure
    data = {
        "session_key": session_key,
        "downloaded_at": datetime.utcnow().isoformat(),
        "session_info": {
            "session_name": session_info.session_name if session_info else "Unknown",
            "country_name": session_info.country_name if session_info else "Unknown",
            "circuit_short_name": session_info.circuit_short_name if session_info else "Unknown",
            "date_start": session_info.date_start.isoformat() if session_info else None,
        } if session_info else None,
        "drivers": [
            {
                "driver_number": d.driver_number,
                "name_acronym": d.name_acronym,
                "full_name": d.full_name,
                "team_name": d.team_name,
                "team_colour": d.team_colour,
            }
            for d in drivers
        ],
        "laps": [
            {
                "driver_number": l.driver_number,
                "lap_number": l.lap_number,
                "lap_duration": l.lap_duration,
                "sector_1_time": l.sector_1_time,
                "sector_2_time": l.sector_2_time,
                "sector_3_time": l.sector_3_time,
                "is_pit_out_lap": l.is_pit_out_lap,
            }
            for l in laps
        ],
        "stints": [
            {
                "driver_number": s.driver_number,
                "stint_number": s.stint_number,
                "compound": s.compound,
                "lap_start": s.lap_start,
                "lap_end": s.lap_end,
                "tyre_age_at_start": s.tyre_age_at_start,
            }
            for s in stints
        ],
        "pits": [
            {
                "driver_number": p.driver_number,
                "lap_number": p.lap_number,
                "pit_duration": p.pit_duration,
            }
            for p in pits
        ],
        "race_control": [
            {
                "lap_number": r.lap_number,
                "category": r.category,
                "flag": r.flag,
                "message": r.message,
            }
            for r in race_control
        ],
    }
    
    # Save to file
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{session_key}.json"
    
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    
    file_size = output_file.stat().st_size / 1024
    print(f"\n✅ Saved to {output_file} ({file_size:.1f} KB)")
    
    return output_file


async def find_session_key(
    client: OpenF1Client,
    year: int,
    round_num: int | None,
    session_type: str,
) -> int | None:
    """Find session key by year, round, and session type."""
    print(f"\n🔍 Searching for {year} {session_type}...")
    
    sessions = await client.get_sessions(year=year)
    
    # Filter by session type
    matching = [s for s in sessions if s.session_name.lower() == session_type.lower()]
    
    if round_num:
        # Try to match by round order
        matching = sorted(matching, key=lambda s: s.date_start or datetime.min)
        if round_num <= len(matching):
            session = matching[round_num - 1]
            print(f"   Found: {session.country_name} - {session.session_name}")
            return session.session_key
    elif matching:
        # Return first/latest
        session = matching[-1]
        print(f"   Found: {session.country_name} - {session.session_name}")
        return session.session_key
    
    return None


async def list_sessions(client: OpenF1Client, year: int) -> None:
    """List available sessions for a year."""
    print(f"\n📋 Sessions for {year}:")
    
    sessions = await client.get_sessions(year=year)
    races = [s for s in sessions if s.session_name == "Race"]
    
    for i, race in enumerate(sorted(races, key=lambda s: s.date_start or datetime.min), 1):
        print(f"   {i:2d}. {race.country_name} ({race.circuit_short_name}) - Key: {race.session_key}")
    
    print(f"\nTotal: {len(races)} races")


async def main():
    parser = argparse.ArgumentParser(description="Download F1 session data for replay")
    parser.add_argument("--session-key", type=int, help="Direct session key")
    parser.add_argument("--year", type=int, default=2023, help="Year (default: 2023)")
    parser.add_argument("--round", type=int, help="Round number")
    parser.add_argument("--session", type=str, default="Race", help="Session type (default: Race)")
    parser.add_argument("--list", action="store_true", help="List available sessions")
    parser.add_argument("--output", type=str, default="data/sessions", help="Output directory")
    
    args = parser.parse_args()
    
    output_dir = Path(__file__).parent.parent / args.output
    client = OpenF1Client()
    
    try:
        if args.list:
            await list_sessions(client, args.year)
            return
        
        # Get session key
        session_key = args.session_key
        if not session_key:
            session_key = await find_session_key(
                client, args.year, args.round, args.session
            )
        
        if not session_key:
            print("❌ Could not find session. Use --list to see available sessions.")
            return
        
        # Download
        await download_session(client, session_key, output_dir)
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
