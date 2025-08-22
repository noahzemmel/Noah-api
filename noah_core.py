# noah_core.py
import os
import io
import re
import math
import json
import time
import base64
import random
import requests
from typing import List, Dict, Tuple
from datetime import datetime, timezone, timedelta

from dateutil import parser as dateparse
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from openai import OpenAI

# ----------------------------
# ENV
# ----------------------------
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
ELEVEN_API_KEY   = os.getenv("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE_ID  = os.getenv("ELEVENLABS_VOICE_ID", "")  # optional default
TAVILY_API_KEY   = os.getenv("TAVILY_API_KEY", "")

oai = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------
# Constants / Tunables
# ----------------------------
# 1. Recency
DEFAULT_LOOKBACK_H = 24               # overwritten by payload
MAX_RESULTS_PER_TOPIC = 20            # increased from 12 for better content coverage
BATCH_FETCH = 8                       # increased from 6 for more content per batch

# 2. Script sizing (empirical)
# ElevenLabs default voices are ~13.8–15.5 characters / second at normal pitch/rate.
CHARS_PER_SEC = 14.2

# 3. Audio timing
TRIM_HEAD_MS = 180
TRIM_TAIL_MS = 220
SILENCE_DB = -38.0

# 4. Time-stretch clamp to avoid artifacts
STRETCH_MIN = 0.80    # don't slow down more than 1/0.80 ≈ +25%
STRETCH_MAX = 1.25    # don't speed up more than 25%

# 5. Content quality thresholds
MIN_CONTENT_RATIO = 0.85  # aim for at least 85% of target time with actual content
MAX_CONTENT_RATIO = 1.15  # don't exceed 115% of target time

ELEVEN_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# ----------------------------
# Utilities
# ----------------------------
def _now_utc():
    return datetime.now(timezone.utc)

def _safe_parse_date(s):
    try:
        dt = dateparse.parse(s)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def _normalize_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip()
    u = re.sub(r"#.*$", "", u)
    u = re.sub(r"\?.*$", "", u)
    u = u.replace("http://", "https://")
    return u

def _dedupe_items(items: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for it in items:
        key = (it.get("title","").strip().lower(), _normalize_url(it.get("url","")))
        if key not in seen and it.get("url"):
            seen.add(key)
            out.append(it)
    return out

def _prioritize_news_items(items: List[Dict], max_items: int) -> List[Dict]:
    """
    Prioritize news items by recency and relevance.
    """
    if not items:
        return []
    
    # Sort by recency first (most recent first)
    def get_timestamp(item):
        published = item.get("published", "")
        if not published:
            return datetime.min.replace(tzinfo=timezone.utc)
        dt = _safe_parse_date(published)
        return dt if dt else datetime.min.replace(tzinfo=timezone.utc)
    
    # Sort by recency, then take top items
    sorted_items = sorted(items, key=get_timestamp, reverse=True)
    
    # Prioritize items with more complete information
    def item_quality_score(item):
        score = 0
        if item.get("title") and len(item["title"]) > 20:
            score += 2
        if item.get("source"):
            score += 1
        if item.get("published"):
            score += 1
        return score
    
    # Sort by quality within recency groups
    sorted_items = sorted(sorted_items, key=item_quality_score, reverse=True)
    
    return sorted_items[:max_items]

# ----------------------------
# Tavily news fetch (recency strict)
# ----------------------------
def _tavily_news(query: str, lookback_h: int, limit: int) -> List[Dict]:
    """
    Use Tavily's /search in news mode.
    We try 'time_range' (hXX) first; if provider complains, fall back to 'days'.
    """
    if not TAVILY_API_KEY:
        return []
    url = "https://api.tavily.com/search"
    payload_base = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "include_answer": False,
        "include_raw_content": False,
        "max_results": min(limit, 10),
        "topic": "news"
    }
    out = []
    # primary attempt – hours window
    try:
        p = dict(payload_base)
        p["time_range"] = f"h{max(1, int(lookback_h))}"
        r = requests.post(url, json=p, timeout=40)
        if r.ok:
            data = r.json()
            for res in data.get("results", []):
                out.append({
                    "title": res.get("title") or "",
                    "url":   _normalize_url(res.get("url") or ""),
                    "source": res.get("source") or "",
                    "published": res.get("published_time") or res.get("published_date") or ""
                })
    except Exception:
        pass

    # fallback – days
    if not out:
        try:
            p = dict(payload_base)
            p["days"] = max(1, int(math.ceil(lookback_h/24)))
            r = requests.post(url, json=p, timeout=40)
            if r.ok:
                data = r.json()
                for res in data.get("results", []):
                    out.append({
                        "title": res.get("title") or "",
                        "url":   _normalize_url(res.get("url") or ""),
                        "source": res.get("source") or "",
                        "published": res.get("published_time") or res.get("published_date") or ""
                    })
        except Exception:
            pass
    # filter to window strictly
    cutoff = _now_utc() - timedelta(hours=lookback_h)
    strict = []
    for it in out:
        when = _safe_parse_date(it.get("published") or "")
        if when and when >= cutoff and it.get("url"):
            strict.append({**it, "published": when.isoformat()})
    return _dedupe_items(strict)

# ----------------------------
# Enhanced Script building with dynamic content allocation
# ----------------------------
def _allocate_char_budget_dynamic(total_sec: int, topics_n: int, head_tail_sec=8) -> Tuple[int, int, List[int]]:
    """
    Reserve intro/outro then dynamically allocate the rest based on content availability.
    """
    total_chars = max(200, int((total_sec - head_tail_sec) * CHARS_PER_SEC))
    per_topic = max(200, total_chars // max(1, topics_n))
    return total_chars, per_topic, [per_topic]*topics_n

def _llm_script_for_topic_enhanced(topic: str, items: List[Dict], char_budget: int, language: str, tone: str, target_seconds: float) -> Tuple[str, List[Dict], float]:
    """
    Enhanced version that returns (script_text, used_items, estimated_seconds).
    """
    if not items:
        return "", [], 0.0
    
    # Build comprehensive context with more details
    cites = []
    for idx, it in enumerate(items, 1):
        # Include more context for better summarization
        source_info = f" — {it.get('source','')}" if it.get('source') else ""
        time_info = f" ({it.get('published','')})" if it.get('published') else ""
        cites.append(f"[{idx}] {it['title']}{source_info}{time_info} :: {it['url']}")

    # Calculate target sentences based on time
    target_sentences = max(3, min(15, int(target_seconds * 0.8)))  # 0.8 factor for natural pacing
    
    sys = (
        "You are a professional news anchor. Create a concise, engaging summary using ONLY facts from the provided sources. "
        "Focus on the most recent and impactful developments. Write in {language}, tone: {tone}. "
        "Use clear, conversational sentences suitable for voice-over. Aim for approximately {sentences} sentences."
    ).format(language=language, tone=tone, sentences=target_sentences)

    user = (
        "TOPIC: {topic}\n"
        "TARGET_CHARS: {chars} (approximately {seconds:.1f} seconds)\n"
        "RULES:\n"
        " - Use ONLY facts from the SOURCES list (do not invent anything).\n"
        " - Prioritize news from the last 24 hours when possible.\n"
        " - Every sentence should be informative and engaging.\n"
        " - Vary sentence length for natural flow.\n"
        " - Output plain text (no markdown).\n\n"
        "SOURCES:\n{src}\n\n"
        "Write the script now. If sources are insufficient for {topic}, write a brief summary of what's available."
    ).format(topic=topic, chars=char_budget, seconds=target_seconds, src="\n".join(cites))

    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {"role":"system","content":sys},
            {"role":"user","content":user}
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    
    # Enforce hard char ceiling
    if len(text) > char_budget:
        text = text[:char_budget].rsplit(".", 1)[0] + "."
    
    # Estimate actual seconds
    estimated_seconds = len(text) / CHARS_PER_SEC
    
    return text, items, estimated_seconds

def _compose_full_script_enhanced(intro: str, segments: List[Tuple[str,str]], outro: str, target_seconds: float) -> Tuple[str, float]:
    """
    Enhanced composition that tracks actual content length and adjusts if needed.
    """
    parts = []
    if intro: parts.append(intro.strip())
    for h, b in segments:
        if b.strip():
            if h: parts.append(h.strip())
            parts.append(b.strip())
    if outro: parts.append(outro.strip())
    script = "\n\n".join([p for p in parts if p])
    # Normalize spaces
    script = re.sub(r"[ \t]+", " ", script)
    script = script.strip()
    
    # Calculate actual content time
    actual_seconds = len(script) / CHARS_PER_SEC
    
    return script, actual_seconds

def _expand_content_for_timing(topics: List[str], sources_by_topic: Dict, target_seconds: float, 
                             current_seconds: float, language: str, tone: str, 
                             lookback_hours: int, max_expansions: int = 3) -> Tuple[List[Tuple[str,str]], float]:
    """
    Dynamically expand content to reach target timing.
    """
    if current_seconds >= target_seconds * MIN_CONTENT_RATIO:
        return [], current_seconds
    
    segments = []
    remaining_time = target_seconds - current_seconds
    expansion_attempts = 0
    
    while current_seconds < target_seconds * MIN_CONTENT_RATIO and expansion_attempts < max_expansions:
        expansion_attempts += 1
        
        # Calculate how much more content we need
        needed_seconds = target_seconds - current_seconds
        needed_chars = int(needed_seconds * CHARS_PER_SEC)
        
        # Try to expand each topic with additional content
        for topic in topics:
            if current_seconds >= target_seconds * MIN_CONTENT_RATIO:
                break
                
            current_sources = sources_by_topic.get(topic, [])
            if len(current_sources) >= MAX_RESULTS_PER_TOPIC:
                continue
            
            # Fetch additional content
            additional_needed = min(BATCH_FETCH, MAX_RESULTS_PER_TOPIC - len(current_sources))
            additional_items = _tavily_news(topic, lookback_hours, additional_needed)
            
            # Filter out duplicates
            existing_urls = {s["url"] for s in current_sources}
            fresh_items = [item for item in additional_items if item["url"] not in existing_urls]
            
            if not fresh_items:
                continue
            
            # Calculate budget for this expansion
            expansion_chars = min(needed_chars // len(topics), int(needed_seconds * CHARS_PER_SEC // len(topics)))
            expansion_chars = max(200, expansion_chars)
            
            # Generate additional content
            additional_script, used_items, est_seconds = _llm_script_for_topic_enhanced(
                topic, fresh_items, expansion_chars, language, tone, needed_seconds / len(topics)
            )
            
            if additional_script.strip():
                # Add to segments
                segments.append((f"Additional {topic}:", additional_script))
                
                # Update tracking
                current_seconds += est_seconds
                sources_by_topic[topic].extend(used_items)
                
                # Update remaining time
                remaining_time = target_seconds - current_seconds
                if remaining_time <= 0:
                    break
        
        # If we can't expand more, try to add filler content
        if current_seconds < target_seconds * MIN_CONTENT_RATIO and expansion_attempts >= 2:
            filler_chars = int((target_seconds - current_seconds) * CHARS_PER_SEC)
            if filler_chars > 100:
                filler_script = _generate_filler_content(topics, filler_chars, language, tone)
                if filler_script:
                    segments.append(("Additional insights:", filler_script))
                    current_seconds += len(filler_script) / CHARS_PER_SEC
    
    return segments, current_seconds

def _generate_filler_content(topics: List[str], char_budget: int, language: str, tone: str) -> str:
    """
    Generate contextual filler content when we need more material.
    """
    if char_budget < 100:
        return ""
    
    # Create a context-aware filler that relates to the topics
    topic_summary = ", ".join(topics[:3])  # Use first 3 topics
    
    sys = (
        "You are a news analyst. Create a brief, engaging transition or contextual note "
        "that relates to the topics: {topics}. Write in {language}, tone: {tone}. "
        "Keep it informative and relevant. Maximum {chars} characters."
    ).format(topics=topic_summary, language=language, tone=tone, chars=char_budget)
    
    user = (
        "Create a brief, contextual note that could serve as a transition or additional insight "
        "related to these news topics: {topics}. "
        "This should be 2-3 sentences maximum, engaging, and relevant to current events. "
        "Do not invent specific facts, but you can provide general context or observations."
    ).format(topics=topic_summary)
    
    try:
        resp = oai.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            messages=[
                {"role":"system","content":sys},
                {"role":"user","content":user}
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        
        # Enforce character limit
        if len(text) > char_budget:
            text = text[:char_budget].rsplit(".", 1)[0] + "."
        
        return text
    except Exception:
        return ""

def _generate_dynamic_intro(topics: List[str], language: str, tone: str, target_seconds: float) -> str:
    """
    Generate a dynamic, engaging introduction based on topics and timing.
    """
    topic_count = len(topics)
    topic_summary = ", ".join(topics[:3]) if topics else "today's top stories"
    
    # Adjust intro length based on total briefing time
    if target_seconds < 300:  # Less than 5 minutes
        intro_style = "brief"
    elif target_seconds < 600:  # 5-10 minutes
        intro_style = "standard"
    else:  # More than 10 minutes
        intro_style = "detailed"
    
    if intro_style == "brief":
        return f"Welcome to Noah. Here's your {target_seconds/60:.0f}-minute briefing on {topic_summary}."
    elif intro_style == "standard":
        return f"Good day! This is Noah with your {target_seconds/60:.0f}-minute briefing covering {topic_count} key areas: {topic_summary}."
    else:
        return f"Welcome to your comprehensive Noah briefing. We'll spend the next {target_seconds/60:.0f} minutes diving deep into {topic_count} critical topics: {topic_summary}. Let's begin."

def _generate_dynamic_outro(topics: List[str], language: str, tone: str) -> str:
    """
    Generate a dynamic, engaging conclusion based on content.
    """
    topic_count = len(topics)
    
    if topic_count <= 2:
        return "That concludes your Noah briefing. Stay informed and have a great day."
    elif topic_count <= 4:
        return f"Thank you for listening to Noah. We've covered {topic_count} key topics to keep you informed. See you next time."
    else:
        return f"That's your comprehensive Noah briefing covering {topic_count} important areas. Stay ahead of the news with Noah. Until next time."

# ----------------------------
# Audio helpers
# ----------------------------
def trim_silence(seg: AudioSegment, head_ms: int = TRIM_HEAD_MS, tail_ms: int = TRIM_TAIL_MS, threshold_db: float = SILENCE_DB) -> AudioSegment:
    try:
        lead = detect_leading_silence(seg, silence_threshold=threshold_db)
        rev  = seg.reverse()
        trail = detect_leading_silence(rev, silence_threshold=threshold_db)
    except TypeError:
        lead = detect_leading_silence(seg, threshold_db)
        rev  = seg.reverse()
        trail = detect_leading_silence(rev, threshold_db)

    start = max(0, lead - head_ms)
    end   = len(seg) - max(0, trail - tail_ms)
    trimmed = seg[start:end]
    if len(trimmed) < 200:
        trimmed = trimmed + AudioSegment.silent(duration=200)
    return trimmed

def _time_stretch(seg: AudioSegment, factor: float) -> AudioSegment:
    """
    factor > 1 => longer audio; factor < 1 => shorter audio
    Uses frame-rate trick to keep pitch pleasant.
    """
    factor = max(STRETCH_MIN, min(STRETCH_MAX, factor))
    new_rate = int(seg.frame_rate / factor)
    stretched = seg._spawn(seg.raw_data, overrides={'frame_rate': new_rate})
    return stretched.set_frame_rate(seg.frame_rate)

def _eleven_tts(text: str, voice_id: str) -> AudioSegment:
    if not ELEVEN_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY missing")
    if not voice_id:
        if not ELEVEN_VOICE_ID:
            raise RuntimeError("No ElevenLabs voice_id configured")
        voice_id = ELEVEN_VOICE_ID

    url = f"{ELEVEN_TTS_URL}/{voice_id}/stream?optimize_streaming_latency=4"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json"
    }
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.46, "similarity_boost": 0.7, "style": 0.25, "use_speaker_boost": True}
    }
    r = requests.post(url, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    raw = io.BytesIO(r.content)
    seg = AudioSegment.from_file(raw, format="mp3")
    return seg

# ----------------------------
# Public entry
# ----------------------------
def health_check() -> Dict:
    return {
        "openai": bool(OPENAI_API_KEY),
        "elevenlabs": bool(ELEVEN_API_KEY),
        "tavily": bool(TAVILY_API_KEY),
        "ok": bool(OPENAI_API_KEY and ELEVEN_API_KEY and TAVILY_API_KEY)
    }

def make_noah_audio(
    queries: List[str],
    minutes: int,
    language: str,
    tone: str,
    lookback_hours: int,
    cap_per_topic: int,
    strict_timing: bool,
    voice_id: str = ""
) -> Dict:
    """
    Returns: dict with keys:
      ok, target_sec, actual_sec, playback_rate, mp3_path, bullets_by_topic, sources_by_topic
    """
    assert minutes >= 2
    target_sec = minutes * 60

    # 1) Fetch recent sources per topic, with possible expansion
    all_segments = []
    bullets_out = {}
    sources_out = {}

    topics = [q.strip() for q in queries if q.strip()]
    topics = topics[:6] if topics else ["Top headlines"]  # safety

    total_chars, per_topic_chars, per_topic_budgets = _allocate_char_budget_dynamic(target_sec, len(topics))
    per_topic_limit = max(2, min(MAX_RESULTS_PER_TOPIC, cap_per_topic))

    for i, topic in enumerate(topics):
        gathered = []
        attempts = 0
        while len(gathered) < per_topic_limit and attempts < 3:
            need = min(BATCH_FETCH, per_topic_limit - len(gathered))
            got = _tavily_news(topic, lookback_hours, limit=need)
            # de-dup with ones we already have
            cur_urls = {g["url"] for g in gathered}
            fresh = [x for x in got if x["url"] not in cur_urls]
            if not fresh:
                break
            gathered.extend(fresh)
            attempts += 1

        # If absolutely nothing, skip this topic
        if not gathered:
            continue

        # Prioritize the best news items for this topic
        prioritized_items = _prioritize_news_items(gathered, per_topic_limit)

        # Build a compact script from only these fresh items
        body, used, est_seconds = _llm_script_for_topic_enhanced(topic, prioritized_items, per_topic_budgets[i], language, tone, target_sec / len(topics))

        # record bullets and sources to show in UI
        bullets_out[topic] = [f"- {u['title']}" for u in used]
        sources_out[topic] = used

        all_segments.append((f"{topic}:", body))

    # 2) Compose full script with dynamic intro/outro based on content
    intro = _generate_dynamic_intro(topics, language, tone, target_sec)
    outro = _generate_dynamic_outro(topics, language, tone)
    script, actual_sec = _compose_full_script_enhanced(intro, all_segments, outro, target_sec)

    # Enhanced content expansion to reach target timing
    if actual_sec < target_sec * MIN_CONTENT_RATIO:
        # Use the new dynamic expansion system
        additional_segments, final_actual_sec = _expand_content_for_timing(
            topics, sources_out, target_sec, actual_sec, language, tone, lookback_hours
        )
        
        # Add additional segments to the main script
        all_segments.extend(additional_segments)
        
        # Update bullets for additional content
        for header, content in additional_segments:
            if header.startswith("Additional "):
                topic_name = header.replace("Additional ", "").replace(":", "")
                if topic_name in bullets_out:
                    # Add a summary bullet for the additional content
                    bullets_out[topic_name].append(f"- Additional updates on {topic_name}")
        
        # Re-compose with all content
        script, actual_sec = _compose_full_script_enhanced(intro, all_segments, outro, target_sec)

    # 3) TTS once; then time-stretch to exact target if strict requested
    #    Enhanced timing control with content quality preservation
    voice_to_use = voice_id or ELEVEN_VOICE_ID
    if not voice_to_use:
        raise RuntimeError("No voice_id configured for ElevenLabs.")

    audio = _eleven_tts(script, voice_to_use)
    audio = trim_silence(audio)

    actual = len(audio) / 1000.0
    rate = 1.0

    # Enhanced timing control - only stretch if we're significantly off target
    if strict_timing and abs(actual - target_sec) > 2.0:
        # Calculate stretch factor with bounds
        rate = target_sec / actual
        rate = max(STRETCH_MIN, min(STRETCH_MAX, rate))
        
        # Only apply stretch if it's reasonable
        if 0.9 <= rate <= 1.1:
            audio = _time_stretch(audio, factor=rate)
            audio = trim_silence(audio)
            actual = len(audio) / 1000.0
        else:
            # If stretch would be too aggressive, try to adjust content instead
            if actual < target_sec * 0.8:
                # Content is too short - add more content if possible
                additional_chars = int((target_sec - actual) * CHARS_PER_SEC)
                if additional_chars > 200:
                    filler = _generate_filler_content(topics, additional_chars, language, tone)
                    if filler:
                        # Re-generate audio with filler
                        extended_script = script + "\n\n" + filler
                        audio = _eleven_tts(extended_script, voice_to_use)
                        audio = trim_silence(audio)
                        actual = len(audio) / 1000.0
                        script = extended_script

    # 4) Persist mp3 to disk for download
    safe_ts = int(time.time())
    fname = f"noah_{safe_ts}.mp3"
    out_dir = os.getenv("AUDIO_DIR", "/tmp")
    os.makedirs(out_dir, exist_ok=True)
    fpath = os.path.join(out_dir, fname)
    audio.export(fpath, format="mp3", bitrate="128k")

    return {
        "ok": True,
        "target_sec": target_sec,
        "actual_sec": round(actual, 2),
        "playback_rate": round(rate, 3),
        "mp3_path": fpath,
        "bullets_by_topic": bullets_out,
        "sources_by_topic": sources_out,
        "script_chars": len(script)
    }
