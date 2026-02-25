from dataclasses import dataclass 
from typing import List, Dict, Any 
import re
import requests 
from urllib.parse import quote_plus
import requests
import feedparser 
from urllib.parse import quote, urlparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

@dataclass 
class Source: 
    title: str 
    url: str 
    publisher: str 
    published_at: str | None 
    domain_score: float 
    freshness_score: float 

@dataclass 
class Canidate: 
    provider: str 
    claim: str 
    answer: str 
    sources: List[Source] 
    base_confidence: float 
    reward_breakdown: Dict[str, float] 
    total_reward: float 
    reasoning_notes: List[str] 

MATH_KEYWORDS = {
    "sum", "difference", "product", "quotient", "percent", "percentage",
    "solve", "equation", "calculate", "average", "total", "how many",
    "how much", "per week", "per day", "allowance", "profit", "cost"
}

AMBIGUOUS_KEYWORDS = {
    "best", "top", "good", "better", "should i", "recommend", "vs",
    "compare", "worth it", "ideas", "suggest", "opinion"
}

"""This is to classify the Query type to save time upfront when agent is searching"""
def classify_query_type(query: str) -> str:  

    q = (query or "").strip().lower() 
    if not q: 
        return "factual" 

    # find Math score from RegEx
    math_score = 0
    if re.search(r"\d", q):
        math_score += 1
    if re.search(r"[\+\-\*/=]", q):
        math_score += 2
    if re.search(r"\$\s*\d+|\d+\s*%|\b\d+(\.\d+)?\b", q):
        math_score += 1
    if any(k in q for k in MATH_KEYWORDS):
        math_score += 2 

    # if it is not clear if the problem is factual or not
    ambiguous_score = 0
    if any(k in q for k in AMBIGUOUS_KEYWORDS): 
        ambiguous_score += 1
    if "or" in q: 
        ambiguous_score += 1 
    if len(q.split()) <= 3: 
        ambiguous_score += 1 
    

    # Then return based on scoring
    if math_score >= 3: 
        return "math" 
    if ambiguous_score >= 3: 
        return "ambiguous" 
    # default will be factual if no math or amb. score is found
    return 'factual' 



# fetch the DDG query using DDG API
def fetch_DDG(query: str) -> str: 
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
    } 

    resp = requests.get(url, params, timeout=10) 
    resp.raise_for_status()
    data = resp.json() 

    if data.get("AbstractText"): 
        return {
            "answer": data["AbstractText"],
            "source": data.get("AbstractSource", "DuckDuckGo"),
            "url": data.get("AbstractURL", "")            
        }

    related_topics = data.get("RelatedTopics", []) 
    for item in related_topics: 
        if "Text" in item: 
            return {
                "answer": item["Text"], 
                "source": "DuckDuckGo related Topics", 
                "url": item.get("FirstURL", "")
            }
   
    return {"answer": "No instant answer", "source": "DuckDuckGo", "url": ""} 

# Fetch using Google News API
def fetch_G_news(query: str) -> str: 
    rss_url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )   

    headers = {"UserAgent": "Fact-Checker-Agent"} 

    resp = requests.get(rss_url, headers=headers, timeout=10) 
    resp.raise_for_status() 

    feed = feedparser.parse(resp.text) 
    items = [] 

    for entry in feed.entries[5]: 
        title = entry.get("title", "").strip() 
        publisher = "" 
        if " - " in title: 
            title, publisher = title.rsplit(" - ", 1) 
        items.append( {
            "title": title, 
            "url" : entry.get("link", ""), 
            "publisher": publisher or "Google News", 
            "published_at": entry.get("published", None), 
            "domain_score": 0.5, 
            "freshness_score": 0.5,
        })
    return {
        "provider": "google_news", 
        "claim": query, 
        "answer": items[0]["title"] if items else "No results found", 
        "sources": items, 
        "base_confidence": 0.5 if items else 0.2,
        "reasoning_notes": ["Fetched from Google News"], 
    }

