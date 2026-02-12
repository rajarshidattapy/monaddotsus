"""
Blockchain Integration Module for MonadSus.

Connects the autonomous game engine to on-chain contracts:
- AgentRegistry: Track agent stats (games played, wins)
- GameRegistry: Register games with deterministic hashes
- PredictionMarket: Create/resolve prediction markets
- GameResolver: Batch-resolve markets when game ends

This module can operate in two modes:
1. Simulation mode (default): Logs events locally, no on-chain calls
2. Live mode: Sends transactions to Monad testnet

Contract Addresses (Monad Testnet):
- Set via environment variables or config file
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------

class GameStatus(Enum):
    CREATED = 0
    RUNNING = 1
    FINISHED = 2


class MarketType(Enum):
    AGENT_IS_IMPOSTER = "AGENT_{}_IS_IMPOSTER"
    AGENT_SURVIVES = "AGENT_{}_SURVIVES"
    CREW_WINS = "CREW_WINS"
    IMPOSTER_WINS = "IMPOSTER_WINS"
    AGENT_EJECTED = "AGENT_{}_EJECTED"


@dataclass
class GameEvent:
    """Single game event for logging and hashing."""
    timestamp: float
    event_type: str
    agent_id: Optional[str]
    data: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "t": self.timestamp,
            "type": self.event_type,
            "agent_id": self.agent_id,
            "data": self.data,
        }

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True)


@dataclass
class PredictionMarket:
    """Local representation of a prediction market."""
    market_id: int
    game_id: int
    question: str
    yes_pool: float = 0.0
    no_pool: float = 0.0
    resolved: bool = False
    outcome: Optional[bool] = None


# ---------------------------------------------------------------------------
# Event Logger (FR-6 from Dialogue PRD + Settlement requirements)
# ---------------------------------------------------------------------------

class EventLogger:
    """
    Logs all game events for:
    - Spectator playback
    - Deterministic game hash generation
    - Market settlement verification
    """

    def __init__(self):
        self.events: list[GameEvent] = []
        self.game_start_time: float = 0.0

    def start_game(self):
        """Mark game start time."""
        self.game_start_time = time.time()
        self.events = []
        self.log("GAME_START", None, {})

    def log(self, event_type: str, agent_id: Optional[str], data: dict):
        """Log an event."""
        t = time.time() - self.game_start_time if self.game_start_time else 0.0
        event = GameEvent(timestamp=t, event_type=event_type, agent_id=agent_id, data=data)
        self.events.append(event)
        return event

    def log_kill(self, killer: str, victim: str):
        return self.log("KILL", killer, {"victim": victim})

    def log_meeting(self, caller: str):
        return self.log("MEETING_START", caller, {})

    def log_speak(self, agent: str, message: str):
        return self.log("SPEAK", agent, {"message": message})

    def log_vote(self, voter: str, target: Optional[str]):
        return self.log("VOTE", voter, {"target": target})

    def log_eject(self, agent: str, was_imposter: bool):
        return self.log("EJECT", agent, {"was_imposter": was_imposter})

    def log_game_end(self, winner: str, imposter: str):
        return self.log("GAME_END", None, {"winner": winner, "imposter": imposter})

    def compute_hash(self) -> str:
        """
        Compute deterministic hash of all events.
        Used for on-chain game registration and settlement verification.
        """
        event_data = [e.to_json() for e in self.events]
        combined = "|".join(event_data)
        return hashlib.sha256(combined.encode()).hexdigest()

    def export_json(self) -> str:
        """Export all events as JSON for storage/verification."""
        return json.dumps([e.to_dict() for e in self.events], indent=2)


# ---------------------------------------------------------------------------
# Blockchain Connector (Simulation Mode)
# ---------------------------------------------------------------------------

class BlockchainConnector:
    """
    Connects game to smart contracts.
    
    In simulation mode (default), all calls are logged locally.
    In live mode, transactions are sent to Monad testnet.
    """

    def __init__(self, live_mode: bool = False, rpc_url: str = "", private_key: str = ""):
        self.live_mode = live_mode
        self.rpc_url = rpc_url
        self.private_key = private_key

        # Contract addresses (set these for live mode)
        self.agent_registry_address = ""
        self.game_registry_address = ""
        self.prediction_market_address = ""
        self.game_resolver_address = ""

        # Simulation state
        self.agents: dict[str, dict] = {}  # agent_id -> {name, games_played, wins}
        self.games: dict[int, dict] = {}   # game_id -> {hash, status}
        self.markets: dict[int, PredictionMarket] = {}
        self.next_game_id = 1
        self.next_market_id = 1

        # Web3 instance (lazy loaded)
        self._web3 = None

    # ---- Agent Registry ----

    def register_agent(self, agent_id: str, name: str) -> int:
        """Register an agent. Returns agent ID."""
        if self.live_mode:
            result = self._call_contract("AgentRegistry", "registerAgent", [name])
            return result if result else 0

        # Simulation
        self.agents[agent_id] = {"name": name, "games_played": 0, "wins": 0}
        print(f"  [CHAIN] Agent registered: {name} (id={agent_id})")
        return len(self.agents)

    def update_agent_stats(self, agent_id: str, won: bool):
        """Update agent after game ends."""
        if self.live_mode:
            return self._call_contract("AgentRegistry", "updateAgent", [agent_id, won])

        # Simulation
        if agent_id in self.agents:
            self.agents[agent_id]["games_played"] += 1
            if won:
                self.agents[agent_id]["wins"] += 1
            print(f"  [CHAIN] Agent stats updated: {agent_id} won={won}")

    # ---- Game Registry ----

    def create_game(self, game_hash: str) -> int:
        """Create a new game on-chain. Returns game ID."""
        if self.live_mode:
            result = self._call_contract("GameRegistry", "createGame", [game_hash])
            return result if result else 0

        # Simulation
        game_id = self.next_game_id
        self.next_game_id += 1
        self.games[game_id] = {"hash": game_hash, "status": GameStatus.CREATED}
        print(f"  [CHAIN] Game created: id={game_id} hash={game_hash[:16]}...")
        return game_id

    def start_game(self, game_id: int):
        """Mark game as running."""
        if self.live_mode:
            return self._call_contract("GameRegistry", "startGame", [game_id])

        # Simulation
        if game_id in self.games:
            self.games[game_id]["status"] = GameStatus.RUNNING
            print(f"  [CHAIN] Game started: id={game_id}")

    def finish_game(self, game_id: int):
        """Mark game as finished."""
        if self.live_mode:
            return self._call_contract("GameRegistry", "finishGame", [game_id])

        # Simulation
        if game_id in self.games:
            self.games[game_id]["status"] = GameStatus.FINISHED
            print(f"  [CHAIN] Game finished: id={game_id}")

    # ---- Prediction Market ----

    def create_market(self, game_id: int, question: str) -> int:
        """Create a prediction market. Returns market ID."""
        if self.live_mode:
            result = self._call_contract("PredictionMarket", "createMarket", [game_id, question])
            return result if result else 0

        # Simulation
        market_id = self.next_market_id
        self.next_market_id += 1
        self.markets[market_id] = PredictionMarket(
            market_id=market_id,
            game_id=game_id,
            question=question,
        )
        print(f"  [CHAIN] Market created: id={market_id} '{question}'")
        return market_id

    def resolve_market(self, market_id: int, outcome: bool):
        """Resolve a prediction market."""
        if self.live_mode:
            return self._call_contract("PredictionMarket", "resolveMarket", [market_id, outcome])

        # Simulation
        if market_id in self.markets:
            self.markets[market_id].resolved = True
            self.markets[market_id].outcome = outcome
            q = self.markets[market_id].question
            print(f"  [CHAIN] Market resolved: id={market_id} '{q}' → {'YES' if outcome else 'NO'}")

    # ---- Game Resolver (Batch) ----

    def resolve_game(self, game_id: int, market_outcomes: dict[int, bool]):
        """
        Finish game and resolve all associated markets atomically.
        market_outcomes: {market_id: outcome_bool}
        """
        if self.live_mode:
            market_ids = list(market_outcomes.keys())
            outcomes = list(market_outcomes.values())
            return self._call_contract("GameResolver", "resolveGame", [game_id, market_ids, outcomes])

        # Simulation
        self.finish_game(game_id)
        for market_id, outcome in market_outcomes.items():
            self.resolve_market(market_id, outcome)

    # ---- Internal ----

    def _call_contract(self, contract_name: str, method: str, args: list):
        """Make an actual on-chain call (requires web3.py)."""
        # This would use web3.py in live mode
        # For now, just log the call
        print(f"  [CHAIN TX] {contract_name}.{method}({args})")
        return None


# ---------------------------------------------------------------------------
# Game Integration Helper
# ---------------------------------------------------------------------------

class MonadSusChainIntegration:
    """
    High-level integration for autonomous game.
    
    Usage:
        chain = MonadSusChainIntegration()
        game_id = chain.on_game_start(agents, imposter_id)
        # ... during game ...
        chain.logger.log_kill(killer, victim)
        chain.logger.log_speak(agent, message)
        # ... at end ...
        chain.on_game_end(winner, imposter_id, alive_agents)
    """

    def __init__(self, live_mode: bool = False):
        self.connector = BlockchainConnector(live_mode=live_mode)
        self.logger = EventLogger()
        self.game_id: Optional[int] = None
        self.markets: dict[str, int] = {}  # question -> market_id
        self.agent_colours: list[str] = []
        self.imposter_colour: str = ""

    def on_game_start(self, agent_colours: list[str], imposter_colour: str) -> int:
        """Called when a new game starts."""
        self.agent_colours = agent_colours
        self.imposter_colour = imposter_colour
        self.markets = {}

        # Start event logging
        self.logger.start_game()

        # Register agents (if not already registered)
        for colour in agent_colours:
            if colour not in self.connector.agents:
                self.connector.register_agent(colour, colour)

        # Create game with initial hash (will be updated at end)
        initial_hash = hashlib.sha256(f"MONADSUS_{time.time()}".encode()).hexdigest()
        self.game_id = self.connector.create_game(initial_hash)
        self.connector.start_game(self.game_id)

        # Create prediction markets
        self._create_markets()

        return self.game_id

    def _create_markets(self):
        """Create prediction markets for this game."""
        assert self.game_id is not None
        
        # Crew vs Imposter win
        self.markets["CREW_WINS"] = self.connector.create_market(
            self.game_id, "Will the Crew win?"
        )

        # Agent-specific markets
        for colour in self.agent_colours:
            # "Is X the imposter?"
            q_imp = f"Is {colour} the Imposter?"
            self.markets[f"{colour}_IS_IMPOSTER"] = self.connector.create_market(
                self.game_id, q_imp
            )

            # "Will X survive?"
            q_surv = f"Will {colour} survive the game?"
            self.markets[f"{colour}_SURVIVES"] = self.connector.create_market(
                self.game_id, q_surv
            )

    def on_game_end(self, winner: str, imposter_colour: str, alive_agents: list[str]):
        """Called when game ends. Resolves all markets."""
        assert self.game_id is not None
        
        # Log final event
        self.logger.log_game_end(winner, imposter_colour)

        # Compute final game hash
        final_hash = self.logger.compute_hash()
        print(f"\n  [CHAIN] Final game hash: {final_hash}")

        # Resolve all markets
        outcomes: dict[int, bool] = {}

        # Crew wins market
        crew_won = (winner == "CREW")
        outcomes[self.markets["CREW_WINS"]] = crew_won

        # Agent-specific markets
        for colour in self.agent_colours:
            # Imposter market
            is_imposter = (colour == imposter_colour)
            outcomes[self.markets[f"{colour}_IS_IMPOSTER"]] = is_imposter

            # Survival market
            survived = colour in alive_agents
            outcomes[self.markets[f"{colour}_SURVIVES"]] = survived

        # Batch resolve
        self.connector.resolve_game(self.game_id, outcomes)

        # Update agent stats
        for colour in self.agent_colours:
            won = False
            if colour == imposter_colour:
                won = (winner == "IMPOSTER")
            else:
                won = (winner == "CREW")
            self.connector.update_agent_stats(colour, won)

        # Export event log
        export_path = f"game_log_{self.game_id}.json"
        with open(export_path, "w") as f:
            f.write(self.logger.export_json())
        print(f"  [CHAIN] Event log exported: {export_path}")

        return final_hash


# ---------------------------------------------------------------------------
# Example Usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Demo the integration
    chain = MonadSusChainIntegration(live_mode=False)

    # Simulate a game
    agents = ["Red", "Blue", "Green", "Yellow", "Black"]
    imposter = "Green"

    game_id = chain.on_game_start(agents, imposter)
    print(f"\nGame ID: {game_id}")

    # Simulate some events
    chain.logger.log_kill("Green", "Blue")
    chain.logger.log_meeting("Red")
    chain.logger.log_speak("Red", "I think Green is suspicious")
    chain.logger.log_speak("Green", "It's not me!")
    chain.logger.log_vote("Red", "Green")
    chain.logger.log_vote("Yellow", "Green")
    chain.logger.log_vote("Black", "Green")
    chain.logger.log_vote("Green", "Red")
    chain.logger.log_eject("Green", True)

    # End game
    chain.on_game_end("CREW", imposter, ["Red", "Yellow", "Black"])
