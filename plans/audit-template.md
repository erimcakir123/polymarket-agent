PHASE 1 — Scoped Context (grep-first, RAM-aware):

1. Read ONLY the files listed as CHANGED in PHASE 2 below.
2. For each changed file, discover external consumers via grep (not Read):
     Grep pattern: "from src.<module>|import.*<module_name>"
     Grep pattern: "<exported_function_name>|<exported_class_name>"
   Look at the grep output as a LIST of candidate files — do not open them blindly.
3. Read ONLY the consumer files that grep actually returned. These are the
   files that could be broken by the change. Nothing else is relevant.
4. For huge consumer files (>1000 lines), read only the relevant function/region
   via Read(..., offset=X, limit=Y). Do not load entire large files.

BANNED patterns (cause RAM crashes, wasted context):
- "Read ALL src/*.py files" — blind glob-and-read. This is the #1 audit crash cause.
- Reading files that grep did not return as consumers.
- Reading API Guides/, docs/, logs/, tests/, .env, config YAML that is unchanged.
- Spawning sub-agents (subagent_type=Agent).

PREFERRED patterns:
- Grep over Read for symbol-level flow understanding.
- Targeted Read with offset+limit for huge files.
- Early "CLEAN" exit if grep shows no broken references in consumers.

PHASE 2 — Focused Audit: Check these CHANGED files for issues:
Files: [liste]
Changes: [her dosyada ne değişti, 1 cümle]

Look for:
- Runtime errors (missing imports, wrong args, undefined vars)
- Logic bugs (wrong conditions, broken control flow, edge cases)
- Breaking changes (grep-verified consumer breakage)
- Interface mismatches (signature changed but caller not updated)
- Dead code (RAPORLA ama silme, kullanıcıya sor)
- Spaghetti code (fonksiyon >80 satır, duplicate logic, iş mantığı main.py'de)

Rules:
- Do NOT spawn sub-agents
- Do NOT read API Guides or docs/
- IGNORE: cosmetic issues, type hints, docstrings, formatting, naming style
- Report format: file:line — description — severity (critical/warning)
