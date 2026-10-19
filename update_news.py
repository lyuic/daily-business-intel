```python
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

FEEDS = [
    (
        "TechCrunch AI",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
    ),
    (
        "Google China Tech",
        "https://news.google.com/rss/search?q=China+technology+AI&hl=en-US&gl=US&ceid=US:en",
    ),
    (
        "Google US Business",
        "https://news.google.com/rss/search?q=US+companies+earnings+business&hl=en-US&gl=US&ceid=US:en",
    ),
    (
        "Google Markets",
        "https://news.google.com/rss/search?q=stock+market+economy+interest+rates&hl=en-US&gl=US&ceid=US:en",
    ),
]

# 使用更有区分度的关键词，减少所有新闻都命中同一类别的情况
CATEGORIES = {
    "美国公司": [
        "apple", "microsoft", "amazon", "nvidia", "tesla",
        "meta platforms", "alphabet", "openai", "anthropic",
        "earnings", "quarterly results", "revenue", "profit",
        "ceo", "acquisition", "merger", "layoffs",
        "us company", "american company",
    ],
    "市场": [
        "stock market", "stock prices", "shares fell", "shares rose",
        "nasdaq", "s&p 500", "dow jones", "bond yields",
        "interest rates", "federal reserve", "inflation",
        "wall street", "investors", "market selloff",
        "market rally", "economic growth", "unemployment",
    ],
    "AI与科技": [
        "artificial intelligence", "generative ai", "large language model",
        "ai model", "ai chip", "machine learning", "robotics",
        "semiconductor", "data center", "cloud computing",
        "deepseek", "chatgpt", "anthropic", "openai",
        "technology company", "tech startup",
    ],
    "中国科技": [
        "china tech", "chinese tech", "chinese technology",
        "bytedance", "alibaba", "tencent", "baidu", "huawei",
        "xiaomi", "zhipu", "moonshot ai", "china's ai",
        "chinese ai", "china technology policy",
    ],
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

def classify(title, summary, source=""):
    text = (title + " " + summary).lower()
    found = []

    for category, keywords in CATEGORIES.items():
        if any(keyword in text for keyword in keywords):
            found.append(category)

    # 来源只用于补充 AI 类别，不会单凭“中国科技”来源就强制贴中国科技标签
    if "TechCrunch AI" in source and "AI与科技" not in found:
        found.append("AI与科技")

    # 对完全没有匹配到关键词的新闻，避免空分类
    return found or ["全球商业"]

def parse_date(value):
    if value:
        try:
            dt = parsedate_to_datetime(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return ""

def fetch_feed(name, url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 DailyBusinessIntel/1.0"},
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        root = ET.fromstring(response.read())

    results = []
    for item in root.findall(".//item"):
        title = get_text(item, "title")
        link = get_text(item, "link")
        summary = get_text(item, "description")
        published = parse_date(
            get_text(
                item,
                "pubDate",
                "{http://purl.org/dc/elements/1.1/}date",
            )
        )

        if not title or not link:
            continue

        results.append({
            "title": title,
            "summary": summary[:700],
            "url": link,
            "source": name,
            "published": published,
            "categories": classify(title, summary, name),
        })

    return results

def main():
    articles = []
    feed_status = []

    for name, url in FEEDS:
        try:
            fetched = fetch_feed(name, url)
            articles.extend(fetched)
            feed_status.append({
                "source": name,
                "count": len(fetched),
            })
            print(f"{name}: {len(fetched)} articles")
        except Exception as error:
            feed_status.append({
                "source": name,
                "count": 0,
                "error": str(error),
            })
            print(f"Warning: {name}: {error}")

    # 去重：优先保留先采集到的文章
    unique = {}
    for article in articles:
        unique.setdefault(article["url"], article)

    articles = list(unique.values())
    articles.sort(
        key=lambda item: item["published"],
        reverse=True,
    )
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

    # 输出分类统计，方便在 GitHub Actions 日志中检查结果
    category_counts = {}
    for article in articles:
        for category in article["categories"]:
            category_counts[category] = category_counts.get(category, 0) + 1

    print("Category counts:", json.dumps(
        category_counts, ensure_ascii=False
    ))

if __name__ == "__main__":
    main()
```
