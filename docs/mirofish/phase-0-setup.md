# MiroFish Political Bot — Phase 0: Setup & Mechanical Test

> **Paste this into a NEW Claude Code window.**
> Working directory: `c:\Users\erimc\OneDrive\Desktop\CLAUDE\MiroFish Political Bot`

---

## CONTEXT

We are building a SEPARATE political prediction bot that uses MiroFish (social simulation engine) to trade political/geopolitical markets on Polymarket. This is Phase 0 of 5.

**This bot is 100% INDEPENDENT from the existing Polymarket sports bot.** Do not touch, modify, import from, or interfere with anything in `c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent\`. That bot has live positions and must not be disrupted.

## OBJECTIVE

Install and configure MiroFish Offline, verify the pipeline works end-to-end. NO API costs — use whatever free/default LLM MiroFish ships with. We are testing MECHANICS only, not simulation quality.

## HARD RULES

1. **Read this ENTIRE prompt before doing anything.**
2. **Do NOT touch the Polymarket Agent directory** — `c:\Users\erimc\OneDrive\Desktop\CLAUDE\Polymarket Agent\` is off-limits.
3. **Do NOT spend money** — no paid API keys. Use free tiers or whatever default MiroFish provides.
4. **Do NOT install anything globally** that could conflict with the existing Polymarket Agent's Python environment.
5. **Test after EVERY installation step** — verify each component works before proceeding.
6. **Ask before any destructive action** — no `rm -rf`, no deleting existing Docker containers, no killing processes.
7. **Document everything** — write what you did, what worked, what didn't, in `docs/setup-log.md`.

## SYSTEM INFO

- OS: Windows 11
- CPU: Intel i7-11800H (8 core)
- RAM: 16 GB
- GPU: RTX 3050 Laptop — 4 GB VRAM (NOT enough for local LLM)
- Python: 3.11-3.12 (already installed for Polymarket Agent)
- Node.js: Check if installed (`node -v`)
- Docker: Probably NOT installed yet

## STEP-BY-STEP TODO LIST

### Step 1: Create Project Directory
```bash
mkdir -p "c:/Users/erimc/OneDrive/Desktop/CLAUDE/MiroFish Political Bot"
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/MiroFish Political Bot"
git init
```
Create a CLAUDE.md for this project with these rules:
- This is a MiroFish-based political prediction bot
- Completely separate from Polymarket Agent
- Never touch other project directories
- Profile: default

### Step 2: Install Docker Desktop
- Check if Docker is already installed: `docker --version`
- If not: Download Docker Desktop for Windows from docker.com
- Install with default settings
- After install, verify: `docker --version` and `docker compose version`
- **WARNING**: Docker Desktop may require a restart. Save all work first.
- **WARNING**: Make sure WSL2 is enabled (Docker Desktop installer usually handles this)

### Step 3: Clone MiroFish Offline
```bash
cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/MiroFish Political Bot"
git clone https://github.com/nikmcfly/MiroFish-Offline.git mirofish-engine
```
If the offline repo doesn't exist or is broken, fall back to the main repo:
```bash
git clone https://github.com/666ghj/MiroFish.git mirofish-engine
```

### Step 4: Examine MiroFish Structure
- Read the README thoroughly
- Read .env.example — understand what API keys are needed
- Read docker-compose.yml — understand what services run
- Read backend/app/config.py — understand configuration
- Document findings in `docs/setup-log.md`

### Step 5: Configure Environment
```bash
cd mirofish-engine
cp .env.example .env
```
Fill in .env:
- LLM_API_KEY: Use a FREE option:
  - Option A: Groq free API key (get from console.groq.com, free signup)
  - Option B: Google AI Studio free key (get from aistudio.google.com)
  - Option C: Whatever free option is easiest
- LLM_BASE_URL: Set based on chosen provider
- LLM_MODEL_NAME: Use the cheapest/free model available
- ZEP_API_KEY: For cloud version, get from app.getzep.com (free tier)
  - For offline version with Neo4j: check if Zep is needed or replaced

### Step 6: Start Docker Services
```bash
docker compose up -d
```
Verify all containers are running:
```bash
docker compose ps
```
Expected: Neo4j (or Zep), possibly Ollama, backend, frontend

Check resource usage:
```bash
docker stats --no-stream
```
Document RAM/CPU usage in setup-log.md.

### Step 7: Install Dependencies
```bash
npm run setup:all
# OR step by step:
npm run setup
npm run setup:backend
```

### Step 8: Start MiroFish
```bash
npm run dev
```
- Frontend should be at http://localhost:3000
- Backend should be at http://localhost:5001
- Open browser, verify UI loads

### Step 9: Run a Test Simulation
Pick a simple, non-political topic for mechanical testing:
- Example: "What would happen if a major social media platform went down for a week?"
- Use SMALLEST possible settings: 20 agents, 10 rounds
- Goal is NOT a good prediction — goal is verifying the pipeline works:
  1. Can you input seed text? YES/NO
  2. Does graph building complete? YES/NO
  3. Does environment setup complete? YES/NO
  4. Does simulation run? YES/NO
  5. Does report generate? YES/NO

### Step 10: Document Results
Write comprehensive findings in `docs/setup-log.md`:
- What was installed, versions
- What worked, what didn't
- Any errors and how they were fixed
- Resource usage (RAM, CPU, disk)
- How long each step took
- Screenshot of working UI (if possible)

## SUCCESS CRITERIA

ALL of these must be true:
- [ ] Docker running, no errors
- [ ] Neo4j (or graph DB) accessible
- [ ] MiroFish frontend loads in browser
- [ ] MiroFish backend API responds
- [ ] A test simulation ran to completion (any quality)
- [ ] Report was generated from simulation
- [ ] Docker resource usage documented (RAM < 4GB)
- [ ] Existing Polymarket Agent is UNTOUCHED and still works

## FAILURE CRITERIA — STOP AND REPORT

If any of these happen, STOP and document in setup-log.md:
- Docker won't install or start (WSL2 issues, Hyper-V conflicts)
- MiroFish Offline repo is broken/unmaintained
- Neo4j requires more than 4GB RAM
- Simulation crashes mid-run
- Can't get ANY free LLM to work with MiroFish

## ANTI-SPAGHETTI RULES

- Do NOT modify MiroFish source code in this phase. Use it as-is.
- Do NOT create wrapper scripts or automation yet. Manual testing only.
- Do NOT install Python packages globally — use virtual environments.
- Keep the project directory clean — no temp files, no scattered scripts.

## AUDIT AT END OF PHASE

Before marking Phase 0 complete:
1. `docker compose ps` — all services healthy
2. `docker stats --no-stream` — document resource usage
3. Check that Polymarket Agent is untouched: `cd "c:/Users/erimc/OneDrive/Desktop/CLAUDE/Polymarket Agent" && git status`
4. Verify no new global Python packages were installed that could conflict
5. Read `docs/setup-log.md` — is it complete and accurate?

## WHAT'S NEXT

After Phase 0 succeeds, Phase 1 (Blind Validation Test) will test MiroFish on REAL resolved Polymarket political markets to see if it produces useful signals. That's a separate prompt.
