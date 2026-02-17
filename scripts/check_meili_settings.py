import meilisearch
import os

MEILI_URL = os.getenv("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY", "masterKey")

client = meilisearch.Client(MEILI_URL, MEILI_KEY)
index = client.index('jobs')

print(f"Checking index: jobs at {MEILI_URL}")
try:
    settings = index.get_settings()
    print("Filterable Attributes:", settings.get('filterableAttributes'))
    print("Searchable Attributes:", settings.get('searchableAttributes'))
    print("Sortable Attributes:", settings.get('sortableAttributes'))
except Exception as e:
    print(f"Error: {e}")
