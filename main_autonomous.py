"""
MonadSus — Autonomous Agent Mode Entry Point

Launch this to watch AI agents play a full match of Among Us.
No keyboard or mouse input is used for gameplay — humans are spectators only.

Every character you see is an autonomous agent.

Usage:
    python main_autonomous.py

Controls (spectator):
    TAB   — cycle camera between alive agents
    1-9   — jump to specific agent
    ESC   — quit
    SPACE — restart (on game-over screen)
"""

from autonomous_game import AutonomousGame


def main():
    print("\n" + "=" * 60)
    print("  MonadSus — Autonomous Agent Simulation")
    print("  Every player is an AI agent. No humans are playing.")
    print("=" * 60 + "\n")

    while True:
        game = AutonomousGame()
        restart = game.run()
        if not restart:
            break


if __name__ == "__main__":
    main()
