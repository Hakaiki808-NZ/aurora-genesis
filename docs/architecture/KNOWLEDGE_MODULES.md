# Genesis knowledge modules — v0.1 reference implementation

## Purpose

Install, update, disable, search and remove subject-matter reference packs independently of the core Genesis model. A future Kyro marketplace could sell licensed packs, including degree-level physics material, without claiming that installation confers an accredited degree or human-equivalent competence.

The initial implementation is deliberately knowledge-only. Packs do not execute code, alter weights, install tools, create Guardians, change the Constitution, or grant Aurora authority.

## Architecture and boundaries

- Genesis validates a JSON manifest, persists data-only chapters in separate SQLite tables, retrieves passages and can give untrusted source passages to an already configured neural text backend.
- Aurora remains authoritative for execution, sandboxing, networking and future license verification and payment-related actions. This feature does not modify private Aurora internals.
- Kyro is intended to show a catalogue, purchases, installation, versions, enable/disable, provenance and proficiency. That marketplace UI is not yet built.

Installed texts are unverified reference data. Instructions embedded in source text must never be promoted to authority. A neural response can still be wrong when provided with a good source.

## Pack manifest (schema 1)

The schema includes: schema_version (integer 1), id (lowercase slug), title, version (major.minor.patch), publisher, license, subject, distribution (currently only open) and chapters (1–250 objects of id, title, content, source).

Unknown executable fields are rejected. A normalized SHA-256 fingerprint is calculated on installation, replacement needs an explicit flag and the installation is persistent. Limits are 2 MB per pack and 12,000 characters per chapter. This is a prototype for small references, not a complete multi-year course-library pipeline.

The SHA-256 is a change detector, not a publisher signature. License and publisher metadata are self-declared and NOT verified. Do not distribute third-party copyrighted materials without rights.

## Python example

    import json
    from pathlib import Path
    from genesis import Genesis

    pack = json.loads(Path("examples/modules/physics-foundations.json").read_text())
    with Genesis(enable_ollama=False) as model:
        model.install_knowledge_module(pack)
        print(model.search_knowledge_modules("Explain net force and acceleration"))
        print(model.respond("Explain net force and acceleration"))
        model.enable_knowledge_module("physics-foundations", False)
        model.uninstall_knowledge_module("physics-foundations")

## HTTP endpoints

- GET /modules — list installed packs
- GET /modules/search?q=... — search enabled passages
- POST /modules — install with request body containing package and optional replace flag
- POST /modules/{module_id}/status — enable or disable
- DELETE /modules/{module_id} — uninstall

All mutations require the X-Genesis-Module-Admin header matching GENESIS_MODULE_ADMIN_TOKEN (minimum 24 characters). Without the configured secret they fail closed. Keep the v0.1 HTTP service restricted to localhost or a trusted private network. A static token is not suitable authentication for a public multi-user marketplace.

User chat messages do not automatically install or upgrade packages. Installation is an explicit administrative action.

## Testing

Run python -m tests.knowledge_modules or python verify.py. Tests cover installation, duplicate idempotency, version replacement, search in cognition, attribution, disabling, persistence, removal, validation and admin gating. The demonstration pack covers three brief classical mechanics topics and is NOT an accredited course or degree.

## Production launch gates — not completed

1. Rights and entitlements: signed publisher manifests, source licensing, authenticated purchasers, transaction-controlled activation and revocation. Protect signing and billing keys outside Genesis.
2. Multi-user accounts and isolation: per-user entitlements and separate pack indexes. Current module data is shared within a single Genesis state file.
3. Proficiency: syllabus mapping, topic coverage, problem solving, independent examinations, calibrated scores and human review. Installation alone does not prove competency.
4. Specialist weights: optional compatible LoRA/PEFT adapters for supported open-weight models, with model compatibility checks and bounded compute. NOT implemented here.
5. Security and operations: publisher trust, abuse review, adversarial document testing, semantic retrieval, update/rollback audit and real Aurora module admission.

Suggested progression: Knowledge Pack (reference information), Skill Pack (validated procedures, guarded tools), Expertise Pack (knowledge, optional model adapter and measured proficiency). A purchase grants access to content, not an automatic university credential.
