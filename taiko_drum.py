import cv2
import numpy as np
import random
import time
from game_base import GameBase
from threading import Thread
import simpleaudio as sa

class TaikoDrum(GameBase):
    def __init__(self, screen_size=(800, 600)):
        super().__init__("Taiko Drum")
        self.screen_size = screen_size
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.notes = []
        self.score = 0
        self.judge_x = 110
        self.combo = 0
        self.current_group = -1
        self.group_notes = []
        self.group_note_idx = 0
        self.group_start_time = 0
        self.group_interval = 2.0  # 秒
        self.last_time = time.time()
        self.window_name = "Taiko Drum"

        # 載入音效
        self.adrum_sound = "Adrum.mp3"
        self.ldrum_sound = "Ldrum.mp3"
        self.wrong_sound = "Wrong.mp3"

        # 載入圖片
        self.background = cv2.resize(cv2.imread("taiko_drum_bgi.png"), self.screen_size)
        self.a_circle = cv2.resize(cv2.imread('A_circle.png', cv2.IMREAD_UNCHANGED), (100, 100))
        self.l_circle = cv2.resize(cv2.imread('L_circle.png', cv2.IMREAD_UNCHANGED), (100, 100))
        self.a_miss = cv2.resize(cv2.imread('A_miss.png', cv2.IMREAD_UNCHANGED), (100, 100))
        self.l_miss = cv2.resize(cv2.imread('L_miss.png', cv2.IMREAD_UNCHANGED), (100, 100))
        self.a_miss_banner = cv2.resize(cv2.imread('A_miss_banner.png', cv2.IMREAD_UNCHANGED), (200, 80))
        self.l_miss_banner = cv2.resize(cv2.imread('L_miss_banner.png', cv2.IMREAD_UNCHANGED), (200, 80))
        self.black_miss_banner = cv2.resize(cv2.imread('black_miss_banner.png', cv2.IMREAD_UNCHANGED), (200, 80))
        self.miss_banner = None  # (img, show_until_time)

    def play_sound(self, path):
        def _play():
            try:
                sa.WaveObject.from_wave_file(path).play()
            except Exception:
                pass
        Thread(target=_play, daemon=True).start()

    def start_new_group(self):
        note_count = random.choice([2, 4, 6])
        min_interval = 0.3
        max_time = self.group_interval
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
        self.group_start_time = time.time()

    def update(self):
        now = time.time()
        group = int(now // self.group_interval)
        if group != self.current_group:
            self.current_group = group
            self.start_new_group()

        # 產生新音符
        while (self.group_note_idx < len(self.group_notes) and
               now - self.group_start_time >= self.group_notes[self.group_note_idx][0]):
            note_type = self.group_notes[self.group_note_idx][1]
            self.notes.append({'x': 800, 'type': note_type, 'hit': False, 'miss': False})
            self.group_note_idx += 1

        missed = False
        for note in self.notes:
            note['x'] -= 5
            if not note['hit'] and not note['miss'] and note['x'] < self.judge_x - 30:
                note['miss'] = True
                missed = True
                # 顯示miss banner
                if note['type'] == 'left':
                    self.miss_banner = (self.a_miss_banner, now + 0.5)
                else:
                    self.miss_banner = (self.l_miss_banner, now + 0.5)
        if missed:
            self.combo = 0
            self.play_sound(self.wrong_sound)

        self.notes = [n for n in self.notes if n['x'] > 0 and not n['hit']]

        # miss banner自動消失
        if self.miss_banner and now > self.miss_banner[1]:
            self.miss_banner = None

    def handle_event(self, key):
        hit = False
        now = time.time()
        if key == ord('a') or key == ord('l'):
            for note in self.notes:
                if not note['hit'] and not note['miss'] and abs(note['x'] - self.judge_x) < 30:
                    if note['type'] == 'left' and key == ord('a'):
                        note['hit'] = True
                        self.combo += 1
                        if 11 <= self.combo <= 30:
                            self.score += 2
                        elif 31 <= self.combo <= 50:
                            self.score += 5
                        else:
                            self.score += 1
                        hit = True
                        self.play_sound(self.adrum_sound)
                        break
                    elif note['type'] == 'right' and key == ord('l'):
                        note['hit'] = True
                        self.combo += 1
                        if 11 <= self.combo <= 30:
                            self.score += 2
                        elif 31 <= self.combo <= 50:
                            self.score += 5
                        else:
                            self.score += 1
                        hit = True
                        self.play_sound(self.ldrum_sound)
                        break
            if not hit:
                self.combo = 0
                self.play_sound(self.wrong_sound)
                miss_type = None
                for note in self.notes:
                    if not note['hit'] and not note['miss'] and abs(note['x'] - self.judge_x) < 30:
                        miss_type = note['type']
                        break
                if miss_type == 'left':
                    self.miss_banner = (self.a_miss_banner, now + 0.5)
                elif miss_type == 'right':
                    self.miss_banner = (self.l_miss_banner, now + 0.5)
                else:
                    self.miss_banner = (self.black_miss_banner, now + 0.5)

    def overlay_image(self, background, overlay, x, y):
        """將 overlay 圖片（含 alpha）貼到 background 上 (左上角 x, y)"""
        h, w = overlay.shape[:2]
        if overlay.shape[2] == 4:
            alpha = overlay[:, :, 3] / 255.0
            for c in range(3):
                background[y:y+h, x:x+w, c] = (1 - alpha) * background[y:y+h, x:x+w, c] + alpha * overlay[:, :, c]
        else:
            background[y:y+h, x:x+w] = overlay

    def render(self):
        frame = self.background.copy()
        for note in self.notes:
            img = self.a_miss if note['type'] == 'left' and note['miss'] else \
                  self.l_miss if note['type'] == 'right' and note['miss'] else \
                  self.a_circle if note['type'] == 'left' else self.l_circle
            x = int(note['x']) - 50
            y = 250
            self.overlay_image(frame, img, x, y)
        # 顯示miss banner
        if self.miss_banner:
            banner_img = self.miss_banner[0]
            self.overlay_image(frame, banner_img, self.judge_x-100, 120)
        cv2.putText(frame, f"Score: {self.score}", (10, 40), self.font, 1, (0, 255, 255), 2)
        if self.combo > 1:
            cv2.putText(frame, f"Combo : {self.combo}", (300, 60), self.font, 1, (0, 0, 0), 2)
        cv2.imshow(self.window_name, frame)

    def main_loop(self):
        cv2.namedWindow(self.window_name)
        while True:
            self.update()
            self.render()
            key = cv2.waitKey(30) & 0xFF
            if key == 27:  # ESC
                break
            elif key != 255:
                self.handle_event(key)
        cv2.destroyWindow(self.window_name)

