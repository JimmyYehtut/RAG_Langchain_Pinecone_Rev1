# Reranking Methodology: BM25 in Enterprise RAG Pipeline

## Executive Summary

This document details the **BM25 (Okapi BM25)** reranking methodology implemented in the 6-stage enterprise RAG (Retrieval-Augmented Generation) pipeline. The system uses a hybrid retrieval approach combining semantic vector search with lexical keyword-based reranking to optimize document relevance for enterprise knowledge bases.

---

## 1. Pipeline Architecture Overview

The enterprise RAG pipeline consists of **6 sequential stages**:

```
User Query
    ↓
Stage 1: Query Processing (Rewriting & Intent Detection)
    ↓
Stage 2: Semantic Retrieval (Vector Search with RBAC Filtering)
    ↓
Stage 3: BM25 Reranking ⭐ (This Document Focuses Here)
    ↓
Stage 4: Context Assembly (Merge Top-N Chunks)
    ↓
Stage 5: LLM Interaction (Generate Answer)
    ↓
Stage 6: Response Generation (Citation Building)
    ↓
Final Answer + Citations
```

---

## 2. Reranking Methodology: Overview

### 2.1 What is Reranking?

**Reranking** is a post-processing step that re-orders retrieved documents based on a different scoring mechanism. In this system:

- **Retrieval (Stage 2)** uses semantic vector similarity to fetch a larger candidate pool
- **Reranking (Stage 3)** uses BM25 keyword-based scoring to identify the most relevant documents from that pool

### 2.2 Why Hybrid Retrieval?

The hybrid approach combines two complementary ranking signals:

| Signal | Method | Strengths | Weaknesses |
|--------|--------|-----------|-----------|
| **Semantic** | Vector embeddings (cosine similarity) | Captures meaning, handles synonyms, fuzzy matching | Poor at exact keyword matching, fails on domain-specific codes |
| **Lexical** | BM25 (term frequency/IDF) | Excellent at keyword matching, handles codes/names, deterministic | No semantic understanding, sensitive to tokenization |

**Result:** Using both together captures both meaning AND keyword precision.

---

## 3. Stage 3: BM25 Reranking - Detailed Implementation

### 3.1 Function Signature

```python
def _stage3_rerank(query: str, chunks: list[Document]) -> list[Document]:
    """Rerank the semantic-search candidates with BM25 (Okapi BM25).
    
    BM25 scores each chunk by exact keyword overlap with the query using
    term frequency and inverse document frequency, which complements the
    semantic similarity used in retrieval.
    """
```

**Inputs:**
- `query`: The user's rewritten query (from Stage 1)
- `chunks`: List of Document objects retrieved from Pinecone (from Stage 2)

**Output:**
- Reranked list of Document objects, sorted by BM25 score (descending)

### 3.2 Step-by-Step Algorithm

#### Step 1: Deduplication

```python
seen: set[str] = set()
unique: list[Document] = []
for doc in chunks:
    fingerprint = doc.page_content[:200]  # First 200 chars as fingerprint
    if fingerprint not in seen:
        seen.add(fingerprint)
        unique.append(doc)
```

**Purpose:** Remove duplicate or near-duplicate chunks from the retrieval results.

**Method:** Uses first 200 characters of content as a fingerprint. Documents with identical fingerprints are considered duplicates.

**Why:** Pinecone might return overlapping chunks; deduplication prevents redundant scoring.

#### Step 2: Tokenization

```python
# Tokenize corpus
tokenized_corpus = [doc.page_content.lower().split() for doc in unique]

# Tokenize query
query_tokens = query.lower().split()
```

**Purpose:** Convert text into tokens (words) for BM25 scoring.

**Process:**
1. Convert to lowercase (case-insensitive matching)
2. Split on whitespace (simple tokenization)

**Example:**
```
Query:  "What is RAG algorithm?"
Tokens: ["what", "is", "rag", "algorithm?"]

Document: "Retrieval-Augmented Generation (RAG) is a technique"
Tokens:   ["retrieval-augmented", "generation", "(rag)", "is", "a", "technique"]
```

