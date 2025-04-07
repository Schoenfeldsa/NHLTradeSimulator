import requests
from bs4 import BeautifulSoup
import json

def scrape_nhl_team_caps():
    # Replace this URL with the specific page you want to scrape
    url = "https://www.spotrac.com/nhl/cap/"
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Find the table by its class
    table = soup.find("table", class_="table dataTable premium")
    if not table:
        print("Could not find the team cap tracker table.")
        return []

    # 2. Locate the table body (<tbody>)
    tbody = table.find("tbody")
    if not tbody:
        print("No table body found.")
        return []

    # 3. Iterate over each row <tr> in the table body
    rows = tbody.find_all("tr", recursive=False)

    all_teams_data = []
    for row in rows:
        # Each <td> is one column in the row
        cols = row.find_all("td")
        if len(cols) < 13:
            # Skip rows that don't have enough columns
            continue

        # Extract data from each column by index
        rank = cols[0].get_text(strip=True)
        
        # Team name is typically in the 2nd column; it may contain an <a> with the text
        # e.g., "SJS" after an <img> tag
        team = cols[1].get_text(strip=True)  # e.g., "SJS"

        record = cols[2].get_text(strip=True)  # e.g., "20-43-9 (49)"
        players_active = cols[3].get_text(strip=True)  # e.g., "28 / 23"
        players_retained = cols[4].get_text(strip=True)  # e.g., "5 / 3"
        players_total = cols[5].get_text(strip=True)  # e.g., "62 / 50"
        avg_age = cols[6].get_text(strip=True)  # e.g., "25.5"
        cap_space = cols[7].get_text(strip=True)  # e.g., "$23,209,573"
        total_cap = cols[8].get_text(strip=True)  # e.g., "$64,790,427"
        ltir = cols[9].get_text(strip=True)  # e.g., "-"
        active = cols[10].get_text(strip=True)  # e.g., "$45,286,333"
        injured = cols[11].get_text(strip=True)  # e.g., "$10,750,000"
        injured_lt = cols[12].get_text(strip=True)  # e.g., "-"

        team_data = {
            "rank": rank,
            "team": team,
            "record": record,
            "players_active": players_active,
            "players_retained": players_retained,
            "players_total": players_total,
            "avg_age": avg_age,
            "cap_space": cap_space,
            "total_cap": total_cap,
            "ltir_adjustment": ltir,
            "active_cap": active,
            "injured_cap": injured,
            "injured_long_term_cap": injured_lt
        }
        all_teams_data.append(team_data)

    return all_teams_data

if __name__ == "__main__":
    data = scrape_nhl_team_caps()
    print(f"Found {len(data)} teams.")
    
    # Print the first few teams
    for team_info in data[:5]:
        print(team_info)
    
    # Optionally, write to JSON
    with open("nhl_team_caps.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Saved data to nhl_team_caps.json")
