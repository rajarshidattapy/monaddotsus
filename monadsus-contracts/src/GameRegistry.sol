// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract GameRegistry{
    enum GameStatus {
        CREATED,
        RUNNING,
        FINISHED
    }

    struct Game{
        uint256 id;
        bytes32 gameHash;
        GameStatus status;
        address resolver;
    }

    mapping(uint256 => Game) public games;
    uint256 public gameCount;

    function createGame(bytes32 gameHash) external {
        gameCount++;
        games[gameCount]=Game({
            id: gameCount,
            gameHash: gameHash,
            status: GameStatus.CREATED,
            resolver: msg.sender
        });
    }

    function startGame(uint256 gameId) external {
        Game storage game = games[gameId];
        require(game.status==GameStatus.CREATED,"Game not in created state");
        require(msg.sender==game.resolver,"Not resolver");
        game.status= GameStatus.RUNNING;
    }

    function finishGame(uint256 gameId) external {
        Game storage game = games[gameId];
        require(game.status==GameStatus.RUNNING,"Game not running");
        require(msg.sender==game.resolver,"Not resolver");
        game.status=GameStatus.FINISHED;
    }
}