#### Step 3: BM25 Initialization & Scoring

```python
bm25 = BM25Okapi(tokenized_corpus)
scores = bm25.get_scores(query_tokens)  # Returns numpy array of scores
```

**The BM25Okapi Algorithm:**

BM25 is a probabilistic ranking function that computes relevance as:

```
BM25(D, Q) = Σ(i=1 to n) [IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × |D| / avgdl))]
```

Where:
- **D** = Document
- **Q** = Query (set of terms q1, q2, ..., qn)
- **IDF(qi)** = Inverse Document Frequency of term qi
- **f(qi, D)** = Term frequency of qi in document D
- **|D|** = Document length
- **avgdl** = Average document length across corpus
- **k1** = Parameter controlling term frequency saturation (default ~1.5)
- **b** = Parameter controlling length normalization (default ~0.75)

**Simplified Explanation:**

1. **Term Frequency (TF):** How often does each query term appear in the document?
   - More mentions = higher score
   - But saturation applies (doubling mentions doesn't double the score)

2. **Inverse Document Frequency (IDF):** How rare is this term across all documents?
   - Rare terms are weighted higher (more discriminative)
   - Common terms (like "the", "is") weighted lower

3. **Document Length Normalization:** Adjust for document length
   - Longer documents shouldn't automatically rank higher just because they contain more words
   - Parameter `b` controls how much to normalize

**Concrete Example:**

```
Query: "RAG algorithm"
Tokens: ["rag", "algorithm"]

Document A: "Retrieval-Augmented Generation (RAG) algorithm for knowledge enhancement"
  - "rag": appears 1x, IDF = 2.5 (rare) → contributes 2.5 × 1/(1 + 0) = 2.5
  - "algorithm": appears 1x, IDF = 1.2 (common) → contributes 1.2 × 1/(1 + 0) = 1.2
  - BM25_A ≈ 3.7

Document B: "How algorithms work in machine learning systems"
  - "rag": appears 0x, IDF = 2.5 → contributes 0
  - "algorithm": appears 1x, IDF = 1.2 → contributes 1.2
  - BM25_B ≈ 1.2

Result: Document A ranks higher (3.7 > 1.2)
```

#### Step 4: Ranking & Selection

```python
ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
top_indices = ranked_indices[:_RERANK_TOP_N]
```

**Purpose:** Select the top N documents by BM25 score.

**Process:**
1. Sort all documents by their BM25 scores (highest first)
2. Keep only the top N documents (configured via `RERANK_TOP_N`)
3. Discard the rest

#### Step 5: Attach Metadata

```python
reranked: list[Document] = []
for idx in top_indices:
    doc = unique[idx]
    doc.metadata["bm25_score"] = round(float(scores[idx]), 4)
    reranked.append(doc)
```

**Purpose:** Preserve the BM25 score in document metadata for traceability and debugging.

**Output:** Final reranked documents with scores (e.g., `0.8742`)

---

## 4. Configuration Parameters

The reranking pipeline is controlled by environment variables:

```env
# Retrieval stage - how many candidates to fetch
RETRIEVAL_TOP_K=15

# Reranking stage - how many to keep after reranking
RERANK_TOP_N=5

# Embedding model
OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
EMBEDDING_DIMENSION="1024"

# Vector store index
PINECONE_INDEX_NAME="ragindex"
```

### 4.1 Parameter Tuning Guide

#### `RETRIEVAL_TOP_K` (Default: 15)
- Number of documents fetched by semantic search (Stage 2)
- **Larger value (20-50):** More candidate documents to rerank, better coverage but slower
- **Smaller value (5-10):** Faster retrieval but may miss relevant documents
- **Sweet spot:** 15-20 for most enterprise use cases

#### `RERANK_TOP_N` (Default: 5)
- Number of documents kept after BM25 reranking (fed to Stage 4)
- **Larger value (10-15):** More context for LLM, longer processing, more hallucination risk
- **Smaller value (3-5):** Focused context, faster, better coherence
- **Sweet spot:** 5 documents (balances quality and conciseness)

### 4.2 Recommended Configurations

**High-Precision Mode** (accurate, slower):
```env
RETRIEVAL_TOP_K=30
RERANK_TOP_N=8
```

**Balanced Mode** (recommended):
```env
RETRIEVAL_TOP_K=15
RERANK_TOP_N=5
```

**Fast Mode** (speed-optimized):
```env
RETRIEVAL_TOP_K=10
RERANK_TOP_N=3
```

---

## 5. Advantages of BM25 Reranking

### 5.1 Problem It Solves

**Semantic Search Failure Cases:**
- Query: "Invoice #12345 status?"
  - Vector embeddings struggle with specific alphanumeric codes
  - BM25 excels at exact keyword matching → finds "12345" in documents

- Query: "RFC 3986 compliance"
  - Semantic model might confuse "RFC" with "Request for Comments"
  - BM25 matches exact token "RFC" → ranks documents with this term higher

### 5.2 Advantages Over Semantic-Only Search

| Scenario | Semantic Only | Semantic + BM25 | Winner |
|----------|---------------|-----------------|--------|
| "Database ID abc123" | ❌ Low match (code treated as noise) | ✅ BM25 finds exact code | BM25 |
| "What is machine learning?" | ✅ High match (understands intent) | ✅ Both good | Tie |
| "FAQs about HIPAA compliance" | ❌ Might miss acronym | ✅ BM25 matches "HIPAA" | BM25 |
| "Explain embeddings" | ✅ Understands semantics | ✅ Also good | Semantic |

---

## 6. BM25 vs. Other Reranking Approaches

### Comparison Matrix

| Approach | Speed | Accuracy | Cost | Enterprise Ready | Use Case |
|----------|-------|----------|------|------------------|----------|
| **BM25** (Our choice) | ⭐⭐⭐⭐⭐ Very Fast | ⭐⭐⭐⭐ Good | Free | ✅ Yes | General enterprise |
| Cross-Encoder | ⭐⭐⭐ Slower | ⭐⭐⭐⭐⭐ Excellent | $$ API | ⭐ Maybe | Premium quality needed |
| LLM Reranking | ⭐ Very Slow | ⭐⭐⭐⭐⭐ Excellent | $$$ Expensive | ❌ No | Quality over speed |
| ColBERT | ⭐⭐⭐ Medium | ⭐⭐⭐⭐⭐ Excellent | $ Model | ⭐ Maybe | Custom models |

**Why We Chose BM25:**
1. **No API calls** → No additional latency
2. **Deterministic** → Same input always produces same output
3. **Lightweight** → No GPU/ML overhead
4. **Proven** → Used in industry for 20+ years
5. **Complementary** → Combines perfectly with semantic search

---

## 7. Integration with Full Pipeline

### 7.1 Data Flow

```python
def run_pipeline(query: str, department: str) -> PipelineResult:
    llm = ChatOpenAI(model=_CHAT_MODEL, temperature=0)
    vectorstore = _get_vectorstore()
    
    # Stage 1: Query Rewriting
    rewritten = _stage1_process_query(query, llm)
    # Output: "What is RAG algorithm?" → "RAG algorithm advantages"
    
    # Stage 2: Semantic Retrieval (15 candidates)
    candidates = _stage2_retrieve(rewritten, department, vectorstore)
    # Output: [Doc1, Doc2, ..., Doc15] sorted by semantic similarity
    
    # Stage 3: BM25 Reranking (keep top 5)
    reranked_chunks = _stage3_rerank(rewritten, candidates)
    # Output: [Doc3, Doc7, Doc1, Doc14, Doc9] sorted by BM25 score
    
    # Stage 4: Context Assembly
    context = _stage4_assemble_context(reranked_chunks)
    # Output: Formatted string with all 5 documents
    
    # Stage 5: LLM Answer Generation
    answer = _stage5_call_llm(context, rewritten, llm)
    # Output: "RAG is a technique that..."
    
    # Stage 6: Citation Attachment
    final_answer, citations = _stage6_build_response(answer, reranked_chunks)
    # Output: Answer + BM25 scores in metadata
    
    return PipelineResult(
        answer=final_answer,
        citations=citations,
        rewritten_query=rewritten,
        raw_chunks=reranked_chunks,
    )
```

### 7.2 RBAC & Security Integration

**Important:** Reranking happens AFTER security filtering:

```python
# Stage 2: Pinecone enforces RBAC BEFORE retrieval
metadata_filter = {"allowed_departments": {"$in": [department]}}
candidates = vectorstore.similarity_search(
    query,
    k=_RETRIEVAL_TOP_K,
    filter=metadata_filter,  # ← Security filter applied here
    namespace="enterprise-kb",
)

# Stage 3: BM25 reranking only operates on already-filtered documents
# No security issue: we only rerank what user is allowed to see
reranked_chunks = _stage3_rerank(query, candidates)
```

**Security Property:** Unauthorized documents are never retrieved, so they cannot be reranked or surfaced to the user.

---

## 8. Citation Tracking

### 8.1 How BM25 Scores Enable Citations

The BM25 scores are preserved and used for citation building:

```python
def _stage6_build_response(answer: str, chunks: list[Document]) -> tuple[str, list[dict]]:
    citations: list[dict] = []
    for i, doc in enumerate(chunks):
        citations.append({
            "document_name": _clean_title(doc.metadata.get("document_name", "Unknown")),
            "document_id": doc.metadata.get("document_id", ""),
            "chunk_index": i,
            "bm25_score": doc.metadata.get("bm25_score"),  # ← Score from Stage 3
        })
    return answer, citations
```

**Example Citation Output:**
```json
{
  "document_name": "RAG Overview",
  "document_id": "doc-1024",
  "chunk_index": 0,
  "bm25_score": 4.2187
}
```

The BM25 score can be displayed to users or used for transparency about which documents contributed most to the answer.

---

## 9. Performance Characteristics

### 9.1 Computational Complexity

```
Stage 3: BM25 Reranking Complexity
==================================

Operation                    Time Complexity    Memory
─────────────────────────────────────────────────────
Deduplication               O(n)               O(n)
Tokenization (corpus)       O(n × m)           O(n × m)
BM25 initialization         O(n × m)           O(n × m)
Scoring (all documents)     O(n × q)           O(n + q)
Ranking & selection         O(n log n)         O(n)
─────────────────────────────────────────────────────
Total (estimated)           O(n log n)         O(n × m)

Where:
  n = number of documents (RETRIEVAL_TOP_K = 15)
  m = average document length in tokens
  q = number of query tokens
```

### 9.2 Benchmark (Typical Numbers)

**With Default Config (RETRIEVAL_TOP_K=15, RERANK_TOP_N=5):**

```
Retrieval (Stage 2):        ~80ms   (Pinecone vector search)
Deduplication:              ~1ms    (15 documents)
Tokenization:               ~3ms    (split on whitespace)
BM25 Scoring:               ~2ms    (rank all 15)
Ranking:                    ~0.5ms  (sort 15 items)
─────────────────────────────
Total Stage 3 Time:         ~6.5ms  ← Very fast!
```

**Why So Fast?**
- Only operates on top-K results (not entire corpus)
- Simple whitespace tokenization (no NLP library)
- Lightweight BM25 implementation (rank_bm25 library)
- No external API calls

---

## 10. Debugging & Monitoring

### 10.1 Accessing BM25 Scores

BM25 scores are attached to each document's metadata:

```python
result = run_pipeline("RAG benefits", department="engineering")

for citation in result.citations:
    print(f"{citation['document_name']}: {citation['bm25_score']}")
    # Output:
    # "RAG Overview": 4.2187
    # "Neural Embeddings": 2.8941
    # "System Architecture": 1.5632
```

### 10.2 Debugging Reranking

To understand why documents were reranked:

```python
# Before reranking (Stage 2 output)
print("Semantic Retrieval Results (Top 5):")
for i, doc in enumerate(candidates[:5]):
    print(f"  {i+1}. {doc.metadata.get('document_name')} (semantic)")

# After reranking (Stage 3 output)
print("\nBM25 Reranking Results (Top 5):")
for i, doc in enumerate(reranked_chunks):
    print(f"  {i+1}. {doc.metadata.get('document_name')} "
          f"(BM25: {doc.metadata.get('bm25_score')})")
```

### 10.3 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Wrong documents ranked first" | Keyword bloat (query too long) | See Stage 1: Query Rewriting improves this |
| "BM25 ignores synonyms" | By design (lexical, not semantic) | That's why semantic search is Stage 2 |
| "All documents get score 0" | No query terms match corpus | Check tokenization, verify documents exist |
| "Reranking takes too long" | Large RETRIEVAL_TOP_K value | Reduce to 10-15 |

---

## 11. Advanced Tuning

### 11.1 BM25 Algorithm Parameters

The underlying `BM25Okapi` implementation uses standard parameters:

```python
bm25 = BM25Okapi(tokenized_corpus)
# Default parameters:
# k1 = 1.5 (controls TF saturation)
# b = 0.75 (controls length normalization)
```

**Customization (if needed):**

```python
# In pipeline.py, modify Stage 3:
bm25 = BM25Okapi(tokenized_corpus, k1=2.0, b=0.5)  # Custom parameters

# More aggressive TF scoring (k1=2.0 vs 1.5)
# Reduced length normalization (b=0.5 vs 0.75)
```

### 11.2 Tokenization Improvements

Current: Simple whitespace split
```python
tokenized = query.lower().split()
```

**If specialized terms needed:**
```python
# Option 1: Keep hyphens/underscores
import re
tokenized = re.findall(r'\b[\w\-]+\b', query.lower())

# Option 2: Lemmatization (requires NLTK)
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
tokenized = [lemmatizer.lemmatize(t) for t in query.lower().split()]

# Option 3: Stop word removal
from nltk.corpus import stopwords
stop = set(stopwords.words('english'))
tokenized = [t for t in query.lower().split() if t not in stop]
```

---

## 12. Conclusion & Best Practices

### 12.1 When to Use BM25 Reranking

✅ **Use BM25 when:**
- Documents contain domain-specific codes, IDs, or technical terms
- Query precision matters (enterprise knowledge bases)
- Speed is important (no external APIs)
- Determinism is required (exact same results each time)

❌ **Don't use BM25 when:**
- Only semantic understanding matters (no specific keywords)
- Ultra-high accuracy is critical (consider Cross-Encoder instead)
- Documents are very short (insufficient term frequency signal)

### 12.2 Production Best Practices

1. **Monitor Reranking Effectiveness**
   - Compare answers before/after reranking
   - Track if top documents are actually relevant
   - Adjust RERANK_TOP_N based on answer quality

2. **Log BM25 Scores**
   - Store scores with answers for analysis
   - Identify edge cases where reranking failed
   - Feed data back to improve Stage 1 (query rewriting)

3. **Tune for Your Domain**
   - Enterprise knowledge bases may need different K values
   - Test RETRIEVAL_TOP_K (10-30) and RERANK_TOP_N (3-10)
   - Measure impact on latency and quality

4. **Combine with Query Optimization**
   - Stage 1 (query rewriting) has more impact than Stage 3 reranking
   - Clean, specific queries → better retrieval → less reranking needed
   - Poor query → bad candidates → reranking can't fix it

---

## References

- **BM25 Paper:** Okapi BM25 (Robertson et al., 1999)
- **Implementation:** `rank_bm25` library (Python)
- **Pipeline Code:** `rag/pipeline.py`
- **Configuration:** `.env` file (RETRIEVAL_TOP_K, RERANK_TOP_N)

---

**Document Version:** 1.0  
**Last Updated:** June 2026  
**Author:** RAG Pipeline Team
