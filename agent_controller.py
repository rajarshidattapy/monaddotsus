"""
Agent Controller Module for MonadSus Autonomous Agent Mode.

Implements FR-2 (Agent Controller Interface) from AGENT.md PRD.
Each agent produces exactly one action per tick. Invalid actions are ignored safely.

Action Schema:
    {"type": "MOVE", "data": "UP"|"DOWN"|"LEFT"|"RIGHT"}
    {"type": "KILL", "data": target_colour}
    {"type": "VOTE", "data": target_colour | None}
    {"type": "SPEAK", "data": "string message"}
    {"type": "NONE"}
"""

import random


# ---------------------------------------------------------------------------
# Dialogue Templates (FR-3 from Dialogue PRD)
# ---------------------------------------------------------------------------

ACCUSATION_TEMPLATES = [
    "I think {target} is suspicious.",
    "I saw {target} acting weird near the body.",
    "{target} was following me... very sus.",
    "Vote {target}! I'm pretty sure it's them.",
    "Has anyone else noticed {target} lurking around?",
]

DEFENSE_TEMPLATES = [
    "I was just doing tasks, I swear!",
    "It's not me, I was nowhere near there.",
    "I've been in the other room the whole time.",
    "Why would I kill? Check my task progress!",
    "I'm innocent, you have to believe me.",
]

UNCERTAINTY_TEMPLATES = [
    "Not enough info, maybe we should skip.",
    "I'm not sure who it is...",
    "Could be anyone at this point.",
    "I didn't see anything useful.",
    "Let's not vote randomly, we might lose.",
]

OBSERVATION_TEMPLATES = [
    "I saw {target} near the body area.",
    "{target} was running away from the scene.",
    "I was with {safe} so it's not them.",
    "The body was found near {room}, anyone there?",
    "{target} has been quiet... too quiet.",
]

IMPOSTER_DEFLECT_TEMPLATES = [
    "I think it's {target}, they've been acting sus.",
    "Why is everyone looking at me? Check {target}!",
    "I saw {target} vent! ...wait, no, maybe not.",
    "{target} was near the body, not me!",
    "Let's focus on {target}, I have a bad feeling.",
]

ROOMS = ["Cafeteria", "Medbay", "Electrical", "Storage", "Admin", "Navigation", "Reactor"]


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
    - Speaks during dialogue phase, votes during voting phase
    """

    def __init__(self, agent_id, role="CREW"):
        self.agent_id = agent_id
        self.role = role
        self.current_direction = random.choice(["UP", "DOWN", "LEFT", "RIGHT"])
        self.direction_ticks = 0
        self.direction_duration = random.randint(30, 120)
        self.has_voted = False
        self.has_spoken = False
        self.vote_target = None  # Remember who we accused for consistent voting
        self.wall_stuck_counter = 0
        self.last_pos = None

    def _generate_dialogue(self, observation):
        """Generate a dialogue message based on role and observation (FR-3)."""
        alive = observation.get("alive_agents", [])
        dead = observation.get("dead_agents", [])
        
        # Pick a random target (someone to accuse or mention)
        candidates = [a for a in alive if a != self.agent_id]
        target = random.choice(candidates) if candidates else "someone"
        
        if self.role == "IMPOSTER":
            # Imposter deflects blame onto others
            if random.random() < 0.7:
                template = random.choice(IMPOSTER_DEFLECT_TEMPLATES)
            else:
                template = random.choice(DEFENSE_TEMPLATES)
            self.vote_target = target  # Vote for who we accused
        else:
            # Crew member: accuse, observe, or express uncertainty
            roll = random.random()
            if roll < 0.4:
                template = random.choice(ACCUSATION_TEMPLATES)
                self.vote_target = target
            elif roll < 0.6:
                template = random.choice(OBSERVATION_TEMPLATES)
                self.vote_target = target
            elif roll < 0.8:
                template = random.choice(UNCERTAINTY_TEMPLATES)
                self.vote_target = None  # Will skip
            else:
                template = random.choice(DEFENSE_TEMPLATES)
                self.vote_target = random.choice(candidates) if candidates else None
        
        # Fill in template placeholders
        safe = random.choice([a for a in alive if a != target and a != self.agent_id]) if len(alive) > 1 else self.agent_id
        room = random.choice(ROOMS)
        
        message = template.format(target=target, safe=safe, room=room)
        return message

    def get_action(self, observation):
        """Produce one action per tick based on observation."""

        # --- MEETING PHASES ---
        if observation.get("meeting_active", False):
            meeting_phase = observation.get("meeting_phase", "voting")
            
            # Dialogue phase: speak once
            if meeting_phase == "dialogue":
                if not self.has_spoken:
                    self.has_spoken = True
                    message = self._generate_dialogue(observation)
                    return {"type": "SPEAK", "data": message}
                return {"type": "NONE"}
            
            # Voting phase: vote once
            if meeting_phase == "voting":
                if not self.has_voted:
                    self.has_voted = True
                    # Use the target from dialogue, or pick randomly
                    if self.vote_target and self.vote_target in observation.get("alive_agents", []):
                        return {"type": "VOTE", "data": self.vote_target}
                    # Fallback: random vote
                    alive = observation.get("alive_agents", [])
                    candidates = [a for a in alive if a != self.agent_id]
                    candidates.append(None)  # skip option
                    return {"type": "VOTE", "data": random.choice(candidates)}
                return {"type": "NONE"}
            
            return {"type": "NONE"}

        # Reset flags when meeting ends
        self.has_voted = False
        self.has_spoken = False
        self.vote_target = None

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
        """Reset meeting state for a new meeting."""
        self.has_voted = False
        self.has_spoken = False
        self.vote_target = None
