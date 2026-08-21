# Architecture

Vaaani has two connected planes: a live answer plane for voice and text requests, and an offline knowledge plane that prepares multilingual evidence. The architecture is split into focused flowcharts so each path stays readable in VS Code, MkDocs, and GitHub instead of being compressed into one poster-sized SVG.

## Live request flow

This is the primary end-to-end path. Read it top to bottom; each horizontal band is one stage of the request. Solid arrows are request or data flow. Dashed arrows are supporting data or telemetry.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Inter, ui-sans-serif, system-ui","primaryTextColor":"#172033","lineColor":"#64748b","clusterBkg":"#f8fafc","clusterBorder":"#cbd5e1"},"flowchart":{"curve":"linear","nodeSpacing":30,"rankSpacing":42,"htmlLabels":true}}}%%
flowchart TB
    subgraph INPUT["1 · USER INPUT"]
        direction TB
        USER((User)) --> MODE{"Voice or text?"}
        MODE -->|Voice| REC["Browser recorder"]
        REC --> STT["Sarvam STT<br/>audio to transcript"]
        MODE -->|Text| TEXT["Typed question"]
        STT --> TRANSCRIPT["Normalized transcript<br/>language + history"]
        TEXT --> TRANSCRIPT
    end

    subgraph UNDERSTAND["2 · UNDERSTAND AND GUARD"]
        direction TB
        TRANSCRIPT --> TOPIC{"Safe and searchable?"}
        TOPIC -->|Allowed| REWRITE["Rewrite query<br/>resolve references"]
    end

    subgraph RETRIEVE["3 · HYBRID RETRIEVAL"]
        direction TB
        REWRITE --> DENSE["Multilingual MPNet<br/>Qdrant dense top 50"]
        REWRITE --> SPARSE["Language filter<br/>BM25 sparse top 50"]
        DENSE --> RRF["Reciprocal rank fusion<br/>top 20"]
        SPARSE --> RRF
        RRF --> RERANK["MS MARCO cross-encoder<br/>rerank candidates"]
        RERANK --> TOP5["Top 5 evidence passages"]
    end

    subgraph ANSWER["4 · GENERATE AND VERIFY"]
        direction TB
        TOP5 --> CONF{"Confidence passed?"}
        CONF -->|Yes| GENERATE["Evidence-only generation<br/>inline citations"]
        GENERATE --> GROUND{"Grounded in evidence?"}
        GROUND -->|Yes| TTS["Sarvam TTS<br/>trusted answer to audio"]
    end

    subgraph DELIVER["5 · RESPONSE"]
        direction TB
        TTS -->|Audio available| RESPONSE["Typed QueryResponse<br/>answer + sources + audio"]
        TTS -->|TTS unavailable| TEXTONLY["Trusted text only<br/>mark TTS degraded"]
        TEXTONLY --> RESPONSE
        RESPONSE --> UI["Answer workspace<br/>stream + citations + timings"]
    end

    TOPIC -->|Blocked or empty| REFUSE["Refuse safely<br/>machine-readable reason"]
    CONF -->|No results or low score| REFUSE
    GROUND -->|Unsupported or checker error| REFUSE
    STT -->|Failed after retries| REFUSE
    REFUSE --> RESPONSE

    QDRANT[("Qdrant passage index<br/>vectors + multilingual payload")] -.-> DENSE
    QDRANT -.-> SPARSE
    TRACE[("Per-node trace<br/>latency + status + degradation")] -.-> RESPONSE

    classDef actor fill:#172033,color:#ffffff,stroke:#172033,stroke-width:2px;
    classDef input fill:#e0f2fe,color:#0c4a6e,stroke:#38bdf8,stroke-width:1.5px;
    classDef process fill:#eef2ff,color:#312e81,stroke:#818cf8,stroke-width:1.5px;
    classDef retrieval fill:#f3e8ff,color:#581c87,stroke:#c084fc,stroke-width:1.5px;
    classDef decision fill:#fef3c7,color:#78350f,stroke:#f59e0b,stroke-width:1.5px;
    classDef storage fill:#ecfdf5,color:#064e3b,stroke:#34d399,stroke-width:1.5px;
    classDef danger fill:#fee2e2,color:#7f1d1d,stroke:#f87171,stroke-width:2px;
    classDef success fill:#dcfce7,color:#14532d,stroke:#4ade80,stroke-width:2px;

    class USER actor;
    class REC,STT,TEXT,TRANSCRIPT input;
    class REWRITE,GENERATE,TTS,TEXTONLY,RESPONSE,TRACE process;
    class DENSE,SPARSE,RRF,RERANK,TOP5 retrieval;
    class MODE,TOPIC,CONF,GROUND decision;
    class QDRANT storage;
    class REFUSE danger;
    class UI success;
