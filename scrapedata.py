#!/usr/bin/env python3
import os
import time
import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ─── Make sure JSON is always written beside this script ────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def scrape_players(page):
    RANKINGS = (
        "https://www.spotrac.com/nhl/rankings/player/"
        "_/year/2025/sort/contract_average/"
    )
    # Wait until basic HTML is there (faster than full networkidle)
    page.goto(RANKINGS, wait_until="domcontentloaded")
    page.wait_for_selector("ul.list-group li.list-group-item")
    soup = BeautifulSoup(page.content(), "html.parser")

    players = []
    for row in soup.select("ul.list-group li.list-group-item"):
        a = row.select_one("div.text-body div.link a")
        if not a:
            continue
        name = a.get_text(strip=True)
        href = a["href"]
        pid  = next((p for p in href.split("/") if p.isdigit()), None)
        slug = name.lower().replace(" ", "-")
        url  = (
            f"https://www.spotrac.com/nhl/player/_/id/{pid}/{slug}/contract/cash"
            if pid else None
        )

        team_tag = row.select_one("div.text-body small")
        sal_tag  = row.select_one("span.medium")
        players.append({
            "name":         name,
            "team":         team_tag.get_text(strip=True) if team_tag else None,
            "salary":       sal_tag.get_text(strip=True)  if sal_tag  else None,
            "contract_url": url
        })
    return players

def scrape_contract(page, url, timeout=30):
    """
    Navigate to the cash page, then poll up to `timeout` seconds for
    the <table> inside the active tab pane.
    """
    page.goto(url, wait_until="domcontentloaded")
    deadline = time.time() + timeout
    table = None

    while time.time() < deadline:
        soup = BeautifulSoup(page.content(), "html.parser")
        table = soup.select_one("div.tab-pane.show.active table.contract-breakdown")
        if table:
            break
        time.sleep(1)

    if not table:
        print(f"⚠️  Timed out waiting for table at {url}")
        return None

    # Extract headers
    headers = [th.get_text(strip=True) for th in table.select("thead th")]

    # Extract rows
    data = []
    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        data.append(dict(zip(headers, cells)))

    return data

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()

        print("🕸️  Scraping player list…")
        players = scrape_players(page)

        all_contracts = {}
        for info in players:
            url = info["contract_url"]
            if not url:
                continue
            print("→", info["name"], "@", url)
            cdata = scrape_contract(page, url, timeout=30)
            if cdata:
                all_contracts[info["name"]] = {
                    "team":               info["team"],
                    "salary":             info["salary"],
                    "contract_breakdown": cdata
                }
            time.sleep(1)

        browser.close()

    out_path = os.path.join(os.getcwd(), "all_contracts.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_contracts, f, indent=2)
    print(f"✅  Saved {len(all_contracts)} players to {out_path}")

if __name__ == "__main__":
    main()
