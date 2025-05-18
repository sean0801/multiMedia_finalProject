import pygame
import random
import cv2
import numpy as np
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

        # 你可以在這裡載入自己的圖片
        # self.bg_img = cv2.imread('your_bg.png')

    def spawn_note(self):
        note_type = random.choice(['left', 'right'])
        self.notes.append({'x': 800, 'type': note_type, 'hit': False})

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.spawn_timer > 1000:
            self.spawn_note()
            self.spawn_timer = now

        for note in self.notes:
            note['x'] -= 5

        self.notes = [n for n in self.notes if n['x'] > 0 and not n['hit']]

    def handle_event(self, event):
        global current_game
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            current_game = None
            return
        for note in self.notes:
            if not note['hit'] and abs(note['x'] - self.judge_x) < 30:
                if note['type'] == 'left' and event.key == pygame.K_a:
                    note['hit'] = True
                    self.score += 1
                    break
                elif note['type'] == 'right' and event.key == pygame.K_l:
                    note['hit'] = True
                    self.score += 1
                    break

    def render(self):
        # 1. 用 pygame 畫到 Surface
        self.screen.fill((30, 30, 60))
        pygame.draw.rect(self.screen, (255, 255, 255), (self.judge_x-10, 250, 20, 100), 2)
        for note in self.notes:
            color = (255, 0, 0) if note['type'] == 'left' else (0, 0, 255)
            pygame.draw.circle(self.screen, color, (int(note['x']), 300), 30)
        score_text = self.font.render(f"Score: {self.score}", True, (255, 255, 0))
        self.screen.blit(score_text, (10, 10))

        # 2. 轉成 numpy array
        raw_str = pygame.image.tostring(self.screen, "RGB")
        img = np.frombuffer(raw_str, dtype=np.uint8)
        img = img.reshape((self.screen.get_height(), self.screen.get_width(), 3))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # 3. 用 OpenCV 顯示
        cv2.imshow("Taiko Drum", img)
        cv2.waitKey(1)  # 必須要有這行，否則不會更新

        # 你可以在這裡用 cv2.draw 或 cv2.putText 畫自己的圖片或文字