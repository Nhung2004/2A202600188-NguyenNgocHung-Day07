# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Ngọc Hưng - 2A202600188
**Nhóm:**
**Ngày:** 2026-04-10

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
> High cosine similarity (gần 1.0) nghĩa là hai đoạn văn bản có **hướng vector gần giống nhau** trong không gian embedding, tức là chúng mang ý nghĩa ngữ cảnh tương tự. Hai vector có cosine similarity cao khi góc giữa chúng nhỏ, cho thấy nội dung ngữ nghĩa (semantic) của hai đoạn text gần nhau, bất kể độ dài hay cách diễn đạt khác nhau.

**Ví dụ HIGH similarity:**
- Sentence A: "Python is a programming language used for machine learning."
- Sentence B: "Python is widely used in AI and data science."
- Tại sao tương đồng: Cả hai câu đều nói về Python trong bối cảnh AI/ML. Chúng chia sẻ chủ đề chính (Python, lĩnh vực AI), dù diễn đạt khác nhau thì ý nghĩa tổng thể là tương đồng. Trong không gian embedding, các từ khóa "machine learning", "AI", "data science" sẽ được ánh xạ vào vùng gần nhau.

**Ví dụ LOW similarity:**
- Sentence A: "The weather is sunny and warm today."
- Sentence B: "Deep learning models require GPU acceleration."
- Tại sao khác: Hai câu thuộc hai lĩnh vực hoàn toàn khác nhau (thời tiết vs. deep learning). Không có từ khóa hay khái niệm ngữ nghĩa chung nào, dẫn đến vector embedding hướng theo các hướng rất khác nhau trong không gian đa chiều.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
> Cosine similarity đo **góc giữa hai vector** thay vì khoảng cách tuyệt đối, nên nó **bất biến với độ dài (magnitude)** của vector. Trong text embeddings, hai đoạn văn bản có cùng ý nghĩa nhưng độ dài khác nhau sẽ tạo ra các vector có magnitude khác nhau — Euclidean distance sẽ cho kết quả sai lệch vì nó bị ảnh hưởng bởi magnitude, trong khi cosine similarity chỉ quan tâm đến hướng vector, phản ánh chính xác hơn sự tương đồng ngữ nghĩa.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> **Công thức:** `num_chunks = ceil((doc_length - overlap) / (chunk_size - overlap))`
>
> **Phép tính:**
> ```
> num_chunks = ceil((10000 - 50) / (500 - 50))
>            = ceil(9950 / 450)
>            = ceil(22.11)
>            = 23 chunks
> ```
> **Đáp án: 23 chunks**

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**
> Với overlap=100: `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = ceil(24.75) = 25 chunks`. Tăng overlap từ 50 lên 100 làm tăng số chunk từ 23 lên 25, vì mỗi bước tiến (step) nhỏ hơn (400 thay vì 450 ký tự). Overlap nhiều hơn giúp **bảo toàn ngữ cảnh** ở ranh giới giữa các chunk — một câu hoặc ý tưởng bị cắt ở cuối chunk trước sẽ được lặp lại ở đầu chunk sau, giảm nguy cơ mất thông tin quan trọng khi retrieval.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** AI & Data Engineering Technical Documentation (Tài liệu kỹ thuật về AI, Vector Store, RAG systems)

