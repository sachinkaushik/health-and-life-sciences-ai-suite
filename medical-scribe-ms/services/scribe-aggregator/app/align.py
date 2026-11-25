# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Speaker alignment: gives each transcribed word the diarization speaker it overlaps most, groups
words into sentences and picks each sentence's speaker by a duration-weighted vote.

Ported from the Demo Studio sample (frontend/src/samples/medical-scribe/lib/alignment), where it ran
in the browser. Three tiers: word timestamps, else segment timestamps split by length, else the
text split across speaker turns by duration."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import TypedDict

SENTENCE_TERMINATOR = re.compile(r"[.!?。！？；…]+[\"')\]」』）]*$")
MAX_DESYNC_FRACTION = 0.15
MAX_PIECES_PER_TOKEN = 4
MIN_WORD_WEIGHT = 0.01
TIE_BREAK_BONUS = 0.01

_CJK_CHAR = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u309f\u30a0-\u30ff"
_CJK_PUNCT = "\u3000-\u303f\uff01-\uff65"
CJK_ANY = re.compile(f"[{_CJK_CHAR}{_CJK_PUNCT}]")


class Timed(TypedDict):
    text: str
    start: float
    end: float


class Segment(TypedDict):
    speaker: str
    start: float
    end: float


class Entry(TypedDict):
    speaker: str
    text: str
    start: float
    end: float


@dataclass
class Token:
    text: str
    start: float
    end: float
    boundary: bool = False
    speaker: str = ""


def tokenize(text: str) -> list[str]:
    """Whitespace tokens; CJK runs split into single characters, non-CJK runs kept whole."""
    tokens: list[str] = []
    for chunk in text.strip().split():
        if not CJK_ANY.search(chunk):
            tokens.append(chunk)
            continue
        run = ""
        for ch in chunk:
            if CJK_ANY.match(ch):
                if run:
                    tokens.append(run)
                    run = ""
                tokens.append(ch)
            else:
                run += ch
        if run:
            tokens.append(run)
    return tokens


def join_tokens(parts: list[str]) -> str:
    """Joins with spaces, except next to CJK characters."""
    result = ""
    for part in parts:
        if not part:
            continue
        if not result:
            result = part
            continue
        needs_space = not (CJK_ANY.match(result[-1]) or CJK_ANY.match(part[0]))
        result += (" " if needs_space else "") + part
    return result


