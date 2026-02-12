"""
Agent Controller Module for MonadSus Autonomous Agent Mode.

Implements FR-2 (Agent Controller Interface) from AGENT.md PRD.
Each agent produces exactly one action per tick. Invalid actions are ignored safely.

Action Schema:
    {"type": "MOVE", "data": "UP"|"DOWN"|"LEFT"|"RIGHT"}
    {"type": "KILL", "data": target_colour}
    {"type": "VOTE", "data": target_colour | None}
    {"type": "NONE"}
"""

import random


class AgentController:
    """Base class for agent controllers."""

    def get_action(self, observation):
        """
        Given an observation dict, return an action dict.

        Observation:
            position: (x, y)
            nearby_agents: [colour, ...]     agents within kill range
            alive_agents: [colour, ...]      all alive agents except self
            role: "IMPOSTER" | "CREW"
            meeting_active: bool
            can_kill: bool                   imposter + cooldown ready + not in meeting
        """
        raise NotImplementedError


class SimpleAgent(AgentController):
    """
    Random / heuristic agent for hackathon demo (FR-3, FR-4, FR-6).

    - Moves randomly, changing direction every 30-120 ticks
    - Detects walls (stuck detection) and changes direction
    - Imposter kills nearby agents with 50% chance when cooldown ready
    - Votes randomly among alive agents (or skip) during meetings
    """

    def __init__(self, agent_id, role="CREW"):
        self.agent_id = agent_id
        self.role = role
        self.current_direction = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])
        self.direction_ticks = 0
        self.direction_duration = random.randint(30, 120)
        self.has_voted = False
        self.wall_stuck_counter = 0
        self.last_pos = None

    def get_action(self, observation):
        """Produce one action per tick based on observation."""

        # --- MEETING: vote once, then idle ---
        if observation.get("meeting_active", False):
            if not self.has_voted:
                self.has_voted = True
                alive = observation.get("alive_agents", [])
                # Vote for someone other than self, or skip (None)
                candidates = [a for a in alive if a != self.agent_id]
                candidates.append(None)  # skip vote option
                return {"type": "VOTE", "data": random.choice(candidates)}
            return {"type": "NONE"}

        # Reset vote flag when meeting ends
        self.has_voted = False

        # --- STUCK DETECTION: change direction if not moving ---
        current_pos = observation.get("position", (0, 0))
        if self.last_pos is not None:
            dx = abs(current_pos[0] - self.last_pos[0])
            dy = abs(current_pos[1] - self.last_pos[1])
            if dx < 1 and dy < 1:
                self.wall_stuck_counter += 1
            else:
                self.wall_stuck_counter = 0
        self.last_pos = current_pos

        # Force direction change when stuck against wall
        if self.wall_stuck_counter > 10:
            self.wall_stuck_counter = 0
            self.current_direction = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])
            self.direction_duration = random.randint(20, 60)
            self.direction_ticks = 0

        # --- IMPOSTER: try to kill nearby agents ---
        if self.role == "IMPOSTER" and observation.get("can_kill", False):
            nearby = observation.get("nearby_agents", [])
            if nearby and random.random() < 0.5:
                return {"type": "KILL", "data": random.choice(nearby)}

        # --- MOVEMENT: random walk with periodic direction changes ---
        self.direction_ticks += 1
        if self.direction_ticks >= self.direction_duration:
            self.current_direction = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])
            self.direction_duration = random.randint(30, 120)
            self.direction_ticks = 0

        return {"type": "MOVE", "data": self.current_direction}

    def reset_vote(self):
        """Reset vote state for a new meeting."""
        self.has_voted = False
