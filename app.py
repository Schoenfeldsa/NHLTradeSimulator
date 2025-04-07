from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

def parse_salary(salary_str):
    """Converts '$13,250,000' to 13250000.0."""
    if not salary_str:
        return 0.0
    return float(salary_str.replace('$', '').replace(',', ''))

def parse_team(team_str):
    """Player JSON is stored as 'TOR, C', return 'TOR' to match the team data. """
    return team_str.split(',')[0].strip()

def load_players():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, 'all_contracts.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

    
def clean_team_code(team_code):
    """If team_code is doubled for some reason, so return only the first half."""
    if team_code:
        length = len(team_code)
        if length % 2 == 0:
            half = length // 2
            if team_code[:half] == team_code[half:]:
                return team_code[:half]
    return team_code


def load_teams():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, 'nhl_team_caps.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        team_list = json.load(f)

    teams = {}
    for team_info in team_list:
        # Clean the team code
        raw_team_code = team_info.get("team", "")
        team_code = clean_team_code(raw_team_code)
        teams[team_code] = team_info
    return teams


def simulate_trade(player_a, player_b, teams, league_cap=88000000.0):
    # 1. Identify each player's team & salary
    team_a_code = parse_team(player_a["basic_info"]["team"])
    team_b_code = parse_team(player_b["basic_info"]["team"])
    salary_a = parse_salary(player_a["basic_info"]["salary"])
    salary_b = parse_salary(player_b["basic_info"]["salary"])

    # 2. Parse each team’s current data
    team_a_data = teams.get(team_a_code, {})
    team_b_data = teams.get(team_b_code, {})

    # Active Cap (Payroll) BEFORE
    active_a_before = parse_salary(team_a_data.get("active_cap", "0"))
    active_b_before = parse_salary(team_b_data.get("active_cap", "0"))

    # If you want to ignore the stored "cap_space" and
    # just compute from the league cap:
    cap_space_a_before = league_cap - active_a_before
    cap_space_b_before = league_cap - active_b_before

    # total_cap might be stored in your data, or you can recalc if you prefer
    total_cap_a_before = parse_salary(team_a_data.get("total_cap", "0"))
    total_cap_b_before = parse_salary(team_b_data.get("total_cap", "0"))

    # 3. Compute new active caps after swapping salaries
    active_a_after = active_a_before - salary_a + salary_b
    active_b_after = active_b_before - salary_b + salary_a

    # 4. Compute new cap space from the league cap
    cap_space_a_after = league_cap - active_a_after
    cap_space_b_after = league_cap - active_b_after

    # 5. Adjust total cap if needed
    #    (depends on how you define "total_cap"—you could recalc or do net diffs)
    net_diff_a = (active_a_after - active_a_before)
    net_diff_b = (active_b_after - active_b_before)
    total_cap_a_after = total_cap_a_before + net_diff_a
    total_cap_b_after = total_cap_b_before + net_diff_b

    # 6. Return updated data
    return {
        "team_a": {
            "team": team_a_code,
            "active_cap_before": active_a_before,
            "active_cap_after": active_a_after,
            "cap_space_before": cap_space_a_before,
            "cap_space_after": cap_space_a_after,
            "total_cap_before": total_cap_a_before,
            "total_cap_after": total_cap_a_after,
            "cap_compliant": (active_a_after <= league_cap)
        },
        "team_b": {
            "team": team_b_code,
            "active_cap_before": active_b_before,
            "active_cap_after": active_b_after,
            "cap_space_before": cap_space_b_before,
            "cap_space_after": cap_space_b_after,
            "total_cap_before": total_cap_b_before,
            "total_cap_after": total_cap_b_after,
            "cap_compliant": (active_b_after <= league_cap)
        }
    }


players_data = load_players()
teams_data = load_teams()

def parse_start_year(year_range):
    # If "Year" is "2024-25", split by '-'
    parts = year_range.split('-')
    try:
        return int(parts[0])
    except:
        return None

def get_contract_summary(player_data, current_season_start=2024):
    """
    Returns a summary of the player's contract:
      - years_left: how many guaranteed years remain (based on the last row with a valid cap hit)
      - contract_expires: the final season (e.g., "2027-28")
      - cap_hit_final_year: the Cap HitAnnual in the final season
    """
    breakdown = player_data.get("contract_breakdown", [])
    
    # Filter rows that have a valid cap hit (not "" or "UFA")
    valid_rows = []
    for row in breakdown:
        cap_hit = row.get("Cap HitAnnual", "")
        # Exclude rows with "UFA", "RFA", or empty
        if cap_hit and cap_hit not in ["UFA", "RFA"]:
            valid_rows.append(row)
    
    if not valid_rows:
        # No valid contract years found
        return {
            "years_left": 0,
            "contract_expires": None,
            "cap_hit_final_year": None
        }
    
    # The last valid row is the final guaranteed season
    final_row = valid_rows[-1]
    final_season = final_row.get("Year", "")
    final_cap_hit = final_row.get("Cap HitAnnual", "")
    
    # Parse the start year from something like "2027-28"
    final_start_year = parse_start_year(final_season)
    if final_start_year is None:
        years_left = 0
    else:
        # Example: if final_start_year=2027 and current_season_start=2024, that's 3 seasons left
        # but if the player is under contract *through* 2027-28, we might add 1
        years_left = (final_start_year - current_season_start) + 1
    
    return {
        "years_left": years_left,
        "contract_expires": final_season,
        "cap_hit_final_year": final_cap_hit
    }



@app.route("/player_details", methods=["GET"])
def player_details():
    """
    Example endpoint: /player_details?player=Auston%20Matthews
    Returns JSON with contract summary for the requested player.
    """
    player_name = request.args.get("player")
    if not player_name or player_name not in players_data:
        return jsonify({"error": "Invalid or missing player name"}), 400
    
    player_data = players_data[player_name]
    summary = get_contract_summary(player_data)
    print("Contract summary for", player_name, ":", summary)
    return jsonify(summary)

@app.route('/')
def index():
    # Sorted list of player names for dropdown
    player_names = sorted(players_data.keys())
    return render_template('index.html', player_names=player_names)

@app.route('/simulate_trade', methods=['POST'])
def simulate_trade_api():
    data = request.get_json()
    player_a_name = data.get("player_a")
    player_b_name = data.get("player_b")

    if not player_a_name or not player_b_name:
        return jsonify({"error": "Both players must be selected."}), 400
    if player_a_name not in players_data or player_b_name not in players_data:
        return jsonify({"error": "Invalid player selection."}), 400

    player_a = players_data[player_a_name]
    player_b = players_data[player_b_name]

    result = simulate_trade(player_a, player_b, teams_data, league_cap=88000000.0)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
