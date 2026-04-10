# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Ngọc Hưng - 2A202600188
**Nhóm:** Nhóm07
**Ngày:** 2026-04-10

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
> High cosine similarity (gần 1.0) nghĩa là hai đoạn văn bản có **hướng vector gần giống nhau** trong không gian embedding, tức là chúng mang ý nghĩa ngữ cảnh tương tự. Hai vector có cosine similarity cao khi góc giữa chúng nhỏ, cho thấy nội dung ngữ nghĩa (semantic) của hai đoạn text gần nhau, bất kể độ dài hay cách diễn đạt khác nhau.

**Ví dụ HIGH similarity:**
- Sentence A: "Children have the right to be protected from sexual abuse."
- Sentence B: "Children have the right to be protected from labor exploitation."
- Tại sao tương đồng: Cả hai câu đều trích từ Luật Trẻ em, có cùng cấu trúc ngữ pháp ("Children have the right to be protected from…"), cùng chủ đề (quyền trẻ em), và cùng ngữ nghĩa bảo vệ trẻ em. Trong không gian embedding, các từ "protected", "children", "right" sẽ kéo hai vector về cùng hướng.

**Ví dụ LOW similarity:**
- Sentence A: "The Government uniformly manages the press nationwide."
- Sentence B: "Replacement-level fertility means the average of 2.1 children per woman."
- Tại sao khác: Hai câu thuộc hai lĩnh vực hoàn toàn khác nhau (quản lý báo chí vs. dân số học). Không có từ khóa hay khái niệm ngữ nghĩa chung nào, dẫn đến vector embedding hướng theo các hướng rất khác nhau trong không gian đa chiều.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
> Cosine similarity đo **góc giữa hai vector** thay vì khoảng cách tuyệt đối, nên nó **bất biến với độ dài (magnitude)** của vector. Trong text embeddings, hai đoạn văn bản có cùng ý nghĩa nhưng độ dài khác nhau sẽ tạo ra các vector có magnitude khác nhau — Euclidean distance sẽ cho kết quả sai lệch vì nó bị ảnh hưởng bởi magnitude, trong khi cosine similarity chỉ quan tâm đến hướng vector, phản ánh chính xác hơn sự tương đồng ngữ nghĩa. Ví dụ thực tế: Điều 1 của Luật Hôn nhân (ngắn, ~50 từ) và Điều 8 (dài, ~200 từ) đều nói về kết hôn — cosine similarity sẽ phát hiện đúng, Euclidean distance sẽ báo chúng "xa nhau" do magnitude khác biệt.

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
> Với overlap=100: `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = ceil(24.75) = 25 chunks`. Tăng overlap từ 50 lên 100 làm tăng số chunk từ 23 lên 25, vì mỗi bước tiến (step) nhỏ hơn (400 thay vì 450 ký tự). Overlap nhiều hơn giúp **bảo toàn ngữ cảnh** ở ranh giới giữa các chunk — đặc biệt quan trọng với tài liệu luật, nơi một điều khoản có thể tham chiếu đến khoản trước đó (ví dụ: "theo quy định tại Khoản 1 Điều này"). Overlap giúp chunk sau vẫn chứa phần cuối chunk trước, giảm nguy cơ mất thông tin tham chiếu chéo.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Hệ thống Pháp luật Việt Nam (Vietnamese Legal Documents)

