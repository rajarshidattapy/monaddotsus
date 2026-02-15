"""
Contract ABIs for MonadSus Blockchain Integration.

Separated to avoid circular imports between blockchain.py and tokenization.py.
"""

# Persistent Agent Token ABI
PERSISTENT_AGENT_TOKEN_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "_agentName", "type": "string"},
            {"internalType": "string", "name": "_personality", "type": "string"},
            {"internalType": "uint256", "name": "_initialSupply", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [],
        "name": "agentName",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "agentPersonality",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "gamesPlayed",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "gamesWon",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "winRate",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bool", "name": "_enabled", "type": "bool"}],
        "name": "setTradingEnabled",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bool", "name": "won", "type": "bool"}],
        "name": "updateStats",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "receiveRewards",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "tradingEnabled",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Agent Token Registry ABI
AGENT_TOKEN_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "agentName", "type": "string"},
            {"internalType": "string", "name": "personality", "type": "string"}
        ],
        "name": "getOrCreateToken",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "", "type": "string"}],
        "name": "agentTokens",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getAllTokens",
        "outputs": [{"internalType": "address[]", "name": "", "type": "address[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "string", "name": "agentName", "type": "string"},
            {"indexed": True, "internalType": "address", "name": "tokenAddress", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "personality", "type": "string"}
        ],
        "name": "AgentTokenCreated",
        "type": "event"
    }
]

# Game Prize Pool ABI
GAME_PRIZE_POOL_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "_registry", "type": "address"},
            {"internalType": "address", "name": "_platformWallet", "type": "address"},
            {"internalType": "uint256", "name": "_prizePoolPercentage", "type": "uint256"},
            {"internalType": "uint256", "name": "_platformFeePercentage", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "gameId", "type": "uint256"}],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "gameId", "type": "uint256"},
            {"internalType": "address[]", "name": "winningTokens", "type": "address[]"},
            {"internalType": "uint256[]", "name": "percentages", "type": "uint256[]"}
        ],
        "name": "distributeRewards",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "gameId", "type": "uint256"}],
        "name": "getGameStats",
        "outputs": [
            {"internalType": "uint256", "name": "totalDeposited", "type": "uint256"},
            {"internalType": "uint256", "name": "prizePool", "type": "uint256"},
            {"internalType": "uint256", "name": "platformFee", "type": "uint256"},
            {"internalType": "bool", "name": "distributed", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "gameId", "type": "uint256"},
            {"internalType": "address", "name": "tokenAddress", "type": "address"}
        ],
        "name": "claimReward",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]
