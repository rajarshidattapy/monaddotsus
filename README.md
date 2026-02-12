# MonadSus

MonadSus is a **spectator-only, multi-agent social deduction simulation** where all players are autonomous AI agents. Humans don't play — they watch and bet on outcomes via prediction markets.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run autonomous agent mode
python main_autonomous.py
```

**Controls:** TAB = cycle camera | 1-9 = pick agent | SPACE = restart | ESC = quit

---

## Current Implementation Status

### ✅ Phase 1 — Autonomous Agent Gameplay (Complete)

| Feature | Status |
|---------|--------|
| Agent Controller Interface | ✅ `agent_controller.py` |
| Random Walk Movement | ✅ Stuck detection included |
| Imposter Kill Logic | ✅ Range check, cooldown, body spawn |
| Body Detection → Meeting | ✅ Crew detects corpses |
| Meeting Dialogue System | ✅ Template-based accusations/defenses |
| Voting & Ejection | ✅ Majority vote, ties skip |
| Win Conditions | ✅ Crew wins if imposter ejected, imposter wins if outnumbered |
| Dead Body Sprites | ✅ Proper death rendering |

### ✅ Phase 2 — Agent Dialogue (Complete)

| Feature | Status |
|---------|--------|
| SPEAK action type | ✅ |
| Dialogue templates (Accusation, Defense, Uncertainty, Observation) | ✅ |
| Role-aware dialogue (Imposter deflection) | ✅ |
| Meeting phases: Alert → Dialogue → Voting | ✅ |
| Turn-based speaking (shuffled order) | ✅ |
| Console logging of all dialogue | ✅ |

### ✅ Phase 3 — Blockchain Integration (Complete)

| Feature | Status |
|---------|--------|
| Event logging system | ✅ `blockchain.py` |
| Deterministic game hash | ✅ SHA-256 of all events |
| Agent Registry connector | ✅ Track games played, wins |
| Game Registry connector | ✅ Register/start/finish games |
| Prediction Market connector | ✅ Create/resolve markets |
| Batch settlement via GameResolver | ✅ |
| JSON event log export | ✅ `game_log_{id}.json` |

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    SPECTATOR (Human)                       │
│              Watch match, trade predictions                │
└────────────────────────▲───────────────────────────────────┘
                         │ read-only
┌────────────────────────┴───────────────────────────────────┐
│                   BLOCKCHAIN MODULE                        │
│  blockchain.py                                             │
│  - EventLogger: logs kills, meetings, dialogue, votes     │
│  - BlockchainConnector: simulation / Monad testnet        │
│  - MonadSusChainIntegration: high-level game hooks        │
└────────────────────────▲───────────────────────────────────┘
                         │ events
┌────────────────────────┴───────────────────────────────────┐
│                   GAME ENGINE                              │
│  autonomous_game.py                                        │
│  - AutonomousGame: main loop, phases, rendering           │
│  - Meeting phases: ALERT → DIALOGUE → VOTING              │
│  - Win conditions, ejection, body detection               │
└────────────────────────▲───────────────────────────────────┘
                         │ actions
┌────────────────────────┴───────────────────────────────────┐
│                   AGENT CONTROLLERS                        │
│  agent_controller.py                                       │
│  - AgentController: base class                            │
│  - SimpleAgent: random walk, kill, speak, vote            │
│  - Dialogue templates: accusation, defense, uncertainty   │
└────────────────────────────────────────────────────────────┘
```

---

## Smart Contracts (Monad Testnet)

Located in `monadsus-contracts/src/`:

| Contract | Purpose |
|----------|---------|
| `AgentRegistry.sol` | Track agent names, games played, wins |
| `GameRegistry.sol` | Register games with hash, manage lifecycle |
| `PredictionMarket.sol` | YES/NO betting pools, payout claims |
| `GameResolver.sol` | Batch-resolve markets when game ends |

### Contract Deployment

```bash
cd monadsus-contracts
forge build
forge script script/Deploy.s.sol --rpc-url <MONAD_RPC> --broadcast
```

---

## File Structure

```
monaddotsus/
├── main_autonomous.py      # Entry point for autonomous mode
├── autonomous_game.py      # Game engine (850+ lines)
├── agent_controller.py     # Agent interface + SimpleAgent
├── blockchain.py           # On-chain integration module
├── game.py                 # Original game (for reference)
├── sprites.py              # Player/Bot sprites (modified for autonomous flag)
├── settings.py             # Config, sprite loading
├── monadsus-contracts/     # Solidity contracts (Foundry)
│   └── src/
│       ├── AgentRegistry.sol
│       ├── GameRegistry.sol
│       ├── GameResolver.sol
│       └── PredictionMarket.sol
└── Assets/                 # Sprites, sounds, maps
```

---

## Prediction Markets

When a game starts, these markets are created:

| Market | Resolution |
|--------|------------|
| `Will the Crew win?` | YES if crew wins |
| `Is {Agent} the Imposter?` | YES if agent is imposter |
| `Will {Agent} survive?` | YES if agent alive at end |

All markets settle deterministically from the final game state hash.

---

## Event Log Format

Every game exports a JSON log:

```json
[
  {"t": 0.0, "type": "GAME_START", "agent_id": null, "data": {}},
  {"t": 15.2, "type": "KILL", "agent_id": "Green", "data": {"victim": "Blue"}},
  {"t": 30.5, "type": "MEETING_START", "agent_id": "Red", "data": {}},
  {"t": 31.0, "type": "SPEAK", "agent_id": "Red", "data": {"message": "I think Green is suspicious."}},
  {"t": 32.0, "type": "VOTE", "agent_id": "Red", "data": {"target": "Green"}},
  {"t": 35.0, "type": "EJECT", "agent_id": "Green", "data": {"was_imposter": true}},
  {"t": 35.1, "type": "GAME_END", "agent_id": null, "data": {"winner": "CREW", "imposter": "Green"}}
]
```

---

## Next Steps (Roadmap)

### Phase 4 — LLM Agents
- Replace `SimpleAgent` with GPT/Claude-powered reasoning
- Memory system for tracking observations
- Strategic deception and persuasion

### Phase 5 — Spectator Frontend
- Web UI for watching matches
- Real-time event stream
- Market trading interface

### Phase 6 — Live Blockchain Mode
- Deploy contracts to Monad mainnet
- Web3 wallet integration
- Real prediction market trading

---

## Why This Matters

This is **AI systems research wearing a game skin**:

- Study deception, persuasion, and coalition formation in LLM agents
- Aggregate human belief signals via prediction markets
- Generate measurable agent performance metrics over time
- Deterministic, reproducible matches for benchmarking

---

## License

MIT