**Tại sao nhóm chọn domain này?**
> Nhóm chọn domain tài liệu kỹ thuật AI vì đây là lĩnh vực phù hợp nhất với nội dung lab — các tài liệu có cấu trúc rõ ràng (headings, paragraphs, bullet points) giúp kiểm chứng hiệu quả của các chiến lược chunking khác nhau. Ngoài ra, domain này cho phép tạo benchmark queries với gold answers chính xác, dễ verify, và tài liệu có cả tiếng Anh lẫn tiếng Việt để test khả năng xử lý đa ngôn ngữ của hệ thống retrieval.

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | python_intro.txt | Lab sample data | 1,944 | source, extension, category=technical, lang=en |
| 2 | vector_store_notes.md | Lab sample data | 2,123 | source, extension, category=technical, lang=en |
| 3 | rag_system_design.md | Lab sample data | 2,391 | source, extension, category=technical, lang=en |
| 4 | customer_support_playbook.txt | Lab sample data | 1,703 | source, extension, category=operations, lang=en |
| 5 | chunking_experiment_report.md | Lab sample data | 2,008 | source, extension, category=technical, lang=en |
| 6 | vi_retrieval_notes.md | Lab sample data | 2,188 | source, extension, category=technical, lang=vi |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| category | string | "technical", "operations" | Cho phép filter theo loại tài liệu — khi user hỏi về kỹ thuật, chỉ search trong tài liệu technical, tránh nhiễu từ tài liệu operations |
| lang | string | "en", "vi" | Hỗ trợ filter theo ngôn ngữ — khi user hỏi bằng tiếng Việt, ưu tiên tài liệu tiếng Việt để cải thiện relevance |
| source | string | "data/python_intro.txt" | Traceability — cho phép user biết câu trả lời đến từ tài liệu nào, tăng trust |
| extension | string | ".md", ".txt" | Phân biệt format tài liệu, markdown files thường có cấu trúc heading rõ ràng hơn |

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu (chunk_size=200):

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| python_intro.txt (1,944 chars) | FixedSizeChunker (`fixed_size`) | 10 | 194.4 | ❌ Cắt giữa câu, mất ngữ cảnh |
| python_intro.txt | SentenceChunker (`by_sentences`) | 5 | 387.0 | ✅ Giữ trọn câu, context tốt |
| python_intro.txt | RecursiveChunker (`recursive`) | 14 | 136.9 | ⚠️ Chunk nhỏ, nhưng tách tại ranh giới tự nhiên |
| vector_store_notes.md (2,123 chars) | FixedSizeChunker (`fixed_size`) | 11 | 193.0 | ❌ Cắt giữa heading/paragraph |
| vector_store_notes.md | SentenceChunker (`by_sentences`) | 8 | 263.6 | ✅ Tốt cho prose text |
| vector_store_notes.md | RecursiveChunker (`recursive`) | 18 | 116.1 | ⚠️ Quá nhiều chunk nhỏ |
| rag_system_design.md (2,391 chars) | FixedSizeChunker (`fixed_size`) | 12 | 199.2 | ❌ Không respect markdown structure |
| rag_system_design.md | SentenceChunker (`by_sentences`) | 5 | 476.0 | ⚠️ Chunk khá lớn, nhưng coherent |
| rag_system_design.md | RecursiveChunker (`recursive`) | 20 | 117.7 | ✅ Tách theo `\n\n` trước, respect markdown |

### Strategy Của Tôi

**Loại:** RecursiveChunker (tuned parameters) + Metadata-enhanced indexing

**Mô tả cách hoạt động:**
> RecursiveChunker hoạt động theo nguyên tắc "thử separator từ thô đến mịn". Đầu tiên, nó thử tách text bằng `\n\n` (paragraph break) — separator tự nhiên nhất trong markdown. Nếu các phần sau khi tách vẫn quá lớn, nó tiếp tục thử `\n` (line break), rồi `. ` (sentence break), rồi ` ` (word break), và cuối cùng là tách từng ký tự. Các phần nhỏ hơn chunk_size được gộp lại thành chunk lớn hơn để tận dụng không gian. Strategy này đặc biệt phù hợp với tài liệu markdown vì nó respect cấu trúc heading/paragraph tự nhiên của tài liệu.

**Tại sao tôi chọn strategy này cho domain nhóm?**
> Tài liệu kỹ thuật thường có cấu trúc markdown rõ ràng với headings, paragraphs, và bullet points. RecursiveChunker khai thác cấu trúc này bằng cách ưu tiên tách tại paragraph breaks (`\n\n`) trước, giữ nguyên các section hoàn chỉnh. Điều này giúp mỗi chunk chứa một ý tưởng trọn vẹn (ví dụ: một section "Metadata Matters" hoặc "Common Risks") thay vì bị cắt giữa chừng như FixedSizeChunker.

**Code snippet:**
```python
class RecursiveChunker:
    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators=None, chunk_size=500):
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text):
        if not text or len(text) <= self.chunk_size:
            return [text] if text else []
        results = self._split(text, self.separators)
        return [c.strip() for c in results if c.strip()]

    def _split(self, current_text, remaining_separators):
        if len(current_text) <= self.chunk_size:
            return [current_text] if current_text else []
        if not remaining_separators:
            return [current_text[i:i+self.chunk_size] for i in range(0, len(current_text), self.chunk_size)]

        separator = remaining_separators[0]
        if separator == "":
            return [current_text[i:i+self.chunk_size] for i in range(0, len(current_text), self.chunk_size)]

        parts = current_text.split(separator)
        merged, buffer = [], ""
        for part in parts:
            candidate = buffer + separator + part if buffer else part
            if len(candidate) <= self.chunk_size:
                buffer = candidate
            else:
                if buffer: merged.append(buffer)
                buffer = ""
                if len(part) <= self.chunk_size:
                    buffer = part
                else:
                    merged.extend(self._split(part, remaining_separators[1:]))
        if buffer: merged.append(buffer)
        return merged
```