def normalize_word(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


def words_to_tokens(full_text: str, words: list[Timed]) -> list[Token] | None:
    """Reconciles the punctuated text with word timings (which may be split or unpunctuated);
    None when too many tokens can't be matched."""
    tokens = tokenize(full_text)
    if not tokens or not words:
        return None
    result: list[Token] = []
    w = 0
    desyncs = 0
    last_end = words[0]["start"]
    for token in tokens:
        target = normalize_word(token)
        if not target:
            result.append(Token(token, last_end, last_end))
            continue
        if w >= len(words):
            result.append(Token(token, last_end, last_end))
            desyncs += 1
            continue
        acc = ""
        start = words[w]["start"]
        end = start
        consumed = 0
        while w + consumed < len(words) and len(acc) < len(target) and consumed < MAX_PIECES_PER_TOKEN:
            piece = words[w + consumed]
            acc += normalize_word(piece["text"])
            end = piece["end"]
            consumed += 1
        if consumed > 0 and acc == target:
            w += consumed
            result.append(Token(token, start, end))
            last_end = end
            continue
        piece = words[w]
        result.append(Token(token, piece["start"], piece["end"]))
        w += 1
        desyncs += 1
        last_end = piece["end"]
    if desyncs / len(tokens) > MAX_DESYNC_FRACTION:
        return None
    return result


def segments_to_tokens(segments: list[Timed]) -> list[Token]:
    """Splits each timed chunk into words with spans proportional to their length."""
    tokens: list[Token] = []
    for chunk in segments:
        text = chunk["text"].strip()
        if not text:
            continue
        words = tokenize(text)
        duration = max(0.0, chunk["end"] - chunk["start"])
        total = sum(len(word) for word in words) or len(words)
        elapsed = 0
        for i, word in enumerate(words):
            start_frac = elapsed / total
            elapsed += len(word) or 1
            tokens.append(
                Token(
                    word,
                    chunk["start"] + start_frac * duration,
                    chunk["start"] + (elapsed / total) * duration,
                    boundary=i == len(words) - 1,
                )
            )
    return tokens


def _overlap(tok: Token, seg: Segment) -> float:
    return min(tok.end, seg["end"]) - max(tok.start, seg["start"])


def _distance(tok: Token, seg: Segment) -> float:
    mid = (tok.start + tok.end) / 2
    if mid < seg["start"]:
        return seg["start"] - mid
    if mid > seg["end"]:
        return mid - seg["end"]
    return 0.0


def _assign_speaker(tok: Token, segs: list[Segment], cursor: int, latest_ended: Segment | None) -> str:
    best = segs[cursor]
    best_overlap = float("-inf")
    j = cursor
    while j < len(segs) and segs[j]["start"] < tok.end:
        overlap = _overlap(tok, segs[j])
        if overlap > best_overlap:
            best_overlap = overlap
            best = segs[j]
        j += 1
    if best_overlap > 0:
        return best["speaker"]
    if latest_ended and _distance(tok, latest_ended) < _distance(tok, best):
        return latest_ended["speaker"]
    return best["speaker"]


def _align_tokens(tokens: list[Token], segs: list[Segment]) -> list[Entry]:
    if not tokens or not segs:
        return []
    seg_idx = 0
    latest_ended: Segment | None = None
    tagged: list[Token] = []
    for tok in tokens:
        while seg_idx < len(segs) - 1 and segs[seg_idx]["end"] <= tok.start:
            skipped = segs[seg_idx]
            if latest_ended is None or skipped["end"] > latest_ended["end"]:
                latest_ended = skipped
            seg_idx += 1
        tagged.append(replace(tok, speaker=_assign_speaker(tok, segs, seg_idx, latest_ended)))

    sentences: list[list[Token]] = []
    current: list[Token] = []
    for tok in tagged:
        current.append(tok)
        if SENTENCE_TERMINATOR.search(tok.text) or tok.boundary:
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)

    merged: list[Entry] = []
    prev_speaker: str | None = None
    for sentence in sentences:
        weights: dict[str, float] = {}
        for tok in sentence:
            weights[tok.speaker] = weights.get(tok.speaker, 0.0) + max(tok.end - tok.start, MIN_WORD_WEIGHT)
        speaker = sentence[0].speaker
        best_weight = float("-inf")
        for candidate, weight in weights.items():
            adjusted = weight + TIE_BREAK_BONUS if candidate == prev_speaker else weight
            if adjusted > best_weight:
                best_weight = adjusted
                speaker = candidate
        text = join_tokens([t.text for t in sentence])
        start, end = sentence[0].start, sentence[-1].end
        if merged and merged[-1]["speaker"] == speaker:
            merged[-1]["text"] = join_tokens([merged[-1]["text"], text]).strip()
            merged[-1]["end"] = end
        else:
            merged.append({"speaker": speaker, "text": text, "start": start, "end": end})
        prev_speaker = speaker
    return merged


def align_by_duration(full_text: str, segs: list[Segment]) -> list[Entry]:
    words = tokenize(full_text)
    total = sum(s["end"] - s["start"] for s in segs)
    index = 0
    out: list[Entry] = []
    for i, seg in enumerate(segs):
        fraction = (seg["end"] - seg["start"]) / total if total > 0 else 1 / len(segs)
        remaining = len(words) - index
        count = remaining if i == len(segs) - 1 else min(max(0, round(fraction * len(words))), remaining)
        out.append(
            {
                "speaker": seg["speaker"],
                "text": join_tokens(words[index : index + count]),
                "start": seg["start"],
                "end": seg["end"],
            }
        )
        index += count
    return out


def align_transcript(
    full_text: str,
    segs: list[Segment],
    words: list[Timed] | None = None,
    segments: list[Timed] | None = None,
) -> list[Entry]:
    """Best available alignment of a transcription with diarization segments."""
    if not segs or not full_text.strip():
        return []
    segs = sorted(segs, key=lambda s: (s["start"], s["end"]))
    if words:
        tokens = words_to_tokens(full_text, words)
        if tokens:
            result = _align_tokens(tokens, segs)
            if result:
                return result
    if segments:
        result = _align_tokens(segments_to_tokens(segments), segs)
        if result:
            return result
    return align_by_duration(full_text, segs)
