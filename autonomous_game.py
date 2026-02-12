"""
Autonomous Agent Game Mode for MonadSus.

Runs a full match where every player is an autonomous AI agent.
No keyboard or mouse input is used for gameplay.
Humans are spectators only — they can switch camera views.

Implements all Functional Requirements from AGENT.md:
  FR-1: Replace human input with agent actions
  FR-2: Agent controller interface
  FR-3: Agent movement (random walk)
  FR-4: Imposter kill logic
  FR-5: Meeting trigger (body detection + timer fallback)
  FR-6: Voting logic
  FR-7: Game end conditions
"""
from __future__ import annotations

import random
import math
import pygame as pg
import sys
from os import path

from game import Game
from sprites import Player, Bot
from settings import *
from agent_controller import SimpleAgent


# ---------------------------------------------------------------------------
# Color-to-sprite lookup (avoids eval)
# ---------------------------------------------------------------------------

def build_color_sprites():
    """Build dict mapping colour name -> directional sprite arrays."""
    return {
        "Red":    {"left": red_player_imgs_left,    "right": red_player_imgs_right,    "up": red_player_imgs_up,    "down": red_player_imgs_down,    "dead": red_player_imgs_dead},
        "Blue":   {"left": blue_player_imgs_left,   "right": blue_player_imgs_right,   "up": blue_player_imgs_up,   "down": blue_player_imgs_down,   "dead": blue_player_imgs_dead},
        "Green":  {"left": green_player_imgs_left,  "right": green_player_imgs_right,  "up": green_player_imgs_up,  "down": green_player_imgs_down,  "dead": green_player_imgs_dead},
        "Orange": {"left": orange_player_imgs_left, "right": orange_player_imgs_right, "up": orange_player_imgs_up, "down": orange_player_imgs_down, "dead": orange_player_imgs_dead},
        "Yellow": {"left": yellow_player_imgs_left, "right": yellow_player_imgs_right, "up": yellow_player_imgs_up, "down": yellow_player_imgs_down, "dead": yellow_player_imgs_dead},
        "Black":  {"left": black_player_imgs_left,  "right": black_player_imgs_right,  "up": black_player_imgs_up,  "down": black_player_imgs_down,  "dead": black_player_imgs_dead},
        "Brown":  {"left": brown_player_imgs_left,  "right": brown_player_imgs_right,  "up": brown_player_imgs_up,  "down": brown_player_imgs_down,  "dead": brown_player_imgs_dead},
        "Pink":   {"left": pink_player_imgs_left,   "right": pink_player_imgs_right,   "up": pink_player_imgs_up,   "down": pink_player_imgs_down,   "dead": pink_player_imgs_dead},
        "Purple": {"left": purple_player_imgs_left, "right": purple_player_imgs_right, "up": purple_player_imgs_up, "down": purple_player_imgs_down, "dead": purple_player_imgs_dead},
        "White":  {"left": white_player_imgs_left,  "right": white_player_imgs_right,  "up": white_player_imgs_up,  "down": white_player_imgs_down,  "dead": white_player_imgs_dead},
    }


# Display-color mapping for HUD text
COLOR_MAP = {
    "Red": (255, 60, 60), "Blue": (60, 120, 255), "Green": (60, 220, 60),
    "Orange": (255, 165, 0), "Yellow": (255, 255, 80), "Black": (160, 160, 160),
    "Brown": (180, 110, 50), "Pink": (255, 130, 200), "Purple": (180, 80, 220),
    "White": (230, 230, 230),
}

vec = pg.math.Vector2


# ---------------------------------------------------------------------------
# AutonomousGame
# ---------------------------------------------------------------------------

