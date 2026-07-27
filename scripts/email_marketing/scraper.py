#!/usr/bin/env python3
"""
Product Scraper for Scale Group Digital Library
Extracts product catalog (name, price, category, description, image URL, link)
and saves to products.json.
"""
import os
import sys
import json
import subprocess

SITE_URL = "https://edgepack.thescaleconference.com"
HOME_JS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/js/home.js"))
OUTPUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "products.json"))

def parse_catalog_from_home_js():
    if not os.path.exists(HOME_JS_PATH):
        raise FileNotFoundError(f"Could not find catalog file at {HOME_JS_PATH}")
    
    node_cmd = [
        "node", "-e",
        f"const fs = require('fs'); const code = fs.readFileSync('{HOME_JS_PATH}', 'utf8'); const match = code.match(/const BOOKS = (\\[[\\s\\S]*?\\n\\];)/); const books = eval(match[1].replace(/;$/, '')); console.log(JSON.stringify(books));"
    ]
    
    res = subprocess.run(node_cmd, capture_output=True, text=True, check=True)
    books_data = json.loads(res.stdout)

    products = []
    for item in books_data:
        prod_id = item.get("id", "")
        title = item.get("title", "")
        cover = item.get("cover", "")
        if cover.startswith("/"):
            image_url = f"{SITE_URL}{cover}"
        else:
            image_url = cover

        category = item.get("category", "Digital Masterclass")
        description = item.get("description", "")
        amount = item.get("amount", 5000)

        # Build clean direct link
        product_link = f"{SITE_URL}/#product-{prod_id}" if prod_id != "bundle_3" else f"{SITE_URL}/#bundle"

        products.append({
            "id": prod_id,
            "name": title,
            "price": amount,
            "currency": "NGN",
            "formatted_price": f"₦ {amount:,}",
            "category": category,
            "description": description,
            "image_url": image_url,
            "product_url": product_link,
            "bullets": item.get("bullets", [])
        })

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as out_f:
        json.dump(products, out_f, indent=2, ensure_ascii=False)

    print(f"Successfully scraped {len(products)} products into {OUTPUT_PATH}")
    return products

if __name__ == "__main__":
    parse_catalog_from_home_js()
