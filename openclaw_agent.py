"""
OpenClaw Agent Controller for MonadSus.

Integrates LLM-powered decision making for autonomous agents.
Supports OpenAI, Anthropic, and local models via simple API calls.
"""

import os
import json
import random
from typing import Dict, Any, Optional
from agent_controller import AgentController

# Try importing LLM libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class OpenClawAgentController(AgentController):
    """
    LLM-powered agent controller using OpenClaw-style orchestration.
    
    Features:
    - Personality-driven decision making
    - Memory of past events
    - Strategic reasoning for Crew vs Imposter roles
    - Natural language dialogue generation
    """
    
    def __init__(self, agent_id: str, role: str = "CREW", personality_type: str = "balanced"):
        self.agent_id = agent_id
        self.role = role
        self.personality_type = personality_type
        
        # LLM configuration
        self.llm_provider = os.environ.get("LLM_PROVIDER", "openai")
        self.llm_model = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")
        
        # Memory system
        self.memory = []
        self.max_memory = 10
        
        # Load personality
        self.personality = self._load_personality(personality_type, role)
        
        # Decision caching (reduce API calls)
        self.last_action = {"type": "NONE"}
        self.action_cooldown = 0
        
        # Meeting state tracking (same as SimpleAgent)
        self.has_voted = False
        self.has_spoken = False
        
        print(f"  [OPENCLAW] Initialized {agent_id} as {role} with {personality_type} personality")
    
    def _load_personality(self, personality_type: str, role: str) -> Dict[str, str]:
        """Load personality traits from personality files or use defaults."""
        personality_dir = os.environ.get("AGENT_PERSONALITY_DIR", "./agent_personalities")
        personality_file = os.path.join(personality_dir, f"{role.lower()}_{personality_type}.md")
        
        # Try to load from file
        if os.path.exists(personality_file):
            with open(personality_file, 'r') as f:
                content = f.read()
                return {"description": content}
        
        # Default personalities
        if role == "IMPOSTER":
            if personality_type == "aggressive":
                return {
                    "description": "You are an aggressive imposter. Kill quickly and deflect suspicion boldly.",
                    "strategy": "Kill early, blame others confidently"
                }
            else:  # subtle
                return {
                    "description": "You are a subtle imposter. Act innocent, build trust, kill strategically.",
                    "strategy": "Blend in, kill when alone, act shocked at bodies"
                }
        else:  # CREW
            if personality_type == "detective":
                return {
                    "description": "You are analytical. Track movements, remember details, make logical deductions.",
                    "strategy": "Observe carefully, vote based on evidence"
                }
            elif personality_type == "follower":
                return {
                    "description": "You are cautious. Follow others' leads, avoid risky accusations.",
                    "strategy": "Vote with majority, stay safe"
                }
            else:  # balanced
                return {
                    "description": "You are balanced. Mix observation with intuition.",
                    "strategy": "Vote when confident, skip when uncertain"
                }
    
    def get_action(self, observation: Dict[str, Any]) -> Dict[str, str]:
        """
        Get action from LLM based on observation.
        Falls back to simple heuristics if LLM unavailable.
        """
        # Cooldown to reduce API calls
        if self.action_cooldown > 0:
            self.action_cooldown -= 1
            return self.last_action
        
        # Update memory
        self._update_memory(observation)
        
        # Get action based on meeting state
        if observation.get("meeting_active"):
            meeting_phase = observation.get("meeting_phase", "none")
            if meeting_phase == "dialogue":
                action = self._get_dialogue_action(observation)
            elif meeting_phase == "voting":
                action = self._get_vote_action(observation)
            else:
                action = {"type": "NONE"}
        else:
            # Normal gameplay
            action = self._get_gameplay_action(observation)
        
        # Cache action
        self.last_action = action
        self.action_cooldown = random.randint(5, 15)  # Wait 5-15 ticks
        
        return action
    
    def _update_memory(self, observation: Dict[str, Any]):
        """Update agent memory with recent events."""
        recent_events = observation.get("recent_events", [])
        for event in recent_events:
            if event not in self.memory:
                self.memory.append(event)
        
        # Keep only recent memory
        if len(self.memory) > self.max_memory:
            self.memory = self.memory[-self.max_memory:]
    
    def _get_gameplay_action(self, observation: Dict[str, Any]) -> Dict[str, str]:
        """Get action during normal gameplay (movement/killing)."""
        # Try LLM if available
        if self._can_use_llm():
            try:
                return self._query_llm_gameplay(observation)
            except Exception as e:
                # Log to file for debugging
                try:
                    with open("openclaw_errors.log", "a") as f:
                        f.write(f"[{self.agent_id}] Gameplay LLM error: {e}\n")
                except:
                    pass
                print(f"  [OPENCLAW] {self.agent_id} LLM error: {e}, falling back")
        
        # Fallback: Simple heuristics
        if self.role == "IMPOSTER" and observation.get("can_kill"):
            nearby = observation.get("nearby_agents", [])
            if nearby and random.random() > 0.5:
                target = random.choice(nearby)
                return {"type": "KILL", "data": target["agent"]}
        
        # Random movement
        return {"type": "MOVE", "data": random.choice(["UP", "DOWN", "LEFT", "RIGHT"])}
    
    def _get_dialogue_action(self, observation: Dict[str, Any]) -> Dict[str, str]:
        """Generate dialogue during meeting."""
        # Try LLM if available
        if self._can_use_llm():
            try:
                return self._query_llm_dialogue(observation)
            except Exception as e:
                try:
                    with open("openclaw_errors.log", "a") as f:
                        f.write(f"[{self.agent_id}] Dialogue LLM error: {e}\n")
                except:
                    pass
                print(f"  [OPENCLAW] {self.agent_id} LLM error: {e}, falling back")
        
        # Fallback: Template-based dialogue
        alive = observation.get("alive_agents", [])
        if not alive:
            return {"type": "SPEAK", "data": "I don't know who it is..."}
        
        if self.role == "IMPOSTER":
            target = random.choice(alive)
            return {"type": "SPEAK", "data": f"I think {target} is suspicious!"}
        else:
            if random.random() > 0.5:
                target = random.choice(alive)
                return {"type": "SPEAK", "data": f"I saw {target} acting weird."}
            else:
                return {"type": "SPEAK", "data": "Not sure, maybe we should skip."}
    
    def _get_vote_action(self, observation: Dict[str, Any]) -> Dict[str, str]:
        """Decide who to vote for."""
        # Try LLM if available
        if self._can_use_llm():
            try:
                return self._query_llm_vote(observation)
            except Exception as e:
                try:
                    with open("openclaw_errors.log", "a") as f:
                        f.write(f"[{self.agent_id}] Vote LLM error: {e}\n")
                except:
                    pass
                print(f"  [OPENCLAW] {self.agent_id} LLM error: {e}, falling back")
        
        # Fallback: Random vote or skip
        alive = observation.get("alive_agents", [])
        if alive and random.random() > 0.3:
            target = random.choice(alive)
            return {"type": "VOTE", "data": target}
        else:
            return {"type": "VOTE", "data": None}  # Skip
    
    def _can_use_llm(self) -> bool:
        """Check if LLM is available and configured."""
        if self.llm_provider == "openai":
            return OPENAI_AVAILABLE and os.environ.get("OPENAI_API_KEY")
        elif self.llm_provider == "anthropic":
            return ANTHROPIC_AVAILABLE and os.environ.get("ANTHROPIC_API_KEY")
        elif self.llm_provider == "local":
            return REQUESTS_AVAILABLE and os.environ.get("OLLAMA_URL")
        return False
    
    def _query_llm_gameplay(self, observation: Dict[str, Any]) -> Dict[str, str]:
        """Query LLM for gameplay decision."""
        prompt = self._build_gameplay_prompt(observation)
        response = self._call_llm(prompt)
        return self._parse_llm_response(response, "gameplay")
    
    def _query_llm_dialogue(self, observation: Dict[str, Any]) -> Dict[str, str]:
        """Query LLM for dialogue."""
        prompt = self._build_dialogue_prompt(observation)
        response = self._call_llm(prompt)
        return self._parse_llm_response(response, "dialogue")
    
    def _query_llm_vote(self, observation: Dict[str, Any]) -> Dict[str, str]:
        """Query LLM for vote decision."""
        prompt = self._build_vote_prompt(observation)
        response = self._call_llm(prompt)
        return self._parse_llm_response(response, "vote")
    
    def _build_gameplay_prompt(self, observation: Dict[str, Any]) -> str:
        """Build prompt for gameplay decision."""
        prompt = f"""You are {self.agent_id}, a {self.role} in Among Us.
{self.personality['description']}

Current situation:
- Nearby agents: {observation.get('nearby_agents', [])}
- Alive agents: {observation.get('alive_agents', [])}
- Dead agents: {observation.get('dead_agents', [])}
- Can kill: {observation.get('can_kill', False)}

Recent events: {', '.join(self.memory[-3:])}

What do you do? Respond with ONE of:
- MOVE UP/DOWN/LEFT/RIGHT
- KILL <agent_name> (if you're imposter and can kill)
- NONE (do nothing)

Your action:"""
        return prompt
    
    def _build_dialogue_prompt(self, observation: Dict[str, Any]) -> str:
        """Build prompt for dialogue."""
        dialogue_history = observation.get('dialogue_history', [])
        
        prompt = f"""You are {self.agent_id}, a {self.role} in Among Us.
{self.personality['description']}

Meeting called! Recent dialogue:
{self._format_dialogue(dialogue_history)}

Alive: {observation.get('alive_agents', [])}
Dead: {observation.get('dead_agents', [])}
Your memory: {', '.join(self.memory[-3:])}

What do you say? (Keep it under 100 characters, be natural)

Your message:"""
        return prompt
    
    def _build_vote_prompt(self, observation: Dict[str, Any]) -> str:
        """Build prompt for voting."""
        dialogue_history = observation.get('dialogue_history', [])
        votes_so_far = observation.get('votes_so_far', {})
        
        prompt = f"""You are {self.agent_id}, a {self.role} in Among Us.
{self.personality['description']}

Voting time! Dialogue summary:
{self._format_dialogue(dialogue_history[-5:])}

Current votes: {votes_so_far}
Alive: {observation.get('alive_agents', [])}

Who do you vote for? Respond with:
- VOTE <agent_name>
- SKIP (vote to skip)

Your vote:"""
        return prompt
    
    def _format_dialogue(self, dialogue_history):
        """Format dialogue history for prompt."""
        if not dialogue_history:
            return "No dialogue yet."
        return "\n".join([f"{agent}: {msg}" for agent, msg in dialogue_history[-5:]])
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM API."""
        if self.llm_provider == "openai":
            return self._call_openai(prompt)
        elif self.llm_provider == "anthropic":
            return self._call_anthropic(prompt)
        elif self.llm_provider == "local":
            return self._call_ollama(prompt)
        raise ValueError(f"Unknown LLM provider: {self.llm_provider}")
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=self.llm_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=self.llm_model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    
    def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama API."""
        url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        response = requests.post(url, json={
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False
        })
        return response.json()["response"].strip()
    
    def _parse_llm_response(self, response: str, action_type: str) -> Dict[str, str]:
        """Parse LLM response into action dict."""
        response = response.upper().strip()
        
        if action_type == "gameplay":
            if "MOVE" in response:
                for direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
                    if direction in response:
                        return {"type": "MOVE", "data": direction}
            elif "KILL" in response:
                # Extract target name
                words = response.split()
                if len(words) >= 2:
                    target = words[1].strip()
                    return {"type": "KILL", "data": target}
            return {"type": "NONE"}
        
        elif action_type == "dialogue":
            # Return the message as-is
            message = response.replace("YOUR MESSAGE:", "").strip()
            return {"type": "SPEAK", "data": message[:200]}  # Limit length
        
        elif action_type == "vote":
            if "SKIP" in response:
                return {"type": "VOTE", "data": None}
            elif "VOTE" in response:
                words = response.split()
                if len(words) >= 2:
                    target = words[1].strip()
                    return {"type": "VOTE", "data": target}
            return {"type": "VOTE", "data": None}
        
        return {"type": "NONE"}
