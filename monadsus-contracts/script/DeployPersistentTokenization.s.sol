// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/AgentTokenRegistry.sol";
import "../src/GamePrizePool.sol";

/**
 * @title DeployPersistentTokenization
 * @notice Deployment script for persistent agent tokenization system
 */
contract DeployPersistentTokenization is Script {
    function run() external {
        // Get deployment parameters from environment
        address deployer = vm.envAddress("DEPLOYER_ADDRESS");
        address platformWallet = vm.envOr("PLATFORM_WALLET_ADDRESS", deployer);
        
        vm.startBroadcast();
        
        // 1. Deploy AgentTokenRegistry
        AgentTokenRegistry registry = new AgentTokenRegistry(deployer);
        console.log("AgentTokenRegistry deployed at:", address(registry));
        
        // 2. Deploy GamePrizePool
        GamePrizePool prizePool = new GamePrizePool(platformWallet, deployer);
        console.log("GamePrizePool deployed at:", address(prizePool));
        
        vm.stopBroadcast();
        
        // Log deployment info
        console.log("\n=== Deployment Summary ===");
        console.log("Network:", block.chainid);
        console.log("Deployer:", deployer);
        console.log("Platform Wallet:", platformWallet);
        console.log("AgentTokenRegistry:", address(registry));
        console.log("GamePrizePool:", address(prizePool));
        console.log("\nAdd these to your .env file:");
        console.log("AGENT_TOKEN_REGISTRY_ADDRESS=%s", address(registry));
        console.log("GAME_PRIZE_POOL_ADDRESS=%s", address(prizePool));
    }
}