### So Sánh: Strategy của tôi vs Baseline

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|-------------------|
| vector_store_notes.md | best baseline (SentenceChunker) | 8 | 263.6 | Tốt, nhưng có chunk chứa nhiều ý |
| vector_store_notes.md | **RecursiveChunker (tuned, size=300)** | ~12 | ~170 | Tốt hơn — mỗi chunk là 1 section/paragraph hoàn chỉnh |
| rag_system_design.md | best baseline (SentenceChunker) | 5 | 476.0 | Chunk quá lớn, dilute semantic focus |
| rag_system_design.md | **RecursiveChunker (tuned, size=300)** | ~14 | ~165 | Tốt nhất — respect markdown sections |

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Tôi | RecursiveChunker (tuned) | 8/10 | Respect cấu trúc markdown, chunk coherent | Chunk count cao hơn, tốn memory |
| Duy - 2A202600189 | LegalArticleChunker | 9/10 | Giữ trọn vẹn bối cảnh Điều luật. Giảm 4x chunks → tiết kiệm chi phí. | Avg cosine score thấp hơn do chunk dài. Cần điều chỉnh regex nếu format header thay đổi. | 
| Huỳnh Lê Xuân Ánh - 2A202600083 | sentence | 8.5 | Chunk size cân đối, giữ được ngữ cảnh văn bản luật, similarity score đồng đều | Không tối ưu cho tài liệu rất dài | 
|Huyynh Nhut Huy - 2A202600084 | structured_legal | 9.5/10 | giữ được 100% article coverage| Tuy nhiên hơi mất thời gian cho quá trình embedding tất cả tài liệu

**Strategy nào tốt nhất cho domain này? Tại sao?**
> RecursiveChunker là strategy tốt nhất cho domain tài liệu kỹ thuật markdown vì nó tôn trọng cấu trúc tự nhiên của tài liệu. Khi tách theo `\n\n` trước, mỗi section (ví dụ "## Metadata Matters", "## Common Risks") được giữ nguyên thành một chunk, giúp retrieval trả về đúng section chứa câu trả lời thay vì một đoạn text bị cắt giữa chừng. SentenceChunker cũng tốt cho prose text nhưng không khai thác được cấu trúc heading.

---

## 4. My Approach — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi implement các phần chính trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** — approach:
> Sử dụng regex pattern `(?<=[.!?])(?:\s+|\n)` để phát hiện ranh giới câu — pattern này lookbehind cho dấu kết thúc câu (`.`, `!`, `?`) rồi match whitespace hoặc newline phía sau. Sau khi tách, các câu được strip whitespace và group thành chunks theo `max_sentences_per_chunk`. Edge case xử lý: empty text trả về `[]`, câu cuối không có dấu chấm vẫn được bắt, multiple whitespace giữa các câu được normalize. Sử dụng `" ".join()` để gộp các câu trong cùng chunk thay vì nối trực tiếp, đảm bảo formatting đồng nhất.

**`RecursiveChunker.chunk` / `_split`** — approach:
> Algorithm hoạt động theo cơ chế đệ quy top-down: bắt đầu với separator thô nhất (`\n\n`), tách text thành các phần, rồi gộp (merge) các phần liền kề nếu tổng kích thước ≤ chunk_size. Nếu một phần vẫn quá lớn, đệ quy gọi `_split` với separator tiếp theo trong danh sách. Base case: text ≤ chunk_size thì trả về nguyên, hoặc danh sách separator rỗng thì force-split theo chunk_size. Separator `""` được xử lý đặc biệt — tách từng ký tự rồi gộp thành chunk_size, đảm bảo algorithm luôn terminate.

### EmbeddingStore

**`add_documents` + `search`** — approach:
> Mỗi document được chuyển thành record gồm: unique id (doc_id + index), content, embedding vector (từ embedding_fn), và metadata (copy từ document + thêm doc_id). Records được lưu trong `self._store` (list of dicts) cho in-memory mode, hoặc ChromaDB collection nếu available. Search hoạt động bằng cách embed query, tính dot product giữa query embedding và tất cả stored embeddings, sort descending theo score, rồi trả về top_k kết quả. Mỗi kết quả chứa `content`, `metadata`, và `score`.

