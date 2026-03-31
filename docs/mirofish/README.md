# MiroFish Political Bot — Master Plan

## Overview

A separate political prediction bot using MiroFish social simulation engine to trade political/geopolitical markets on Polymarket. Completely independent from the existing sports bot.

## Architecture Decision

```
Sports Bot (Polymarket Agent)    Political Bot (MiroFish)
       │  INDEPENDENT               │  INDEPENDENT
       ├── own executor              ├── own executor
       ├── own portfolio             ├── own portfolio
       ├── own risk manager          ├── own risk manager
       │                             │
       └──► Polymarket API ◄─────────┘
            (same account)
```

Two bots, one Polymarket account. Neither knows about the other. Neither can break the other.

## Technology Stack

| Component | Choice | Cost | Why |
|---|---|---|---|
| Simulation Engine | MiroFish Offline | $0 | Open-source, local |
| Graph Database | Neo4j (Docker) | $0 | Local, unlimited, fast |
| LLM (Phase 0-3) | Groq free / Google AI Studio free | $0 | Test concept at zero cost |
| LLM (Phase 4+) | Gemini Flash paid (upgrade only if proven) | ~$9/month | Best cost/quality ratio |
| Order Execution | Copied from sports bot | $0 | Proven code |
| Notifications | Same Telegram bot | $0 | [POLITICAL] prefix |

## Phases

| Phase | Name | Duration | Cost | Kill/Continue? |
|---|---|---|---|---|
| **0** | [Setup & Mechanical Test](phase-0-setup.md) | 1-2 days | **$0** | Continue if pipeline works |
| **1** | [Blind Validation Test (FREE)](phase-1-blind-test.md) | 3-7 days | **$0** | KILL if 0-1/5, GRAY if 2/5, CONTINUE if 3+/5 |
| **1b** | Optional: Retest with different free LLM | 2-3 days | **$0** | Only if Phase 1 was gray zone |
| **2** | [Pipeline Build](phase-2-pipeline.md) | 1 week | **$0** | Continue if tests pass |
| **3** | [Polymarket Integration](phase-3-integration.md) | 1 week | **$0** | Continue if dry_run works |
| **4** | [Paper Trading](phase-4-paper-trading.md) | 2 weeks | ~$9 | **KILL if win rate < 35%** |
| **5** | [Live Trading](phase-5-live.md) | 8+ weeks | ~$9/month | Scale up if profitable |

**Cost to prove concept works (Phase 0-1b): $0**
**Cost to reach paper trading (Phase 0-3): $0**
**Cost to reach live trading (Phase 0-4): ~$9 (first Gemini Flash paid month)**
**Ongoing monthly cost: ~$9/month (Gemini Flash)**

## Kill Points

Three decision points:

1. **Phase 1 (day 5-7):** Free LLM blind test. If 0-1/5 correct → hard kill. **$0 lost.**
2. **Phase 1b (day 8-10, optional):** If Phase 1 was gray zone, retest with different free LLM. If still bad → kill. **$0 lost.**
3. **Phase 4 (day 21-35):** Paper trading. If win rate < 35% → kill. **~$9 lost.**

**Maximum money at risk before any live trade: $9 (Phase 4 Gemini Flash)**
**Money at risk to test if concept works at all: $0**
**Phases 0 through 3 are completely free.**

## Key Rules

- Sports bot is NEVER touched or affected
- Default mode is always DRY_RUN
- Live trading starts at 1% position size, scales gradually
- Max political exposure: 15% of bankroll (even at full scale)
- Daily monitoring is mandatory during live trading
