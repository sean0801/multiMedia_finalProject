import pygame
import random
from game_base import GameBase

class TaikoDrum(GameBase):
    def __init__(self, screen):
        super().__init__("Taiko Drum")
        self.screen = screen
        self.font = pygame.font.SysFont(None, 36)
        self.notes = []
        self.spawn_timer = 0
        self.score = 0
        self.judge_x = 120
        self.current_group = -1
        self.spawn_interval = 1000
        self.combo = 0

        # 載入音效
        self.adrum_sound = pygame.mixer.Sound("Adrum.mp3")
        self.ldrum_sound = pygame.mixer.Sound("Ldrum.mp3")
        self.wrong_sound = pygame.mixer.Sound("wrong.mp3")
        # 指定 Channel
        self.adrum_channel = pygame.mixer.Channel(1)
        self.ldrum_channel = pygame.mixer.Channel(2)
        self.wrong_channel = pygame.mixer.Channel(3)

    def spawn_note(self):
        note_type = random.choice(['left', 'right'])
        self.notes.append({'x': 800, 'type': note_type, 'hit': False})

    def update(self):
        now = pygame.time.get_ticks()
        group = now // 2000
        if group != self.current_group:
            self.current_group = group
            self.spawn_interval = random.randint(200, 1200)
        if now - self.spawn_timer > self.spawn_interval:
            self.spawn_note()
            self.spawn_timer = now

        missed = False
        for note in self.notes:
            note['x'] -= 5
            if not note['hit'] and note['x'] < self.judge_x - 30:
                missed = True
        if missed:
            self.combo = 0
            self.wrong_channel.play(self.wrong_sound)

        self.notes = [n for n in self.notes if n['x'] > 0 and not n['hit']]

    def handle_event(self, event):
        global current_game
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            current_game = None
            return

        if event.type == pygame.KEYDOWN and (event.key == pygame.K_a or event.key == pygame.K_l):
            hit = False
            for note in self.notes:
                if not note['hit'] and abs(note['x'] - self.judge_x) < 30:
                    if note['type'] == 'left' and event.key == pygame.K_a:
                        note['hit'] = True
                        self.combo += 1
                        if 11 <= self.combo <= 30:
                            self.score += 2
                        elif 31 <= self.combo <= 50:
                            self.score += 5
                        else:
                            self.score += 1
                        hit = True
                        self.adrum_channel.play(self.adrum_sound)
                        break
                    elif note['type'] == 'right' and event.key == pygame.K_l:
                        note['hit'] = True
                        self.combo += 1
                        if 11 <= self.combo <= 30:
                            self.score += 2
                        elif 31 <= self.combo <= 50:
                            self.score += 5
                        else:
                            self.score += 1
                        hit = True
                        self.ldrum_channel.play(self.ldrum_sound)
                        break
            if not hit:
                self.combo = 0
                self.wrong_channel.play(self.wrong_sound)

    def render(self):
        self.screen.fill((30, 30, 60))
        pygame.draw.rect(self.screen, (255, 255, 255), (self.judge_x-10, 250, 20, 100), 2)
        for note in self.notes:
            color = (255, 0, 0) if note['type'] == 'left' else (0, 0, 255)
            pygame.draw.circle(self.screen, color, (int(note['x']), 300), 30)
        score_text = self.font.render(f"Score: {self.score}", True, (255, 255, 0))
        self.screen.blit(score_text, (10, 10))
        if self.combo > 1:
            combo_text = self.font.render(f"Combo : {self.combo}", True, (255, 100, 0))
            self.screen.blit(combo_text, (300, 30))
        pygame.display.flip()