def fetch_Wikipedia(query: str) -> str:
    headers = {"User-Agent": "fact-checker-agent/1.0 (resume project)"}

    try:
        # Step 1: Find best-matching page title
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": 1,
        }

        s_resp = requests.get(search_url, params=search_params, headers=headers, timeout=10)
        s_resp.raise_for_status()
        s_data = s_resp.json()

        search_results = s_data.get("query", {}).get("search", [])
        if not search_results:
            return {
                "provider": "wikipedia",
                "claim": query,
                "answer": "No Wikipedia result found.",
                "sources": [],
                "base_confidence": 0.2,
                "reasoning_notes": ["Wikipedia search returned no hits."],
            }

        title = search_results[0]["title"]

        # Step 2: Get page summary by title
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
        p_resp = requests.get(summary_url, headers=headers, timeout=10)
        p_resp.raise_for_status()
        p_data = p_resp.json()

        extract = p_data.get("extract", "") or "No summary available."
        page_url = p_data.get("content_urls", {}).get("desktop", {}).get("page", "")

        return {
            "provider": "wikipedia",
            "claim": query,
            "answer": extract,
            "sources": [
                {
                    "title": title,
                    "url": page_url,
                    "publisher": "Wikipedia",
                    "published_at": None,
                    "domain_score": 0.8,
                    "freshness_score": 0.5,
                }
            ],
            "base_confidence": 0.75 if extract and extract != "No summary available." else 0.45,
            "reasoning_notes": [f"Selected top Wikipedia search hit: {title}"],
        }

    except requests.RequestException as e:
        return {
            "provider": "wikipedia",
            "claim": query,
            "answer": f"Wikipedia request failed: {e}",
            "sources": [],
            "base_confidence": 0.1,
            "reasoning_notes": ["Network/API error while calling Wikipedia."],
        } 

MAJOR_PUBLISHERS = {
    "reuters", "apnews", "bbc", "nytimes", "wsj", "bloomberg",
    "economist", "npr", "theguardian", "washingtonpost"
}

LOW_TRUST_HINTS = {
    "blogspot", "wordpress", "medium.com", "pinterest", "reddit.com"
}

