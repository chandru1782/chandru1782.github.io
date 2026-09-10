import os
import re
import sys
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Required libraries not found. Run: pip install beautifulsoup4 requests")
    sys.exit(1)

# Ensure paths resolve relative to the repository root regardless of where script is invoked
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
NEWS_DIR = os.path.join(REPO_ROOT, "_news")

MTTS_URL = "https://mtts.org.in/announcements"

def clean_slug(text):
    """Generate a clean, filename-safe slug from title text."""
    slug = re.sub(r'[^a-zA-Z0-9]', '_', text.lower())
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug[:40]

def parse_date(article):
    """Extract date from WordPress time elements or raw article text."""
    time_tag = article.find("time")
    if time_tag:
        if time_tag.has_attr("datetime"):
            match = re.search(r'\d{4}-\d{2}-\d{2}', time_tag["datetime"])
            if match:
                return match.group(0)
        
        date_raw = time_tag.get_text(strip=True)
        match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}', date_raw)
        if match:
            try:
                dt = datetime.strptime(match.group(0), "%B %d, %Y")
                return dt.strftime("%Y-%m-%d")
            except Exception:
                pass

    text = article.get_text()
    match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}', text)
    if match:
        try:
            dt = datetime.strptime(match.group(0), "%B %d, %Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    return datetime.now().strftime("%Y-%m-%d")

def fetch_announcements():
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"Targeting directory: {NEWS_DIR}")
    print(f"Fetching announcements from: {MTTS_URL}")

    try:
        response = requests.get(MTTS_URL, headers=headers, timeout=15)
        print(f"HTTP Status Code: {response.status_code}")
        response.raise_for_status()
    except Exception as e:
        print(f"Error connecting to MTTS website: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    os.makedirs(NEWS_DIR, exist_ok=True)

    # WordPress / GeneratePress post containers
    articles = soup.find_all("article")
    if not articles:
        articles = soup.find_all("div", class_=re.compile(r"post|entry"))

    print(f"Found {len(articles)} potential announcement posts.")

    new_items_count = 0

    for idx, article in enumerate(articles[:10]):
        # Specifically target the WordPress post heading
        title_heading = article.find(["h2", "h1", "h3"], class_=re.compile(r"entry-title|title|post-title"))
        if not title_heading:
            title_heading = article.find(["h2", "h1", "h3"])

        if not title_heading:
            continue

        link_tag = title_heading.find("a", href=True) or article.find("a", href=True)
        title = title_heading.get_text(strip=True)

        if not title or title.lower() in ["announcements", "menu", "search"]:
            continue

        link = link_tag["href"] if link_tag else MTTS_URL
        date_str = parse_date(article)
        slug = clean_slug(title)

        if not slug:
            slug = f"announcement_{idx+1}"

        filename = os.path.join(NEWS_DIR, f"mtts_{slug}.md")

        md_content = f"""---
layout: post
title: "{title}"
date: {date_str} 00:00:00-0000
inline: true
related_posts: false
---

[MTTS Announcement]({link}): {title}
"""

        if not os.path.exists(filename):
            with open(filename, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"[CREATED] {filename}")
            new_items_count += 1
        else:
            print(f"[SKIPPED] Already exists: {filename}")

    print(f"Finished. Total new announcements created: {new_items_count}")

if __name__ == "__main__":
    fetch_announcements()