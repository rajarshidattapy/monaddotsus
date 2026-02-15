    def _draw_pre_game_screen(self):
        """Display countdown and trading info during pre-game period."""
        screen = self.game.screen
        screen.fill((20, 20, 40))  # Dark blue background
        
        # Calculate remaining time
        remaining_ticks = self.PRE_GAME_TRADING_TICKS - self.pre_game_timer
        remaining_seconds = remaining_ticks // 60
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        
        # Title
        title_font = pg.font.Font(None, 72)
        title = title_font.render("PRE-GAME TRADING", True, (100, 200, 255))
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 4))
        screen.blit(title, title_rect)
        
        # Countdown timer
        timer_font = pg.font.Font(None, 120)
        timer_color = (255, 200, 50) if remaining_seconds > 60 else (255, 100, 100)
        timer_text = timer_font.render(f"{minutes}:{seconds:02d}", True, timer_color)
        timer_rect = timer_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(timer_text, timer_rect)
        
        # Info text
        info_font = pg.font.Font(None, 36)
        info_lines = [
            "Buy agent tokens now!",
            "Trading will lock when the game starts.",
            "",
            "Winners' token holders split 90% of prize pool."
        ]
        
        y_offset = HEIGHT * 3 // 4
        for line in info_lines:
            info = info_font.render(line, True, WHITE)
            info_rect = info.get_rect(center=(WIDTH // 2, y_offset))
            screen.blit(info, info_rect)
            y_offset += 40
        
        # Agent list
        agent_font = pg.font.Font(None, 28)
        agents_title = agent_font.render("Agents in this game:", True, (150, 150, 150))
        agents_rect = agents_title.get_rect(center=(WIDTH // 2, HEIGHT - 150))
        screen.blit(agents_title, agents_rect)
        
        # Display agent colors
        agent_text = ", ".join(self.all_colours[:10])  # First 10 agents
        agents_display = agent_font.render(agent_text, True, (200, 200, 200))
        agents_display_rect = agents_display.get_rect(center=(WIDTH // 2, HEIGHT - 120))
        screen.blit(agents_display, agents_display_rect)
        
        pg.display.flip()
