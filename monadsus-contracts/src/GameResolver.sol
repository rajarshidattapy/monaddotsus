// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IGameRegistry {
    function finishGame(uint256 gameId) external;
}

interface IPredictionMarket{
    function resolveMarket(uint256 gameId,bool outcome) external;
}

contract GameResolver{
    address public owner;
    IGameRegistry public gameRegistry;
    IPredictionMarket public predictionMarket;

    constructor(address _gameRegistry,address _predictionMarket){
        owner = msg.sender;
        gameRegistry = IGameRegistry(_gameRegistry);
        predictionMarket = IPredictionMarket(_predictionMarket);
    }

    modifier onlyOwner(){
        require(msg.sender==owner,"Not Owner");
        _;
    }

    function resolveGame(
        uint256 gameId,
        uint256[] calldata marketIds,
        bool[] calldata outcomes
    ) external onlyOwner {
        require(marketIds.length == outcomes.length, "Length mismatch");

        gameRegistry.finishGame(gameId);

        for (uint256 i = 0; i < marketIds.length; i++) {
            predictionMarket.resolveMarket(marketIds[i], outcomes[i]);
        }
    }
}