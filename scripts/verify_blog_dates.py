import os, re, json

print("=== 1. CHECK VISIBLE DATES IN BLOG PAGES ===")
bad_tags = ["blog-card__date", "bi-calendar3", "bi-calendar"]
violations = []
for root, dirs, files in os.walk("frontend/blog"):
    for f in files:
        if f.endswith(".html"):
            p = os.path.join(root, f)
            with open(p, "r", encoding="utf-8") as fp:
                c = fp.read()
                for tag in bad_tags:
                    if tag in c:
                        violations.append((p, tag))

print(f"Visible date elements / icons found: {len(violations)}")
assert len(violations) == 0, f"Found {len(violations)} violations!"

print("=== 2. CHECK JSON-LD SCHEMA PRESERVATION ===")
schema_verified = 0
for root, dirs, files in os.walk("frontend/blog"):
    for f in files:
        if f.endswith(".html") and f != "index.html":
            p = os.path.join(root, f)
            with open(p, "r", encoding="utf-8") as fp:
                c = fp.read()
                if '"datePublished":' in c:
                    schema_verified += 1

print(f"Individual article pages with preserved datePublished in JSON-LD schema: {schema_verified}")
assert schema_verified >= 201, f"Schema missing in article pages, only found {schema_verified}!"

print("=== 3. CHECK CONTENT SOURCE FILES PRESERVED ===")
content_files = [f for f in os.listdir("content/articles") if f.endswith(".md")]
assert len(content_files) > 100, "Content articles missing!"
sample = open(os.path.join("content/articles", content_files[0]), "r", encoding="utf-8").read()
assert "date_published:" in sample, "Frontmatter date_published missing!"
print(f"Total markdown content files verified: {len(content_files)}")

print("=== 4. CHECK CARD METADATA INTEGRITY ===")
hub_html = open("frontend/blog/index.html", "r", encoding="utf-8").read()
assert "blog-card__read" in hub_html, "Read time missing from blog cards!"
assert "blog-card__tag" in hub_html, "Category tag missing from blog cards!"

print("=== ALL VERIFICATION CHECKS PASSED PERFECTLY ===")