**Tại sao nhóm chọn domain này?**
> Nhóm chọn domain luật pháp Việt Nam vì đây là loại tài liệu có **cấu trúc phân cấp rõ ràng** (Chương → Mục → Điều → Khoản → Điểm), tạo cơ hội tối ưu để thiết kế và đánh giá custom chunking strategy. Tài liệu luật cũng cho phép tạo benchmark queries với gold answers **chính xác, có thể verify** (trích dẫn đúng Điều, Khoản). Ngoài ra, các luật thuộc nhiều lĩnh vực khác nhau (gia đình, đầu tư, giáo dục, báo chí, dân số) giúp kiểm tra khả năng **cross-domain retrieval** và hiệu quả của **metadata filtering** (filter theo category, year). Đây cũng là domain thực tế với nhu cầu tra cứu pháp luật cao, phù hợp để xây dựng ứng dụng Legal RAG.

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | Law on Marriage and Family 2014.txt | Luật số 52/2014/QH13 | 96,219 | source, extension, category=family-civil, year=2014, lang=en |
| 2 | Children Law 2016.txt | Luật số 102/2016/QH13 | 92,195 | source, extension, category=family-civil, year=2016, lang=en |
| 3 | Law on Educators 2025.txt | Luật số 73/2025/QH15 | 38,960 | source, extension, category=education, year=2025, lang=en |
| 4 | Law on Investment 2025.txt | Luật số 143/2025/QH15 | 106,798 | source, extension, category=business, year=2025, lang=en |
| 5 | Law on Press 2025.txt | Luật số 126/2025/QH15 | 61,199 | source, extension, category=media-press, year=2025, lang=en |
| 6 | Law on Population 2025.txt | Luật số 113/2025/QH15 | 29,859 | source, extension, category=population, year=2025, lang=en |

**Tổng:** 6 tài liệu, ~425,000 ký tự, 5 lĩnh vực pháp luật khác nhau

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| category | string | "family-civil", "business", "education", "media-press", "population" | **Critical cho legal retrieval** — khi user hỏi về đầu tư, filter `category=business` loại bỏ hoàn toàn các luật không liên quan (gia đình, báo chí), tăng precision đáng kể |
| year | string | "2014", "2016", "2025" | Cho phép filter theo **thời gian hiệu lực** — luật mới thay thế luật cũ, nên khi user hỏi "quy định hiện hành", filter `year=2025` trả về luật mới nhất |
| lang | string | "en" | Đánh dấu ngôn ngữ tài liệu — hỗ trợ tương lai khi thêm bản tiếng Việt song song |
| source | string | "Law on Marriage and Family 2014.txt" | **Traceability** — cho phép trích dẫn chính xác nguồn luật trong câu trả lời, tăng trust và compliance |
| extension | string | ".txt" | Phân loại format tài liệu cho pipeline processing |

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu pháp luật (chunk_size=500):

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Legal Structure? |
|-----------|----------|-------------|------------|---------------------------|
| Law on Marriage and Family 2014 (5000 chars) | FixedSizeChunker | 10 | 500.0 | ❌ Cắt giữa Điều, trộn nội dung 2 điều khoản vào 1 chunk |
| Law on Marriage and Family 2014 | SentenceChunker | 16 | 310.2 | ⚠️ Giữ câu, nhưng tách Điều thành nhiều chunk rời rạc |
| Law on Marriage and Family 2014 | RecursiveChunker | 13 | 382.8 | ⚠️ Tách tại `\n\n`, tốt hơn fixed nhưng không nhận biết "Article" |
| Law on Marriage and Family 2014 | **LawArticleChunker** | **14** | **353.6** | ✅ **Mỗi chunk = 1-2 Điều hoàn chỉnh, giữ nguyên heading** |
| Children Law 2016 (5000 chars) | FixedSizeChunker | 10 | 500.0 | ❌ Cắt giữa điều khoản |
| Children Law 2016 | SentenceChunker | 21 | 235.0 | ⚠️ Chunk nhỏ, mất liên kết giữa các khoản cùng Điều |
| Children Law 2016 | RecursiveChunker | 14 | 355.0 | ⚠️ Trung bình, không optimal cho law |
| Children Law 2016 | **LawArticleChunker** | **17** | **289.2** | ✅ **Tách đúng ranh giới Điều, chunk coherent** |
| Law on Educators 2025 (5000 chars) | FixedSizeChunker | 10 | 500.0 | ❌ Trộn chapter header vào content |
| Law on Educators 2025 | SentenceChunker | 24 | 205.1 | ⚠️ Quá nhiều chunk nhỏ, fragmented |
| Law on Educators 2025 | RecursiveChunker | 12 | 414.5 | ⚠️ Chunk lớn hơn nhưng cắt ngang Article |
| Law on Educators 2025 | **LawArticleChunker** | **14** | **351.2** | ✅ **Respect Chapter > Section > Article hierarchy** |

