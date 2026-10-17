import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

FEEDS = [
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("AP Business", "https://apnews.com/hub/business?output=rss"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("Google China Tech", "https://news.google.com/rss/search?q=China+technology+AI&hl=en-US&gl=US&ceid=US:en"),
]

CATEGORIES = {
    "美国公司": ["apple", "microsoft", "google", "amazon", "meta", "nvidia",
                "tesla", "openai", "anthropic", "amazon", "company", "earnings"],
    "市场": ["stock", "market", "shares", "nasdaq", "dow", "fed", "interest rate",
            "inflation", "investor", "economy", "bond"],
    "AI与科技": ["ai", "artificial intelligence", "chip", "semiconductor",
                "robot", "data center", "cloud", "technology", "tech"],
    "中国科技": ["china", "chinese", "bytedance", "alibaba", "tencent",
                "baidu", "huawei", "xiaomi", "deepseek"],
}

def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()

def get_text(item, *names):
    for name in names:
        node = item.find(name)
        if node is not None and node.text:
            return clean(node.text)
    return ""

def classify(title, summary):
    text = (title + " " + summary).lower()
    found = []
    for category, keywords in CATEGORIES.items():
        if any(word in text for word in keywords):
            found.append(category)
    return found or ["全球商业"]

def parse_date(value):
    if value:
        try:
            return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return ""

def fetch_feed(name, url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "DailyBusinessIntel/1.0"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        root = ET.fromstring(response.read())

    items = root.findall(".//item")
    results = []
    for item in items:
        title = get_text(item, "title")
        link = get_text(item, "link")
        summary = get_text(item, "description")
        published = parse_date(
            get_text(item, "pubDate", "{http://purl.org/dc/elements/1.1/}date")
        )
        if not title or not link:
            continue
        results.append({
            "title": title,
            "summary": summary[:700],
            "url": link,
            "source": name,
            "published": published,
            "categories": classify(title, summary),
        })
    return results

def main():
    articles = []
    feed_status = []

    for name, url in FEEDS:
        try:
            fetched = fetch_feed(name, url)
            articles.extend(fetched)
            feed_status.append({"source": name, "count": len(fetched)})
            print(f"{name}: {len(fetched)} articles")
        except Exception as error:
            feed_status.append({"source": name, "error": str(error)})
            print(f"Warning: {name}: {error}")

    unique = {}
    for article in articles:
        unique.setdefault(article["url"], article)

    articles = list(unique.values())
    articles.sort(key=lambda x: x["published"], reverse=True)
    articles = articles[:60]

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(articles),
        "feed_status": feed_status,
        "articles": articles,
    }

    with open("news.json", "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print(f"Saved {len(articles)} unique articles to news.json")

if __name__ == "__main__":
    main()
