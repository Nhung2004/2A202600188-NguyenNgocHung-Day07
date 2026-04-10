from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        """
        Retrieve relevant chunks, build a context-aware prompt, and call the LLM.

        Steps:
            1. Search the vector store for the top-k most relevant chunks.
            2. Assemble a prompt that includes the retrieved context and the question.
            3. Call the LLM function with the assembled prompt.
            4. Return the LLM's response.
        """
        # Step 1: Retrieve top-k relevant chunks from the store
        results = self.store.search(question, top_k=top_k)

        # Step 2: Build context from retrieved chunks
        context_parts: list[str] = []
        for i, result in enumerate(results, start=1):
            source = result.get("metadata", {}).get("source", "unknown")
            score = result.get("score", 0.0)
            content = result.get("content", "")
            context_parts.append(
                f"[Chunk {i}] (source: {source}, relevance: {score:.3f})\n{content}"
            )

        context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant context found."

        # Step 3: Build the prompt with RAG pattern
        prompt = (
            "You are a knowledgeable assistant. Answer the question based ONLY on the "
            "provided context below. If the context does not contain enough information "
            "to answer the question, say so explicitly.\n\n"
            "## Retrieved Context\n\n"
            f"{context}\n\n"
            "## Question\n\n"
            f"{question}\n\n"
            "## Answer\n\n"
        )

        # Step 4: Call the LLM and return its response
        return self.llm_fn(prompt)