### Strategy Của Tôi: LawArticleChunker

**Loại:** Custom domain-specific chunker (kế thừa từ `RecursiveChunker`)

**Mô tả cách hoạt động:**
> `LawArticleChunker` là một chiến lược chunking được thiết kế đặc biệt cho tài liệu pháp luật. Thay vì sử dụng các separator mặc định (`\n\n`, `\n`, `. `, ` `, `""`), chunker này sử dụng **chuỗi separator ưu tiên theo cấu trúc luật**:
>
> 1. `"\nChapter "` — tách tại ranh giới Chương (đơn vị cấu trúc lớn nhất)
> 2. `"\nSection "` — tách tại ranh giới Mục
> 3. `"\nArticle "` — **separator chính** — tách tại ranh giới Điều (đơn vị ngữ nghĩa cốt lõi)
> 4. `"\n\n"` → `"\n"` → `". "` → `" "` → `""` — fallback cascade cho các Điều quá dài
>
> Khi một Điều luật có kích thước ≤ `chunk_size` (mặc định 600 chars), nó được giữ nguyên thành 1 chunk. Nếu vượt quá, nó được chia nhỏ hơn bằng cascade separator tiếp theo (`\n\n` → paragraph breaks trong Điều).

**Tại sao tôi chọn strategy này cho domain pháp luật?**
> Tài liệu pháp luật Việt Nam có cấu trúc phân cấp chặt chẽ: **Chương → Mục → Điều → Khoản → Điểm**. Mỗi Điều (Article) là một **đơn vị ngữ nghĩa tự chứa** — nó quy định một vấn đề cụ thể và thường được trích dẫn độc lập (ví dụ: "theo Điều 8 Luật Hôn nhân"). FixedSizeChunker cắt giữa Điều, tạo chunk chứa nửa cuối Điều 7 + nửa đầu Điều 8 → vô nghĩa cho retrieval. LawArticleChunker đảm bảo mỗi chunk chứa **toàn bộ một Điều**, giúp retrieval trả về đúng Điều chứa câu trả lời.

**Code snippet:**
```python
class LawArticleChunker(RecursiveChunker):
    """Domain-specific chunker for legal documents."""

    LAW_SEPARATORS = [
        "\nChapter ",   # broadest structural unit
        "\nSection ",   # sub-structural unit
        "\nArticle ",   # individual provision — primary target
        "\n\n", "\n", ". ", " ", "",
    ]

    def __init__(self, chunk_size: int = 600) -> None:
        super().__init__(separators=self.LAW_SEPARATORS, chunk_size=chunk_size)
```

### Deep Analysis: LawArticleChunker vs RecursiveChunker (chunk_size=600, 10,000 chars)

| Tài liệu | LawArticleChunker | RecursiveChunker | Winner |
|-----------|-------------------|------------------|--------|
| Law on Marriage and Family 2014 | 23 chunks, avg=431 chars | 21 chunks, avg=474 chars | **LawArticle** — chunk bắt đầu bằng "Article X." heading |
| Children Law 2016 | 23 chunks, avg=429 chars | 22 chunks, avg=452 chars | **LawArticle** — Điều 1 "A child is a human being below 16" giữ nguyên |
| Law on Educators 2025 | 26 chunks, avg=378 chars | 21 chunks, avg=474 chars | **LawArticle** — tách Chapter I/II boundaries chính xác |

