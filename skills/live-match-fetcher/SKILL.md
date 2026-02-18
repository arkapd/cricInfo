---
name: live-match-fetcher
description: >
  Fetches live cricket match data and outputs a standardized JSON snapshot of the
  current match state including batter, bowler, score, overs, run rate, match phase,
  and partnership details. Use this skill whenever you need to get real-time cricket
  match data, pull live scorecard information, or get the current state of a cricket
  match in progress. This is the data ingestion layer of the cricket bot.
---

# Live Match Fetcher

## What This Skill Does

Connects to a live cricket data source, fetches the current match state, and
outputs a standardized JSON file (`match_state.json`) that all downstream skills
consume. It is the single source of truth for "what is happening right now in
the match."

## Data Sources (Free, No Cost)

### Primary: CricAPI Free Tier
- Endpoint: `https://api.cricapi.com/v1/currentMatches?apikey={KEY}`
- Free tier: 100 requests/day (enough for ~1 match at 60-second intervals)
- Returns: match list with live scores, batting/bowling cards
- API key stored in environment variable `CRICAPI_KEY`
- Sign up at: https://cricapi.com

### Fallback: Cricbuzz Scraping via pycricbuzz
- Library: `pycricbuzz` (pip install pycricbuzz)
- No API key needed — scrapes Cricbuzz live scorecard
- Less structured data, requires parsing
- Use ONLY if CricAPI is down or rate-limited

## Input

None. This skill initiates the pipeline. It may optionally accept a `--match-id`
argument to skip the match selection prompt.

## Output

A file called `match_state.json` saved in the project's working directory.

### Required Output Schema

```json
{
  "match": {
    "id": "string — unique match identifier from the API",
    "teams": "string — e.g. 'IND vs AUS'",
    "format": "string — one of: T20, ODI, Test",
    "venue": "string — ground name and city",
    "innings": "integer — 1 or 2 (or 3/4 for Tests)",
    "target": "integer or null — target score if 2nd innings, null if 1st",
    "toss": "string — who won toss and chose to bat/bowl",
    "status": "string — 'live', 'innings_break', 'completed'"
  },
  "score": {
    "runs": "integer",
    "wickets": "integer",
    "overs": "float — e.g. 34.2",
    "run_rate": "float — current run rate",
    "required_rate": "float or null — null if batting first"
  },
  "current_batter": {
    "name": "string — full name",
    "runs": "integer — runs scored in this innings",
    "balls": "integer — balls faced",
    "strike_rate": "float",
    "fours": "integer",
    "sixes": "integer"
  },
  "non_striker": {
    "name": "string",
    "runs": "integer",
    "balls": "integer",
    "strike_rate": "float"
  },
  "current_bowler": {
    "name": "string — full name",
    "overs": "float — overs bowled in this spell/innings",
    "runs_conceded": "integer",
    "wickets": "integer",
    "economy": "float",
    "maidens": "integer"
  },
  "partnership": {
    "runs": "integer",
    "balls": "integer",
    "batter1": "string",
    "batter2": "string"
  },
  "match_phase": "string — one of: powerplay, middle_overs, death_overs, session_1, session_2, session_3 (for Tests)",
  "last_5_overs": {
    "runs": "integer",
    "wickets": "integer"
  },
  "recent_wickets": [
    {
      "batter_name": "string",
      "runs": "integer",
      "bowler_name": "string",
      "how_out": "string"
    }
  ],
  "fetched_at": "string — ISO 8601 timestamp"
}
Behavior Requirements
1.	When the script starts, hit the CricAPI /currentMatches endpoint.
2.	Filter for matches where matchStarted is true and matchEnded is false.
3.	If no live matches found: print "No live cricket matches right now." and exit.
4.	If one live match: use it automatically.
5.	If multiple live matches: print a numbered list (e.g. "1. IND vs AUS — ODI, MCG") and let the user pick by entering a number.
6.	Parse the API response into the exact schema above. If a field is unavailable from the API, set it to null — never omit the key.
7.	Determine match_phase from overs: 0-6 = powerplay (limited overs), 6-35 = middle_overs, 35-50 = death_overs (ODI). For T20: 0-6 powerplay, 6-15 middle, 15-20 death. For Tests: use session time if available, otherwise set to null.
8.	Save output to match_state.json in the current working directory.
9.	Print a one-line summary: "✓ IND 187/3 (34.2 ov) — Kohli 67* | Starc 1/42 (7 ov)"
10.	If CricAPI fails (timeout, rate limit, error), automatically fall back to pycricbuzz. Print "CricAPI unavailable, using Cricbuzz fallback..."
11.	All API keys read from .env file using python-dotenv. Never hardcode keys.
Error Handling
•	Network timeout: Retry once after 3 seconds, then fail with clear message.
•	Invalid API key: Print "Invalid CricAPI key. Check your .env file." and exit.
•	Rate limit exceeded: Print "CricAPI daily limit reached. Switching to Cricbuzz..." and use fallback.
•	Malformed API response: Log the raw response to error_log.txt and exit with a message.
Testing
To test this skill without a live match, save a sample API response to evals/sample_match_states/sample_cricapi_response.json and add a --test flag that reads from this file instead of hitting the API.
