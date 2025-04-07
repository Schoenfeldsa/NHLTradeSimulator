import json

def generate_html_from_json(json_filename, html_filename):
    # Load the latest data
    with open(json_filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Note the double curly braces in the CSS below
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>NHL Contract Data</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
  </style>
</head>
<body>
  <h1>NHL Contract Data</h1>
  <table>
    <thead>
      <tr>
        <th>Player Name</th>
        <th>Team</th>
        <th>Salary</th>
        <th>Contract Years</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>"""
    
    # Create table rows from the JSON data.
    rows_html = ""
    for player_name, details in data.items():
        team = details["basic_info"].get("team", "")
        salary = details["basic_info"].get("salary", "")
        years = len(details["contract_breakdown"])
        rows_html += f"<tr><td>{player_name}</td><td>{team}</td><td>{salary}</td><td>{years} year(s)</td></tr>\n"
    
    html_content = html_template.format(rows=rows_html)
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"{html_filename} has been updated with the latest data!")

if __name__ == "__main__":
    generate_html_from_json("all_contracts.json", "players.html")
