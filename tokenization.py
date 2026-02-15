"""
Persistent Tokenization Module for MonadSus.

Manages persistent agent tokens that survive across games.
Integrates with AgentTokenRegistry and GamePrizePool contracts.
"""

import os
from contract_abis import PERSISTENT_AGENT_TOKEN_ABI, AGENT_TOKEN_REGISTRY_ABI, GAME_PRIZE_POOL_ABI

class PersistentTokenization:
    """Manages persistent agent tokens across games."""
    
    def __init__(self, connector: 'BlockchainConnector'):
        self.connector = connector
        self.registry_address = os.environ.get("AGENT_TOKEN_REGISTRY_ADDRESS", "")
        self.prize_pool_address = os.environ.get("GAME_PRIZE_POOL_ADDRESS", "")
        self.agent_tokens: dict[str, str] = {}  # agent_name => token_address
        
    def get_or_create_token(self, agent_name: str, personality: str) -> str:
        """Get existing token or create new one for agent."""
        if not self.connector.live_mode:
            # Simulation mode
            if agent_name not in self.agent_tokens:
                mock_addr = f"0x{'0' * 38}{hash(agent_name) % 100:02d}"
                self.agent_tokens[agent_name] = mock_addr
                print(f"  [TOKEN] Created persistent token for {agent_name}: {mock_addr}")
            return self.agent_tokens[agent_name]
        
        # Check if we already have this token cached
        if agent_name in self.agent_tokens:
            return self.agent_tokens[agent_name]
        
        # Live mode: call AgentTokenRegistry.getOrCreateToken
        try:
            # First check if token already exists
            existing = self.connector._call_view(
                "AgentTokenRegistry",
                "agentTokens",
                [agent_name]
            )
            
            if existing and existing != "0x0000000000000000000000000000000000000000":
                self.agent_tokens[agent_name] = existing
                print(f"  [TOKEN] Found existing token for {agent_name}: {existing}")
                return existing
            
            # Create new token
            receipt = self.connector._send_transaction(
                "AgentTokenRegistry",
                "getOrCreateToken",
                [agent_name, personality]
            )
            
            token_address = self.connector._get_event_arg(
                receipt, "AgentTokenRegistry", "AgentTokenCreated", "tokenAddress"
            )
            
            if token_address:
                self.agent_tokens[agent_name] = token_address
                print(f"  [TOKEN] Created token for {agent_name}: {token_address}")
                return token_address
            
            # Fallback: query the mapping
            token_address = self.connector._call_view(
                "AgentTokenRegistry",
                "agentTokens",
                [agent_name]
            )
            
            # Validate token was created successfully
            if not token_address or token_address == "0x0000000000000000000000000000000000000000":
                raise ValueError(f"Failed to create token for {agent_name}")
            
            self.agent_tokens[agent_name] = token_address
            return token_address
            
        except Exception as e:
            print(f"  [TOKEN] Error getting/creating token for {agent_name}: {e}")
            return None
    
    def lock_trading(self, game_id: int):
        """Lock trading for all agent tokens when game starts."""
        print(f"  [TOKEN] Locking trading for game {game_id}")
        
        if not self.connector.live_mode:
            return
        
        for agent_name, token_address in self.agent_tokens.items():
            try:
                # Get token contract instance
                assert self.connector._web3 is not None
                token_contract = self.connector._web3.eth.contract(
                    address=self.connector._web3.to_checksum_address(token_address),
                    abi=PERSISTENT_AGENT_TOKEN_ABI
                )
                
                # Call setTradingEnabled(false)
                self.connector._send_transaction_private_key(
                    token_contract,
                    token_contract.functions.setTradingEnabled(False),
                    "PersistentAgentToken",
                    "setTradingEnabled"
                )
                print(f"  [TOKEN] Locked trading for {agent_name}")
            except Exception as e:
                print(f"  [TOKEN] Error locking {agent_name}: {e}")
    
    def unlock_trading(self, game_id: int):
        """Unlock trading after game ends."""
        print(f"  [TOKEN] Unlocking trading for game {game_id}")
        
        if not self.connector.live_mode:
            return
        
        for agent_name, token_address in self.agent_tokens.items():
            try:
                assert self.connector._web3 is not None
                token_contract = self.connector._web3.eth.contract(
                    address=self.connector._web3.to_checksum_address(token_address),
                    abi=PERSISTENT_AGENT_TOKEN_ABI
                )
                
                self.connector._send_transaction_private_key(
                    token_contract,
                    token_contract.functions.setTradingEnabled(True),
                    "PersistentAgentToken",
                    "setTradingEnabled"
                )
                print(f"  [TOKEN] Unlocked trading for {agent_name}")
            except Exception as e:
                print(f"  [TOKEN] Error unlocking {agent_name}: {e}")
    
    def distribute_rewards(self, game_id: int, winner: str, survivors: list[str], imposter: str):
        """Distribute 90% of prize pool to winning token holders."""
        winning_tokens = []
        percentages = []
        
        if winner == "CREW":
            # All survivors split rewards equally
            if survivors:
                for agent_name in survivors:
                    if agent_name in self.agent_tokens:
                        winning_tokens.append(self.agent_tokens[agent_name])
                        percentages.append(100 // len(survivors))
        else:
            # Imposter gets all rewards
            if imposter in self.agent_tokens:
                winning_tokens.append(self.agent_tokens[imposter])
                percentages.append(100)
        
        if not winning_tokens:
            print(f"  [TOKEN] No winning tokens to distribute rewards to")
            return
        
        if not self.connector.live_mode:
            print(f"  [TOKEN] Distributing 90% of prize pool (simulation)")
            for token, pct in zip(winning_tokens, percentages):
                print(f"  [TOKEN] {token} gets {pct}% of 90% prize pool")
            return
        
        # Live mode: call GamePrizePool.distributeRewards
        try:
            self.connector._send_transaction(
                "GamePrizePool",
                "distributeRewards",
                [game_id, winning_tokens, percentages]
            )
            print(f"  [TOKEN] Rewards distributed for game {game_id}")
        except Exception as e:
            print(f"  [TOKEN] Error distributing rewards: {e}")
    
    def update_agent_stats(self, agent_name: str, won: bool):
        """Update agent token stats after game."""
        if agent_name not in self.agent_tokens:
            return
        
        token_address = self.agent_tokens[agent_name]
        
        if not self.connector.live_mode:
            print(f"  [TOKEN] Updated stats for {agent_name}: won={won}")
            return
        
        try:
            assert self.connector._web3 is not None
            token_contract = self.connector._web3.eth.contract(
                address=self.connector._web3.to_checksum_address(token_address),
                abi=PERSISTENT_AGENT_TOKEN_ABI
            )
            
            self.connector._send_transaction_private_key(
                token_contract,
                token_contract.functions.updateStats(won),
                "PersistentAgentToken",
                "updateStats"
            )
            print(f"  [TOKEN] Updated stats for {agent_name}: won={won}")
        except Exception as e:
            print(f"  [TOKEN] Error updating stats for {agent_name}: {e}")
    
    def get_token_stats(self, agent_name: str) -> dict:
        """Get on-chain stats for an agent token."""
        if agent_name not in self.agent_tokens:
            return {"gamesPlayed": 0, "gamesWon": 0, "winRate": 0}
        
        token_address = self.agent_tokens[agent_name]
        
        if not self.connector.live_mode:
            return {"gamesPlayed": 0, "gamesWon": 0, "winRate": 0}
        
        try:
            assert self.connector._web3 is not None
            token_contract = self.connector._web3.eth.contract(
                address=self.connector._web3.to_checksum_address(token_address),
                abi=PERSISTENT_AGENT_TOKEN_ABI
            )
            
            games_played = token_contract.functions.gamesPlayed().call()
            games_won = token_contract.functions.gamesWon().call()
            win_rate = token_contract.functions.winRate().call()
            
            return {
                "gamesPlayed": games_played,
                "gamesWon": games_won,
                "winRate": win_rate
            }
        except Exception as e:
            print(f"  [TOKEN] Error getting stats for {agent_name}: {e}")
            return {"gamesPlayed": 0, "gamesWon": 0, "winRate": 0}
