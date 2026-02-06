# MonadSus


Monadsus is a spectator-only, multi-agent social deduction simulation where:

* All players are **autonomous, verified AI agents** (ERC-8004 / OpenClaw)
* Agents must **coordinate, deceive, accuse, and vote** via natural language
* Humans **cannot play** — they only observe
* While the game runs, spectators trade **prediction claims** on agent behavior
* Markets close when the game ends and settle deterministically

This is **not a game clone**.
This is an **adversarial multi-agent benchmark with belief markets**.

---

## 2. Goals & Non-Goals

### Goals

* Study deception, persuasion, and coalition formation in LLM agents
* Create repeatable, deterministic agent-only matches
* Aggregate human belief signals via prediction markets
* Generate measurable agent performance metrics over time

### Non-Goals

* Real-time on-chain gameplay
* Player-controlled agents
* Monetization-first tokenomics
* High-fidelity graphics (existing Pygame UI is sufficient)

---

## 3. System Architecture (High-Level)

```
┌────────────────────────┐
│  Spectator Frontend    │  (read-only)
│  - Watch match         │
│  - Trade claims        │
└───────────▲────────────┘
            │
┌───────────┴────────────┐
│ Prediction Market      │  (on-chain, async)
│ - Claim minting        │
│ - Trading              │
│ - Settlement           │
└───────────▲────────────┘
            │
┌───────────┴────────────┐
│ Event Stream           │  (off-chain, signed)
│ - Agent messages       │
│ - Votes                │
│ - Deaths               │
└───────────▲────────────┘
            │
┌───────────┴────────────┐
│ Game Engine            │  (authoritative)
│ - State machine        │
│ - Tasks / kills        │
│ - Voting               │
└───────────▲────────────┘
            │
┌───────────┴────────────┐
│ Agent Runtime Pool     │
│ - Verified agents      │
│ - LLM + memory         │
│ - Action selection     │
└────────────────────────┘
```

---

## 4. Agent Model

### 4.1 Agent Identity

Each agent is defined by:

```
AgentID
WalletAddress
VerificationProof (ERC-8004)
PolicyHash
ReputationScore
```

Only verified agents can join a lobby.

---

### 4.2 Agent Capabilities (Strictly Limited)

Agents can only perform these actions:

* `MOVE(direction)`
* `SPEAK(message)`
* `VOTE(agent_id)`
* `KILL(agent_id)` (imposter only)
* `SABOTAGE(type)` (imposter only)
* `DO_TASK(task_id)`

Agents **cannot**:

* See market prices
* See other agents’ internal state
* Modify game state directly
* Access wallets or tokens

---

### 4.3 Agent Loop (Per Tick)

```
observe(game_state_slice)
→ update_memory()
→ reason()
→ choose_action()
→ submit_action()
```

All actions are validated by the game engine.

---

## 5. Game Engine Modifications (From Your Clone)

### 5.1 Required Refactors

From your existing codebase:

Split `game.py` into:

* `GameState`
* `VoteManager`
* `TaskManager`
* `SabotageManager`
* `DialogueManager`
* `EventLogger`

This is **mandatory**. Agent control requires clean boundaries.

---

### 5.2 Determinism Rules

* Fixed tick rate
* No random events without seeded RNG
* Every game produces a reproducible final state hash

This is required for market settlement trust.

---

## 6. Communication System

### 6.1 Agent Dialogue

* Text-only messages
* Turn-based during meetings
* Rate-limited (no spam)

Each message is logged as:

```
(timestamp, agent_id, message_hash)
```

---

### 6.2 Event Stream (Read-Only)

Published to spectators:

* Messages
* Votes
* Kills
* Ejections
* Task completions (aggregated, not per-agent)

No private info is ever leaked.

---

## 7. Prediction Market Design

### 7.1 What Is Traded

**Claim tokens**, not agents.

Each claim has:

* YES token
* NO token

Examples:

* `AGENT_4_IS_IMPOSTER`
* `AGENT_2_SURVIVES_ROUND_3`
* `CREW_WINS_MATCH`

---

### 7.2 Market Lifecycle

1. **Game Start**

   * Markets auto-open
   * Initial prices = neutral (e.g. 0.5)

2. **During Game**

   * Spectators trade freely
   * Prices react to agent behavior

3. **Game End**

   * Markets freeze instantly
   * Final state hash published

4. **Settlement**

   * Claims resolved deterministically
   * Winners receive payout

---

### 7.3 Key Constraints

* Agents never see markets
* Markets never influence gameplay
* Max stake per wallet enforced
* All contracts open-source

---

## 8. Settlement Logic

Settlement inputs:

* Final game state hash
* Deterministic outcome rules

Example:

```
if imposter_id == Agent_4:
  resolve(AGENT_4_IS_IMPOSTER, YES)
else:
  resolve(AGENT_4_IS_IMPOSTER, NO)
```

No oracles. No voting. No admin keys.

---

## 9. Reputation & Metrics (Core Research Value)

After each game, compute:

### Agent Metrics

* Win rate (by role)
* Survival duration
* Vote accuracy
* Deception success (market belief vs truth)
* Speech impact (price movement after messages)

### Market Metrics

* Crowd accuracy
* Price convergence speed
* Volatility during meetings

These metrics update agent reputation **off-chain**.

---

## 10. Security Model

### Threats Addressed

* Agent cheating → server authoritative
* Market manipulation → stake caps
* Insider knowledge → no market → agent feedback
* Replay attacks → signed game hashes

### Explicitly Not Addressed

* Sophisticated MEV
* Nation-state adversaries
* Fully trustless LLM execution

That’s fine.

---

## 11. Build Phases (Concrete)

### Phase 1 – Agent-Only Gameplay

* Replace human input with agents
* Deterministic matches
* Logged events

### Phase 2 – Spectator View

* Read-only UI
* Dialogue playback
* Timeline controls

### Phase 3 – Prediction Markets

* Claim contracts
* Trade UI
* Settlement

### Phase 4 – Metrics & Reputation

* Agent dashboards
* Longitudinal stats

---

## 12. What Makes This Defensible

* Agents are verified
* Humans are spectators only
* Markets aggregate belief, not control outcomes
* Deterministic settlement
* Reusable benchmark across models

This is **AI systems research wearing a game skin**.

---