class AutonomousGame:
    """Runs a fully autonomous Among Us match with AI agents."""

    # Tunable constants
    KILL_RANGE            = 120     # px — distance for imposter kill
    BODY_DETECT_RANGE     = 200     # px — crew can spot a dead body
    KILL_COOLDOWN         = 600     # ticks (10 s @ 60 fps)
    MEETING_COOLDOWN      = 900     # ticks (15 s)
    MEETING_ALERT_TICKS   = 90      # ticks (1.5 s) — "EMERGENCY" splash
    MEETING_DIALOGUE_TICKS = 360    # ticks (6 s) — dialogue window
    MEETING_VOTE_TICKS    = 600     # ticks (10 s) — vote window
    EJECT_TICKS           = 180     # ticks (3 s) — ejection screen
    MAX_GAME_TICKS        = 36000   # ticks (10 min)
    AUTO_MEETING_INTERVAL = 7200    # ticks (2 min) — fallback meeting

    def __init__(self):
        self.color_sprites = build_color_sprites()
        self.game = Game()

        # Agent / entity maps
        self.agents = {}          # colour → SimpleAgent
        self.entities = {}        # colour → sprite
        self.all_colours = []
        self.imposter_colour = None

        # Runtime state
        self.dead_bodies = []     # [(x, y, colour)]
        self.kill_cooldown = 0
        self.meeting_cooldown = 0
        self.ticks_since_meeting = 0

        # Meeting state
        self.meeting_active = False
        self.meeting_phase = 0    # 0=alert, 1=dialogue, 2=vote
        self.meeting_timer = 0
        self.meeting_trigger_colour = None
        self.votes = {}
        
        # Dialogue state (FR-1 to FR-6 from Dialogue PRD)
        self.dialogue_order: list[str] = []        # shuffled order of speakers
        self.dialogue_messages: list[tuple[str, str]] = []  # [(colour, message), ...]
        self.spoken_agents: set[str] = set()       # agents who have spoken
        self.current_speaker_idx = 0               # index into dialogue_order
        self.dialogue_ticks_per_agent = 60         # ticks to display each message

        # Eject state
        self.eject_active = False
        self.eject_timer = 0
        self.ejected_colour = None

        # Outcome
        self.tick = 0
        self.game_over = False
        self.winner = None        # "CREW" | "IMPOSTER"

        # Camera
        self.camera_target_idx = 0

        # HUD (assigned in setup())
        self.hud_font: pg.font.Font | None = None
        self.hud_font_sm: pg.font.Font | None = None
        self.hud_font_lg: pg.font.Font | None = None
        self.dim_screen: pg.Surface | None = None
        self.event_log: list[str] = []

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup(self):
        """Initialise game world and assign agents."""
        # Set attributes dynamically (Game class sets these externally)
        setattr(self.game, 'player_colour', "Red")
        setattr(self.game, 'gamemode', "Freeplay")
        self.game.new()                      # builds map, obstacles, bots

        # Create camera-target player, mark autonomous
        self.game.player = Player(
            self.game,
            random.choice(self.game.player_pos),
            0, True, "Red",
        )
        self.game.player.autonomous = True
        self.game.playing = True
        self.game.imposter_among_us_status = False

        # Remove bot whose colour matches the player entity
        player_colour = getattr(self.game, 'player_colour', 'Red')
        for b in list(self.game.bots):
            if b.bot_colour == player_colour:
                b.kill()
                break

        # Register entities
        bot_list = list(self.game.bots)
        self.entities["Red"] = self.game.player
        for bot in bot_list:
            self.entities[bot.bot_colour] = bot
            # Attach directional sprite arrays to bots (same as Player has)
            sp = self.color_sprites.get(bot.bot_colour, {})
            bot.player_imgs_left  = sp.get("left",  [bot.image])
            bot.player_imgs_right = sp.get("right", [bot.image])
            bot.player_imgs_up    = sp.get("up",    [bot.image])
            bot.player_imgs_down  = sp.get("down",  [bot.image])
            bot.left_img_index = 0
            bot.right_img_index = 0
            bot.up_img_index = 0
            bot.down_img_index = 0

        self.all_colours = ["Red"] + [b.bot_colour for b in bot_list]

        # Pick random imposter
        self.imposter_colour = random.choice(self.all_colours)

        # Create agent controllers
        for colour in self.all_colours:
            role = "IMPOSTER" if colour == self.imposter_colour else "CREW"
            self.agents[colour] = SimpleAgent(agent_id=colour, role=role)
            self.entities[colour].imposter = (role == "IMPOSTER")

        # Camera starts following the imposter
        self.camera_target_idx = self.all_colours.index(self.imposter_colour)

        # Fonts & overlay surface
        self.hud_font    = pg.font.Font(FONT, 22)
        self.hud_font_sm = pg.font.Font(FONT, 16)
        self.hud_font_lg = pg.font.Font(FONT, 42)
        self.dim_screen  = pg.Surface(self.game.screen.get_size(), pg.SRCALPHA)
        self.dim_screen.fill((0, 0, 0, 180))

        # Background music
        pg.mixer.music.play(-1)
        pg.mixer.music.set_volume(0.5)

        self._log(f"Match started — {len(self.all_colours)} agents")
        self._log(f"Imposter: {self.imposter_colour}")

        print(f"\n{'=' * 60}")
        print(f"  MONADSUS — AUTONOMOUS AGENT MODE")
        print(f"{'=' * 60}")
        print(f"  Agents : {', '.join(self.all_colours)}")
        print(f"  Imposter: {self.imposter_colour}")
        print(f"  Controls: TAB = cycle camera | 1-9 = pick agent | ESC = quit")
        print(f"{'=' * 60}\n")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, msg):
        self.event_log.append(msg)
        if len(self.event_log) > 6:
            self.event_log.pop(0)
        print(f"  [{self.tick // 60:>3}s] {msg}")

    def _log_dialogue(self, agent_id, message):
        """Log a dialogue event (FR-6 from Dialogue PRD)."""
        # Console output
        print(f"  [{self.tick // 60:>3}s] [{agent_id}]: {message}")
        # Structured event (could be extended to file/JSON logging)
        # Format: {"t": timestamp, "type": "SPEAK", "agent_id": agent_id, "message": message}

    def alive_colours(self):
        return [c for c in self.all_colours if self.entities[c].alive_status]

    def _dist(self, a, b):
        return math.hypot(a.pos.x - b.pos.x, a.pos.y - b.pos.y)

    # ------------------------------------------------------------------
    # Observation builder (FR-6)
    # ------------------------------------------------------------------

    def _observation(self, colour):
        ent = self.entities[colour]
        alive = self.alive_colours()
        dead = [c for c in self.all_colours if not self.entities[c].alive_status]
        nearby = []
        for oc in alive:
            if oc == colour:
                continue
            if self._dist(ent, self.entities[oc]) <= self.KILL_RANGE:
                nearby.append(oc)
        
        # Determine meeting phase name for agents
        phase_name = "none"
        if self.meeting_active:
            if self.meeting_phase == 1:
                phase_name = "dialogue"
            elif self.meeting_phase == 2:
                phase_name = "voting"

        return {
            "position":       (ent.pos.x, ent.pos.y),
            "nearby_agents":  nearby,
            "alive_agents":   [c for c in alive if c != colour],
            "dead_agents":    dead,
            "role":           self.agents[colour].role,
            "meeting_active": self.meeting_active,
            "meeting_phase":  phase_name,
            "can_kill":       (
                self.agents[colour].role == "IMPOSTER"
                and self.kill_cooldown <= 0
                and not self.meeting_active
                and ent.alive_status
            ),
        }

    # ------------------------------------------------------------------
    # Movement (FR-3)
    # ------------------------------------------------------------------

    def _apply_move(self, colour, direction):
        ent = self.entities[colour]
        ent.vel = vec(0, 0)
        imgs, attr = None, None

        if direction == "LEFT":
            ent.vel.x = -PLAYER_SPEED
            imgs = ent.player_imgs_left
            attr = "left_img_index"
        elif direction == "RIGHT":
            ent.vel.x = PLAYER_SPEED
            imgs = ent.player_imgs_right
            attr = "right_img_index"
        elif direction == "UP":
            ent.vel.y = -PLAYER_SPEED
            imgs = ent.player_imgs_up
            attr = "up_img_index"
        elif direction == "DOWN":
            ent.vel.y = PLAYER_SPEED
            imgs = ent.player_imgs_down
            attr = "down_img_index"

        if imgs and attr:
            idx = getattr(ent, attr, 0)
            ent.image = imgs[idx % len(imgs)]
            setattr(ent, attr, (idx + 1) % len(imgs))

    # ------------------------------------------------------------------
    # Kill logic (FR-4)
    # ------------------------------------------------------------------

    def _try_kill(self, killer_c, victim_c):
        killer = self.entities[killer_c]
        victim = self.entities[victim_c]

        if (not victim.alive_status or not killer.alive_status
                or self.agents[killer_c].role != "IMPOSTER"
                or self.kill_cooldown > 0):
            return False
        if self._dist(killer, victim) > self.KILL_RANGE:
            return False

        # Kill succeeds
        victim.alive_status = False
        
        # Use the entity's own dead image if available
        # Player class uses `image_dead`, Bot class uses `dead_player_img`
        if hasattr(victim, 'image_dead') and victim.image_dead is not None:
            victim.image = victim.image_dead
        elif hasattr(victim, 'dead_player_img') and victim.dead_player_img is not None:
            victim.image = victim.dead_player_img
        else:
            dead_img = self.color_sprites.get(victim_c, {}).get("dead")
            if dead_img is not None:
                victim.image = dead_img.convert_alpha()
        
        victim.vel = vec(0, 0)
        self.dead_bodies.append((victim.pos.x, victim.pos.y, victim_c))
        self.kill_cooldown = self.KILL_COOLDOWN

        try:
            self.game.effect_sounds['imposter_kill_sound'].play()
        except Exception:
            pass

        self._log(f"{killer_c} killed {victim_c}!")
        return True

    # ------------------------------------------------------------------
    # Meeting logic (FR-5 / FR-6)
    # ------------------------------------------------------------------

    def _start_meeting(self, trigger_colour):
        if self.meeting_active or self.meeting_cooldown > 0:
            return
        self.meeting_active = True
        self.meeting_phase = 0
        self.meeting_timer = 0
        self.meeting_trigger_colour = trigger_colour
        self.votes = {}
        
        # Initialize dialogue state (FR-4: shuffled order)
        self.dialogue_order = self.alive_colours()
        random.shuffle(self.dialogue_order)
        self.dialogue_messages = []
        self.spoken_agents = set()
        self.current_speaker_idx = 0
        
        for agent in self.agents.values():
            agent.reset_vote()
        for c in self.all_colours:
            self.entities[c].vel = vec(0, 0)

        try:
            if self.dead_bodies:
                self.game.effect_sounds['dead_body_found'].play()
            else:
                self.game.effect_sounds['emergency_alarm'].play()
        except Exception:
            pass

        self._log(f"Meeting called by {trigger_colour}!")

    def _process_votes(self):
        """Return colour to eject (or None for skip / tie)."""
        counts = {}
        skips = 0
        for _, voted in self.votes.items():
            if voted is None:
                skips += 1
            else:
                counts[voted] = counts.get(voted, 0) + 1
        if not counts:
            return None

        max_votes = max(counts.values())
        top = [c for c, v in counts.items() if v == max_votes]
        if len(top) == 1 and max_votes > skips:
            return top[0]
        return None

    def _end_meeting(self):
        ejected = self._process_votes()

        summary = ", ".join(
            f"{v}->{'skip' if t is None else t}" for v, t in self.votes.items()
        )
        self._log(f"Votes: {summary}")

        if ejected:
            self.eject_active = True
            self.eject_timer = 0
            self.ejected_colour = ejected
            self.entities[ejected].alive_status = False
            self.entities[ejected].vel = vec(0, 0)
            imp = self.agents[ejected].role == "IMPOSTER"
            self._log(
                f"{ejected} was ejected! "
                + ("They were the Imposter!" if imp else "They were NOT the Imposter.")
            )
        else:
            self._log("No one was ejected (tie or skip).")

        # Clear reported bodies & respawn alive agents to spawn points
        self.dead_bodies.clear()
        alive = self.alive_colours()
        for i, c in enumerate(alive):
            self.entities[c].pos = vec(
                self.game.player_pos[i % len(self.game.player_pos)]
            )

        self.meeting_active = False
        self.meeting_cooldown = self.MEETING_COOLDOWN
        self.ticks_since_meeting = 0

    # ------------------------------------------------------------------
    # Body detection (FR-5)
    # ------------------------------------------------------------------

    def _check_body_detection(self):
        if not self.dead_bodies or self.meeting_active or self.meeting_cooldown > 0:
            return
        for c in self.alive_colours():
            if self.agents[c].role == "IMPOSTER":
                continue
            ent = self.entities[c]
            for bx, by, _ in self.dead_bodies:
                if math.hypot(ent.pos.x - bx, ent.pos.y - by) <= self.BODY_DETECT_RANGE:
                    self._start_meeting(c)
                    return

    # ------------------------------------------------------------------
    # Win conditions (FR-7)
    # ------------------------------------------------------------------

    def _check_win(self):
        alive = self.alive_colours()
        crew   = [c for c in alive if self.agents[c].role == "CREW"]
        imps   = [c for c in alive if self.agents[c].role == "IMPOSTER"]

        if not imps:
            self.game_over = True
            self.winner = "CREW"
            self._log("CREW WINS — the imposter was eliminated!")
            return True
        if len(imps) >= len(crew):
            self.game_over = True
            self.winner = "IMPOSTER"
            self._log("IMPOSTER WINS — crew is outnumbered!")
            return True
        return False

    # ------------------------------------------------------------------
    # Event handling (spectator controls only)
    # ------------------------------------------------------------------

    def _handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type != pg.KEYDOWN:
                continue
            if event.key == pg.K_ESCAPE:
                pg.quit()
                sys.exit()
            # Number keys 1-9 to pick camera target
            if pg.K_1 <= event.key <= pg.K_9:
                idx = event.key - pg.K_1
                if idx < len(self.all_colours):
                    self.camera_target_idx = idx
            if event.key == pg.K_0 and len(self.all_colours) > 9:
                self.camera_target_idx = 9
            # TAB cycles through alive agents
            if event.key == pg.K_TAB:
                alive = self.alive_colours()
                if alive:
                    cur = self.all_colours[self.camera_target_idx % len(self.all_colours)]
                    try:
                        ni = (alive.index(cur) + 1) % len(alive)
                    except ValueError:
                        ni = 0
                    self.camera_target_idx = self.all_colours.index(alive[ni])

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _camera_target(self):
        idx = self.camera_target_idx % len(self.all_colours)
        return self.entities[self.all_colours[idx]]

    def _draw(self):
        assert self.hud_font_sm  # Initialized in setup()
        screen = self.game.screen
        cam = self.game.camera

        # Camera follows selected entity
        cam.update(self._camera_target())

        # Map
        screen.blit(self.game.map_img, cam.apply_rect(self.game.map_rect))

        # Sprites
        for sprite in self.game.all_sprites:
            screen.blit(sprite.image, cam.apply(sprite))

        # Name tags above each alive agent
        for c in self.all_colours:
            ent = self.entities[c]
            if not ent.alive_status:
                continue
            tag = self.hud_font_sm.render(c, True, COLOR_MAP.get(c, WHITE))
            tag_rect = tag.get_rect(centerx=cam.apply(ent).centerx, bottom=cam.apply(ent).top - 2)
            screen.blit(tag, tag_rect)

        # HUD overlay
        self._draw_hud(screen)

        # Meeting overlay
        if self.meeting_active:
            self._draw_meeting(screen)

        # Eject overlay
        if self.eject_active:
            self._draw_eject(screen)

        # Game-over overlay
        if self.game_over:
            self._draw_game_over(screen)

        pg.display.flip()

    # ---- HUD ----

    def _draw_hud(self, screen):
        assert self.hud_font and self.hud_font_sm and self.hud_font_lg  # Initialized in setup()
        alive = self.alive_colours()

        # Status panel (top-left)
        panel = pg.Surface((360, 125), pg.SRCALPHA)
        panel.fill((0, 0, 0, 160))
        screen.blit(panel, (10, 10))

        screen.blit(self.hud_font.render("AUTONOMOUS AGENT MODE", True, (255, 200, 50)), (20, 15))

        screen.blit(self.hud_font_sm.render(
            f"Alive: {len(alive)}/{len(self.all_colours)}", True, WHITE), (20, 45))

        secs = self.tick // 60
        screen.blit(self.hud_font_sm.render(
            f"Time: {secs // 60}:{secs % 60:02d}", True, WHITE), (200, 45))

        target_c = self.all_colours[self.camera_target_idx % len(self.all_colours)]
        role = self.agents[target_c].role
        clr = (255, 80, 80) if role == "IMPOSTER" else (100, 255, 100)
        screen.blit(self.hud_font_sm.render(
            f"Following: {target_c} ({role})", True, clr), (20, 70))

        if role == "IMPOSTER" and self.kill_cooldown > 0:
            screen.blit(self.hud_font_sm.render(
                f"Kill CD: {self.kill_cooldown // 60}s", True, (255, 100, 100)), (20, 93))

        screen.blit(self.hud_font_sm.render(
            "TAB=cycle camera  ESC=quit", True, (150, 150, 150)), (20, 110))

        # Agent roster (top-right)
        roster = pg.Surface((170, 22 * len(self.all_colours) + 10), pg.SRCALPHA)
        roster.fill((0, 0, 0, 140))
        screen.blit(roster, (WIDTH - 180, 10))
        for i, c in enumerate(self.all_colours):
            is_alive = self.entities[c].alive_status
            tc = COLOR_MAP.get(c, WHITE) if is_alive else (80, 80, 80)
            label = c + ("" if is_alive else " [DEAD]")
            if c == self.imposter_colour:
                label += " *"   # spectator hint
            screen.blit(self.hud_font_sm.render(label, True, tc), (WIDTH - 175, 15 + i * 22))

        # Event log (bottom)
        if self.event_log:
            log_h = 20 * min(len(self.event_log), 6) + 10
            log_bg = pg.Surface((550, log_h), pg.SRCALPHA)
            log_bg.fill((0, 0, 0, 140))
            y0 = HEIGHT - log_h - 10
            screen.blit(log_bg, (10, y0))
            for i, msg in enumerate(self.event_log[-6:]):
                screen.blit(self.hud_font_sm.render(msg, True, (220, 220, 220)), (15, y0 + 5 + i * 20))

    # ---- Meeting ----

    def _draw_meeting(self, screen):
        assert self.hud_font and self.hud_font_sm and self.hud_font_lg and self.dim_screen
        screen.blit(self.dim_screen, (0, 0))

        if self.meeting_phase == 0:
            # Alert splash
            t1 = self.hud_font_lg.render("EMERGENCY MEETING!", True, (255, 50, 50))
            screen.blit(t1, t1.get_rect(center=(WIDTH // 2, HEIGHT // 3)))
            t2 = self.hud_font.render(f"Called by {self.meeting_trigger_colour}", True, WHITE)
            screen.blit(t2, t2.get_rect(center=(WIDTH // 2, HEIGHT // 3 + 55)))
        
        elif self.meeting_phase == 1:
            # Dialogue phase (FR-5: Dialogue Display)
            t1 = self.hud_font_lg.render("DISCUSSION", True, (100, 200, 255))
            screen.blit(t1, t1.get_rect(center=(WIDTH // 2, 45)))
            
            remaining = max(0, (self.MEETING_DIALOGUE_TICKS - self.meeting_timer) // 60)
            t2 = self.hud_font.render(f"Time: {remaining}s", True, (255, 200, 50))
            screen.blit(t2, t2.get_rect(center=(WIDTH // 2, 85)))
            
            # Show dialogue messages (scrolling chat log)
            y = 120
            max_display = 8  # Show last N messages
            messages_to_show = self.dialogue_messages[-max_display:]
            for agent_c, msg in messages_to_show:
                clr = COLOR_MAP.get(agent_c, WHITE)
                # Agent name
                name_surf = self.hud_font.render(f"[{agent_c}]:", True, clr)
                screen.blit(name_surf, (60, y))
                # Message text (truncate if too long)
                display_msg = msg if len(msg) < 45 else msg[:42] + "..."
                msg_surf = self.hud_font_sm.render(display_msg, True, (220, 220, 220))
                screen.blit(msg_surf, (180, y + 4))
                y += 32
            
            # Show who hasn't spoken yet
            not_spoken = [c for c in self.alive_colours() if c not in self.spoken_agents]
            if not_spoken:
                waiting_text = f"Waiting: {', '.join(not_spoken[:4])}{'...' if len(not_spoken) > 4 else ''}"
                wait_surf = self.hud_font_sm.render(waiting_text, True, (150, 150, 150))
                screen.blit(wait_surf, (60, HEIGHT - 80))
        
        elif self.meeting_phase == 2:
            # Vote screen
            t1 = self.hud_font_lg.render("VOTING", True, WHITE)
            screen.blit(t1, t1.get_rect(center=(WIDTH // 2, 55)))
            remaining = max(0, (self.MEETING_VOTE_TICKS - self.meeting_timer) // 60)
            t2 = self.hud_font.render(f"Time: {remaining}s", True, (255, 200, 50))
            screen.blit(t2, t2.get_rect(center=(WIDTH // 2, 95)))

            alive = self.alive_colours()
            y = 135
            for c in alive:
                clr = COLOR_MAP.get(c, WHITE)
                screen.blit(self.hud_font.render(c, True, clr), (WIDTH // 4, y))
                if c in self.votes:
                    v = self.votes[c]
                    vs = f"-> {v}" if v else "-> SKIP"
                    screen.blit(self.hud_font_sm.render(vs, True, (180, 180, 180)), (WIDTH // 2, y + 4))
                else:
                    screen.blit(self.hud_font_sm.render("thinking...", True, (120, 120, 120)), (WIDTH // 2, y + 4))
                vr = sum(1 for v in self.votes.values() if v == c)
                if vr:
                    screen.blit(self.hud_font_sm.render(f"({vr})", True, (255, 100, 100)), (WIDTH * 3 // 4, y + 4))
                y += 40

    # ---- Eject ----

    def _draw_eject(self, screen):
        assert self.hud_font and self.hud_font_lg and self.dim_screen
        screen.blit(self.dim_screen, (0, 0))
        imp = self.agents[self.ejected_colour].role == "IMPOSTER"
        t1 = self.hud_font_lg.render(f"{self.ejected_colour} was ejected.", True, WHITE)
        screen.blit(t1, t1.get_rect(center=(WIDTH // 2, HEIGHT // 3)))
        t2 = self.hud_font.render(
            "They were the Imposter!" if imp else "They were NOT the Imposter.",
            True, (255, 80, 80) if imp else (100, 255, 100),
        )
        screen.blit(t2, t2.get_rect(center=(WIDTH // 2, HEIGHT // 3 + 55)))

    # ---- Game Over ----

    def _draw_game_over(self, screen):
        assert self.hud_font and self.hud_font_sm and self.hud_font_lg and self.dim_screen
        screen.blit(self.dim_screen, (0, 0))
        if self.winner == "CREW":
            t1 = self.hud_font_lg.render("CREW WINS!", True, (60, 200, 255))
        else:
            t1 = self.hud_font_lg.render("IMPOSTER WINS!", True, (255, 50, 50))
        screen.blit(t1, t1.get_rect(center=(WIDTH // 2, HEIGHT // 3)))

        t2 = self.hud_font.render(f"Imposter was: {self.imposter_colour}", True, (255, 100, 100))
        screen.blit(t2, t2.get_rect(center=(WIDTH // 2, HEIGHT // 3 + 55)))

        deaths = len(self.all_colours) - len(self.alive_colours())
        secs = self.tick // 60
        t3 = self.hud_font_sm.render(
            f"Duration: {secs // 60}m {secs % 60:02d}s  |  Deaths: {deaths}", True, (180, 180, 180))
        screen.blit(t3, t3.get_rect(center=(WIDTH // 2, HEIGHT // 3 + 95)))

        t4 = self.hud_font_sm.render("SPACE = new match  |  ESC = quit", True, (150, 150, 150))
        screen.blit(t4, t4.get_rect(center=(WIDTH // 2, HEIGHT // 3 + 130)))

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        """Run a full autonomous match. Returns True to restart."""
        self.setup()
        clock = pg.time.Clock()
        victory_played = False

        while True:
            dt = clock.tick(FPS) / 1000.0
            self.game.dt = dt

            self._handle_events()

            # ---- GAME OVER: wait for restart ----
            if self.game_over:
                if not victory_played:
                    pg.mixer.music.stop()
                    try:
                        snd = "victory_crew" if self.winner == "CREW" else "victory_imposter"
                        self.game.effect_sounds[snd].play()
                    except Exception:
                        pass
                    victory_played = True
                self._draw()
                keys = pg.key.get_pressed()
                if keys[pg.K_SPACE]:
                    try:
                        self.game.effect_sounds.get("victory_crew", pg.mixer.Sound(buffer=b'')).stop()
                        self.game.effect_sounds.get("victory_imposter", pg.mixer.Sound(buffer=b'')).stop()
                    except Exception:
                        pass
                    return True
                continue

            # ---- MEETING PHASE ----
            if self.meeting_active:
                self.meeting_timer += 1
                if self.meeting_phase == 0:
                    # Alert splash
                    if self.meeting_timer >= self.MEETING_ALERT_TICKS:
                        self.meeting_phase = 1
                        self.meeting_timer = 0
                        self._log("Dialogue phase started...")
                
                elif self.meeting_phase == 1:
                    # Dialogue phase: agents speak in order (FR-1, FR-4)
                    for c in self.dialogue_order:
                        if c not in self.spoken_agents and self.entities[c].alive_status:
                            obs = self._observation(c)
                            act = self.agents[c].get_action(obs)
                            if act["type"] == "SPEAK":
                                message = act.get("data", "...")
                                self.dialogue_messages.append((c, message))
                                self.spoken_agents.add(c)
                                # Log dialogue event (FR-6)
                                self._log_dialogue(c, message)
                                break  # One speaker per tick for turn-taking
                    
                    # Transition to voting when all have spoken or timeout
                    alive = self.alive_colours()
                    all_spoken = all(c in self.spoken_agents for c in alive)
                    if all_spoken or self.meeting_timer >= self.MEETING_DIALOGUE_TICKS:
                        self.meeting_phase = 2
                        self.meeting_timer = 0
                        self._log("Voting phase started...")
                
                elif self.meeting_phase == 2:
                    # Collect votes
                    for c in self.alive_colours():
                        if c not in self.votes:
                            obs = self._observation(c)
                            act = self.agents[c].get_action(obs)
                            if act["type"] == "VOTE":
                                self.votes[c] = act.get("data")
                    alive = self.alive_colours()
                    if all(c in self.votes for c in alive) or self.meeting_timer >= self.MEETING_VOTE_TICKS:
                        self._end_meeting()

            # ---- EJECT ANIMATION ----
            elif self.eject_active:
                self.eject_timer += 1
                if self.eject_timer >= self.EJECT_TICKS:
                    self.eject_active = False
                    self.ejected_colour = None
                    self._check_win()

            # ---- NORMAL GAMEPLAY ----
            else:
                if self.kill_cooldown > 0:
                    self.kill_cooldown -= 1
                if self.meeting_cooldown > 0:
                    self.meeting_cooldown -= 1
                self.ticks_since_meeting += 1

                # Agent tick
                for c in self.alive_colours():
                    obs = self._observation(c)
                    act = self.agents[c].get_action(obs)
                    atype = act.get("type", "NONE")

                    if atype == "MOVE":
                        self._apply_move(c, act.get("data", ""))
                    elif atype == "KILL":
                        target = act.get("data")
                        if not target or not self._try_kill(c, target):
                            self._apply_move(c, random.choice(["UP", "DOWN", "LEFT", "RIGHT"]))
                    else:
                        self.entities[c].vel = vec(0, 0)

                # Physics
                self.game.all_sprites.update()

                # Body detection → meeting
                self._check_body_detection()

                # Fallback meeting timer
                if (self.ticks_since_meeting >= self.AUTO_MEETING_INTERVAL
                        and not self.meeting_active
                        and self.meeting_cooldown <= 0):
                    alive = self.alive_colours()
                    if alive:
                        self._start_meeting(random.choice(alive))

                # Win check
                self._check_win()

            # ---- DRAW ----
            self._draw()
            self.tick += 1

            # Safety timeout
            if self.tick >= self.MAX_GAME_TICKS:
                self.game_over = True
                self.winner = "CREW"
                self._log("Time limit reached — crew wins by default.")