**`search_with_filter` + `delete_document`** — approach:
> `search_with_filter` áp dụng strategy "filter trước, search sau" — đầu tiên lọc `self._store` chỉ giữ các records có metadata match tất cả key-value pairs trong `metadata_filter`, rồi chạy `_search_records` trên tập đã lọc. Nếu `metadata_filter` là None, fallback về `search()` thông thường. `delete_document` sử dụng list comprehension để tạo store mới không chứa records có `doc_id` matching, rồi so sánh length trước/sau để return True/False. Cả hai method đều support cả ChromaDB và in-memory mode.

### KnowledgeBaseAgent

**`answer`** — approach:
> RAG pattern gồm 3 bước: (1) Retrieve top-k chunks từ store bằng `self.store.search(question, top_k)`; (2) Build prompt có cấu trúc rõ ràng với section "Retrieved Context" chứa các chunk được đánh số, kèm source và relevance score, và section "Question" chứa câu hỏi; (3) Call `self.llm_fn(prompt)` để generate answer. Prompt được thiết kế với instruction yêu cầu LLM chỉ trả lời dựa trên context được cung cấp ("Answer based ONLY on the provided context"), giúp giảm hallucination. Context được format với separator `---` giữa các chunk để LLM dễ phân biệt.

### Test Results

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.0.3, pluggy-1.6.0
rootdir: D:\2026AI\Day-07-Lab-Data-Foundations
plugins: anyio-4.13.0, langsmith-0.7.29
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.21s ==============================
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

> **Lưu ý:** Kết quả dưới đây sử dụng `_mock_embed` (hash-based deterministic embedding) nên score không phản ánh semantic similarity thực sự. Với local embedder (`all-MiniLM-L6-v2`) hoặc OpenAI embedder, kết quả sẽ phản ánh ngữ nghĩa chính xác hơn.

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Python is a programming language used for machine learning." | "Python is widely used in AI and data science." | high | 0.0441 | ⚠️ Thấp hơn dự đoán (do mock embedder) |
| 2 | "The weather is sunny and warm today." | "Deep learning models require GPU acceleration." | low | -0.0840 | ✅ Đúng — score âm, rất khác nhau |
| 3 | "Vector databases store embeddings for similarity search." | "A vector store retrieves the most similar items to a query." | high | 0.0575 | ⚠️ Thấp hơn kỳ vọng (mock limitation) |
| 4 | "Dogs are loyal companions." | "Cats are independent pets." | low | 0.1497 | ⚠️ Cao hơn dự đoán — pets/animals domain overlap |
| 5 | "Cosine similarity measures the angle between two vectors." | "Euclidean distance computes the straight-line distance." | high | 0.1150 | ⚠️ Moderate — cùng math domain |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
> Kết quả bất ngờ nhất là Pair 4 ("Dogs" vs "Cats"): dự đoán low similarity vì chó và mèo là khác nhau, nhưng actual score lại cao nhất (0.1497). Điều này cho thấy mock embeddings (hash-based) không phản ánh semantic meaning mà chỉ dựa trên hash của text. Với real embeddings, Pair 1 và Pair 3 sẽ có score cao hơn nhiều (do cùng semantic domain), còn Pair 2 sẽ gần 0. Bài học: **chất lượng embedding model ảnh hưởng trực tiếp đến retrieval quality** — mock embeddings đủ để test code logic nhưng không phản ánh semantic search thực tế. Để có kết quả meaningful, cần dùng `all-MiniLM-L6-v2` hoặc OpenAI embeddings.

---

## 6. Results — Cá nhân (10 điểm)

Chạy 5 benchmark queries trên implementation cá nhân sử dụng mock embeddings.

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | What is Python commonly used for in production environments? | Python is used to build APIs, data pipelines, internal tools, and model-serving layers using frameworks like FastAPI, Django, and Flask. |
| 2 | What are the four stages of a vector search pipeline? | 1) Chunk documents, 2) Embed each chunk, 3) Store vector and metadata, 4) Embed query and rank by similarity. |
| 3 | What is the goal of the RAG system for the internal knowledge assistant? | Build a retrieval-augmented generation system that finds relevant internal documents before producing answers, reducing hallucinations by grounding responses in retrieved text. |
| 4 | Why is metadata important in vector stores? | Metadata allows filtering search space by fields like source, language, department, improving precision and preventing retrieval of irrelevant or outdated content. |
| 5 | What are the risks of using vector stores for retrieval? | Poor chunking, low-quality embeddings, missing metadata, and weak evaluation can cause misleading results — semantically adjacent but not useful passages. |