**Ví dụ chunk output từ LawArticleChunker (Children Law 2016):**
```
chunk[1]: "I  GENERAL PROVISIONS  Article 1. Children  A child is a 
           human being below the age of 16.  Article 2. Scope  ..."
chunk[2]: "3. Regulated entities  State agencies, political organizations,
           socio-political organizations..."
```
→ Chunk 1 chứa trọn vẹn Điều 1 + Điều 2 (cùng Chapter I), tạo context coherent cho retrieval.

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Mô tả | Điểm mạnh | Điểm yếu |
|-----------|----------|-------|-----------|----------|
| Tôi | **LawArticleChunker** (custom) | Tách theo Article/Chapter/Section boundaries | Giữ nguyên đơn vị pháp lý, chunk coherent, tối ưu cho legal retrieval | Chunk count cao hơn, article dài bị chia nhỏ |
| Thành viên 2 | RecursiveChunker (tuned, size=400) | Tách theo `\n\n` → `\n` → `. ` | Đa năng, hoạt động tốt với mọi loại tài liệu | Không nhận biết cấu trúc Article, chunk có thể cắt giữa Điều |
| Thành viên 3 | SentenceChunker (5 sentences/chunk) | Tách theo ranh giới câu, gom 5 câu | Đơn giản, giữ trọn câu | Mất liên kết giữa các khoản cùng Điều, chunk không có heading |

**Strategy nào tốt nhất cho domain pháp luật? Tại sao?**
> **LawArticleChunker** vượt trội rõ ràng cho domain pháp luật vì nó là chunker duy nhất nhận biết cấu trúc phân cấp Chapter → Section → Article. Cụ thể:
> - **Chunk coherence**: Mỗi chunk bắt đầu bằng "Article X." heading, giúp LLM biết đang đọc Điều nào → giảm hallucination
> - **Retrieval precision**: Khi user hỏi "Điều kiện kết hôn?", chunk chứa trọn Điều 8 (marriage conditions) được trả về thay vì nửa Điều 7 + nửa Điều 8
> - **Legal citation**: Agent có thể trích dẫn chính xác "theo Điều 8, Luật Hôn nhân 2014" vì heading được giữ nguyên
>
> RecursiveChunker hoạt động tạm được nhờ `\n\n` trùng với paragraph breaks trong luật, nhưng không phân biệt được paragraph trong Điều vs. paragraph giữa hai Điều. SentenceChunker kém nhất — tách Điều thành nhiều chunk rời rạc, mất liên kết logic giữa các khoản.

---

## 4. My Approach — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi implement các phần chính trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** — approach:
> Sử dụng regex pattern `(?<=[.!?])(?:\s+|\n)` để phát hiện ranh giới câu — pattern này lookbehind cho dấu kết thúc câu (`.`, `!`, `?`) rồi match whitespace hoặc newline phía sau. Sau khi tách, các câu được strip whitespace và group thành chunks theo `max_sentences_per_chunk`. Edge case xử lý: empty text trả về `[]`, câu cuối không có dấu chấm vẫn được bắt, multiple whitespace giữa các câu được normalize. Sử dụng `" ".join()` để gộp các câu trong cùng chunk thay vì nối trực tiếp, đảm bảo formatting đồng nhất.

**`RecursiveChunker.chunk` / `_split`** — approach:
> Algorithm hoạt động theo cơ chế đệ quy top-down: bắt đầu với separator thô nhất (`\n\n`), tách text thành các phần, rồi gộp (merge) các phần liền kề nếu tổng kích thước ≤ chunk_size. Nếu một phần vẫn quá lớn, đệ quy gọi `_split` với separator tiếp theo trong danh sách. Base case: text ≤ chunk_size thì trả về nguyên, hoặc danh sách separator rỗng thì force-split theo chunk_size. Separator `""` được xử lý đặc biệt — tách từng ký tự rồi gộp thành chunk_size, đảm bảo algorithm luôn terminate.

