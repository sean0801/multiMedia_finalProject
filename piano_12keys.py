import pygame
from game_base import GameBase

WHITE_KEYS = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
BLACK_KEYS = ['C#', 'D#', '', 'F#', 'G#', 'A#', '']
WHITE_KEY_CODES = [pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_t, pygame.K_y, pygame.K_u]
BLACK_KEY_CODES = [pygame.K_2, pygame.K_3, None, pygame.K_5, pygame.K_6, pygame.K_7, None]

class Piano12Keys(GameBase):
    def __init__(self, screen):
        super().__init__("12-Key Piano")
        self.screen = screen
        self.font = pygame.font.SysFont(None, 32)
        self.pressed = [False] * 12  # 0-6:白鍵, 7-11:黑鍵

    def handle_event(self, event):
        global current_game
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            current_game = None
            return
        if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
            is_down = event.type == pygame.KEYDOWN
            # 白鍵
            for i, key in enumerate(WHITE_KEY_CODES):
                if event.key == key:
                    self.pressed[i] = is_down
            # 黑鍵
            for i, key in enumerate(BLACK_KEY_CODES):
                if key and event.key == key:
                    self.pressed[7 + i] = is_down
        elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEBUTTONUP:
            is_down = event.type == pygame.MOUSEBUTTONDOWN
            x, y = event.pos
            # 黑鍵優先
            for i in range(7):
                if BLACK_KEYS[i] and 110 + i*80 <= x <= 170 + i*80 and 100 <= y <= 200:
                    self.pressed[7 + i] = is_down
            # 白鍵
            for i in range(7):
                if 100 + i*80 <= x <= 180 + i*80 and 200 <= y <= 400:
                    self.pressed[i] = is_down

    def update(self):
        pass

    def render(self):
        self.screen.fill((60, 60, 60))
        # 畫白鍵
        for i in range(7):
            color = (220, 220, 220) if not self.pressed[i] else (180, 180, 255)
            pygame.draw.rect(self.screen, color, (100 + i*80, 200, 80, 200))
            pygame.draw.rect(self.screen, (0, 0, 0), (100 + i*80, 200, 80, 200), 2)
            label = self.font.render(WHITE_KEYS[i], True, (0, 0, 0))
            self.screen.blit(label, (130 + i*80, 350))
        # 畫黑鍵
        for i in range(7):
            if BLACK_KEYS[i]:
                idx = 7 + i
                if idx < len(self.pressed):
                    color = (30, 30, 30) if not self.pressed[idx] else (80, 80, 180)
                else:
                    color = (30, 30, 30)
                pygame.draw.rect(self.screen, color, (110 + i * 80, 100, 60, 100))
                pygame.draw.rect(self.screen, (0, 0, 0), (110 + i * 80, 100, 60, 100), 2)
                label = self.font.render(BLACK_KEYS[i], True, (255, 255, 255))
                self.screen.blit(label, (125 + i * 80, 160))
        pygame.display.flip()