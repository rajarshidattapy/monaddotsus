// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title PersistentAgentToken
 * @notice ERC20 token representing a MonadSus agent that persists across games
 * @dev Includes trading lock mechanism and on-chain stats tracking
 */
contract PersistentAgentToken is ERC20, Ownable {
    // Agent metadata
    string public agentName;
    string public agentPersonality;
    uint256 public gamesPlayed;
    uint256 public gamesWon;
    uint256 public totalRewardsEarned;
    
    // Trading control
    bool public tradingEnabled;
    
    // Events
    event TradingStatusChanged(bool enabled);
    event StatsUpdated(uint256 gamesPlayed, uint256 gamesWon);
    event RewardsReceived(uint256 amount);
    
    /**
     * @notice Creates a new persistent agent token
     * @param _agentName Name of the agent (e.g., "Red", "Blue")
     * @param _personality Agent personality type (e.g., "detective", "aggressive")
     * @param _initialSupply Initial token supply (will be multiplied by 10^18)
     */
    constructor(
        string memory _agentName,
        string memory _personality,
        uint256 _initialSupply
    ) ERC20(
        string(abi.encodePacked("MonadSus ", _agentName)),
        string(abi.encodePacked("SUS", _agentName))
    ) Ownable(msg.sender) {
        agentName = _agentName;
        agentPersonality = _personality;
        tradingEnabled = true;
        
        // Mint initial supply to creator
        _mint(msg.sender, _initialSupply * 10**decimals());
    }
    
    /**
     * @notice Enable or disable trading (called by game manager)
     * @param _enabled True to enable trading, false to lock
     */
    function setTradingEnabled(bool _enabled) external onlyOwner {
        tradingEnabled = _enabled;
        emit TradingStatusChanged(_enabled);
    }
    
    /**
     * @notice Update agent stats after a game
     * @param won Whether the agent won the game
     */
    function updateStats(bool won) external onlyOwner {
        gamesPlayed++;
        if (won) gamesWon++;
        emit StatsUpdated(gamesPlayed, gamesWon);
    }
    
    /**
     * @notice Receive reward distribution from prize pool
     */
    function receiveRewards() external payable {
        totalRewardsEarned += msg.value;
        emit RewardsReceived(msg.value);
    }
    
    /**
     * @notice Calculate agent's win rate percentage
     * @return Win rate as percentage (0-100)
     */
    function winRate() public view returns (uint256) {
        if (gamesPlayed == 0) return 0;
        return (gamesWon * 100) / gamesPlayed;
    }
    
    /**
     * @notice Override transfer to respect trading lock
     * @dev Minting and burning are always allowed
     */
    function _update(address from, address to, uint256 value) internal virtual override {
        if (from != address(0) && to != address(0)) {
            // Regular transfer (not mint/burn)
            require(tradingEnabled, "Trading is locked during game");
        }
        super._update(from, to, value);
    }
}
