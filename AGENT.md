Here’s a **tight, execution-focused PRD** for the **minimal hackathon path** — no overengineering, no crypto fluff, just *get-it-working*.

You should be able to hand this to a teammate and build in parallel.

---

# PRD — MonadSus (Minimal Autonomous Agent Mode)

## 1. Objective

Convert the existing **human-controlled Among Us clone** into a **fully autonomous agent simulation** where:

* Every player is controlled by an AI agent
* No keyboard or mouse input is used
* Agents move, vote, kill (imposter), and trigger meetings
* Humans are spectators only
* A full match can start, progress, and end without human input

This milestone proves:

> **“Every player is an autonomous agent.”**

---

## 2. Non-Goals (Explicit)

For this phase, we are **not** doing:

* Smart deception logic
* LLM-powered reasoning
* ERC-8004 verification
* Prediction market integration
* Sophisticated pathfinding
* Voice or text persuasion

Random / heuristic behavior is acceptable.

---

## 3. User Stories

### Spectator

* Can launch the game and watch agents play
* Can see agents moving, killing, voting
* Can see the game end with a winner

### System

* Can run an entire match deterministically
* Does not depend on keyboard or mouse input
* Does not crash or stall

---

## 4. Functional Requirements

### FR-1: Replace Human Input with Agent Actions

* Remove all direct keyboard and mouse control from players
* Player updates must be driven by an **action object** supplied by an agent

**Acceptance Criteria**

* No code path calls `pygame.key.get_pressed()` for player control
* Player movement works without user input

---

### FR-2: Agent Controller Interface

Each player must have an attached agent controller.

**Agent Action Schema (minimal)**

```python
{
  "type": "MOVE" | "VOTE" | "KILL" | "NONE",
  "data": optional
}
```

Examples:

```python
{"type": "MOVE", "data": "UP"}
{"type": "KILL", "data": agent_id}
{"type": "VOTE", "data": agent_id}
{"type": "NONE"}
```

**Acceptance Criteria**

* Each player produces exactly one action per tick
* Invalid actions are ignored safely

---

### FR-3: Agent Movement

* Agents move randomly or semi-randomly on the map
* No pathfinding required
* Collision handling stays unchanged

**Acceptance Criteria**

* All agents move continuously
* No agent remains permanently idle

---

### FR-4: Imposter Kill Logic (Random)

* Exactly one agent is assigned the **imposter** role
* Imposter randomly kills a nearby agent if:

  * Kill cooldown is over
  * At least one valid target is in range

**Acceptance Criteria**

* At least one kill occurs in most matches
* Only the imposter can kill

---

### FR-5: Meeting Trigger

A meeting is triggered when:

* A dead body is detected **or**
* A fixed timer expires (fallback)

During meetings:

* Agents do not move
* Each agent emits one `VOTE` action

**Acceptance Criteria**

* Meetings start reliably
* Votes are counted
* One agent can be ejected

---

### FR-6: Voting Logic

* Each agent votes randomly among alive agents (including skip)
* Tie resolution can be random or skip

**Acceptance Criteria**

* Votes are cast without human input
* Ejection logic works

---

### FR-7: Game End Conditions

Game ends when:

* Imposter is ejected → **Crew wins**
* Imposter equals or outnumbers crew → **Imposter wins**

**Acceptance Criteria**

* Game reaches a terminal state
* Winner is displayed
* Game loop stops cleanly

---

## 5. Technical Design (Minimal)

### 5.1 New Components

#### `AgentController`

```python
class AgentController:
    def get_action(self, observation) -> dict
```

#### `SimpleAgent`

* Random movement
* Random voting
* Random kill (if imposter)

---

### 5.2 Modified Components

#### `Player`

* Remove keyboard logic
* Accept `action` in `update(action)`

#### `Game Loop`

Before:

```python
player.update()
```

After:

```python
action = agent.get_action(observation)
player.update(action)
```

---

## 6. Observations Provided to Agents (Minimal)

```python
{
  "position": (x, y),
  "nearby_agents": [agent_ids],
  "alive_agents": [...],
  "role": "IMPOSTER" | "CREW",
  "meeting_active": bool
}
```

No hidden information.

---

## 7. Success Metrics (Hackathon-Level)

A run is considered successful if:

* 5–10 agents spawn
* At least one meeting occurs
* At least one kill occurs
* A winner is declared
* No keyboard or mouse input is used

---

## 8. Out of Scope (Explicitly Deferred)

* LLM prompts
* Agent memory
* Deception metrics
* ERC-8004 verification
* Markets / tokens
* Performance optimization

---

## 9. Milestones & Timeboxing

### Milestone 1 (2–3 hours)

* Replace keyboard input
* Agents move autonomously

### Milestone 2 (2 hours)

* Random imposter + kill logic
* Meeting trigger

### Milestone 3 (1–2 hours)

* Voting
* Win/loss condition
* Demo-ready run

---

## 10. Demo Script (What You’ll Show)

1. Start game
2. Agents spawn and move
3. Imposter kills
4. Meeting triggers
5. Voting happens
6. Agent is ejected
7. Game ends automatically

Narration line:

> “Every character you see is an autonomous agent — no humans are playing.”

---

## 11. Risks & Mitigations

| Risk          | Mitigation              |
| ------------- | ----------------------- |
| Agents idle   | Force random movement   |
| No meetings   | Add timer-based meeting |
| No kills      | Reduce kill cooldown    |
| Infinite loop | Add max game duration   |

---

## 12. Definition of Done

* No keyboard/mouse control exists
* Full match completes autonomously
* Code is stable for demo
* README updated with “Autonomous Agent Mode”

---
