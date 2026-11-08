"""Hierarchical section-aware chunking."""

from __future__ import annotations

from app.ingestion.types import ChunkDraft, ParsedBlock, ParsedDocument

# Approximate tokens via whitespace-separated words (good enough for Phase 2).
DEFAULT_TARGET_TOKENS = 750
DEFAULT_MIN_TOKENS = 600
DEFAULT_MAX_TOKENS = 900
DEFAULT_OVERLAP_TOKENS = 100


def estimate_tokens(text: str) -> int:
    """Estimate token count without an external tokenizer."""
    words = [part for part in text.split() if part]
    return max(1, len(words)) if text.strip() else 0


def _heading_path(stack: list[tuple[int, str]]) -> str:
    return " / ".join(title for _, title in stack)


def _split_with_overlap(
    text: str,
    *,
    start_offset: int,
    heading_path: str,
    page_number: int | None,
    chunk_index_start: int,
    max_tokens: int,
    overlap_tokens: int,
) -> list[ChunkDraft]:
    words = text.split()
    if not words:
        return []

    chunks: list[ChunkDraft] = []
    index = chunk_index_start
    # Map word index -> character offset approximation using original text find.
    # Prefer stable offsets from the contiguous slice of `text`.
    cursor = 0
    word_spans: list[tuple[int, int]] = []
    for word in words:
        pos = text.find(word, cursor)
        if pos < 0:
            pos = cursor
        word_spans.append((pos, pos + len(word)))
        cursor = pos + len(word)

    start_word = 0
    while start_word < len(words):
        end_word = min(len(words), start_word + max_tokens)
        piece = " ".join(words[start_word:end_word])
        abs_start = start_offset + word_spans[start_word][0]
        abs_end = start_offset + word_spans[end_word - 1][1]
        chunks.append(
            ChunkDraft(
                chunk_index=index,
                text=piece,
                heading_path=heading_path,
                page_number=page_number,
                start_offset=abs_start,
                end_offset=abs_end,
                token_count=estimate_tokens(piece),
            )
        )
        index += 1
        if end_word >= len(words):
            break
        start_word = max(end_word - overlap_tokens, start_word + 1)
    return chunks


def chunk_document(
    parsed: ParsedDocument,
    *,
    target_tokens: int = DEFAULT_TARGET_TOKENS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[ChunkDraft]:
    """
    Chunk a parsed document without merging unrelated sections.

    Headings update the section path. Body blocks under one heading path are
    packed until max_tokens, then split with overlap. Different heading paths
    never share a chunk.
    """
    _ = target_tokens  # reserved for future soft packing preference
    heading_stack: list[tuple[int, str]] = []
    buffers: dict[str, list[ParsedBlock]] = {}
    order: list[str] = []

    def ensure_key(path: str) -> None:
        if path not in buffers:
            buffers[path] = []
            order.append(path)

    for block in parsed.blocks:
        if block.kind == "heading" and block.heading_level is not None:
            level = block.heading_level
            title = block.text.strip()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            ensure_key(_heading_path(heading_stack))
            continue

        path = _heading_path(heading_stack)
        ensure_key(path)
        buffers[path].append(block)

    drafts: list[ChunkDraft] = []
    next_index = 0
    for path in order:
        blocks = buffers[path]
        if not blocks:
            continue
        # Pack contiguous blocks under the same heading path.
        packed_parts: list[str] = []
        packed_start = blocks[0].start_offset
        packed_end = blocks[0].end_offset
        packed_page = blocks[0].page_number
        packed_tokens = 0

        for block in blocks:
            block_tokens = estimate_tokens(block.text)
            if packed_parts and packed_tokens + block_tokens > max_tokens:
                text = "\n\n".join(packed_parts)
                new_chunks = _split_with_overlap(
                    text,
                    start_offset=packed_start,
                    heading_path=path,
                    page_number=packed_page,
                    chunk_index_start=next_index,
                    max_tokens=max_tokens,
                    overlap_tokens=overlap_tokens,
                )
                drafts.extend(new_chunks)
                next_index += len(new_chunks)
                packed_parts = []
                packed_tokens = 0
                packed_start = block.start_offset
                packed_page = block.page_number
            if not packed_parts:
                packed_start = block.start_offset
                packed_page = block.page_number
            packed_parts.append(block.text)
            packed_end = block.end_offset
            packed_tokens += block_tokens
            if packed_tokens >= max_tokens:
                text = "\n\n".join(packed_parts)
                new_chunks = _split_with_overlap(
                    text,
                    start_offset=packed_start,
                    heading_path=path,
                    page_number=packed_page,
                    chunk_index_start=next_index,
                    max_tokens=max_tokens,
                    overlap_tokens=overlap_tokens,
                )
                drafts.extend(new_chunks)
                next_index += len(new_chunks)
                packed_parts = []
                packed_tokens = 0
                packed_start = packed_end

        if packed_parts:
            text = "\n\n".join(packed_parts)
            new_chunks = _split_with_overlap(
                text,
                start_offset=packed_start,
                heading_path=path,
                page_number=packed_page,
                chunk_index_start=next_index,
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
            )
            drafts.extend(new_chunks)
            next_index += len(new_chunks)

    # Re-number for safety.
    for i, draft in enumerate(drafts):
        draft.chunk_index = i
    return drafts
