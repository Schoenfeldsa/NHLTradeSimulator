import requests
from bs4 import BeautifulSoup
import json
import time

def scrape_players():
    """
    Scrapes the main player listing page to get basic player info
    and constructs a contract details URL for each player.
    """
    url = "https://www.spotrac.com/nhl/rankings/player/_/year/2024/sort/contract_average/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Select all player rows from the list-group.
    rows = soup.select("ul.list-group li.list-group-item")
    
    players = []
    for row in rows:
        # Get the player's name and the link from the <a> element.
        name_tag = row.select_one("div.text-body div.link a")
        if not name_tag:
            continue
        name = name_tag.get_text(strip=True)
        
        # "https://www.spotrac.com/redirect/player/20276"
        player_link = name_tag.get("href")
        
        # Extract player id from the URL.
        player_id = None
        parts = player_link.split("/")
        for part in parts:
            if part.isdigit():
                player_id = part
                break
        
        # Create a slug from the player's name, e.g. "Auston Matthews" => "auston-matthews"
        slug = name.lower().replace(" ", "-")
        
        # Construct the contract details URL.
        # "https://www.spotrac.com/nhl/player/_/id/{player_id}/{slug}/contract/cash"
        if player_id:
            contract_url = f"https://www.spotrac.com/nhl/player/_/id/{player_id}/{slug}/contract/cash"
        else:
            contract_url = None
        
        # Optionally, you can also grab other info (team, salary from listing)
        team_tag = row.select_one("div.text-body small")
        team = team_tag.get_text(strip=True) if team_tag else None
        salary_tag = row.select_one("span.medium")
        salary = salary_tag.get_text(strip=True) if salary_tag else None
        
        players.append({
            "name": name,
            "team": team,
            "salary": salary,
            "contract_url": contract_url
        })
    return players

def scrape_contract_details(contract_url):
    """
    Scrapes the contract breakdown table from a given player's contract page.
    Returns a list of dictionaries (one per table row).
    """
    response = requests.get(contract_url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find the contract table by its class
    contract_table = soup.find("table", class_="table table-white premium contract-breakdown")
    if not contract_table:
        print(f"Contract table not found at {contract_url}")
        return None

    # Extract headers from the table header (<thead>)
    headers = []
    thead = contract_table.find("thead")
    if thead:
        header_row = thead.find("tr")
        for th in header_row.find_all("th"):
            headers.append(th.get_text(strip=True))
    else:
        print("No headers found in the contract table.")

    # Extract rows from the table body (<tbody>)
    contract_data = []
    tbody = contract_table.find("tbody")
    if tbody:
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if not tds:
                continue
            row_data = [td.get_text(strip=True) for td in tds]
            # Pad row_data if it's shorter than headers
            if len(row_data) < len(headers):
                row_data += [""] * (len(headers) - len(row_data))
            contract_data.append(dict(zip(headers, row_data)))
    else:
        print("No table body found in the contract table.")
    
    return contract_data

def scrape_all_contracts():
    """
    Loops over every player from the main listing, scrapes their contract details,
    and returns a dictionary mapping player names to their contract breakdown.
    """
    players = scrape_players()
    all_contracts = {}
    for player in players:
        contract_url = player.get("contract_url")
        if not contract_url:
            print(f"Skipping {player['name']} (no contract URL)")
            continue
        print(f"Scraping contract for {player['name']} at {contract_url}")
        contract_details = scrape_contract_details(contract_url)
        if contract_details:
            all_contracts[player["name"]] = {
                "basic_info": {
                    "team": player.get("team"),
                    "salary": player.get("salary")
                },
                "contract_breakdown": contract_details
            }
        else:
            print(f"Contract details not found for {player['name']}")
        # Sleep a short while to be respectful to the server.
        time.sleep(1)
    return all_contracts

if __name__ == "__main__":
    all_contracts = scrape_all_contracts()
    with open("all_contracts.json", "w", encoding="utf-8") as f:
        json.dump(all_contracts, f, indent=2)
    print("All contract data saved to all_contracts.json")
