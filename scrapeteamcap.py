#!/usr/bin/env python3
import os
import json
import requests
from bs4 import BeautifulSoup

# ─── Make sure JSON lands beside this script ────────────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# A real‐browser User‑Agent to avoid minimal/bot HTML
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    )
}

def scrape_nhl_team_caps():
    """
    Scrape https://www.spotrac.com/nhl/cap/,
    extract the team cap table into a list of dicts.
    """
    url = "https://www.spotrac.com/nhl/cap/"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", class_="table dataTable premium")
    if not table:
        print("❌ Could not find the team cap table.")
        return []

    # Dynamically pull the column names
    headers = [th.get_text(strip=True) for th in table.select("thead th")]

    teams = []
    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.select("td")]
        if not cells:
            continue
        # Pad/truncate to match headers, if necessary
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        elif len(cells) > len(headers):
            cells = cells[: len(headers)]

        # Build a dict mapping header->cell
        team_data = dict(zip(headers, cells))
        teams.append(team_data)

    return teams

def main():
    data = scrape_nhl_team_caps()
    print(f"Found {len(data)} teams in the NHL cap table.\n")

    # Print a sample of the first 5 teams
    for team in data[:5]:
        print(team)
    print()

    # Write out to JSON
    out_file = "nhl_team_caps.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved all team cap data to {out_file}")

if __name__ == "__main__":
    main()
