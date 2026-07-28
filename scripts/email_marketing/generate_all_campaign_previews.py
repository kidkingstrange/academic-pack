#!/usr/bin/env python3
"""
Generate Campaign Previews for All 5 Categories / All 30 Books
Renders HTML campaign email files for each theme in dry_run_output/
"""
import os
import json
from jinja2 import Environment, FileSystemLoader

from send_campaign import CAMPAIGN_THEMES, load_products, render_email_content, DRY_RUN_DIR

def generate_all_previews():
    all_products = load_products()
    os.makedirs(DRY_RUN_DIR, exist_ok=True)

    summary_list = []

    for theme_name, theme_info in CAMPAIGN_THEMES.items():
        # Get products matching theme
        matching = [p for p in all_products if theme_name.lower()[:5] in p["category"].lower()]
        if not matching:
            matching = all_products[:6]

        selected_products = matching[:6]

        html_out, txt_out, _ = render_email_content(
            recipient_name="David",
            recipient_email="david@example.com",
            selected_products=selected_products,
            theme_info=theme_info
        )

        slug = theme_name.lower().replace(" & ", "_").replace(" ", "_")
        filename = f"campaign_{slug}.html"
        filepath = os.path.join(DRY_RUN_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_out)

        summary_list.append({
            "category": theme_name,
            "subject": theme_info["subject"],
            "preheader": theme_info["preheader"],
            "headline": theme_info["lead_headline"],
            "featured_count": len(selected_products),
            "file": filename,
            "filepath": filepath,
            "books": [p["name"] for p in selected_products]
        })

        print(f"✅ Generated {filename} ({len(selected_products)} books featured)")

    return summary_list

if __name__ == "__main__":
    generate_all_previews()
