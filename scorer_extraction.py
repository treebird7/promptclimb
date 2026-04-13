"""scorer_extraction.py — Promptclimb scorer for selfimprove extraction task.

Calls gemma-4-26b on M5 :8082 for extraction, i7 :8083 for embeddings.
Torrent shredding for long sections (>1200 chars → chunk → extract → dedup).
Loads gold/samples directly (selfimprove gold format ≠ promptclimb case format).

Usage:
    phc run --prompt prompt.md --eval scorer_extraction.py --gold gold/ \
        --iterations 30 --model http://localhost:8082/v1 \
        --proposer anthropic:haiku
"""

import glob
import json
import os
import re
import time

import numpy as np
import requests

TORRENT_CHUNK_SIZE = 1200
TORRENT_OVERLAP = 150

VALID_TYPES = {
    "decision",
    "finding",
    "pattern",
    "rule",
    "milestone",
    "capability",
    "integration",
}


def _generate(system: str, user: str) -> str:
    executor_url = os.environ.get("EXECUTOR_URL", "http://localhost:8082")
    executor_model = os.environ.get("SELFIMPROVE_EXECUTOR", "gemma-4-26b-a4b-it")

    for attempt in range(3):
        try:
            resp = requests.post(
                f"{executor_url}/v1/chat/completions",
                json={
                    "model": executor_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": 1024,
                    "temperature": 0,
                },
                timeout=(15, 300),
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"  [scorer] generate failed: {e}")
    return ""


def _embed(texts: list[str]) -> list[list[float]]:
    embedding_url = os.environ.get("EMBEDDING_URL", "http://localhost:8083")
    prefixed = [f"search_document: {t}" for t in texts]
    try:
        resp = requests.post(
            f"{embedding_url}/v1/embeddings",
            json={"input": prefixed, "model": "nomic-embed-text"},
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [d["embedding"] for d in sorted(data, key=lambda x: x["index"])]
    except Exception as e:
        print(f"  [scorer] embed failed: {e}")
        return []


def _cosine(a, b):
    a, b = np.array(a), np.array(b)
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / d) if d > 0 else 0.0