```

The red refusal lane is intentionally shared by STT, topic safety, retrieval confidence, and groundedness. In particular, a groundedness-check exception after retries follows the same refusal path; an unchecked draft never reaches TTS.

## Knowledge and indexing flow

This flow runs offline. It creates the persistent collection consumed by both dense and sparse retrieval in the live request flow.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Inter, ui-sans-serif, system-ui","primaryTextColor":"#172033","lineColor":"#64748b"},"flowchart":{"curve":"linear","nodeSpacing":28,"rankSpacing":38,"htmlLabels":true}}}%%
flowchart TB
    SOURCE[("MSMARCO-XI<br/>parallel query-passage data")]
    LANGS["Balanced language subsets<br/>3 or more languages"]
    NORMALIZE["Normalize records<br/>IDs + language + provenance"]
    CHOICE{"Chunk strategy"}
    FIXED["Fixed-size<br/>overlapping chunks"]
    SEMANTIC["Semantic<br/>sentence breakpoints"]
    META["Metadata-aware<br/>native boundaries"]
    CHUNKS["Typed chunks<br/>stable UUIDs"]
    EMBED["Multilingual MPNet<br/>768-dimensional vectors"]
    UPSERT["IndexBuilder<br/>batched upsert"]
    INDEX[("Persistent Qdrant collection<br/>vector + filterable payload")]
    READY["Health check<br/>indexed chunk count"]

    SOURCE --> LANGS --> NORMALIZE --> CHOICE
    CHOICE --> FIXED
    CHOICE --> SEMANTIC
    CHOICE --> META
    FIXED --> CHUNKS
    SEMANTIC --> CHUNKS
    META --> CHUNKS
    CHUNKS --> EMBED --> UPSERT --> INDEX --> READY

    classDef source fill:#e0f2fe,color:#0c4a6e,stroke:#38bdf8,stroke-width:1.5px;
    classDef process fill:#eef2ff,color:#312e81,stroke:#818cf8,stroke-width:1.5px;
    classDef choice fill:#fef3c7,color:#78350f,stroke:#f59e0b,stroke-width:1.5px;
    classDef store fill:#ecfdf5,color:#064e3b,stroke:#34d399,stroke-width:2px;

    class SOURCE source;
    class LANGS,NORMALIZE,FIXED,SEMANTIC,META,CHUNKS,EMBED,UPSERT,READY process;
    class CHOICE choice;
    class INDEX store;
```

## Runtime and deployment flow

