"""
Trading Server for MonadSus Token Trading UI.

Serves the trading UI and provides REST API endpoints for game state.
"""

from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for MetaMask

# Global game state
current_game_state = {
    "gameId": 1,
    "status": "pre_game",  # pre_game, in_progress, ended
    "timeRemaining": 300,  # seconds
    "agentTokens": {},
    "prizePool": "0"
}

@app.route('/')
def index():
    """Serve the trading UI."""
    return send_file('token_trading_ui.html')

@app.route('/api/config')
def get_config():
    """Get contract addresses and configuration."""
    return jsonify({
        "registryAddress": os.getenv("AGENT_TOKEN_REGISTRY_ADDRESS", "0x0000000000000000000000000000000000000000"),
        "prizePoolAddress": os.getenv("GAME_PRIZE_POOL_ADDRESS", "0x0000000000000000000000000000000000000000"),
        "rpcUrl": os.getenv("MONAD_RPC_URL", "https://testnet.monad.xyz/rpc"),
        "liveMode": os.getenv("MONAD_LIVE_MODE", "0") == "1"
    })

@app.route('/api/current-game')
def get_current_game():
    """Get current game state."""
    return jsonify(current_game_state)

@app.route('/api/game-state', methods=['POST'])
def update_game_state():
    """Update game state (called by game backend)."""
    global current_game_state
    data = request.json
    current_game_state.update(data)
    return jsonify({"success": True})

@app.route('/api/agent-tokens')
def get_agent_tokens():
    """Get all agent token addresses."""
    # This would be populated by the game backend
    return jsonify(current_game_state.get("agentTokens", {}))

@app.route('/api/prize-pool/<int:game_id>')
def get_prize_pool(game_id):
    """Get prize pool stats for a game."""
    return jsonify({
        "gameId": game_id,
        "totalDeposited": current_game_state.get("prizePool", "0"),
        "prizePoolAmount": current_game_state.get("prizePool", "0"),
        "platformFee": "0",
        "distributed": False
    })

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.getenv("TRADING_SERVER_PORT", "8000"))
    print(f"🌐 Trading Server starting on http://localhost:{port}")
    print(f"📊 Trading UI: http://localhost:{port}/")
    print(f"🔧 API Config: http://localhost:{port}/api/config")
    print(f"🎮 Game State: http://localhost:{port}/api/current-game")
    app.run(host='0.0.0.0', port=port, debug=True)
