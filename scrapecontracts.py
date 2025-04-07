import requests
from bs4 import BeautifulSoup
import json

def scrape_contract_details(player_url):
    response = requests.get(player_url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find the contract breakdown table by its class
    contract_table = soup.find("table", class_="table table-white premium contract-breakdown")
    if not contract_table:
        print("Contract table not found.")
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
            # Skip rows with no data (or partial rows, if desired)
            if not tds:
                continue
            # Extract text from each cell
            row_data = [td.get_text(strip=True) for td in tds]
            # Optionally, pad the row_data if it's shorter than headers:
            if len(row_data) < len(headers):
                row_data += [""] * (len(headers) - len(row_data))
            # Create a dictionary mapping headers to cell data
            contract_data.append(dict(zip(headers, row_data)))
    else:
        print("No table body found in the contract table.")

    return contract_data

if __name__ == "__main__":
    # Replace the URL below with the URL for the player's contract details.
    url = "https://www.spotrac.com/nhl/player/_/id/20276/auston-matthews/contract/cash"
    data = scrape_contract_details(url)
    if data:
        # Pretty-print the extracted contract data
        print(json.dumps(data, indent=2))
        # Optionally, write to a JSON file:
        with open("auston_matthews_contract.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print("Contract data saved to auston_matthews_contract.json")
    else:
        print("No contract data was scraped.")