**`LawArticleChunker`** — approach:
> Kế thừa toàn bộ logic đệ quy từ `RecursiveChunker`, chỉ override separator list thành `LAW_SEPARATORS` = `["\nChapter ", "\nSection ", "\nArticle ", "\n\n", "\n", ". ", " ", ""]`. Design decision quan trọng: đặt `"\nArticle "` **trước** `"\n\n"` trong priority list, nghĩa là chunker sẽ thử tách theo ranh giới Article trước khi tách theo paragraph. Điều này đảm bảo mỗi chunk tương ứng với một unit pháp lý hoàn chỉnh. Default chunk_size = 600 (lớn hơn mặc định 500) vì các Điều luật thường dài hơn paragraph thông thường.

### EmbeddingStore

**`add_documents` + `search`** — approach:
> Mỗi document được chuyển thành record gồm: unique id (doc_id + index), content, embedding vector (từ embedding_fn), và metadata (copy từ document + thêm doc_id). Records được lưu trong `self._store` (list of dicts) cho in-memory mode, hoặc ChromaDB collection nếu available. Search hoạt động bằng cách embed query, tính dot product giữa query embedding và tất cả stored embeddings, sort descending theo score, rồi trả về top_k kết quả. Mỗi kết quả chứa `content`, `metadata`, và `score`.

**`search_with_filter` + `delete_document`** — approach:
> `search_with_filter` áp dụng strategy "filter trước, search sau" — đầu tiên lọc `self._store` chỉ giữ các records có metadata match tất cả key-value pairs trong `metadata_filter`, rồi chạy `_search_records` trên tập đã lọc. Ví dụ thực tế: khi filter `year=2025`, chỉ 4 luật (Educators, Investment, Press, Population) được search, loại bỏ hoàn toàn Marriage 2014 và Children 2016. `delete_document` sử dụng list comprehension để tạo store mới không chứa records có `doc_id` matching, rồi so sánh length trước/sau để return True/False.

### KnowledgeBaseAgent

**`answer`** — approach:
> RAG pattern gồm 3 bước: (1) Retrieve top-k chunks từ store bằng `self.store.search(question, top_k)`; (2) Build prompt có cấu trúc rõ ràng với section "Retrieved Context" chứa các chunk được đánh số, kèm source và relevance score, và section "Question" chứa câu hỏi; (3) Call `self.llm_fn(prompt)` để generate answer. Prompt được thiết kế với instruction yêu cầu LLM chỉ trả lời dựa trên context được cung cấp ("Answer based ONLY on the provided context"), giúp giảm hallucination — đặc biệt quan trọng cho legal domain nơi accuracy là bắt buộc.

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
...
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.21s ==============================
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

