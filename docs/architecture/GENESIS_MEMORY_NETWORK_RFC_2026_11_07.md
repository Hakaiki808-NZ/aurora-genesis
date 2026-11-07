# Genesis memory network — design and deployment gate

Status: **pre-alpha prototype, not cloud deployed**. Source is committed on the isolated feature branch as `genesis/memory_network.py`, with tests in `tests/memory_network.py`. It is not a deployed cloud capability.

## Architecture

- L0: 64-entry process-local retrieval cache with a short expiry and DB revision tracking.
- L1: transient per-thread RAM-only scratchpad with a short TTL.
- L2: persisted bounded working memory (default 15 minutes, up to 40 active items/thread).
- L3: persisted bounded short-term memory (default 24 hours, up to 240 active items/thread).
- L4: persisted long-term **semantic**, **episodic**, and **procedural** records.
- Associations: directed, typed weighted links, one-hop spreading activation from the five strongest direct hits, max eight edges each.
- Query paths: exact normalized key, FTS5 lexical shortlist, optional embedding encoder, association expansion, bounded top-K retrieval.
- Optional **local neural** encoder: `genesis/memory_encoders.py` uses an independently installed Ollama `/api/embed` model on `127.0.0.1:11434` only. This adapter remains OFF by default, makes no requests on Genesis startup, and never installs/pulls a model.
- Enable deliberately for testing with `GENESIS_MEMORY_ENCODER=ollama` and optionally `GENESIS_MEMORY_EMBEDDING_MODEL=embeddinggemma`. Pre-install the named Ollama embedding model separately and check local loopback availability. This is a synchronous adapter; its failures surface as explicit errors, not silent fallback.
- Model tags are not immutable identifiers. Replacing the model under the same tag requires invalidating and recomputing existing vectors. Corpus-scale ANN, rerankers, and neural-network weight training are not included.
- Safe consolidation: explicit `promote` only; no autonomous conversion of untrusted data to long-term facts.

Existing Genesis: `storage.py` has persisted episodes/facts/rules, `retrieval.py` offers BM25-style knowledge search, `user_capabilities.py` provides per-profile consent records. This is a supplementary typed memory subsystem using the existing SQLite Store and consent scope; it does not replace them or train model weights.

## Trust and privacy

Kyro must authenticate profile IDs server-side, never allow arbitrary profile selection from a browser field. The memory feature must require explicit `ux_consents.memory` consent. A revocation must delete new memory tables through a DB trigger *and* clear process-local transient/cache entries. Existing legacy episodes, SQLite WAL remnants and backups require a separate privacy/deletion migration before production.

Memory-derived procedural text is **data only**, never an authorization to call an Aurora Engine action or change Guardians. Neural search is optional and requires a configured, versioned embedding encoder; a graph link is not a neural weight.

## Work committed to the feature branch

- Prototype implementation `genesis/memory_network.py`
- Standalone SQLite contract tests for consent, cross-profile isolation, TTLs, versioning, link traversal, promotion, deletion and vector hook
- Local test verdict: `MEMORY_NETWORK=PASS; FTS=True`

## Gates before merge/deployment

1. Run native CI against current Genesis `Store` and `Genesis` integration; fix failures before merge.
2. Validate consent/revoke triggers and complete cleanup of process-local memory.
3. Benchmark on representative recall and latency tasks; compare against current BM25 and long context.
4. Add approved authenticated Kyro memory API and isolate multi-worker caches.
5. Add encryption/backup erasure and source verification/contradiction handling.
6. Verify AWS deployment health and explicit cost controls before exposure.

## Sources
- LangGraph: https://langchain-ai.github.io/langgraph/concepts/memory/
- Letta: https://docs.letta.com/v1-sdk/memory/memory-blocks
- Graphiti: https://help.getzep.com/v4/graph-overview
- Redis: https://redis.io/docs/latest/develop/use-cases/memory-layer/
