---
name: mlb-submarket-lab
description: Use when the user says MLB-SUBMARKET-LAB, asks about the MLB submarket prediction lab, says "MLB lab'a devam edelim/bakalım" or similar continuation phrase, or asks to resume work on the MLB totals/spread/run-line model
---

# MLB Submarket Lab — Resume Protocol

## Overview

The user has a designed-but-not-implemented sandbox project: **MLB Submarket Prediction Lab**. A 5-layer model (Log5 + Tango base/out Markov + convolution) for Polymarket MLB totals and run-line spread markets. Both the DRAFT v2 spec and the 35-task implementation plan are written. This skill activates when the user wants to recall the project or continue from where they left off.

## When to Use

- User types `MLB-SUBMARKET-LAB` (the explicit keyword)
- User says any variant of "MLB lab'a bakalım", "kaldığım yerden devam", "MLB submarket'e başlayalım"
- User asks "MLB için ne planlamıştık", "MLB modelini hatırlatır mısın"
- User wants to extend, edit, or implement the MLB submarket model

## When NOT to Use

- General MLB ML strategy questions (existing bot's moneyline strategy — not this lab)
- Tennis lab questions (separate worktree, separate spec)
- Polymarket scanner debugging unrelated to MLB submarkets

## Resume Protocol (mandatory order)

When this skill activates, execute these steps in order — do NOT skip.

### Step 1 — Read both documents

Load with Read tool, in order:

1. `docs/superpowers/specs/2026-05-21-mlb-submarket-lab-design.md` — DRAFT v2 spec (5-layer architecture, Polymarket compliance, calibration plan)
2. `docs/superpowers/plans/2026-05-21-mlb-submarket-lab.md` — 35-task TDD implementation plan (Faz 0 backbone)

Both files exist. Do not assume — if Read fails, surface that to the user.

### Step 2 — Brief the user (concise, non-technical)

Show in 4-6 lines:
- Project status (DRAFT v2 spec + plan ready, code not started)
- Scope (totals + run-line spread, NRFI monitoring only, F5 deferred)
- Spec mantıklılık score: 6.5/10 (current timing); 7.5/10 if prerequisites met
- Estimated effort: 12-16 weeks, ~5,700 LOC
- 35 tasks in the plan, Faz 0 = backbone

### Step 3 — Check prerequisites (spec §11)

Ask the user explicitly:

1. **Mevcut MLB ML kayıpları çözüldü mü?** (entry kalitesi + slipaj fix)
2. **Tenis Prediction Lab tamamlandı mı?** (paper trading template kaynağı)

If both answers are "no" or "not yet", flag this to the user and ask whether to proceed anyway, defer, or work on a prerequisite first.

### Step 4 — Propose next concrete action

Based on user's answer:

- **Both prerequisites done** → Propose Task 1 (sandbox setup: `git worktree add -b feature/mlb-submarket-lab ../mlb-submarket-lab`)
- **One prerequisite open** → Recommend finishing that first; if user insists, proceed but warn about resource conflict
- **Both prerequisites open** → Strongly recommend resolving them first; offer to switch focus

### Step 5 — Execution mode choice

If user confirms to start implementation:
- **Subagent-driven** (recommended for this lab — 35 tasks, fresh context per task helps)
- **Inline execution** (one session, batch checkpoints)

User picks. Then invoke `superpowers:subagent-driven-development` or `superpowers:executing-plans` accordingly.

## Key Facts (no need to re-research)

| Fact | Value |
|---|---|
| Spec path | `docs/superpowers/specs/2026-05-21-mlb-submarket-lab-design.md` |
| Plan path | `docs/superpowers/plans/2026-05-21-mlb-submarket-lab.md` |
| Worktree branch | `feature/mlb-submarket-lab` (not yet created) |
| Worktree path | `../mlb-submarket-lab` |
| Sandbox bankroll | $500 paper |
| Sandbox port | 5052 |
| Markets in scope | totals, run-line spread (ML cross-check only, NRFI monitoring only) |
| Edge thresholds | totals ≥6%, spread ≥5% |
| Max positions/event | 2 |
| Estimated LOC | ~5,700 |
| Estimated time | 12-16 weeks |
| Academic foundation | Log5 (Haechrel multi-class), Tango 24-state base/out Markov, empirical Bayes shrinkage |
| Data sources (all free) | MLB Stats API, Baseball Savant (Statcast), FanGraphs, Tango RE Matrix |
| Key Polymarket compliance | Rainout = market stays open (48h timeout rule), DH 7-inning ayrı path, NRFI YES=koşu var |
| Critical scanner patch | `src/orchestration/scanner.py:94-98` — basketball-only filter gevşetilmeli |
| Designed | 2026-05-21 |

## Red Flags (skill misuse signals)

- Skipping Step 1 (Read both docs) → user gets stale or hallucinated info
- Skipping Step 3 (prerequisite check) → user starts a 12-week project on top of two unresolved fronts
- Writing code before user confirms execution mode (Step 5) → violates the user's explicit "ask before implementing" instruction
- Confusing this lab with tennis lab → tennis is in separate worktree, separate spec
- Assuming the plan is approved → it is DRAFT and prerequisites must be checked each time

## Quick Reference — Spec Sections

| Section | What's in it |
|---|---|
| §1 | Hipotez + kapsam |
| §2 | Akademik temel + Tenis KM kıyas |
| §3 | 5-katmanlı mimari (Layer 0-5 detay) |
| §4 | Veri kaynakları |
| §5 | Entry logic + T-90/T-30/T-10 timing |
| §6 | Exit logic + rainout/DH/suspension |
| §7 | Polymarket compliance + scanner patch |
| §8 | Calibration (walk-forward, Brier, CLV) |
| §9 | LOC tahmini |
| §10 | Riskler |
| §11 | **Ön koşullar (mutlaka §3 kontrol et)** |
| §12 | Mantıklılık skoru 6.5/10 |
| §13 | Referanslar |

## Quick Reference — Plan Phases

| Faz | Tasks | Süre |
|---|---|---|
| Faz 0 (backbone) | Task 1-35 (worktree, 5 layer, scanner patch, entry, diagnostic, integration test) | 4-5 hafta |
| Faz 1 (data clients full) | Statcast/FanGraphs/weather full clients + rate cache builder | 3 hafta |
| Faz 2 (orchestration) | Entry timing scheduler + scratch + rainout loop | 2 hafta |
| Faz 3 (UX) | Dashboard widget + /diagnose CLI | 2 hafta |
| Faz 4 (paper live) | Polymarket wire-up + 4 hafta paper gözlem | 4+ hafta |
| Faz 5 (kalibrasyon) | Calibration audit + paper→live karar | 1 hafta |

Bu plan dosyası SADECE Faz 0'ı (35 task) içerir. Faz 1+ ayrı plan yazılacak.

## Communication Style

The user (Erim) is non-technical. When briefing:
- Plain Turkish, not jargon
- File paths as markdown links
- Tables for comparisons
- No code unless user asks for it
- Confirm before any destructive action (worktree creation is OK, force-push is not)
