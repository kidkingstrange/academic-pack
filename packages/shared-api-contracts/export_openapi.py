import json
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from backend.main import app

os.makedirs('packages/shared-api-contracts', exist_ok=True)
schema = app.openapi()
out_path = 'packages/shared-api-contracts/openapi.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(schema, f, indent=2)

print(f"Exported {len(schema.get('paths', {}))} API paths to {out_path}")