def _shred(
    text: str, chunk_size: int = TORRENT_CHUNK_SIZE, overlap: int = TORRENT_OVERLAP
) -> list[str]:
    """Split long text into overlapping chunks at paragraph/sentence boundaries."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
        search_start = max(start + chunk_size - 200, start)
        search_end = min(start + chunk_size + 200, len(text))
        zone = text[search_start:search_end]
        para = zone.rfind("\n\n")
        if para != -1:
            end = search_start + para + 2
        else:
            sent = zone.rfind(". ")
            if sent != -1:
                end = search_start + sent + 2
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def _dedup_concepts(concepts: list[dict]) -> list[dict]:
    """Deduplicate by lowercase name."""
    seen: set[str] = set()
    out = []
    for c in concepts:
        key = c.get("name", c.get("definition", "")).strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(c)
    return out


def _parse_extraction(text: str) -> list[dict]:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    fence = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [c for c in parsed if isinstance(c, dict) and "definition" in c]
    except json.JSONDecodeError:
        pass
    return []


def _split_prompt(prompt: str):
    for sep in [
        "---\n## USER TEMPLATE\n",
        "---\n## USER TEMPLATE",
        "## USER TEMPLATE\n",
        "## USER TEMPLATE",
    ]:
        idx = prompt.find(sep)
        if idx != -1:
            system = prompt[:idx].strip()
            user = prompt[idx + len(sep) :].strip()
            last_bracket = user.rfind("]")
            if last_bracket != -1:
                user = user[: last_bracket + 1].strip()
            return system, user
    return prompt.strip(), ""


def _score_section(extracted: list[dict], gold: list[dict]) -> float:
    if not gold:
        return 1.0
    if not extracted:
        return 0.0

    ext_defs = [c.get("definition", c.get("name", "")) for c in extracted]
    gold_defs = [c.get("definition", c.get("name", "")) for c in gold]

    all_vecs = _embed(ext_defs + gold_defs)
    if not all_vecs:
        return 0.0
    ext_vecs = all_vecs[: len(ext_defs)]
    gold_vecs = all_vecs[len(ext_defs) :]

    sim_scores = []
    best_idx = []
    for gv in gold_vecs:
        sims = [_cosine(gv, ev) for ev in ext_vecs]
        bi = int(np.argmax(sims))
        sim_scores.append(sims[bi])
        best_idx.append(bi)
    similarity = float(np.mean(sim_scores))

    type_hits = []
    for gi, gc in enumerate(gold):
        gt = gc.get("type", "").strip().lower()
        if gt not in VALID_TYPES:
            continue
        et = extracted[best_idx[gi]].get("type", "").strip().lower()
        type_hits.append(1.0 if et == gt else 0.0)
    type_match = float(np.mean(type_hits)) if type_hits else 0.5

    precision = min(1.0, len(gold) / len(extracted)) if extracted else 0.0

    return 0.7 * similarity + 0.2 * type_match + 0.1 * precision


def score(prompt: str, cases: list) -> float:
    """Promptclimb scorer interface.

    Ignores `cases` (format mismatch) — loads gold/samples directly from
    selfimprove directories. This is honest dogfooding: promptclimb's generic
    case format doesn't fit extraction gold data, and that's a v0.2 fix.
    """
    system, user_template = _split_prompt(prompt)
    if not user_template:
        return 0.0

    samples_dir = os.environ.get(
        "SAMPLES_DIR",
        os.environ.get(
            "PHC_SAMPLES_DIR",
            os.path.join(os.path.dirname(__file__), "..", "selfimprove", "samples"),
        ),
    )
    gold_dir = os.environ.get(
        "PHC_GOLD_DIR",
        os.path.join(os.path.dirname(__file__), "..", "selfimprove", "gold"),
    )
    sample_files = sorted(glob.glob(os.path.join(samples_dir, "section_*.md")))
    golds = {
        os.path.basename(p).replace(".md", ".json"): p
        for p in sorted(glob.glob(os.path.join(gold_dir, "section_*.json")))
    }

    section_scores = []
    for sample_path in sample_files:
        base = os.path.basename(sample_path).replace(".md", ".json")
        gold_path = golds.get(base)
        if not gold_path:
            continue

        gold_items = json.load(open(gold_path))
        if not gold_items:
            continue

        raw = open(sample_path).read()
        title_match = re.search(r"## Title: (.+)", raw)
        title = (
            title_match.group(1).strip()
            if title_match
            else os.path.basename(sample_path)
        )
        content = raw.split("\n", 2)[-1].strip() if title_match else raw

        # Torrent shredding for long sections
        if len(content) > TORRENT_CHUNK_SIZE:
            chunks = _shred(content)
            all_concepts = []
            for ci, chunk in enumerate(chunks):
                user_prompt = user_template.replace(
                    "{title}", f"{title} (part {ci + 1}/{len(chunks)})"
                ).replace("{content}", chunk)
                output = _generate(system, user_prompt)
                all_concepts.extend(_parse_extraction(output))
            extracted = _dedup_concepts(all_concepts)
            mode = "torrent"
        else:
            user_prompt = user_template.replace("{title}", title).replace(
                "{content}", content
            )
            output = _generate(system, user_prompt)
            extracted = _parse_extraction(output)
            mode = "single"

        sec_score = _score_section(extracted, gold_items)
        section_scores.append(sec_score)
        print(f"  {base}: {len(extracted)} concepts, fitness={sec_score:.4f} [{mode}]")

    if not section_scores:
        return 0.0

    avg = sum(section_scores) / len(section_scores)
    print(f"  AVG FITNESS: {avg:.4f} ({len(section_scores)} samples)")
    return avg