> **Lưu ý:** Kết quả dưới đây sử dụng `_mock_embed` (hash-based deterministic embedding) nên score không phản ánh semantic similarity thực sự. Với real embedder (`all-MiniLM-L6-v2` hoặc OpenAI), kết quả sẽ phản ánh ngữ nghĩa chính xác hơn. Tất cả 5 pairs đều sử dụng câu trích từ bộ luật thực tế trong dataset.

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Phân tích |
|------|-----------|-----------|---------|--------------|-----------|
| 1 | "A child is a human being below the age of 16." (Children Law, Art. 1) | "The man must be full 20 years or older to get married." (Marriage Law, Art. 8) | Medium — cả hai về ngưỡng tuổi | **−0.0667** | ⚠️ Mock không nhận ra cùng pattern "age threshold". Real embedding sẽ cho score ~0.4-0.6 vì cùng cấu trúc "X years or older/below" |
| 2 | "Educators are the core force of the education sector." (Educators Law) | "Press agencies are the mouthpieces of Party agencies." (Press Law) | Low — khác domain hoàn toàn | **−0.0470** | ✅ Đúng — gần 0, hai lĩnh vực không liên quan. Tuy nhiên cùng pattern "X are the Y of Z" nên real embedding có thể cho ~0.2 |
| 3 | "The State recognizes and protects the ownership of assets." (Investment Law) | "Investors are entitled to carry out business investment activities." (Investment Law) | Medium — cùng law, quan hệ nhà nước-nhà đầu tư | **0.1140** | ✅ Score cao nhất trong 5 pairs — cùng domain "investment/business", mock hash trùng lặp từ vựng |
| 4 | "Children have the right to be protected from sexual abuse." (Children Law) | "Children have the right to be protected from labor exploitation." (Children Law) | High — cùng cấu trúc, cùng chủ thể | **−0.0895** | ❌ **Bất ngờ nhất!** Cùng 8/12 từ giống hệt nhau nhưng mock cho score âm. Real embedding sẽ cho >0.85 vì gần như paraphrase |
| 5 | "The Government uniformly manages the press nationwide." (Press Law) | "Replacement-level fertility means the average of 2.1 children per woman." (Population Law) | Very low — hoàn toàn khác topic | **−0.1214** | ✅ Score âm nhất — đúng dự đoán, hai câu không có bất kỳ overlap ngữ nghĩa nào |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
> **Pair 4** là kết quả bất ngờ nhất: hai câu gần như giống hệt nhau (chỉ khác "sexual abuse" vs "labor exploitation") nhưng mock embedding cho score −0.0895 (âm!). Điều này chứng minh rõ ràng rằng **mock embeddings (hash-based) hoàn toàn không capture semantic similarity** — chúng tạo vector dựa trên MD5 hash, nên sự khác biệt nhỏ trong text dẫn đến vector hoàn toàn khác. Bài học quan trọng:
> 
> 1. **Embedding quality quyết định retrieval quality** — không có real embedding, mọi evaluation đều không đáng tin cậy
> 2. **Syntactic similarity ≠ hash similarity** — mock embeddings có thể cho score cao với text khác domain nhưng tình cờ có hash tương tự
> 3. **Cần real embedding model** (`all-MiniLM-L6-v2` hoặc `text-embedding-3-small`) để đánh giá chunking strategy một cách chính xác

---

## 6. Results — Cá nhân (10 điểm)

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer | Chunk chứa thông tin |
|---|-------|-------------|---------------------|
| 1 | What is the legal marriage age for men and women in Vietnam? | The man must be full 20 years or older, the woman must be full 18 years or older (Article 8, Law on Marriage and Family 2014) | Marriage Law Art. 8 |
| 2 | What is the definition of a child under Vietnamese law? | A child is a human being below the age of 16 (Article 1, Children Law 2016) | Children Law Art. 1 |
| 3 | What are the prohibited acts regarding the press in Vietnam? | Prohibited acts include posting info opposing the State, inciting violence, disclosing state secrets, disseminating false info (Article 8, Law on Press 2025) | Press Law Art. 8 |
| 4 | What qualifications are required for educators at the university level? | Lecturers at university must possess a master's degree or higher; postgraduate lecturers must hold a doctorate (Article 28, Law on Educators 2025) | Educators Law Art. 28 |
| 5 | What are the banned business lines for investment in Vietnam? | Banned: narcotics, prostitution, human trafficking, asexual reproduction, firecrackers, debt collection services, national treasures, e-cigarettes (Article 6, Law on Investment 2025) | Investment Law Art. 6 |

**Yêu cầu metadata filtering:** Query 5 — sử dụng `category=business` hoặc `year=2025` để filter chỉ Luật Đầu tư, tránh trả về Luật Hôn nhân hay Luật Trẻ em không liên quan.

### Kết Quả Của Tôi (Mock Embeddings)

| # | Query | Top-1 Source | Score | Top-1 Relevant? | Top-3 Relevant? |
|---|-------|-------------|-------|-----------------|-----------------|
| 1 | Legal marriage age? | Law on Investment 2025.txt | 0.2495 | ❌ Sai hoàn toàn | ❌ Marriage Law not in top-3 |
| 2 | Definition of a child? | **Children Law 2016.txt** | 0.1071 | ✅ **Đúng nguồn** | ✅ Top-1 chính xác |
| 3 | Prohibited acts re: press? | **Law on Press 2025.txt** | 0.1598 | ✅ **Đúng nguồn** | ✅ Top-1 chính xác |
| 4 | Educator qualifications? | Children Law 2016.txt | 0.1975 | ❌ Sai hoàn toàn | ❌ Educators Law not in top-3 |
| 5 | Banned business lines? | Law on Press 2025.txt | 0.1584 | ❌ Sai hoàn toàn | ❌ Investment Law not in top-3 |

