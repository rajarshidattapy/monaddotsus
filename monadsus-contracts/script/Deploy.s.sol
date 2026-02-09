// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/GameRegistry.sol";
import "../src/PredictionMarket.sol";
import "../src/AgentRegistry.sol";
import "../src/GameResolver.sol";

contract Deploy is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");

        vm.startBroadcast(deployerKey);

        GameRegistry gameRegistry = new GameRegistry();
        PredictionMarket predictionMarket = new PredictionMarket();
        AgentRegistry agentRegistry = new AgentRegistry();

        GameResolver gameResolver = new GameResolver(
            address(gameRegistry),
            address(predictionMarket)
        );

        vm.stopBroadcast();

        console.log("GameRegistry:", address(gameRegistry));
        console.log("PredictionMarket:", address(predictionMarket));
        console.log("AgentRegistry:", address(agentRegistry));
        console.log("GameResolver:", address(gameResolver));
    }
}
