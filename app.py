#!/usr/bin/env python3
import os
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ─── Utility Functions ─────────────────────────────────────────────────────

def parse_salary(salary):
    """
    Converts '$13,250,000' to 13250000.0, leaves numbers untouched.
    """
    if isinstance(salary, (int, float)):
        return float(salary)
    if not salary:
        return 0.0
    # strip out dollar signs, commas, spaces
    return float(salary.replace('$', '').replace(',', '').replace(' ', ''))

def parse_team(team_str):
    """
    Player JSON is stored as e.g. 'TOR, C'; return 'TOR' to match team codes.
    """
    return team_str.split(',')[0].strip() if team_str else ''

def clean_team_code(team_code):
    """
    If the team code is doubled (e.g. 'VGKVGK'), return only the first half.
    """
    if team_code:
        length = len(team_code)
        half = length // 2
        if length % 2 == 0 and team_code[:half] == team_code[half:]:
            return team_code[:half]
    return team_code

# ─── Load & Shape Data ──────────────────────────────────────────────────────

def load_players():
    """
    Loads all_contracts.json into a dict: { player_name: {team, salary, contract_breakdown} }
    """
    base = os.path.dirname(__file__)
    path = os.path.join(base, "all_contracts.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_teams():
    """
    Loads nhl_team_caps.json, normalizes the relevant columns, and
    returns a dict: { TEAM_CODE: { active_cap, cap_space, total_cap } }
    """
    base = os.path.dirname(__file__)
    path = os.path.join(base, "nhl_team_caps.json")
    with open(path, encoding="utf-8") as f:
        team_list = json.load(f)

    teams = {}
    for info in team_list:
        raw = info.get("Team", "")
        code = clean_team_code(raw)

        teams[code] = {
            # These keys must match exactly what's in your JSON:
            "active_cap": parse_salary(info.get("Active",                 "0")),
            "cap_space":  parse_salary(info.get("Cap SpaceAll",            "0")),
            "total_cap":  parse_salary(info.get("Total CapAllocations",    "0")),
        }
    return teams

players_data = load_players()
teams_data   = load_teams()

# ─── Contract Helpers ───────────────────────────────────────────────────────

CUR_SEASON = 2024  # adjust as needed for the current NHL season start

def get_current_season_salary(player):
    """
    From the player's contract_breakdown, find the row where Year starts
    with the current season (e.g. '2024-25') and return its Cap HitAnnual.
    Fallback to the first row if no exact match.
    """
    breakdown = player.get("contract_breakdown", [])
    for row in breakdown:
        if row.get("Year", "").startswith(str(CUR_SEASON)):
            return parse_salary(row.get("Cap HitAnnual", "0"))
    # fallback
    if breakdown:
        return parse_salary(breakdown[0].get("Cap HitAnnual", "0"))
    return 0.0

def parse_start_year(year_range):
    """Given '2027-28', return 2027 (int)."""
    try:
        return int(year_range.split('-')[0])
    except:
        return None

def get_contract_summary(player_data, current_season_start=CUR_SEASON):
    """
    Returns:
      - years_left: seasons remaining (final_start_year - current_season_start)
      - contract_expires: e.g. '2027-28'
      - cap_hit_final_year: the Cap HitAnnual of that final season
    """
    breakdown = player_data.get("contract_breakdown", [])
    # Filter out rows with no valid Cap HitAnnual
    valid = [
        row for row in breakdown
        if (cap := row.get("Cap HitAnnual", "")) and cap not in ("UFA","RFA")
    ]
    if not valid:
        return {"years_left": 0, "contract_expires": None, "cap_hit_final_year": None}

    final = valid[-1]
    final_season = final.get("Year", "")
    final_cap    = final.get("Cap HitAnnual", "")

    start_year = parse_start_year(final_season)
    if start_year is None:
        years_left = 0
    else:
        years_left = max(0, start_year - current_season_start)

    return {
        "years_left": years_left,
        "contract_expires": final_season,
        "cap_hit_final_year": final_cap
    }

# ─── Core Simulation Logic ─────────────────────────────────────────────────

def simulate_trade(player_a, player_b, teams, league_cap=95500000.0):
    """
    Given two player dicts and the teams_data map, swap each player's
    current-season cap hit and compute before/after Active Cap,
    Cap Space, Total Cap, and compliance.
    """
    # 1) Pull out team codes & current-season salaries
    team_a = parse_team(player_a.get("team", ""))
    team_b = parse_team(player_b.get("team", ""))
    sal_a  = get_current_season_salary(player_a)
    sal_b  = get_current_season_salary(player_b)

    # 2) Lookup each team's before state
    a_before = teams.get(team_a, {})
    b_before = teams.get(team_b, {})

    active_a_b = a_before.get("active_cap",   0.0)
    active_b_b = b_before.get("active_cap",   0.0)
    # (we recompute cap_space from league_cap always)
    capsp_a_b = league_cap - active_a_b
    capsp_b_b = league_cap - active_b_b
    total_a_b = a_before.get("total_cap",    0.0)
    total_b_b = b_before.get("total_cap",    0.0)

    # 3) After swap
    active_a_a = active_a_b - sal_a + sal_b
    active_b_a = active_b_b - sal_b + sal_a

    capsp_a_a = league_cap - active_a_a
    capsp_b_a = league_cap - active_b_a

    total_a_a = total_a_b + (active_a_a - active_a_b)
    total_b_a = total_b_b + (active_b_a - active_b_b)

    return {
        "team_a": {
            "team":               team_a,
            "active_cap_before":  active_a_b,
            "cap_space_before":   capsp_a_b,
            "total_cap_before":   total_a_b,
            "active_cap_after":   active_a_a,
            "cap_space_after":    capsp_a_a,
            "total_cap_after":    total_a_a,
            "cap_compliant":      (active_a_a <= league_cap)
        },
        "team_b": {
            "team":               team_b,
            "active_cap_before":  active_b_b,
            "cap_space_before":   capsp_b_b,
            "total_cap_before":   total_b_b,
            "active_cap_after":   active_b_a,
            "cap_space_after":    capsp_b_a,
            "total_cap_after":    total_b_a,
            "cap_compliant":      (active_b_a <= league_cap)
        }
    }

# ─── Flask Endpoints ───────────────────────────────────────────────────────

@app.route('/')
def index():
    """Render the main dropdown page."""
    names = sorted(players_data.keys())
    return render_template('index.html', player_names=names)

@app.route('/player_details')
def player_details():
    """AJAX endpoint: ?player=Name → contract summary JSON."""
    name = request.args.get("player", "")
    if not name or name not in players_data:
        return jsonify({"error": "Invalid or missing player name"}), 400
    summary = get_contract_summary(players_data[name])
    return jsonify(summary)

@app.route('/simulate_trade', methods=['POST'])
def simulate_trade_api():
    """AJAX POST {player_a,player_b} → simulation JSON."""
    try:
        data = request.get_json(force=True)
        a = data.get("player_a", "")
        b = data.get("player_b", "")
        if not a or not b:
            return jsonify({"error": "Both players must be selected."}), 400
        if a not in players_data or b not in players_data:
            return jsonify({"error": "Invalid player selection."}), 400

        result = simulate_trade(
            players_data[a],
            players_data[b],
            teams_data,
            league_cap=95500000.0
        )
        return jsonify(result)

    except Exception as e:
        app.logger.exception("Error in /simulate_trade")
        return jsonify({"error": str(e)}), 500

# ─── Entry Point ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True)