**Precision Summary:** 2 / 5 queries có relevant source trong top-3 → **Precision@3 = 40%**

### Metadata Filtering Results

| Test | Query | Filter | Top-1 Source | Improvement? |
|------|-------|--------|-------------|-------------|
| No filter | "Banned business lines for investment?" | None | Law on Educators 2025 (score=0.2913) | ❌ Sai |
| Year filter | Same query | `year=2025` | Law on Educators 2025 (score=0.2913) | ❌ Vẫn sai — 4 luật cùng year=2025 |
| Category filter | Same query | `category=family-civil` | Children Law 2016 (score=0.1332) | ❌ Sai direction — family law |

> **Phân tích metadata filtering:**
> - Filter `year=2025` giảm search space từ 6 → 4 luật, nhưng vẫn không đủ precise vì 4 luật đều year=2025
> - Filter `category=business` (nếu dùng chính xác) sẽ chỉ giữ Luật Đầu tư → **precision tăng lên 100%**
> - **Bài học:** Metadata filtering hiệu quả nhất khi dùng field có **high selectivity** (category chia thành 5 nhóm rõ ràng) thay vì field có **low selectivity** (year chỉ có 3 giá trị, 4/6 luật cùng 2025)
> - Với mock embeddings, metadata filtering trở nên **quan trọng hơn bao giờ hết** vì nó là cơ chế duy nhất đảm bảo trả về đúng domain, bù đắp cho việc similarity score không đáng tin cậy

### So Sánh Strategy Trong Nhóm (Ex 3.4)

| Query | LawArticleChunker | RecursiveChunker | SentenceChunker |
|-------|-----------------|---------------|--------------|
| Q1: Marriage age | Wrong source    |  Wrong source |  Wrong source |
| Q2: Child definition | Top-1 correct   |  Top-1 correct |  Top-3 only |
| Q3: Press prohibited acts |  Top-1 correct  |  Top-1 correct |  Top-1 correct |
| Q4: Educator qualifications |  Wrong source   |  Wrong source |  Wrong source |
| Q5: Banned business lines |  Wrong source   |  Wrong source |  Wrong source |
| **Score** | **2/5**         | **2/5** | **1.5/5** |

> **Insight:** Với mock embeddings, tất cả strategies đều perform tương đương (2/5) vì bottleneck là embedding quality, không phải chunking strategy. Tuy nhiên, LawArticleChunker vẫn có lợi thế tiềm ẩn:
> - Khi Q2 trả về đúng Children Law, chunk chứa trọn Điều 1 ("A child is...below 16") thay vì chỉ nửa câu
> - Với real embeddings, LawArticleChunker sẽ vượt trội vì mỗi chunk là 1 Điều hoàn chỉnh → embedding vector focused hơn, dễ match hơn

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
> Học được rằng **cấu trúc tài liệu gốc quyết định strategy tối ưu** — thành viên dùng RecursiveChunker cho rằng `\n\n` là separator đủ tốt, nhưng khi so sánh output cụ thể, LawArticleChunker cho chunk bắt đầu bằng "Article X." heading trong khi RecursiveChunker cắt giữa Điều. Điều này cho thấy: đừng dùng generic chunker khi bạn hiểu rõ cấu trúc dữ liệu — hãy exploit domain knowledge.

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
> Nhận ra tầm quan trọng của **hybrid retrieval** — một nhóm sử dụng keyword pre-filter (BM25) trước vector search, cho phép query "Điều 8 Luật Hôn nhân" match trực tiếp bằng keyword "Điều 8" trước khi so sánh embedding. Đây là giải pháp cho failure case của chúng tôi (Q1, Q4, Q5) nơi mock embedding thất bại nhưng keyword match sẽ thành công.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**
> 1. **Embedding quality:** Sử dụng real embeddings (`all-MiniLM-L6-v2` local hoặc `text-embedding-3-small` OpenAI) — đây là bottleneck chính hiện tại
> 2. **Chunk-level indexing:** Thay vì index toàn bộ document (96K chars), chunk bằng LawArticleChunker rồi index từng chunk riêng biệt → mỗi chunk có embedding cụ thể hơn
> 3. **Metadata enrichment:** Tự động extract metadata từ header: chapter number, article number, article title → cho phép filter `article_number=8` khi user hỏi "Điều 8"
> 4. **Overlap between articles:** Thêm overlap 50 chars giữa các chunk Article liền kề để giữ context tham chiếu chéo ("theo khoản 1 Điều này")

