# Vaaani

Vaaani is a production-oriented, voice-enabled multilingual RAG system for Indian languages. It turns a spoken question into a cited answer and spoken response while exposing the confidence and cost of every pipeline stage.

The reference corpus is [AI4Bharat MSMARCO-XI](https://huggingface.co/datasets/ai4bharat/MSMARCO-XI). English and Hindi are enabled by default; Bengali, Tamil, Marathi, Telugu, Gujarati, Kannada, Malayalam, Odia, and Punjabi use the same ingestion and retrieval code.

## What makes a response trustworthy

- The topic gate rejects unsafe instructions before retrieval.
- Dense multilingual retrieval and BM25 are fused, then reranked.
- A confidence threshold refuses weak retrieval explicitly.
- The answer prompt permits only supplied evidence and requires citations.
- An NLI check blocks claims that are not entailed by the retrieved passages.
- The API returns every decision and duration; the interface does not hide refusals.

Start with the [setup guide](setup.md), then read the [architecture](architecture.md).