### Kết Quả Của Tôi

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | What is Python commonly used for in production environments? | vector_store_notes.md - "A vector store is a database..." | 0.1239 | ❌ (mock limitation) | Context từ vector_store_notes thay vì python_intro |
| 2 | What are the four stages of a vector search pipeline? | chunking_experiment_report.md - "Chunking Experiment Report..." | 0.1998 | ⚠️ Partial — cùng domain nhưng không chứa 4 stages | Context liên quan nhưng thiếu chi tiết 4 stages |
| 3 | What is the goal of the RAG system? | vector_store_notes.md - "A vector store is a database..." | 0.0639 | ⚠️ Partial — liên quan RAG nhưng không đúng doc | Context từ vector_store thay vì rag_system_design |
| 4 | Why is metadata important in vector stores? | vi_retrieval_notes.md - "Ghi chú về Retrieval..." | 0.2853 | ✅ Có nói về metadata | Content đề cập metadata importance |
| 5 | What are the risks of using vector stores? | vi_retrieval_notes.md - "Ghi chú về Retrieval..." | 0.2614 | ✅ Có nói về risks | Content đề cập retrieval risks |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 2 / 5

> **Phân tích:** Với mock embeddings (hash-based, không semantic), retrieval quality thấp là expected. Mock embeddings tạo vector dựa trên MD5 hash của text, không capture ý nghĩa ngữ nghĩa. Khi chuyển sang real embeddings (e.g., `all-MiniLM-L6-v2`), score sẽ phản ánh semantic similarity thực, và retrieval precision sẽ cải thiện đáng kể. Đây chính là bài học quan trọng: **embedding quality là yếu tố quyết định** cho retrieval system, không chỉ chunking strategy hay store implementation.

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
> Học được rằng không có "one-size-fits-all" chunking strategy — SentenceChunker hoạt động tốt cho prose text liên tục nhưng kém với tài liệu có cấu trúc heading, trong khi RecursiveChunker ngược lại. Mỗi strategy có trade-off giữa chunk coherence (giữ ý trọn vẹn) và chunk count (số lượng chunk ảnh hưởng đến search space).

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
> Nhận ra tầm quan trọng của metadata design — một nhóm sử dụng metadata "difficulty" (easy/medium/hard) cho tài liệu FAQ, cho phép agent trả lời câu hỏi đơn giản trước rồi escalate khi cần. Đây là ví dụ thực tế về metadata-driven retrieval improvement mà chỉ filter đơn giản nhưng tác động lớn đến user experience.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**
> Tôi sẽ (1) sử dụng real embeddings (`all-MiniLM-L6-v2`) thay vì mock để có semantic search thực sự; (2) chunk tài liệu markdown theo heading sections thay vì dùng generic RecursiveChunker — tạo custom `MarkdownSectionChunker` tách theo `##` headers; (3) thêm overlap giữa các chunk để tránh mất context ở ranh giới, đặc biệt khi câu trả lời nằm ở cuối section này và đầu section kia.

### Failure Analysis (Ex 3.5)

**Query thất bại:** "What is Python commonly used for in production environments?"

**Tại sao thất bại:**
> Mock embeddings không capture semantic meaning — hash-based vectors tạo ra similarity scores không tương quan với nội dung thực tế. Document `python_intro.txt` chứa câu trả lời chính xác ("Python is commonly used to build APIs, data pipelines, internal tools, and model-serving layers") nhưng không được rank cao vì mock embedding của query không "gần" mock embedding của document.

**Đề xuất cải thiện:**
> 1. **Embedding quality:** Chuyển sang `all-MiniLM-L6-v2` (local) hoặc `text-embedding-3-small` (OpenAI) để có real semantic vectors.
> 2. **Chunking strategy:** Chunk `python_intro.txt` thành các paragraph riêng biệt (mỗi paragraph ~400 chars) thay vì giữ nguyên cả document (~1944 chars) — chunk nhỏ hơn, focused hơn sẽ có embedding cụ thể hơn.
> 3. **Metadata filtering:** Thêm metadata `topic=["python", "production"]` để pre-filter khi query đề cập "Python" hoặc "production".

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 8 / 10 |
| Chunking strategy | Nhóm | 13 / 15 |
| My approach | Cá nhân | 9 / 10 |
| Similarity predictions | Cá nhân | 4 / 5 |
| Results | Cá nhân | 7 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 4 / 5 |
| **Tổng** | | **80 / 100** |
