import json
from bs4 import BeautifulSoup
import pyodbc
from collections import defaultdict
import os 

class DatabaseService:

    def __init__(self):
        self.__conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=xxx;"
            "DATABASE=xxx;"
            "UID=xxxx;"
            "PWD=xxxx;"
        )
        self.cursor = self.__conn.cursor()
        self.pages = []
        self.img_sources = []
        self.root_pages = []
        self.trees_by_module = defaultdict(list)

    def html_to_text(self, html: str) -> str:
        """Convert HTML content to plain text."""
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.find_all('img'):
            img.decompose()
        return soup.get_text(separator=' ', strip=True)

    def database_fetch(self):
        self.cursor.execute("SELECT WikiDocId,Title,ContentHtml, ParentId FROM Wikidocs;")

        rows = self.cursor.fetchall()
        for row in rows:
            wiki_doc_id = row.WikiDocId
            title = row.Title
            content_html = row.ContentHtml if row.ContentHtml else ""
            parent_id = row.ParentId
            plain_text = self.html_to_text(content_html).replace('\u00a0', ' ')

            full_text = plain_text + " "

            self.pages.append({
                "id": wiki_doc_id,
                "title": title,
                "content": full_text,
                "parent_id": parent_id
            })

        self.cursor.close()
        self.__conn.close()

    def build_navigation_tree(self):
        
        all_trees_data = {}

        for page in self.pages:
            parent_id = page["parent_id"]
            if parent_id is None:
                self.root_pages.append(page)
            else:
                self.trees_by_module[parent_id].append(page)

        def build_subtree(parent_id=None):
            return [
                {
                    "title": page["title"].strip(),
                    "id": page["id"],
                    "content": page.get("content", ""),
                    "children": build_subtree(page["id"])
                }
                for page in self.trees_by_module.get(parent_id, [])
            ]
        
        for root_page in self.root_pages:
            module_name = root_page["title"].strip()
            all_trees_data[module_name] = {
                "title": module_name,
                "id": root_page["id"],
                "content": root_page.get("content", ""),
                "children": build_subtree(root_page["id"])
            }

        return all_trees_data
    
        
    def tree_to_json(self,filename: str, nav_tree: dict | list) -> None:
        """
        Save the navigation tree to a JSON file.
        """
        if not filename.endswith(".json"):
            filename += ".json"
        
        os.makedirs("app/source_files", exist_ok=True)
        filepath = os.path.join("app", "source_files", filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(nav_tree, f, indent=2, ensure_ascii=False)

    def save_all_trees(self):
        """
        Orchestrates the process of building all trees and saving them to individual JSON files.
        """
        all_trees = self.build_navigation_tree()
        
        for module_name, tree_data in all_trees.items():
            # Sanitize filename for spaces and case
            sanitized_filename = module_name.replace(" ", "_").lower()
            self.tree_to_json(sanitized_filename, tree_data)
            print(f"Saved navigation tree for module '{module_name}' to {sanitized_filename}.json")


if __name__ == "__main__":
    parser_obj = DatabaseService()
    parser_obj.database_fetch()
    parser_obj.save_all_trees()