The browser talks only to FastAPI. Provider and storage boundaries remain explicit so their latency and failure state can be reported independently.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Inter, ui-sans-serif, system-ui","primaryTextColor":"#172033","lineColor":"#64748b"},"flowchart":{"curve":"linear","nodeSpacing":32,"rankSpacing":42,"htmlLabels":true}}}%%
flowchart TB
    USER((User)) --> WEB["Next.js frontend<br/>Vercel"]
    WEB -->|HTTPS + SSE| API["FastAPI service<br/>Railway"]
    API --> GRAPH["LangGraph<br/>request orchestration"]
    GRAPH --> QDRANT[("Qdrant<br/>persistent evidence index")]
    GRAPH --> SARVAM["Sarvam<br/>STT + TTS"]
    GRAPH --> LLM["OpenAI-compatible LLM<br/>OpenAI or OpenRouter"]
    GRAPH --> MODELS["Hugging Face models<br/>embedding + reranking + NLI"]
    BENCH["50-query multilingual<br/>HTTP benchmark"] -->|real requests| API
    GRAPH -.-> TELEMETRY["Per-stage telemetry<br/>P50 + P70 + P100"]
    TELEMETRY --> REPORTS["JSON + Markdown reports<br/>MkDocs documentation"]

    classDef actor fill:#172033,color:#ffffff,stroke:#172033,stroke-width:2px;
    classDef edge fill:#e0f2fe,color:#0c4a6e,stroke:#38bdf8,stroke-width:1.5px;
    classDef service fill:#eef2ff,color:#312e81,stroke:#818cf8,stroke-width:1.5px;
    classDef provider fill:#fef3c7,color:#78350f,stroke:#f59e0b,stroke-width:1.5px;
    classDef storage fill:#ecfdf5,color:#064e3b,stroke:#34d399,stroke-width:1.5px;
    classDef ops fill:#f0fdfa,color:#134e4a,stroke:#2dd4bf,stroke-width:1.5px;

    class USER actor;
    class WEB edge;
    class API,GRAPH service;
    class SARVAM,LLM,MODELS provider;
    class QDRANT storage;
    class BENCH,TELEMETRY,REPORTS ops;
```

## Component responsibilities

### Online request plane

The browser sends the selected language, recent conversation turns, and either text or Base64-encoded microphone audio. `/query` returns regular JSON; `/query/stream` exposes metadata, validated answer tokens, optional audio, and a terminal request ID as server-sent events.

`ServiceContainer` composes providers during startup. LangGraph passes a typed `GraphState` between nodes, records per-node timing, and uses explicit conditional edges for success, degradation, and refusal paths.

### Hybrid evidence path

The rewritten query fans out into two retrieval paths:

1. **Dense:** multilingual MPNet produces a normalized 768-dimensional query vector and Qdrant performs cosine search under a language filter.
2. **Sparse:** the language-filtered corpus is tokenized and scored with BM25.
3. **Fusion:** reciprocal rank fusion combines both rankings into 20 candidates.
4. **Reranking:** an MS MARCO cross-encoder narrows the evidence to five passages used by confidence, generation, groundedness, and citations.

The Qdrant collection is the single evidence source. Dense and sparse paths use the same passage IDs, language fields, chunk strategy, translation provenance, and evaluation labels written by ingestion.

### Trust and refusal path

Three independent gates protect the answer:

- The topic classifier refuses unsafe or non-searchable input before retrieval.
- The confidence gate exposes both the computed score and configured threshold.
- The groundedness gate compares the draft with the top-five evidence passages.

Groundedness is deliberately **fail-closed**. If the checker fails after all retries, the graph refuses with `groundedness_check_unavailable`. Missing TTS may degrade to trusted text; missing evidence never degrades to an ungrounded answer.

### Response contract

| Channel | Contents |
|---|---|
| Answer | Grounded text with inline citation markers |
| Voice | Optional Sarvam-generated WAV audio |
| Evidence | Top-five passages, ranks, scores, language and provenance |
| Safety | Guardrail name, result, reason and quantitative details |
| Performance | Per-stage timestamps, duration, status and total latency |
| Operations | Request ID and explicit degraded-service names |

This contract drives `AnswerCard`, `SourceCitation`, `GuardrailBanner`, `LatencyDashboard`, and the status surface without hiding fallback or refusal behavior.

## Failure semantics

| Failure | Retry behavior | Terminal behavior |
|---|---|---|
| Sarvam STT unavailable | Three total attempts | Refuse with a specific STT reason |
| Qdrant retrieval unavailable | Three total attempts | Empty evidence reaches the confidence refusal path |
| Retrieval confidence low | No provider retry required | Refuse with score and threshold |
| LLM unavailable | Provider policy applies | Explicit offline mode may use extractive generation |
| Groundedness checker unavailable | Three total attempts | Fail closed with `groundedness_check_unavailable` |
| Answer unsupported by evidence | Deterministic decision | Refuse with `groundedness_entailment_failed` |
| Sarvam TTS unavailable | Three total attempts | Preserve trusted text and mark TTS degraded |
