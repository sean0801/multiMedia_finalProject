import pygame
import random
from game_base import GameBase

class TaikoDrum(GameBase):
    def __init__(self, screen):
        super().__init__("Taiko Drum")
        self.screen = screen
        self.font = pygame.font.SysFont(None, 36)
        self.notes = []
        self.score = 0
        self.judge_x = 110  # 判定區向左移
        self.combo = 0
        self.current_group = -1
        self.group_notes = []
        self.group_note_idx = 0
        self.group_start_time = 0
        self.group_interval = 2000  # 每組持續時間(ms)

        # 載入音效
        self.adrum_sound = pygame.mixer.Sound("Adrum.mp3")
        self.ldrum_sound = pygame.mixer.Sound("Ldrum.mp3")
        self.wrong_sound = pygame.mixer.Sound("wrong.mp3")
        self.wrong_sound.set_volume(0.1)
        self.adrum_channel = pygame.mixer.Channel(1)
        self.ldrum_channel = pygame.mixer.Channel(2)
        self.wrong_channel = pygame.mixer.Channel(3)

        # 載入並縮放背景圖片
        bg_img = pygame.image.load("taiko_drum_back.png").convert()
        self.background = pygame.transform.scale(bg_img, self.screen.get_size())

    def start_new_group(self):
        note_count = random.choice([2, 4, 6])
        min_interval = 0.3
        max_time = self.group_interval / 1000
        times = []
        t = random.uniform(0, max_time - (note_count - 1) * min_interval)
        for i in range(note_count):
            times.append(t)
            if i < note_count - 1:
                t += random.uniform(min_interval,
                                    (max_time - t) / (note_count - i - 1) if (note_count - i - 1) > 0 else min_interval)
        self.group_notes = [(tt, random.choice(['left', 'right'])) for tt in times]
        self.group_notes.sort()
        self.group_note_idx = 0
        self.group_start_time = pygame.time.get_ticks()

    def update(self):
        now = pygame.time.get_ticks()
        group = now // self.group_interval
        if group != self.current_group:
            self.current_group = group
            self.start_new_group()

        # 檢查是否要產生新音符
        while (self.group_note_idx < len(self.group_notes) and
               now - self.group_start_time >= self.group_notes[self.group_note_idx][0] * 1000):
            note_type = self.group_notes[self.group_note_idx][1]
            self.notes.append({'x': 800, 'type': note_type, 'hit': False})
            self.group_note_idx += 1

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
        self.screen.blit(self.background, (0, 0))
        # 判定區方框已移除
        for note in self.notes:
            color = (255, 0, 0) if note['type'] == 'left' else (0, 0, 255)
            pygame.draw.circle(self.screen, color, (int(note['x']), 300), 30)
        score_text = self.font.render(f"Score: {self.score}", True, (255, 255, 0))
        self.screen.blit(score_text, (10, 10))
        if self.combo > 1:
            combo_text = self.font.render(f"Combo : {self.combo}", True, (0, 0, 0))
            self.screen.blit(combo_text, (300, 30))
        pygame.display.flip()