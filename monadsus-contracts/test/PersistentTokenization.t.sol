// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/PersistentAgentToken.sol";
import "../src/AgentTokenRegistry.sol";
import "../src/GamePrizePool.sol";

contract PersistentTokenizationTest is Test {
    AgentTokenRegistry public registry;
    GamePrizePool public prizePool;
    
    address public gameManager = address(1);
    address public platformWallet = address(2);
    address public player1 = address(3);
    address public player2 = address(4);
    
    function setUp() public {
        registry = new AgentTokenRegistry(gameManager);
        prizePool = new GamePrizePool(platformWallet, gameManager);
    }
    
    function testCreateAgentToken() public {
        vm.prank(gameManager);
        address tokenAddr = registry.createAgentToken("Red", "detective");
        
        assertTrue(tokenAddr != address(0), "Token should be created");
        assertEq(registry.agentTokens("Red"), tokenAddr, "Token should be registered");
        
        PersistentAgentToken token = PersistentAgentToken(tokenAddr);
        assertEq(token.agentName(), "Red");
        assertEq(token.agentPersonality(), "detective");
        assertEq(token.totalSupply(), 1_000_000 * 10**18);
    }
    
    function testGetOrCreateToken() public {
        vm.startPrank(gameManager);
        
        // First call creates token
        address token1 = registry.getOrCreateToken("Blue", "aggressive");
        assertTrue(token1 != address(0));
        
        // Second call returns existing token
        address token2 = registry.getOrCreateToken("Blue", "different");
        assertEq(token1, token2, "Should return existing token");
        
        vm.stopPrank();
    }
    
    function testTradingLock() public {
        vm.prank(gameManager);
        address tokenAddr = registry.createAgentToken("Green", "balanced");
        
        PersistentAgentToken token = PersistentAgentToken(tokenAddr);
        
        // Transfer initial tokens to players
        vm.prank(gameManager);
        token.transfer(player1, 1000 * 10**18);
        
        // Trading should work initially
        vm.prank(player1);
        token.transfer(player2, 100 * 10**18);
        assertEq(token.balanceOf(player2), 100 * 10**18);
        
        // Lock trading
        vm.prank(gameManager);
        token.setTradingEnabled(false);
        
        // Trading should fail
        vm.prank(player1);
        vm.expectRevert("Trading is locked during game");
        token.transfer(player2, 100 * 10**18);
        
        // Unlock trading
        vm.prank(gameManager);
        token.setTradingEnabled(true);
        
        // Trading should work again
        vm.prank(player1);
        token.transfer(player2, 100 * 10**18);
        assertEq(token.balanceOf(player2), 200 * 10**18);
    }
    
    function testPrizePoolDeposit() public {
        uint256 gameId = 1;
        
        // Player deposits 10 MON
        vm.deal(player1, 10 ether);
        vm.prank(player1);
        prizePool.deposit{value: 10 ether}(gameId);
        
        (uint256 total, uint256 prize, uint256 fee, bool distributed) = prizePool.getGameStats(gameId);
        
        assertEq(total, 10 ether, "Total should be 10 MON");
        assertEq(prize, 9 ether, "Prize pool should be 90%");
        assertEq(fee, 1 ether, "Platform fee should be 10%");
        assertFalse(distributed, "Should not be distributed yet");
    }
    
    function testRewardDistribution() public {
        uint256 gameId = 1;
        
        // Create tokens
        vm.startPrank(gameManager);
        address redToken = registry.createAgentToken("Red", "detective");
        address blueToken = registry.createAgentToken("Blue", "aggressive");
        vm.stopPrank();
        
        // Players buy tokens
        vm.prank(gameManager);
        PersistentAgentToken(redToken).transfer(player1, 500_000 * 10**18); // 50% of supply
        
        vm.prank(gameManager);
        PersistentAgentToken(blueToken).transfer(player2, 500_000 * 10**18); // 50% of supply
        
        // Deposit prize pool
        vm.deal(player1, 100 ether);
        vm.prank(player1);
        prizePool.deposit{value: 100 ether}(gameId);
        
        // Distribute rewards (Red and Blue both win, 50/50 split)
        address[] memory winners = new address[](2);
        winners[0] = redToken;
        winners[1] = blueToken;
        
        uint256[] memory percentages = new uint256[](2);
        percentages[0] = 50;
        percentages[1] = 50;
        
        vm.prank(gameManager);
        prizePool.distributeRewards(gameId, winners, percentages);
        
        // Check rewards were sent to tokens
        assertEq(PersistentAgentToken(redToken).totalRewardsEarned(), 45 ether); // 50% of 90 MON
        assertEq(PersistentAgentToken(blueToken).totalRewardsEarned(), 45 ether);
    }
    
    function testClaimRewards() public {
        uint256 gameId = 1;
        
        // Create token
        vm.prank(gameManager);
        address redToken = registry.createAgentToken("Red", "detective");
        
        // Player1 gets 50% of tokens
        vm.prank(gameManager);
        PersistentAgentToken(redToken).transfer(player1, 500_000 * 10**18);
        
        // Deposit prize pool
        vm.deal(player2, 100 ether);
        vm.prank(player2);
        prizePool.deposit{value: 100 ether}(gameId);
        
        // Distribute rewards
        address[] memory winners = new address[](1);
        winners[0] = redToken;
        uint256[] memory percentages = new uint256[](1);
        percentages[0] = 100;
        
        vm.prank(gameManager);
        prizePool.distributeRewards(gameId, winners, percentages);
        
        // Player1 claims reward (should get 50% of 90 MON = 45 MON)
        uint256 balanceBefore = player1.balance;
        vm.prank(player1);
        prizePool.claimReward(gameId, redToken);
        uint256 balanceAfter = player1.balance;
        
        assertEq(balanceAfter - balanceBefore, 45 ether, "Should receive 45 MON");
        
        // Can't claim twice
        vm.prank(player1);
        vm.expectRevert("Already claimed");
        prizePool.claimReward(gameId, redToken);
    }
    
    function testStatsUpdate() public {
        vm.prank(gameManager);
        address tokenAddr = registry.createAgentToken("Yellow", "balanced");
        
        PersistentAgentToken token = PersistentAgentToken(tokenAddr);
        
        assertEq(token.gamesPlayed(), 0);
        assertEq(token.gamesWon(), 0);
        assertEq(token.winRate(), 0);
        
        // Play 3 games, win 2
        vm.startPrank(gameManager);
        token.updateStats(true);  // Win
        token.updateStats(false); // Loss
        token.updateStats(true);  // Win
        vm.stopPrank();
        
        assertEq(token.gamesPlayed(), 3);
        assertEq(token.gamesWon(), 2);
        assertEq(token.winRate(), 66); // 66%
    }
}
