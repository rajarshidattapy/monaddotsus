// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AgentRegistry{
    struct Agent{
        string name;
        uint256 gamesPlayed;
        uint256 wins;
    }
    uint256 public agentCount;
    mapping (uint256=>Agent) public  agents;

    event AgentCreated(uint256 agentId,string name);
    event AgentUpdated(uint256 agentId,bool won);

    function registerAgent(string calldata name) external {
        agentCount++;
        agents[agentCount] = Agent(name,0,0);
        emit AgentCreated(agentCount, name);
    }

    function updateAgent(uint256 agentId,bool won) external {
        Agent storage agent = agents[agentId];
        agent.gamesPlayed++;
        if(won){
            agent.wins++;
        }
        emit AgentUpdated(agentId, won);
    }
}