// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract PredictionMarket {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    struct Market {
        uint256 gameId;
        string question;
        uint256 yesPool;
        uint256 noPool;
        bool resolved;
        bool outcome; // true = YES wins
    }

    uint256 public marketCount;
    mapping(uint256 => Market) public markets;

    // marketId => user => amount
    mapping(uint256 => mapping(address => uint256)) public yesBets;
    mapping(uint256 => mapping(address => uint256)) public noBets;

    event MarketCreated(uint256 marketId, uint256 gameId, string question);
    event BetPlaced(uint256 marketId, bool yes, uint256 amount);
    event MarketResolved(uint256 marketId, bool outcome);
    event RewardClaimed(uint256 marketId, address user, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function createMarket(uint256 gameId, string calldata question) external onlyOwner {
        marketCount++;
        markets[marketCount] = Market({
            gameId: gameId,
            question: question,
            yesPool: 0,
            noPool: 0,
            resolved: false,
            outcome: false
        });

        emit MarketCreated(marketCount, gameId, question);
    }

    function betYes(uint256 marketId) external payable {
        Market storage market = markets[marketId];
        require(!market.resolved, "Market resolved");
        require(msg.value > 0, "No value");

        yesBets[marketId][msg.sender] += msg.value;
        market.yesPool += msg.value;

        emit BetPlaced(marketId, true, msg.value);
    }

    function betNo(uint256 marketId) external payable {
        Market storage market = markets[marketId];
        require(!market.resolved, "Market resolved");
        require(msg.value > 0, "No value");

        noBets[marketId][msg.sender] += msg.value;
        market.noPool += msg.value;

        emit BetPlaced(marketId, false, msg.value);
    }

    function resolveMarket(uint256 marketId, bool outcome) external onlyOwner {
        Market storage market = markets[marketId];
        require(!market.resolved, "Already resolved");

        market.resolved = true;
        market.outcome = outcome;

        emit MarketResolved(marketId, outcome);
    }

    function claim(uint256 marketId) external {
        Market storage market = markets[marketId];
        require(market.resolved, "Not resolved");

        uint256 userBet;
        uint256 payout;

        if (market.outcome) {
            userBet = yesBets[marketId][msg.sender];
            require(userBet > 0, "No YES bet");

            payout = (userBet * (market.yesPool + market.noPool)) / market.yesPool;
            yesBets[marketId][msg.sender] = 0;
        } else {
            userBet = noBets[marketId][msg.sender];
            require(userBet > 0, "No NO bet");

            payout = (userBet * (market.yesPool + market.noPool)) / market.noPool;
            noBets[marketId][msg.sender] = 0;
        }

        (bool success, ) = payable(msg.sender).call{value: payout}("");
        require(success, "Transfer failed");
    }
}