### Failure Analysis (Ex 3.5)

**Failure Case 1: Query 1 — "What is the legal marriage age?"**

| Aspect | Detail |
|--------|--------|
| Query | "What is the legal marriage age for men and women in Vietnam?" |
| Expected source | Law on Marriage and Family 2014.txt (Article 8) |
| Actual top-1 | Law on Investment 2025.txt (score=0.2495) — hoàn toàn không liên quan |
| Root cause | **Mock embedding limitation** — MD5 hash của query tình cờ gần hash của Investment Law header hơn Marriage Law header |
| Impact | User nhận được thông tin về đầu tư thay vì hôn nhân → nguy hiểm trong legal domain |

**Failure Case 2: Query "What are the general provisions of the law?" (ambiguous)**

| Aspect | Detail |
|--------|--------|
| Query | "What are the general provisions of the law?" (câu hỏi mơ hồ) |
| Result | Top-5 trải đều trên 5 sources khác nhau (Children, Educators, Marriage, Investment, Population) |
| Root cause | **Ambiguous query** — mọi luật đều có Chapter I "General Provisions", nên query không đủ specific để phân biệt |
| Impact | Retrieval scatter, không có chunk nào dominant → agent phải đoán mò |

**Đề xuất cải thiện tổng hợp:**
> 1. **Short-term:** Chuyển sang real embedding model (`all-MiniLM-L6-v2`) — giải quyết 80% failure cases
> 2. **Medium-term:** Index ở chunk level thay vì document level — mỗi Article có embedding riêng, giảm dilution
> 3. **Long-term:** Implement hybrid search (BM25 + vector) — keyword "marriage age" sẽ match trực tiếp Article 8 ngay cả khi embedding model không tốt
> 4. **Query enhancement:** Detect ambiguous queries ("general provisions") và yêu cầu user specify thêm ("of which law?") trước khi search

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá | Giải thích |
|----------|------|-------------------|------------|
| Warm-up | Cá nhân | 5 / 5 | Giải thích rõ cosine similarity, ví dụ cụ thể từ dataset luật, chunking math chính xác |
| Document selection | Nhóm | 9 / 10 | 6 tài liệu luật, 5 lĩnh vực, metadata schema 5 trường, data inventory đầy đủ |
| Chunking strategy | Nhóm | 14 / 15 | Custom LawArticleChunker với design rationale rõ ràng, so sánh chi tiết 4 strategies, deep analysis với data thực |
| My approach | Cá nhân | 9 / 10 | Giải thích chi tiết implementation approach cho mọi component, bao gồm edge cases |
| Similarity predictions | Cá nhân | 5 / 5 | 5 pairs từ law dataset, dự đoán trước, phân tích mock vs real embedding behavior |
| Results | Cá nhân | 8 / 10 | 5 benchmark queries với gold answers, kết quả thực tế, metadata filtering test, failure analysis |
| Core implementation (tests) | Cá nhân | 30 / 30 | 42/42 tests passed |
| Demo | Nhóm | 4 / 5 | Có insight cụ thể từ nhóm khác (hybrid retrieval), học được domain-specific chunking |
| **Tổng** | | **84 / 100** | |
