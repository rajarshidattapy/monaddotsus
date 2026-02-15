// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./PersistentAgentToken.sol";

/**
 * @title GamePrizePool
 * @notice Manages prize pools and distributes 90% to winners, 10% to platform
 * @dev Supports proportional reward distribution to token holders
 */
contract GamePrizePool is ReentrancyGuard {
    struct GamePool {
        uint256 totalDeposited;
        uint256 prizePool;      // 90% of total
        uint256 platformFee;    // 10% of total
        bool distributed;
    }
    
    // Game ID => GamePool
    mapping(uint256 => GamePool) public games;
    
    // Game ID => Token Address => Reward Amount
    mapping(uint256 => mapping(address => uint256)) public tokenRewards;
    
    // Game ID => User => Token => Claimed
    mapping(uint256 => mapping(address => mapping(address => bool))) public hasClaimed;
    
    // Configuration
    address public platformWallet;
    address public gameManager;
    
    uint256 public constant PRIZE_POOL_PERCENTAGE = 90;
    uint256 public constant PLATFORM_FEE_PERCENTAGE = 10;
    
    // Events
    event Deposited(uint256 indexed gameId, address indexed user, uint256 amount);
    event RewardsDistributed(uint256 indexed gameId, address[] tokens, uint256[] amounts);
    event RewardClaimed(uint256 indexed gameId, address indexed user, address indexed token, uint256 amount);
    event PlatformFeeClaimed(uint256 indexed gameId, uint256 amount);
    
    modifier onlyGameManager() {
        require(msg.sender == gameManager, "Only game manager");
        _;
    }
    
    modifier onlyPlatform() {
        require(msg.sender == platformWallet, "Only platform wallet");
        _;
    }
    
    /**
     * @notice Initialize the prize pool contract
     * @param _platformWallet Address to receive platform fees
     * @param _gameManager Address authorized to distribute rewards
     */
    constructor(address _platformWallet, address _gameManager) {
        require(_platformWallet != address(0), "Invalid platform wallet");
        require(_gameManager != address(0), "Invalid game manager");
        platformWallet = _platformWallet;
        gameManager = _gameManager;
    }
    
    /**
     * @notice Deposit funds into a game's prize pool (no minimum)
     * @param gameId ID of the game
     */
    function deposit(uint256 gameId) external payable {
        require(msg.value > 0, "Must deposit something");
        require(!games[gameId].distributed, "Game already finished");
        
        GamePool storage pool = games[gameId];
        pool.totalDeposited += msg.value;
        
        // Split: 90% prize pool, 10% platform
        uint256 toPrize = (msg.value * PRIZE_POOL_PERCENTAGE) / 100;
        uint256 toFee = msg.value - toPrize;
        
        pool.prizePool += toPrize;
        pool.platformFee += toFee;
        
        emit Deposited(gameId, msg.sender, msg.value);
    }
    
    /**
     * @notice Distribute rewards to winning agent tokens
     * @param gameId ID of the game
     * @param winningTokens Array of winning token addresses
     * @param percentages Array of percentages (must sum to 100)
     */
    function distributeRewards(
        uint256 gameId,
        address[] memory winningTokens,
        uint256[] memory percentages
    ) external onlyGameManager nonReentrant {
        require(!games[gameId].distributed, "Already distributed");
        require(winningTokens.length == percentages.length, "Length mismatch");
        require(winningTokens.length > 0, "No winners");
        
        // Validate percentages sum to 100
        uint256 totalPercentage = 0;
        for (uint256 i = 0; i < percentages.length; i++) {
            totalPercentage += percentages[i];
        }
        require(totalPercentage == 100, "Percentages must sum to 100");
        
        GamePool storage pool = games[gameId];
        uint256 totalPrize = pool.prizePool;
        
        uint256[] memory amounts = new uint256[](winningTokens.length);
        
        for (uint256 i = 0; i < winningTokens.length; i++) {
            uint256 reward = (totalPrize * percentages[i]) / 100;
            tokenRewards[gameId][winningTokens[i]] = reward;
            amounts[i] = reward;
            
            // Send rewards to token contract for accounting
            if (reward > 0) {
                PersistentAgentToken(winningTokens[i]).receiveRewards{value: reward}();
            }
        }
        
        pool.distributed = true;
        emit RewardsDistributed(gameId, winningTokens, amounts);
    }
    
    /**
     * @notice Claim proportional reward based on token holdings
     * @param gameId ID of the game
     * @param tokenAddress Address of the agent token
     */
    function claimReward(uint256 gameId, address tokenAddress) external nonReentrant {
        require(games[gameId].distributed, "Rewards not distributed yet");
        require(!hasClaimed[gameId][msg.sender][tokenAddress], "Already claimed");
        
        uint256 totalReward = tokenRewards[gameId][tokenAddress];
        require(totalReward > 0, "No rewards for this token");
        
        IERC20 token = IERC20(tokenAddress);
        uint256 userBalance = token.balanceOf(msg.sender);
        require(userBalance > 0, "No tokens held");
        
        uint256 totalSupply = token.totalSupply();
        uint256 userReward = (totalReward * userBalance) / totalSupply;
        
        require(userReward > 0, "No rewards to claim");
        
        // Mark as claimed
        hasClaimed[gameId][msg.sender][tokenAddress] = true;
        
        // Transfer MON to user
        (bool success, ) = msg.sender.call{value: userReward}("");
        require(success, "Transfer failed");
        
        emit RewardClaimed(gameId, msg.sender, tokenAddress, userReward);
    }
    
    /**
     * @notice Platform claims accumulated fees for a game
     * @param gameId ID of the game
     */
    function claimPlatformFee(uint256 gameId) external onlyPlatform nonReentrant {
        GamePool storage pool = games[gameId];
        uint256 fee = pool.platformFee;
        require(fee > 0, "No fees to claim");
        
        pool.platformFee = 0;
        
        (bool success, ) = platformWallet.call{value: fee}("");
        require(success, "Transfer failed");
        
        emit PlatformFeeClaimed(gameId, fee);
    }
    
    /**
     * @notice Get game pool statistics
     * @param gameId ID of the game
     * @return totalDeposited Total amount deposited
     * @return prizePool Amount allocated to prize pool (90%)
     * @return platformFee Amount allocated to platform (10%)
     * @return distributed Whether rewards have been distributed
     */
    function getGameStats(uint256 gameId) external view returns (
        uint256 totalDeposited,
        uint256 prizePool,
        uint256 platformFee,
        bool distributed
    ) {
        GamePool storage pool = games[gameId];
        return (
            pool.totalDeposited,
            pool.prizePool,
            pool.platformFee,
            pool.distributed
        );
    }
    
    /**
     * @notice Check if user has claimed reward for a specific token
     * @param gameId ID of the game
     * @param user User address
     * @param tokenAddress Token address
     * @return Whether the user has claimed
     */
    function hasUserClaimed(uint256 gameId, address user, address tokenAddress) external view returns (bool) {
        return hasClaimed[gameId][user][tokenAddress];
    }
}