def score_domain(url: str, publisher: str) -> float: 
    score = 0.50  # neutral baseline
    publisher_l = (publisher or "").lower()

    # Safe parse
    host = ""
    try:
        host = (urlparse(url).netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
    except Exception:
        host = ""

    # TLD / domain class rules
    if host.endswith(".gov"):
        score += 0.35
    elif host.endswith(".edu"):
        score += 0.30
    elif host.endswith(".org"):
        score += 0.10
    elif host.endswith(".com"):
        score += 0.00
    elif host == "":
        score -= 0.10  # unknown host

    # Major publisher boost
    if any(p in host for p in MAJOR_PUBLISHERS) or any(p in publisher_l for p in MAJOR_PUBLISHERS):
        score += 0.20

    # Lower-trust penalty
    if any(h in host for h in LOW_TRUST_HINTS):
        score -= 0.20

    # Clamp to [0, 1]
    return max(0.0, min(1.0, round(score, 3)))

def score_freshness(published_at: str | None) -> float: 
    """
    Freshness score in [0.0, 1.0].
    Newer content => higher score.
    Unknown date => neutral.
    """
    if not published_at:
        return 0.5

    dt = None
    s = published_at.strip()

    # Try RFC2822 (Google News RSS style), then ISO-8601 fallback
    try:
        dt = parsedate_to_datetime(s)
    except Exception:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return 0.5

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    age_days = max(0.0, (now - dt).total_seconds() / 86400.0)

    # Piecewise decay
    if age_days <= 1:
        score = 1.0
    elif age_days <= 7:
        score = 0.9
    elif age_days <= 30:
        score = 0.75
    elif age_days <= 90:
        score = 0.6
    elif age_days <= 365:
        score = 0.4
    else:
        score = 0.2

    return round(score, 3)
REWARD_WEIGHTS = {
    "base_confidence": 0.45, 
    "citation_quality": 0.30, 
    "freshness": 0.15, 
    "route_bonus": 0.10
}

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def compute_reward(
    base_confidence: float,
    citation_quality: float,
    freshness: float,
    route_bonus: float = 0.0,
    weights: dict | None = None,
):
    """
    Weighted reward in [0,1] + explainable breakdown.
    """
    w = weights or REWARD_WEIGHTS

    bc = _clamp01(base_confidence)
    cq = _clamp01(citation_quality)
    fr = _clamp01(freshness)
    rb = _clamp01(route_bonus)

    weighted = {
        "base_confidence": bc * w["base_confidence"],
        "citation_quality": cq * w["citation_quality"],
        "freshness": fr * w["freshness"],
        "route_bonus": rb * w["route_bonus"],
    }

    total = _clamp01(sum(weighted.values()))

    breakdown = {
        "raw": {
            "base_confidence": bc,
            "citation_quality": cq,
            "freshness": fr,
            "route_bonus": rb,
        },
        "weights": w,
        "weighted": {k: round(v, 4) for k, v in weighted.items()},
    }

    return round(total, 4), breakdown

def answer_query(query: str) -> dict: 
    q = (query or "").strip()
    query_type = classify_query_type(q)

    # Route bonus by query type
    route_bonus_by_type = {
        "math": 0.20,
        "factual": 0.10,
        "ambiguous": 0.05,
    }
    route_bonus = route_bonus_by_type.get(query_type, 0.0)

    # Pick providers by route
    provider_calls = []
    if query_type == "math":
        # For now still retrieve; you can add a local math solver later
        provider_calls = [fetch_DDG, fetch_Wikipedia]
    elif query_type == "ambiguous":
        provider_calls = [fetch_DDG, fetch_G_news, fetch_Wikipedia]
    else:  # factual
        provider_calls = [fetch_Wikipedia, fetch_DDG, fetch_G_news]

    candidates = []

    for fn in provider_calls:
        try:
            raw = fn(q)
        except Exception as e:
            raw = {
                "provider": fn.__name__,
                "claim": q,
                "answer": f"Provider failed: {e}",
                "sources": [],
                "base_confidence": 0.05,
                "reasoning_notes": [f"{fn.__name__} failed."],
            }

        # Normalize DDG shape (your DDG currently returns answer/source/url only)
        if "provider" not in raw:
            source_title = raw.get("source", "DuckDuckGo")
            source_url = raw.get("url", "")
            raw = {
                "provider": "duckduckgo",
                "claim": q,
                "answer": raw.get("answer", "No instant answer."),
                "sources": [
                    {
                        "title": source_title,
                        "url": source_url,
                        "publisher": source_title,
                        "published_at": None,
                        "domain_score": 0.5,
                        "freshness_score": 0.5,
                    }
                ] if source_url or source_title else [],
                "base_confidence": 0.60 if raw.get("answer") else 0.20,
                "reasoning_notes": ["Normalized DuckDuckGo response."],
            }

        sources = raw.get("sources", []) or []

        # Re-score each source using your scoring functions
        for s in sources:
            s["domain_score"] = score_domain(
                s.get("url", ""),
                s.get("publisher", "")
            )
            s["freshness_score"] = score_freshness(s.get("published_at"))

        # Aggregate source signals
        if sources:
            citation_quality = sum(s.get("domain_score", 0.5) for s in sources) / len(sources)
            freshness = sum(s.get("freshness_score", 0.5) for s in sources) / len(sources)
        else:
            citation_quality = 0.3
            freshness = 0.5

        total_reward, breakdown = compute_reward(
            base_confidence=raw.get("base_confidence", 0.3),
            citation_quality=citation_quality,
            freshness=freshness,
            route_bonus=route_bonus,
        )

        candidates.append({
            "provider": raw.get("provider", fn.__name__),
            "claim": raw.get("claim", q),
            "answer": raw.get("answer", "No answer."),
            "sources": sources,
            "confidence": round(total_reward, 4),
            "reward_breakdown": breakdown,
            "total_reward": total_reward,
            "reasoning_notes": raw.get("reasoning_notes", []),
        })

    if not candidates:
        return {
            "claim": q,
            "query_type": query_type,
            "answer": "No candidates returned.",
            "sources": [],
            "confidence": 0.0,
            "reasoning_notes": ["No provider candidates available."],
            "reward_breakdown": {},
            "candidate_rewards": [],
        }

    best = max(candidates, key=lambda c: c["total_reward"])

    return {
        "claim": best["claim"],
        "query_type": query_type,
        "answer": best["answer"],
        "sources": best["sources"],
        "confidence": best["confidence"],
        "reasoning_notes": best["reasoning_notes"] + [f"Selected provider: {best['provider']}"],
        "reward_breakdown": best["reward_breakdown"],
        "candidate_rewards": [
            {
                "provider": c["provider"],
                "total_reward": c["total_reward"],
            }
            for c in candidates
        ],
    }