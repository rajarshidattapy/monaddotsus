"""
Blockchain Integration Module for MonadSus.

Connects the autonomous game engine to on-chain contracts:
- AgentRegistry: Track agent stats (games played, wins)
- GameRegistry: Register games with deterministic hashes
- PredictionMarket: Create/resolve prediction markets
- GameResolver: Batch-resolve markets when game ends

Contract Addresses (Monad Testnet):
- Set via environment variables or config file
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()  # Loads from .env in current directory or parent
except ImportError:
    pass  # dotenv not installed, use system env vars only

# Web3 imports - handle gracefully if not installed
try:
    from web3 import Web3
    from web3.middleware.geth_poa import geth_poa_middleware
    from eth_account import Account
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    Web3 = None  # type: ignore
    geth_poa_middleware = None  # type: ignore
    Account = None  # type: ignore


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
# Contract ABIs (extracted from Solidity)
# ---------------------------------------------------------------------------

AGENT_REGISTRY_ABI = [
    {
        "inputs": [{"name": "name", "type": "string"}],
        "name": "registerAgent",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "agentId", "type": "uint256"}, {"name": "won", "type": "bool"}],
        "name": "updateAgent",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "agentCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "", "type": "uint256"}],
        "name": "agents",
        "outputs": [
            {"name": "name", "type": "string"},
            {"name": "gamesPlayed", "type": "uint256"},
            {"name": "wins", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "name": "agentId", "type": "uint256"},
            {"indexed": False, "name": "name", "type": "string"}
        ],
        "name": "AgentCreated",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "name": "agentId", "type": "uint256"},
            {"indexed": False, "name": "won", "type": "bool"}
        ],
        "name": "AgentUpdated",
        "type": "event"
    },
]

GAME_REGISTRY_ABI = [
    {
        "inputs": [{"name": "gameHash", "type": "bytes32"}],
        "name": "createGame",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "gameId", "type": "uint256"}],
        "name": "startGame",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "gameId", "type": "uint256"}],
        "name": "finishGame",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "gameCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "", "type": "uint256"}],
        "name": "games",
        "outputs": [
            {"name": "id", "type": "uint256"},
            {"name": "gameHash", "type": "bytes32"},
            {"name": "status", "type": "uint8"},
            {"name": "resolver", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
]

PREDICTION_MARKET_ABI = [
    {
        "inputs": [],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [{"name": "gameId", "type": "uint256"}, {"name": "question", "type": "string"}],
        "name": "createMarket",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "marketId", "type": "uint256"}],
        "name": "betYes",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"name": "marketId", "type": "uint256"}],
        "name": "betNo",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"name": "marketId", "type": "uint256"}, {"name": "outcome", "type": "bool"}],
        "name": "resolveMarket",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "marketId", "type": "uint256"}],
        "name": "claim",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "marketCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "", "type": "uint256"}],
        "name": "markets",
        "outputs": [
            {"name": "gameId", "type": "uint256"},
            {"name": "question", "type": "string"},
            {"name": "yesPool", "type": "uint256"},
            {"name": "noPool", "type": "uint256"},
            {"name": "resolved", "type": "bool"},
            {"name": "outcome", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "name": "marketId", "type": "uint256"},
            {"indexed": False, "name": "gameId", "type": "uint256"},
            {"indexed": False, "name": "question", "type": "string"}
        ],
        "name": "MarketCreated",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "name": "marketId", "type": "uint256"},
            {"indexed": False, "name": "yes", "type": "bool"},
            {"indexed": False, "name": "amount", "type": "uint256"}
        ],
        "name": "BetPlaced",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "name": "marketId", "type": "uint256"},
            {"indexed": False, "name": "outcome", "type": "bool"}
        ],
        "name": "MarketResolved",
        "type": "event"
    },
]

GAME_RESOLVER_ABI = [
    {
        "inputs": [
            {"name": "_gameRegistry", "type": "address"},
            {"name": "_predictionMarket", "type": "address"}
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [
            {"name": "gameId", "type": "uint256"},
            {"name": "marketIds", "type": "uint256[]"},
            {"name": "outcomes", "type": "bool[]"}
        ],
        "name": "resolveGame",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "gameRegistry",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "predictionMarket",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
]

# ---------------------------------------------------------------------------
# Contract ABIs
# ---------------------------------------------------------------------------

# Import ABIs from separate file to avoid circular imports
from contract_abis import (
    PERSISTENT_AGENT_TOKEN_ABI,
    AGENT_TOKEN_REGISTRY_ABI,
    GAME_PRIZE_POOL_ABI
)


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
# Blockchain Connector
# ---------------------------------------------------------------------------

class BlockchainConnector:
    """
    Connects game to smart contracts.
    
    Live mode requires:
    - RPC URL (e.g., Monad testnet/mainnet)
    - Private key for signing transactions
    - Contract addresses (set via env vars or direct assignment)
    
    Environment variables:
    - MONAD_RPC_URL: RPC endpoint
    - MONAD_PRIVATE_KEY: Private key for signing transactions
    - AGENT_REGISTRY_ADDRESS: Contract address
    - GAME_REGISTRY_ADDRESS: Contract address
    - PREDICTION_MARKET_ADDRESS: Contract address
    - GAME_RESOLVER_ADDRESS: Contract address
    
    For user betting via MetaMask, use betting.html web interface.
    """

    def __init__(
        self,
        live_mode: bool = False,
        rpc_url: str = "",
        private_key: str = "",
    ):
        self.live_mode = live_mode
        self.rpc_url = rpc_url or os.environ.get("MONAD_RPC_URL", "")
        self.private_key = private_key or os.environ.get("MONAD_PRIVATE_KEY", "")

        # Contract addresses from env or direct assignment
        self.agent_registry_address = os.environ.get("AGENT_REGISTRY_ADDRESS", "")
        self.game_registry_address = os.environ.get("GAME_REGISTRY_ADDRESS", "")
        self.prediction_market_address = os.environ.get("PREDICTION_MARKET_ADDRESS", "")
        self.game_resolver_address = os.environ.get("GAME_RESOLVER_ADDRESS", "")

        # Web3 instance and contracts (lazy loaded)
        self._web3: Optional[Any] = None
        self._account: Optional[Any] = None
        self._contracts: dict[str, Any] = {}
        
        # Local tracking for agent name -> on-chain ID mapping
        self.agent_name_to_id: dict[str, int] = {}
        
        # Initialize Web3 if in live mode
        if self.live_mode:
            self._init_web3()

    def _init_web3(self):
        """Initialize Web3 connection and contract instances."""
        if not WEB3_AVAILABLE or Web3 is None or Account is None:
            raise RuntimeError(
                "web3.py or eth_account not installed or failed to import. Run: pip install web3"
            )

        if not self.rpc_url:
            raise ValueError("RPC URL required for live mode. Set MONAD_RPC_URL env var.")

        if not self.private_key:
            raise ValueError(
                "Private key required for live mode. Set MONAD_PRIVATE_KEY env var."
            )

        # Connect to network
        try:
            self._web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        except Exception as e:
            raise RuntimeError(f"Web3 initialization failed: {e}")

        # Add POA middleware for networks that need it (like some testnets)
        if geth_poa_middleware is not None:
            self._web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        if not self._web3.is_connected():
            raise ConnectionError(f"Failed to connect to {self.rpc_url}")

        print(f"  [CHAIN] Connected to {self.rpc_url}")

        # Load account from private key
        try:
            self._account = Account.from_key(self.private_key)
        except Exception as e:
            raise RuntimeError(f"Account creation failed: {e}")
        if not hasattr(self._account, 'address'):
            raise RuntimeError("Account object missing address attribute. Check eth_account installation.")
        # Print account address safely
        account_addr = getattr(self._account, 'address', None)
        print(f"  [CHAIN] Account: {account_addr}")

        # Initialize contract instances
        self._init_contracts()
    
    def _init_contracts(self):
        """Initialize contract instances with ABIs."""
        assert self._web3 is not None
        
        contract_configs = [
            ("AgentRegistry", self.agent_registry_address, AGENT_REGISTRY_ABI),
            ("GameRegistry", self.game_registry_address, GAME_REGISTRY_ABI),
            ("PredictionMarket", self.prediction_market_address, PREDICTION_MARKET_ABI),
            ("GameResolver", self.game_resolver_address, GAME_RESOLVER_ABI),
            # Persistent tokenization contracts
            ("AgentTokenRegistry", os.environ.get("AGENT_TOKEN_REGISTRY_ADDRESS", ""), AGENT_TOKEN_REGISTRY_ABI),
            ("GamePrizePool", os.environ.get("GAME_PRIZE_POOL_ADDRESS", ""), GAME_PRIZE_POOL_ABI),
        ]
        
        for name, address, abi in contract_configs:
            if address:
                checksum_addr = self._web3.to_checksum_address(address)
                self._contracts[name] = self._web3.eth.contract(
                    address=checksum_addr, abi=abi
                )
                print(f"  [CHAIN] Loaded {name} at {address[:10]}...")
            else:
                if name not in ["AgentTokenRegistry", "GamePrizePool"]:
                    # Only warn for non-tokenization contracts
                    print(f"  [CHAIN] Warning: {name} address not set")

    def _send_transaction(self, contract_name: str, method: str, args: list) -> Any:
        """Build, sign, and send a transaction. Returns receipt."""
        assert self._web3 is not None
        assert self._account is not None
        
        if contract_name not in self._contracts:
            raise ValueError(f"Contract {contract_name} not initialized")
        
        contract = self._contracts[contract_name]
        func = getattr(contract.functions, method)(*args)
        
        return self._send_transaction_private_key(contract, func, contract_name, method)
    
    def _send_transaction_private_key(self, contract: Any, func: Any, contract_name: str, method: str) -> Any:
        """Send transaction using private key signing."""
        assert self._web3 is not None
        assert self._account is not None
        
        # Build transaction
        tx = func.build_transaction({
            "from": self._account.address,
            "nonce": self._web3.eth.get_transaction_count(self._account.address),
            "gas": 500000,  # Adjust as needed
            "gasPrice": self._web3.eth.gas_price,
        })
        
        # Sign and send
        signed_tx = self._web3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self._web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"  [CHAIN TX] {contract_name}.{method} -> {tx_hash.hex()[:16]}...")
        
        # Wait for receipt
        receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status != 1:
            raise RuntimeError(f"Transaction failed: {tx_hash.hex()}")
        
        return receipt

    def _call_view(self, contract_name: str, method: str, args: list = []) -> Any:
        """Call a view/pure function (no gas cost)."""
        assert self._web3 is not None
        
        if contract_name not in self._contracts:
            raise ValueError(f"Contract {contract_name} not initialized")
        
        contract = self._contracts[contract_name]
        func = getattr(contract.functions, method)(*args)
        return func.call()

    def _get_event_arg(self, receipt: Any, contract_name: str, event_name: str, arg_name: str) -> Any:
        """Extract argument from event in transaction receipt."""
        assert self._web3 is not None
        
        contract = self._contracts[contract_name]
        event = getattr(contract.events, event_name)
        logs = event().process_receipt(receipt)
        
        if logs:
            return logs[0].args.get(arg_name)
        return None

    # ---- Agent Registry ----

    def register_agent(self, agent_id: str, name: str) -> int:
        """Register an agent. Returns agent ID."""
        if self.live_mode:
            # Check current count before registration
            count_before = self._call_view("AgentRegistry", "agentCount")
            
            # Register agent
            receipt = self._send_transaction("AgentRegistry", "registerAgent", [name])
            
            # Get new agent ID from event
            new_id = self._get_event_arg(receipt, "AgentRegistry", "AgentCreated", "agentId")
            if new_id is None:
                # Fallback: agentCount should have incremented
                new_id = count_before + 1
            
            self.agent_name_to_id[agent_id] = new_id
            print(f"  [CHAIN] Agent registered: {name} (on-chain id={new_id})")
            return new_id
        
        # Local tracking (no on-chain)
        next_id = len(self.agent_name_to_id) + 1
        self.agent_name_to_id[agent_id] = next_id
        print(f"  [CHAIN] Agent registered (local): {name} (id={next_id})")
        return next_id

    def update_agent_stats(self, agent_id: str, won: bool):
        """Update agent after game ends."""
        on_chain_id = self.agent_name_to_id.get(agent_id)
        if on_chain_id is None:
            print(f"  [CHAIN] Warning: Agent {agent_id} not registered")
            return
        
        if self.live_mode:
            self._send_transaction("AgentRegistry", "updateAgent", [on_chain_id, won])
        
        print(f"  [CHAIN] Agent stats updated: {agent_id} won={won}")

    # ---- Game Registry ----

    def create_game(self, game_hash: str) -> int:
        """Create a new game on-chain. Returns game ID."""
        if self.live_mode:
            # Convert hex string to bytes32
            hash_bytes = bytes.fromhex(game_hash) if len(game_hash) == 64 else game_hash.encode()
            hash_bytes32 = hash_bytes.ljust(32, b'\x00')[:32]
            
            count_before = self._call_view("GameRegistry", "gameCount")
            self._send_transaction("GameRegistry", "createGame", [hash_bytes32])
            
            game_id = count_before + 1
            print(f"  [CHAIN] Game created: id={game_id} hash={game_hash[:16]}...")
            return game_id
        
        # Local: return incrementing ID
        game_id = len(self.agent_name_to_id) + 1  # Simple counter
        print(f"  [CHAIN] Game created (local): id={game_id} hash={game_hash[:16]}...")
        return game_id

    def start_game(self, game_id: int):
        """Mark game as running."""
        if self.live_mode:
            self._send_transaction("GameRegistry", "startGame", [game_id])
        print(f"  [CHAIN] Game started: id={game_id}")

    def finish_game(self, game_id: int):
        """Mark game as finished."""
        if self.live_mode:
            self._send_transaction("GameRegistry", "finishGame", [game_id])
        print(f"  [CHAIN] Game finished: id={game_id}")

    # ---- Prediction Market ----

    def create_market(self, game_id: int, question: str) -> int:
        """Create a prediction market. Returns market ID."""
        if self.live_mode:
            count_before = self._call_view("PredictionMarket", "marketCount")
            
            receipt = self._send_transaction(
                "PredictionMarket", "createMarket", [game_id, question]
            )
            
            # Get market ID from event
            market_id = self._get_event_arg(receipt, "PredictionMarket", "MarketCreated", "marketId")
            if market_id is None:
                market_id = count_before + 1
            
            print(f"  [CHAIN] Market created: id={market_id} '{question}'")
            return market_id
        
        # Local counter
        self._local_market_count = getattr(self, "_local_market_count", 0) + 1
        print(f"  [CHAIN] Market created (local): id={self._local_market_count} '{question}'")
        return self._local_market_count

    def resolve_market(self, market_id: int, outcome: bool):
        """Resolve a prediction market."""
        if self.live_mode:
            self._send_transaction("PredictionMarket", "resolveMarket", [market_id, outcome])
        print(f"  [CHAIN] Market resolved: id={market_id} → {'YES' if outcome else 'NO'}")

    # ---- Game Resolver (Batch) ----

    def resolve_game(self, game_id: int, market_outcomes: dict[int, bool]):
        """
        Finish game and resolve all associated markets atomically.
        market_outcomes: {market_id: outcome_bool}
        """
        market_ids = list(market_outcomes.keys())
        outcomes = list(market_outcomes.values())
        
        if self.live_mode:
            self._send_transaction("GameResolver", "resolveGame", [game_id, market_ids, outcomes])
            print(f"  [CHAIN] Game {game_id} resolved with {len(market_ids)} markets")
        else:
            # Individual resolution for local mode
            self.finish_game(game_id)
            for market_id, outcome in market_outcomes.items():
                self.resolve_market(market_id, outcome)


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
        
        # Import tokenization module
        try:
            from tokenization import PersistentTokenization
            self.tokenization = PersistentTokenization(self.connector)
        except ImportError:
            print("  [CHAIN] Warning: tokenization.py not found, tokenization disabled")
            self.tokenization = None
        
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
            if colour not in self.connector.agent_name_to_id:
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

    def on_pre_game_trading_start(self):
        """Called when pre-game trading period begins."""
        print(f"  [CHAIN] Pre-game trading started for game {self.game_id}")
        
        # Trading is unlocked by default, no action needed
        # This is just a notification hook for future extensions
        if self.tokenization:
            print(f"  [CHAIN] Spectators can now trade agent tokens")

    def on_game_actually_start(self):
        """Called when game actually starts (after trading period)."""
        print(f"  [CHAIN] Game {self.game_id} starting - locking trading")
        
        # Lock all agent token trading
        if self.tokenization:
            self.tokenization.lock_trading(self.game_id)

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

        # Distribute token rewards (90% of prize pool)
        if self.tokenization:
            self.tokenization.distribute_rewards(
                self.game_id, winner, alive_agents, imposter_colour
            )

        # Update agent stats (both on-chain and tokenization)
        for colour in self.agent_colours:
            won = False
            if colour == imposter_colour:
                won = (winner == "IMPOSTER")
            else:
                won = (winner == "CREW")
            self.connector.update_agent_stats(colour, won)
            
            # Update token stats
            if self.tokenization:
                self.tokenization.update_agent_stats(colour, won)

        # Unlock trading for next game
        if self.tokenization:
            self.tokenization.unlock_trading(self.game_id)

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
