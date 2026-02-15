# MonadSus Production Deployment Guide

## Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
The `.env` file is already configured for **simulation mode** (no blockchain required).

To use **live mode** with real blockchain:
1. Deploy contracts (see "Contract Deployment" below)
2. Update `.env`:
   ```bash
   MONAD_LIVE_MODE=1
   AGENT_TOKEN_REGISTRY_ADDRESS=0x...  # From deployment
   GAME_PRIZE_POOL_ADDRESS=0x...       # From deployment
   MONAD_PRIVATE_KEY=0x...             # Your private key
   ```

### 3. Start Trading Server
```bash
python trading_server.py
```

Server will start on http://localhost:8000

### 4. Start Game
```bash
# In a new terminal
python main_autonomous.py
```

### 5. Access Trading UI
Open http://localhost:8000 in your browser

---

## Contract Deployment (Optional - For Live Mode)

### Prerequisites
1. Install Foundry:
   ```bash
   curl -L https://foundry.paradigm.xyz | bash
   foundryup
   ```

2. Get Monad testnet MON tokens from faucet

### Deploy Contracts
```bash
cd monadsus-contracts

# Test contracts first
forge test

# Deploy to Monad testnet
forge script script/DeployPersistentTokenization.s.sol \
  --rpc-url $MONAD_RPC_URL \
  --private-key $MONAD_PRIVATE_KEY \
  --broadcast

# Copy deployed addresses to .env
```

---

## Testing

### Test 1: Imports
```bash
python -c "import blockchain; import tokenization; import openclaw_agent; print('✅ All imports successful')"
```

### Test 2: Simulation Mode
```bash
# Make sure MONAD_LIVE_MODE=0 in .env
python main_autonomous.py
```

**Expected**:
- Pre-game trading period (5 minutes)
- Trading locks when game starts
- Tokens created for all agents
- Game completes successfully

### Test 3: Trading UI
```bash
python trading_server.py
# Open http://localhost:8000
# Click "Connect Wallet"
# View agent tokens
```

### Test 4: OpenClaw Agents
```bash
# Update .env:
# AGENT_MODE=openclaw
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...

python main_autonomous.py
```

**Expected**:
- Agents make strategic decisions
- Natural language dialogue
- LLM errors logged to `openclaw_errors.log`

---

## Production Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` configured
- [ ] Trading server running (`python trading_server.py`)
- [ ] Game tested in simulation mode
- [ ] (Optional) Contracts deployed to testnet
- [ ] (Optional) Live mode tested
- [ ] Trading UI accessible

---

## Troubleshooting

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Trading Server Won't Start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Use different port
# Update .env: TRADING_SERVER_PORT=8001
```

### Game Crashes
```bash
# Check logs
tail -f game_log_*.json
tail -f openclaw_errors.log

# Verify .env configuration
cat .env
```

### Trading UI Shows Wrong Data
```bash
# Verify server is running
curl http://localhost:8000/api/config

# Check browser console for errors
```

---

## Architecture

```
┌─────────────────┐
│  Trading UI     │ ← Users trade tokens
│ (port 8000)     │
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│ Trading Server  │ ← Serves UI + API
│ (Flask)         │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Autonomous Game │ ← Game logic
│ (Python)        │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Blockchain      │ ← Smart contracts
│ (Monad)         │
└─────────────────┘
```

---

## File Structure

```
moltiverse monad/
├── .env                    # Configuration (created)
├── .env.example            # Template
├── trading_server.py       # Trading UI server (created)
├── main_autonomous.py      # Game entry point
├── autonomous_game.py      # Game logic
├── blockchain.py           # Blockchain integration
├── tokenization.py         # Token management
├── openclaw_agent.py       # LLM agents
├── token_trading_ui.html   # Trading interface
├── agent_personalities/    # Agent personalities (5 files)
├── monadsus-contracts/     # Smart contracts
│   ├── src/               # Contract source
│   ├── script/            # Deployment scripts
│   └── test/              # Contract tests
└── requirements.txt        # Python dependencies
```

---

## Next Steps

1. **Test in simulation mode** (no blockchain needed)
2. **Deploy contracts** when ready for testnet
3. **Enable live mode** in `.env`
4. **Share trading UI** with spectators

---

## Support

- Check `openclaw_errors.log` for LLM errors
- Check `game_log_*.json` for game events
- Review `.env` configuration
- Ensure all dependencies installed

Ready to launch! 🚀
