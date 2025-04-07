import tkinter as tk
from tkinter import ttk
import json
import re

# ----------------------
# Utility Functions
# ----------------------
def parse_salary(salary_str):
    """
    Converts a string like '$13,250,000' to a float: 13250000.0
    Returns 0.0 if invalid.
    """
    if not salary_str:
        return 0.0
    # Remove '$' and commas
    clean_str = salary_str.replace('$', '').replace(',', '')
    try:
        return float(clean_str)
    except ValueError:
        return 0.0

def parse_team_code(team_str):
    """
    If your 'team' is stored like 'TOR, C', extract just 'TOR'.
    Adjust this logic to match your data format.
    """
    return team_str.split(',')[0].strip()

# ----------------------
# Data Loading
# ----------------------
def load_players(filename):
    """
    Load all_contracts.json into a dictionary:
    {
      "Auston Matthews": {
        "basic_info": {"team": "TOR, C", "salary": "$13,250,000"},
        "contract_breakdown": [...]
      },
      ...
    }
    Returns a dict of player_name -> dict
    """
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def load_teams(filename):
    """
    Load nhl_team_caps.json into a dictionary keyed by the team code, e.g.:
    {
      "SJS": {
        "rank": "1",
        "cap_space": "$23,209,573",
        "active_cap": "$45,286,333",
        ...
      },
      "CGY": { ... },
      ...
    }
    """
    with open(filename, 'r', encoding='utf-8') as f:
        raw_list = json.load(f)
    teams_dict = {}
    for item in raw_list:
        team_code = item["team"]  # e.g. "SJS"
        teams_dict[team_code] = item
    return teams_dict

# ----------------------
# Trade Simulation Logic
# ----------------------
def simulate_trade(player_a, player_b, teams, cap=88000000.0):
    # Extract team codes (e.g., "TOR" from "TOR, C")
    team_a = parse_team_code(player_a["basic_info"]["team"])
    team_b = parse_team_code(player_b["basic_info"]["team"])
    
    # Convert salary strings to float (exact amounts in dollars)
    salary_a = parse_salary(player_a["basic_info"]["salary"])
    salary_b = parse_salary(player_b["basic_info"]["salary"])

    # Get current payroll from teams data (assuming 'active_cap' holds payroll)
    team_a_current = parse_salary(teams.get(team_a, {}).get("active_cap", "$0"))
    team_b_current = parse_salary(teams.get(team_b, {}).get("active_cap", "$0"))

    # Calculate new payrolls after the trade:
    new_team_a = team_a_current - salary_a + salary_b
    new_team_b = team_b_current - salary_b + salary_a

    # Calculate cap space before and after the trade:
    cap_space_before_a = cap - team_a_current
    cap_space_after_a = cap - new_team_a
    cap_space_before_b = cap - team_b_current
    cap_space_after_b = cap - new_team_b

    result = {
        "team_a": {
            "team": team_a,
            "cap": cap,
            "current_payroll": team_a_current,
            "new_payroll": new_team_a,
            "cap_space_before": cap_space_before_a,
            "cap_space_after": cap_space_after_a,
            "cap_compliant": new_team_a <= cap,
            "over_cap_by": max(0, new_team_a - cap)
        },
        "team_b": {
            "team": team_b,
            "cap": cap,
            "current_payroll": team_b_current,
            "new_payroll": new_team_b,
            "cap_space_before": cap_space_before_b,
            "cap_space_after": cap_space_after_b,
            "cap_compliant": new_team_b <= cap,
            "over_cap_by": max(0, new_team_b - cap)
        }
    }
    return result

# ----------------------
# Tkinter GUI
# ----------------------
class TradeSimApp(tk.Tk):
    def __init__(self, players, teams):
        super().__init__()
        self.title("NHL Trade Simulator")
        self.geometry("500x300")

        self.players = players  # dict of player_name -> {player data}
        self.teams = teams      # dict of team_code -> {team data}
        self.cap = 88000000.0

        # Convert players dict keys to a sorted list for dropdown
        self.player_names = sorted(list(self.players.keys()))

        # Create two dropdowns for selecting players
        tk.Label(self, text="Select Player A:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.combo_player_a = ttk.Combobox(self, values=self.player_names, width=30)
        self.combo_player_a.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(self, text="Select Player B:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.combo_player_b = ttk.Combobox(self, values=self.player_names, width=30)
        self.combo_player_b.grid(row=1, column=1, padx=10, pady=10)

        # Button to simulate the trade
        self.btn_simulate = tk.Button(self, text="Simulate Trade", command=self.on_simulate_trade)
        self.btn_simulate.grid(row=2, column=0, columnspan=2, pady=10)

        # Text area to display the results
        self.txt_result = tk.Text(self, height=10, width=60)
        self.txt_result.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

    def on_simulate_trade(self):
        """
        Handle the "Simulate Trade" button click.
        """
        player_a_name = self.combo_player_a.get()
        player_b_name = self.combo_player_b.get()

        # Basic validation
        if not player_a_name or not player_b_name:
            self.txt_result.delete("1.0", tk.END)
            self.txt_result.insert(tk.END, "Please select both players.\n")
            return
        if player_a_name == player_b_name:
            self.txt_result.delete("1.0", tk.END)
            self.txt_result.insert(tk.END, "Cannot trade a player for themselves!\n")
            return

        player_a_data = self.players[player_a_name]
        player_b_data = self.players[player_b_name]

        # Run the simulation
        result_text = simulate_trade(player_a_data, player_b_data, self.teams, cap=self.cap)

        # Display the result in the text box
        self.txt_result.delete("1.0", tk.END)
        self.txt_result.insert(tk.END, result_text)


def main():
    players = load_players("all_contracts.json")
    teams = load_teams("nhl_team_caps.json")

    app = TradeSimApp(players, teams)
    app.mainloop()

if __name__ == "__main__":
    main()
