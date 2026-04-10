from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        # Split on sentence boundaries: ". ", "! ", "? ", or ".\n"
        # We use a regex that splits on these patterns while keeping the
        # delimiter attached to the preceding sentence.
        sentence_pattern = re.compile(r'(?<=[.!?])(?:\s+|\n)')
        raw_sentences = sentence_pattern.split(text)

        # Filter out empty strings and strip whitespace
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        if not sentences:
            return []

        # Group sentences into chunks of max_sentences_per_chunk
        chunks: list[str] = []
        for i in range(0, len(sentences), self.max_sentences_per_chunk):
            group = sentences[i : i + self.max_sentences_per_chunk]
            chunk_text = " ".join(group).strip()
            if chunk_text:
                chunks.append(chunk_text)

        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\\n\\n", "\\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        results = self._split(text, self.separators)
        # Filter out empty chunks and strip whitespace
        return [c.strip() for c in results if c.strip()]

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        # Base case: text fits in a single chunk
        if len(current_text) <= self.chunk_size:
            return [current_text] if current_text else []

        # Base case: no more separators — force-split by character
        if not remaining_separators:
            # Hard split by chunk_size characters
            chunks: list[str] = []
            for i in range(0, len(current_text), self.chunk_size):
                piece = current_text[i : i + self.chunk_size]
                if piece:
                    chunks.append(piece)
            return chunks

        separator = remaining_separators[0]
        next_separators = remaining_separators[1:]

        # Empty separator means split character by character (last resort)
        if separator == "":
            chunks = []
            for i in range(0, len(current_text), self.chunk_size):
                piece = current_text[i : i + self.chunk_size]
                if piece:
                    chunks.append(piece)
            return chunks

        # Split text by the current separator
        parts = current_text.split(separator)

        # Merge small parts together, recurse on oversized parts
        merged_chunks: list[str] = []
        current_buffer = ""

        for i, part in enumerate(parts):
            # Build candidate: what we'd have if we add this part to buffer
            if current_buffer:
                candidate = current_buffer + separator + part
            else:
                candidate = part

            if len(candidate) <= self.chunk_size:
                current_buffer = candidate
            else:
                # Flush the current buffer if it has content
                if current_buffer:
                    merged_chunks.append(current_buffer)
                    current_buffer = ""

                # If the part itself fits, start a new buffer with it
                if len(part) <= self.chunk_size:
                    current_buffer = part
                else:
                    # Part is too large — recurse with finer separators
                    sub_chunks = self._split(part, next_separators)
                    merged_chunks.extend(sub_chunks)

        # Don't forget the remaining buffer
        if current_buffer:
            merged_chunks.append(current_buffer)

        return merged_chunks


class LawArticleChunker(RecursiveChunker):
    """
    Domain-specific chunker for legal documents (Vietnamese / English laws).

    Prioritizes splitting at article boundaries (``\\nArticle ``) to preserve
    the semantic integrity of each legal article.  Falls back to the standard
    RecursiveChunker separators for articles that exceed *chunk_size*.

    Design rationale
    ----------------
    Legal texts are structured around numbered **Articles** that each address
    a self-contained provision.  Generic chunkers (fixed-size, sentence-based)
    often cut across article boundaries, producing chunks that mix provisions
    and confuse retrieval.  By inserting ``"\\nArticle "`` as the *highest-
    priority* separator, this chunker ensures that:

    1. Each chunk ideally corresponds to one or a few complete articles.
    2. Article numbering and headings are preserved at the chunk start.
    3. Overly long articles are recursively subdivided using the usual
       ``\\n\\n → \\n → ". " → " " → ""`` cascade.
    """

    # Chapter / Section headers are also useful breakpoints.
    LAW_SEPARATORS = [
        "\nChapter ",   # broadest structural unit
        "\nSection ",   # sub-structural unit
        "\nArticle ",   # individual provision — primary target
        "\n\n",
        "\n",
        ". ",
        " ",
        "",
    ]

    def __init__(self, chunk_size: int = 600) -> None:
        super().__init__(separators=self.LAW_SEPARATORS, chunk_size=chunk_size)


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    dot_product = _dot(vec_a, vec_b)
    magnitude_a = math.sqrt(_dot(vec_a, vec_a))
    magnitude_b = math.sqrt(_dot(vec_b, vec_b))

    # Guard against zero-magnitude vectors
    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        """
        Call each chunker, compute stats, return comparison dict.

        Returns a dict with keys: 'fixed_size', 'by_sentences', 'recursive',
        and 'law_article'.
        Each value is a dict with 'count', 'avg_length', and 'chunks'.
        """
        # Create instances of each chunking strategy
        fixed_chunker = FixedSizeChunker(chunk_size=chunk_size, overlap=0)
        sentence_chunker = SentenceChunker(max_sentences_per_chunk=3)
        recursive_chunker = RecursiveChunker(chunk_size=chunk_size)
        law_chunker = LawArticleChunker(chunk_size=chunk_size)

        strategies = {
            "fixed_size": fixed_chunker,
            "by_sentences": sentence_chunker,
            "recursive": recursive_chunker,
            "law_article": law_chunker,
        }

        result: dict = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            count = len(chunks)
            avg_length = sum(len(c) for c in chunks) / count if count > 0 else 0.0
            result[name] = {
                "count": count,
                "avg_length": round(avg_length, 2),
                "chunks": chunks,
            }

        return result
