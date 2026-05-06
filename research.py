#!/usr/bin/env python3
"""
Newsletter Research Script — Joseph Khateri (Investing Section 8)

Fetches signal from YouTube, Reddit, HUD/news RSS, and Airtable.
Inlines the result directly into index.html as window.__RESEARCH__.

Run manually: python research.py
Run via GitHub Actions: scheduled Mon/Wed/Fri at 9am ET

Secrets required (GitHub Actions):
    JOSEPH_YT_API_KEY  — YouTube Data API v3 key
    AIRTABLE_TOKEN     — Airtable personal access token
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

YOUTUBE_API_KEY    = os.environ.get("JOSEPH_YT_API_KEY", "REMOVED_KEY")
YOUTUBE_CHANNEL_ID = "UCQXnWqNYluoUnm3IpzeRMuw"

AIRTABLE_TOKEN    = os.environ.get("AIRTABLE_TOKEN", "")
AIRTABLE_BASE_ID  = "apppAaY1mCbpmXSGd"
AIRTABLE_PIPELINE = "tblRt7VOLkoT5KPEO"

REDDIT_SUBREDDITS = [
    "realestateinvesting",
    "section8landlord",
    "landlord",
    "passive_income",
    "financialindependence",
]

REDDIT_MIN_POST_SCORE    = 20
REDDIT_MIN_COMMENT_SCORE = 10
REDDIT_POST_MAX_AGE_DAYS = 14
YOUTUBE_VIDEOS_TO_MINE   = 5
YOUTUBE_COMMENTS_PER_VID = 100
YOUTUBE_MIN_COMMENT_LIKES = 0

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# HTTP HELPERS
# ---------------------------------------------------------------------------

def get(url: str, headers: dict = None, timeout: int = 15) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "newsletter-research/1.0", **(headers or {})}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} — {url}") from e

def get_json(url: str, headers: dict = None) -> dict:
    return json.loads(get(url, headers))

def get_xml(url: str) -> ET.Element:
    return ET.fromstring(get(url))

# ---------------------------------------------------------------------------
# SOURCE 1 — REDDIT
# ---------------------------------------------------------------------------

REDDIT_ALWAYS_RELEVANT = {"section8landlord"}

REDDIT_RELEVANCE_KEYWORDS = [
    "section 8", "section8", "rental", "rent", "real estate", "property",
    "landlord", "tenant", "passive income", "cash flow", "cashflow",
    "investing", "investment", "hud", "voucher", "dscr", "mortgage",
    "w2", "financial freedom", "retire", "portfolio",
]

def _is_reddit_relevant(sub: str, title: str, text: str) -> bool:
    if sub in REDDIT_ALWAYS_RELEVANT:
        return True
    combined = (title + " " + text).lower()
    return any(kw in combined for kw in REDDIT_RELEVANCE_KEYWORDS)

def fetch_reddit() -> list:
    items = []

    for sub in REDDIT_SUBREDDITS:
        try:
            data = get_json(f"https://www.reddit.com/r/{sub}/hot.json?limit=50")
        except Exception as e:
            print(f"  [reddit] r/{sub} failed: {e}", file=sys.stderr)
            continue

        for child in data["data"]["children"]:
            p = child["data"]

            if p.get("stickied"):
                continue
            if p.get("score", 0) < REDDIT_MIN_POST_SCORE:
                continue

            age_days = (time.time() - p.get("created_utc", 0)) / 86400
            if age_days > REDDIT_POST_MAX_AGE_DAYS:
                continue

            if not _is_reddit_relevant(sub, p.get("title", ""), p.get("selftext", "")):
                continue

            post = {
                "source":       f"r/{sub}",
                "type":         "post",
                "title":        p.get("title", ""),
                "text":         p.get("selftext", "")[:600],
                "score":        p.get("score", 0),
                "num_comments": p.get("num_comments", 0),
                "url":          f"https://reddit.com{p.get('permalink', '')}",
                "is_question":  "?" in p.get("title", ""),
                "age_days":     round(age_days, 1),
            }
            items.append(post)

            if p.get("score", 0) >= 50:
                try:
                    thread = get_json(
                        f"https://www.reddit.com/r/{sub}/comments/{p['id']}.json"
                        f"?limit=20&sort=top&depth=1"
                    )
                    for c in thread[1]["data"]["children"][:10]:
                        cd = c.get("data", {})
                        body = cd.get("body", "")
                        if (
                            cd.get("score", 0) >= REDDIT_MIN_COMMENT_SCORE
                            and body
                            and body != "[deleted]"
                            and body != "[removed]"
                        ):
                            items.append({
                                "source":       f"r/{sub}",
                                "type":         "comment",
                                "text":         body[:600],
                                "score":        cd.get("score", 0),
                                "url":          f"https://reddit.com{p.get('permalink', '')}",
                                "parent_title": p.get("title", ""),
                                "is_question":  "?" in body,
                            })
                    time.sleep(0.5)
                except Exception:
                    pass

    items.sort(key=lambda x: x.get("score", 0), reverse=True)
    print(f"  [reddit] {len(items)} items ({sum(1 for i in items if i['is_question'])} questions)")
    return items

# ---------------------------------------------------------------------------
# SOURCE 2 — YOUTUBE
# ---------------------------------------------------------------------------

def fetch_youtube() -> dict:
    if not YOUTUBE_API_KEY:
        print("  [youtube] SKIPPED — JOSEPH_YT_API_KEY not set", file=sys.stderr)
        return {"videos": [], "comments": [], "skipped": True}

    base = "https://www.googleapis.com/youtube/v3"
    key  = f"&key={YOUTUBE_API_KEY}"

    try:
        ch = get_json(f"{base}/channels?id={YOUTUBE_CHANNEL_ID}&part=contentDetails{key}")
        uploads_playlist = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        pl = get_json(
            f"{base}/playlistItems?playlistId={uploads_playlist}"
            f"&maxResults=15&part=snippet{key}"
        )
        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in pl["items"]]

        stats = get_json(
            f"{base}/videos?id={','.join(video_ids)}&part=statistics,snippet{key}"
        )

        videos = []
        for v in stats["items"]:
            s = v["statistics"]
            videos.append({
                "video_id":      v["id"],
                "title":         v["snippet"]["title"],
                "description":   v["snippet"]["description"][:400],
                "published_at":  v["snippet"]["publishedAt"],
                "view_count":    int(s.get("viewCount", 0)),
                "like_count":    int(s.get("likeCount", 0)),
                "comment_count": int(s.get("commentCount", 0)),
                "url":           f"https://youtube.com/watch?v={v['id']}",
            })

        videos.sort(key=lambda x: x["view_count"], reverse=True)

        all_comments = []
        for video in videos[:YOUTUBE_VIDEOS_TO_MINE]:
            try:
                ct = get_json(
                    f"{base}/commentThreads?videoId={video['video_id']}"
                    f"&maxResults={YOUTUBE_COMMENTS_PER_VID}&order=relevance"
                    f"&part=snippet{key}"
                )
                for item in ct.get("items", []):
                    c     = item["snippet"]["topLevelComment"]["snippet"]
                    text  = c.get("textDisplay", "")
                    likes = c.get("likeCount", 0)

                    if likes >= YOUTUBE_MIN_COMMENT_LIKES or "?" in text or len(text) > 80:
                        all_comments.append({
                            "video_id":    video["video_id"],
                            "video_title": video["title"],
                            "text":        text[:500],
                            "likes":       likes,
                            "is_question": "?" in text,
                            "url":         video["url"],
                        })
                time.sleep(0.2)
            except Exception as e:
                print(f"  [youtube] comments for {video['video_id']} failed: {e}", file=sys.stderr)

        all_comments.sort(key=lambda x: x["likes"], reverse=True)

        print(
            f"  [youtube] {len(videos)} videos, "
            f"{len(all_comments)} comments "
            f"({sum(1 for c in all_comments if c['is_question'])} questions)"
        )
        return {"videos": videos, "comments": all_comments, "skipped": False}

    except Exception as e:
        print(f"  [youtube] failed: {e}", file=sys.stderr)
        return {"videos": [], "comments": [], "skipped": True, "error": str(e)}

# ---------------------------------------------------------------------------
# SOURCE 3 — HUD / SECTION 8 NEWS
# ---------------------------------------------------------------------------

SECTION8_KEYWORDS = [
    "section 8", "housing choice voucher", "fair market rent", "fmr",
    "hud", "rental assistance", "housing authority", "voucher program",
]

def _is_section8_relevant(title: str, desc: str) -> bool:
    text = (title + " " + desc).lower()
    return any(kw in text for kw in SECTION8_KEYWORDS)

def fetch_news() -> list:
    items = []

    feeds = [
        ("Google News: Section 8 vouchers", "https://news.google.com/rss/search?q=section+8+housing+voucher&hl=en-US&gl=US&ceid=US:en"),
        ("Google News: Section 8 investing", "https://news.google.com/rss/search?q=%22section+8%22+real+estate+investing&hl=en-US&gl=US&ceid=US:en"),
        ("Google News: HUD rental assistance", "https://news.google.com/rss/search?q=HUD+rental+assistance+voucher&hl=en-US&gl=US&ceid=US:en"),
    ]

    for label, url in feeds:
        try:
            root = get_xml(url)
            for item in root.iter("item"):
                title = item.findtext("title", "")
                link  = item.findtext("link", "")
                desc  = item.findtext("description", "")[:400]
                date  = item.findtext("pubDate", "")

                if not _is_section8_relevant(title, desc):
                    continue

                items.append({
                    "source":      label,
                    "title":       title,
                    "description": desc,
                    "url":         link,
                    "date":        date,
                })
        except Exception as e:
            print(f"  [news] {label} failed: {e}", file=sys.stderr)

    print(f"  [news] {len(items)} items")
    return items

# ---------------------------------------------------------------------------
# SOURCE 4 — AIRTABLE STUDENT WINS
# ---------------------------------------------------------------------------

def fetch_student_wins() -> list:
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PIPELINE}?maxRecords=50"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}

    try:
        data    = get_json(url, headers)
        records = data.get("records", [])

        wins = []
        for r in records:
            f = r.get("fields", {})
            wins.append({
                "name":           f.get("Lead Name", ""),
                "cash_collected": f.get("Cash Collected", 0),
                "lead_source":    f.get("Lead Source", ""),
                "call_date":      f.get("Call Date", ""),
                "product":        f.get("Product", "Investing Section 8"),
            })

        print(f"  [airtable] {len(wins)} wins from {len(records)} records")
        return wins

    except Exception as e:
        print(f"  [airtable] failed: {e}", file=sys.stderr)
        return []

# ---------------------------------------------------------------------------
# ASSEMBLE + INLINE INTO index.html
# ---------------------------------------------------------------------------

def build_output(reddit, youtube, news, wins) -> dict:
    yt_comments = youtube.get("comments", [])
    yt_videos   = youtube.get("videos", [])

    reddit_questions = sorted(
        [r for r in reddit if r.get("is_question")],
        key=lambda x: x.get("score", 0),
        reverse=True
    )[:20]

    yt_questions = sorted(
        [c for c in yt_comments if c.get("is_question")],
        key=lambda x: x.get("likes", 0),
        reverse=True
    )[:20]

    reddit_top      = [r for r in reddit if r.get("type") == "post"][:15]
    yt_top_comments = yt_comments[:20]

    return {
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "youtube_skipped": youtube.get("skipped", False),
        "synthesis_input": {
            "reddit_questions_ranked_by_score":  reddit_questions,
            "youtube_questions_ranked_by_likes": yt_questions,
            "youtube_top_comments":              yt_top_comments,
            "reddit_top_posts":                  reddit_top,
            "news_items":                        news[:12],
            "joseph_recent_videos":              yt_videos[:8],
            "recent_student_wins":               wins[:5],
        },
        "raw": {
            "reddit":  reddit,
            "youtube": youtube,
            "news":    news,
            "wins":    wins,
        },
        "counts": {
            "reddit_items":     len(reddit),
            "reddit_questions": len(reddit_questions),
            "yt_videos":        len(yt_videos),
            "yt_comments":      len(yt_comments),
            "yt_questions":     len(yt_questions),
            "news_items":       len(news),
            "student_wins":     len(wins),
        },
    }

def inline_into_dashboard(output: dict) -> None:
    si = output["synthesis_input"]
    c  = output["counts"]

    dashboard = {
        "generated_at": output["generated_at"],
        "research": {
            "reddit_questions": si["reddit_questions_ranked_by_score"][:15],
            "reddit_top_posts": si["reddit_top_posts"][:10],
            "youtube_questions": si["youtube_questions_ranked_by_likes"][:15],
            "youtube_comments":  si["youtube_top_comments"][:15],
            "news_items":        si["news_items"][:20],
            "joseph_videos":     si["joseph_recent_videos"][:8],
            "student_wins":      si["recent_student_wins"][:5],
        },
        "drafts": [],
        "stats": {
            "total_drafts":     0,
            "this_week_drafts": 0,
            "weekly_goal":      3,
            "reddit_items":     c["reddit_items"],
            "reddit_questions": c["reddit_questions"],
            "yt_comments":      c["yt_comments"],
            "yt_questions":     c["yt_questions"],
            "news_items":       c["news_items"],
        },
    }

    # Save standalone JSON for debugging
    out_json = ROOT / "dashboard-data.json"
    with open(out_json, "w") as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)
    print(f"  dashboard-data.json updated")

    # Inline into index.html
    index_path = ROOT / "index.html"
    if not index_path.exists():
        print(f"  WARNING: index.html not found at {index_path}", file=sys.stderr)
        return

    html = index_path.read_text(encoding="utf-8")
    data_js   = json.dumps(dashboard, ensure_ascii=False)
    new_block = f'<script id="researchDataScript">\nwindow.__RESEARCH__ = {data_js};\n</script>'

    html_new = re.sub(
        r'<script id="researchDataScript">.*?</script>',
        lambda _: new_block,
        html,
        flags=re.DOTALL
    )

    if html_new != html:
        index_path.write_text(html_new, encoding="utf-8")
        print(f"  index.html updated with fresh research data")
    else:
        print(f"  WARNING: researchDataScript placeholder not found in index.html", file=sys.stderr)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("Running newsletter research...\n")

    print("Fetching Reddit...")
    reddit = fetch_reddit()

    print("Fetching YouTube...")
    youtube = fetch_youtube()

    print("Fetching HUD / Section 8 news...")
    news = fetch_news()

    print("Fetching Airtable student wins...")
    wins = fetch_student_wins()

    output = build_output(reddit, youtube, news, wins)

    print("Inlining data into dashboard...")
    inline_into_dashboard(output)

    c = output["counts"]
    print(f"""
Done.

Signal summary:
  Reddit  — {c['reddit_items']} items ({c['reddit_questions']} questions)
  YouTube — {c['yt_videos']} videos, {c['yt_comments']} comments ({c['yt_questions']} questions)
  News    — {c['news_items']} items
  Wins    — {c['student_wins']} student wins
""")
    if output["youtube_skipped"]:
        print("  NOTE: YouTube was skipped. Set JOSEPH_YT_API_KEY to include it.")

if __name__ == "__main__":
    main()
