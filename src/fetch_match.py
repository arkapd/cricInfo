import os
import json
import argparse
import sys
import datetime
import requests
from dotenv import load_dotenv

# Try importing pycricbuzz
try:
    from pycricbuzz import Cricbuzz
    PYCRICBUZZ_AVAILABLE = True
except ImportError:
    PYCRICBUZZ_AVAILABLE = False

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env'))

CRICAPI_KEY = os.getenv('CRICAPI_KEY')

def get_cricapi_data(match_id=None):
    """Fetches data from CricAPI."""
    if not CRICAPI_KEY:
        print("Error: CRICAPI_KEY not found in .env file.")
        return None

    try:
        url = f"https://api.cricapi.com/v1/currentMatches?apikey={CRICAPI_KEY}&offset=0"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        # Retry once
        try:
            print("Timeout... retrying...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"CricAPI connection failed: {e}")
            return None
    except Exception as e:
        print(f"CricAPI error: {e}")
        try:
             print(f"Raw response: {response.text}")
        except:
             pass
        return None

def parse_cricapi_match(match_data, score_data=None):
    """Parses a single match object from CricAPI response into our schema."""
    
    # Extract basic info
    teams_list = match_data.get('teams', [])
    teams_str = " vs ".join(teams_list) if teams_list else match_data.get('name', 'Unknown Match')
    
    match_status = match_data.get('status', '')
    is_completed = match_data.get('matchEnded', False)
    status_enum = 'completed' if is_completed else 'live'
    if 'innings break' in match_status.lower():
        status_enum = 'innings_break'

    # Determine Inning and Score
    # CricAPI 'score' field is often a list of innings.
    # We need to find the current inning.
    scores = match_data.get('score', [])
    current_inning_obj = None
    
    if scores:
        current_inning_obj = scores[-1] # Assume last one is current
    
    runs = 0
    wickets = 0
    overs = 0.0
    
    if current_inning_obj:
        runs = current_inning_obj.get('r', 0)
        wickets = current_inning_obj.get('w', 0)
        overs = current_inning_obj.get('o', 0.0)
    
    # Calculate rates
    run_rate = 0.0
    if overs > 0:
        # Convert overs (e.g. 10.2) to balls
        over_part = int(overs)
        ball_part = int(round((overs - over_part) * 10))
        total_balls = over_part * 6 + ball_part
        if total_balls > 0:
            run_rate = round((runs / total_balls) * 6, 2)
    
    # Match Phase logic
    match_type = match_data.get('matchType', 'unknown').lower()
    phase = "middle_overs"
    if 't20' in match_type:
        if overs < 6: phase = "powerplay"
        elif overs > 15: phase = "death_overs"
    elif 'odi' in match_type:
        if overs < 10: phase = "powerplay"
        elif overs > 40: phase = "death_overs"
    
    # Output Schema
    output = {
        "match": {
            "id": match_data.get('id'),
            "teams": teams_str,
            "format": match_type.upper(),
            "venue": match_data.get('venue'),
            "innings": len(scores) if scores else 1,
            "target": None, # complex to calculate without full scorecard
            "toss": match_data.get('tossWinner', '') + " chose to " + match_data.get('tossChoice', ''),
            "status": status_enum
        },
        "score": {
            "runs": runs,
            "wickets": wickets,
            "overs": overs,
            "run_rate": run_rate,
            "required_rate": None
        },
        "current_batter": {
            "name": "Data Not Available", # CricAPI list endpoint doesn't give ball-by-ball batter stats usually requires `match_info` endpoint
            "runs": 0,
            "balls": 0,
            "strike_rate": 0.0,
            "fours": 0,
            "sixes": 0
        },
        "non_striker": {
            "name": "Data Not Available",
            "runs": 0,
            "balls": 0,
            "strike_rate": 0.0
        },
        "current_bowler": {
            "name": "Data Not Available",
            "overs": 0.0,
            "runs_conceded": 0,
            "wickets": 0,
            "economy": 0.0,
            "maidens": 0
        },
        "partnership": {
            "runs": 0, 
            "balls": 0,
            "batter1": None,
            "batter2": None
        },
        "match_phase": phase,
        "last_5_overs": {
            "runs": 0,
            "wickets": 0
        },
        "recent_wickets": [],
        "fetched_at": datetime.datetime.now().isoformat()
    }
    
    return output

def run_cricbuzz_fallback():
    """Fallback to pycricbuzz if available."""
    if not PYCRICBUZZ_AVAILABLE:
        print("PyCricbuzz not installed. Cannot use fallback.")
        return None
    
    try:
        print("Connecting to Cricbuzz...")
        c = Cricbuzz()
        matches = c.matches()
    except Exception as e:
        print(f"Cricbuzz connection failed: {e}")
        return None
    
    # Filter live matches
    live_matches = [m for m in matches if m['mchstate'] == 'inprogress']
    
    if not live_matches:
        print("No live matches found on Cricbuzz.")
        return None
        
    # TODO: Implement full parsing for Cricbuzz
    # For now, just taking the first one to demonstrate structure
    match = live_matches[0]
    mid = match['id']
    score = c.livescore(mid)
    
    # Construct a similar object (Simplified for this exercise as parsing cricbuzz is complex)
    # This is a placeholder for actual robust cricbuzz parsing
    output = {
        "match": {
            "id": mid,
            "teams": f"{match['team1']['name']} vs {match['team2']['name']}",
            "format": match['type'].upper(),
            "venue": match['venue_name'],
            "innings": 1,
            "target": None,
            "toss": match.get('toss', ''),
            "status": "live"
        },
        "score": {
            "runs": int(score['batting']['score'][0]['runs']),
            "wickets": int(score['batting']['score'][0]['wickets']),
            "overs": float(score['batting']['score'][0]['overs']),
            "run_rate": 0.0,
            "required_rate": None
        },
        # Fill generic data to respect schema
        "current_batter": {"name": "N/A", "runs": 0, "balls": 0, "strike_rate": 0, "fours": 0, "sixes": 0},
        "non_striker": {"name": "N/A", "runs": 0, "balls": 0, "strike_rate": 0},
        "current_bowler": {"name": "N/A", "overs": 0, "runs_conceded": 0, "wickets": 0, "economy": 0, "maidens": 0},
        "partnership": {"runs": 0, "balls": 0, "batter1": "", "batter2": ""},
        "match_phase": "middle_overs",
        "last_5_overs": {"runs": 0, "wickets": 0},
        "recent_wickets": [],
        "fetched_at": datetime.datetime.now().isoformat()
    }
    return output

def main():
    parser = argparse.ArgumentParser(description="Fetch live cricket match data.")
    parser.add_argument('--match-id', type=str, help="Specific match ID to fetch")
    parser.add_argument('--test', action='store_true', help="Use local sample data for testing")
    args = parser.parse_args()

    data_source = None
    
    if args.test:
        print("Running in TEST mode using sample data...")
        sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'evals', 'sample_match_states', 'sample_cricapi_response.json')
        if os.path.exists(sample_path):
            with open(sample_path, 'r') as f:
                data_source = json.load(f)
        else:
            print(f"Sample file not found at {sample_path}")
            sys.exit(1)
    else:
        # Live Fetch
        data_source = get_cricapi_data()
        
        if not data_source or data_source.get('status') != 'success':
            print("CricAPI unavailable or returned error. Switching to Cricbuzz fallback...")
            match_data = run_cricbuzz_fallback()
            if match_data:
                 with open("match_state.json", "w") as f:
                    json.dump(match_data, f, indent=2)
                 print(f"✓ {match_data['match']['teams']} {match_data['score']['runs']}/{match_data['score']['wickets']} ({match_data['score']['overs']} ov)")
                 return
            else:
                 print("Both APIs failed.")
                 sys.exit(1)

    # Process CricAPI data
    if not data_source or 'data' not in data_source:
        print("No match data found.")
        sys.exit(1)

    matches = [m for m in data_source['data'] if m.get('matchStarted') and not m.get('matchEnded')]

    if not matches:
        print("No live cricket matches right now.")
        sys.exit(0)

    selected_match = None
    if len(matches) == 1:
        selected_match = matches[0]
    elif args.match_id:
        selected_match = next((m for m in matches if m['id'] == args.match_id), None)
        if not selected_match:
            print(f"Match ID {args.match_id} not found in live matches.")
            sys.exit(1)
    else:
        print("Multiple live matches found:")
        for i, m in enumerate(matches):
            print(f"{i+1}. {m.get('name')} ({m.get('matchType', '').upper()})")
        
        # In a real interactive script we'd ask input, but for automation/simplicity we assume 1st or require arg if strictly automated
        # For now, let's select the first one if not specified to avoid blocking
        print("Auto-selecting first match (use --match-id to specify otherwise).")
        selected_match = matches[0]

    processed_data = parse_cricapi_match(selected_match)
    
    # Save to file
    with open("match_state.json", "w") as f:
        json.dump(processed_data, f, indent=2)

    # Summary
    score = processed_data['score']
    match = processed_data['match']
    print(f"[OK] {match['teams']} {score['runs']}/{score['wickets']} ({score['overs']} ov)")

if __name__ == "__main__":
    main()
