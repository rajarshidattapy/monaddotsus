// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./PersistentAgentToken.sol";

/**
 * @title AgentTokenRegistry
 * @notice Central registry for creating and managing persistent agent tokens
 * @dev Only the game manager can create tokens
 */
contract AgentTokenRegistry {
    // Mappings
    mapping(string => address) public agentTokens; // agentName => tokenAddress
    mapping(address => bool) public isRegistered;
    address[] public allTokens;

    // Configuration
    address public gameManager;
    uint256 public constant INITIAL_SUPPLY = 1_000_000; // 1M tokens per agent

    // Events
    event AgentTokenCreated(
        string agentName,
        address tokenAddress,
        uint256 timestamp
    );

    modifier onlyGameManager() {
        require(msg.sender == gameManager, "Only game manager");
        _;
    }

    /**
     * @notice Initialize the registry with a game manager
     * @param _gameManager Address authorized to create tokens
     */
    constructor(address _gameManager) {
        gameManager = _gameManager;
    }

    /**
     * @notice Create a new agent token
     * @param agentName Name of the agent
     * @param personality Personality type of the agent
     * @return Address of the newly created token
     */
    function createAgentToken(
        string memory agentName,
        string memory personality
    ) external onlyGameManager returns (address) {
        require(agentTokens[agentName] == address(0), "Token already exists");

        PersistentAgentToken token = new PersistentAgentToken(
            agentName,
            personality,
            INITIAL_SUPPLY
        );

        address tokenAddress = address(token);
        agentTokens[agentName] = tokenAddress;
        isRegistered[tokenAddress] = true;
        allTokens.push(tokenAddress);

        // Transfer ownership to game manager
        token.transferOwnership(gameManager);

        emit AgentTokenCreated(agentName, tokenAddress, block.timestamp);
        return tokenAddress;
    }

    /**
     * @notice Get existing token or create new one if it doesn't exist
     * @param agentName Name of the agent
     * @param personality Personality type (only used if creating new)
     * @return Address of the token
     */
    function getOrCreateToken(
        string memory agentName,
        string memory personality
    ) external onlyGameManager returns (address) {
        address existing = agentTokens[agentName];
        if (existing != address(0)) {
            return existing;
        }
        return this.createAgentToken(agentName, personality);
    }

    /**
     * @notice Get all registered token addresses
     * @return Array of all token addresses
     */
    function getAllTokens() external view returns (address[] memory) {
        return allTokens;
    }

    /**
     * @notice Get token address for an agent
     * @param agentName Name of the agent
     * @return Token address (address(0) if not exists)
     */
    function getTokenAddress(
        string memory agentName
    ) external view returns (address) {
        return agentTokens[agentName];
    }

    /**
     * @notice Get total number of registered tokens
     * @return Count of tokens
     */
    function tokenCount() external view returns (uint256) {
        return allTokens.length;
    }
}
