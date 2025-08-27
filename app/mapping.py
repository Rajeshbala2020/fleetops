import pyodbc
import json

# Connect to your database
conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=;"
            "DATABASE=;"
            "UID=;"
            "PWD="
        )
cursor = conn.cursor()

# Fetch all pages from Wikidocs
cursor.execute("SELECT wikidocid, title, parentid FROM Wikidocs")
rows = cursor.fetchall()

# Build a lookup: wikidocid -> {title, parentid}
page_lookup = {row.wikidocid: {"title": row.title, "parentid": row.parentid} for row in rows}

# Find all top-level modules (parentid is None)
modules = {row.wikidocid: row.title for row in rows if row.parentid is None}

# Build subpage-to-module mapping
subpage_to_module = {}

def find_module(page_id):
    parent_id = page_lookup[page_id]["parentid"]
    if parent_id is None:
        return page_lookup[page_id]["title"]
    return find_module(parent_id)

for row in rows:
    module_title = find_module(row.wikidocid)
    subpage_to_module[row.title.strip()] = module_title.strip()

cursor.close()
conn.close()

# Save the mapping as a JSON file
with open("subpage_to_module.json", "w", encoding="utf-8") as f:
    json.dump(subpage_to_module, f, ensure_ascii=False, indent=2)
