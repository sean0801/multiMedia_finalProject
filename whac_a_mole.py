import pygame
import random
from game_base import GameBase

class WhacAMole(GameBase):
    def __init__(self, screen):
        super().__init__("Whac-A-Mole")
        self.screen = screen
        self.mole_pos = random.randint(0, 3)  # 0:W, 1:A, 2:S, 3:D
        self.last_change = pygame.time.get_ticks()
        self.score = 0
        self.font = pygame.font.SysFont(None, 36)

    def handle_event(self, event):
        global current_game
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            current_game = None
            return
        else:
            key_map = {
            pygame.K_w: 0,
                pygame.K_a: 1,
                pygame.K_s: 2,
                pygame.K_d: 3
            }
            if event.key in key_map and key_map[event.key] == self.mole_pos:
                self.score += 1
                self.mole_pos = random.randint(0, 3)
                self.last_change = pygame.time.get_ticks()

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_change > 1500:  # 1.5秒自動換地鼠
            self.mole_pos = random.randint(0, 3)
            self.last_change = now

    def render(self):
        self.screen.fill((50, 100, 50))
        positions = [(350, 150), (150, 350), (350, 350), (550, 350)]
        labels = ["W", "A", "S", "D"]
        for i, (x, y) in enumerate(positions):
            color = (200, 200, 0) if i == self.mole_pos else (100, 100, 100)
            pygame.draw.circle(self.screen, color, (x, y), 60)
            label = self.font.render(labels[i], True, (0, 0, 0))
            self.screen.blit(label, (x - 15, y - 20))
        score_text = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        self.screen.blit(score_text, (10, 10))
        pygame.display.flip()