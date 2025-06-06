import cv2
import numpy as np
import random
import time
from game_base import GameBase
from threading import Thread
import pygame
import os

# 新增：統一視窗名稱
WINDOW_NAME = "MultiMedia Game"

class TaikoDrum(GameBase):
    def resize_keep_aspect(self, img, max_width, max_height):
        h, w = img.shape[:2]
        scale = min(max_width / w, max_height / h)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def __init__(self, screen_size=(800, 600), speed=5, interval=5.0):
        super().__init__("Taiko Drum")
        self.screen_size = screen_size
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.notes = []
        self.score = 0
        # 判定圓與音符軌道y座標設為畫面上下置中，x維持在左側
        self.judge_x = 105  # 再往左移動5
        self.center_y = self.screen_size[1] // 2 - 10
        self.combo = 0
        self.current_group = -1
        self.group_notes = []
        self.group_note_idx = 0
        self.group_start_time = 0
        self.group_interval = interval  # 秒
        self.last_time = time.time()
        self.note_speed = speed
        self.judge_text = None  # (text, color, show_until_time)

        # 初始化 pygame mixer
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        # 載入音效
        try:
            self.adrum_sound = pygame.mixer.Sound("Adrum.wav")
        except Exception as e:
            print(f"警告：Adrum.wav 載入失敗: {e}")
            self.adrum_sound = None
        try:
            self.ldrum_sound = pygame.mixer.Sound("Ldrum.wav")
        except Exception as e:
            print(f"警告：Ldrum.wav 載入失敗: {e}")
            self.ldrum_sound = None
        try:
            self.wrong_sound = pygame.mixer.Sound("Wrong.wav")
        except Exception as e:
            print(f"警告：Wrong.wav 載入失敗: {e}")
            self.wrong_sound = None

        # 載入圖片（等比例縮放），先判斷是否載入成功
        def safe_imread(path, fallback_shape=None):
            img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if img is None:
                print(f"警告：載入 {path} 失敗")
                if fallback_shape is not None:
                    return np.zeros(fallback_shape, dtype=np.uint8)
                return None
            return img

        bg_img = safe_imread("taiko_drum_bgi.png", (self.screen_size[1], self.screen_size[0], 3))
        self.background = cv2.resize(bg_img, self.screen_size) if bg_img is not None else np.zeros((self.screen_size[1], self.screen_size[0], 3), dtype=np.uint8)
        self.a_circle = self.resize_keep_aspect(safe_imread('A_circle.png', (80, 80, 4)), 80, 80)
        self.l_circle = self.resize_keep_aspect(safe_imread('L_circle.png', (80, 80, 4)), 80, 80)
        self.a_miss = self.resize_keep_aspect(safe_imread('A_miss.png', (80, 80, 4)), 80, 80)
        self.l_miss = self.resize_keep_aspect(safe_imread('L_miss.png', (80, 80, 4)), 80, 80)
        amb = safe_imread('A_miss_banner.png', (80, 200, 4))
        self.a_miss_banner = cv2.resize(amb, (200, 80)) if amb is not None else np.zeros((80, 200, 4), dtype=np.uint8)
        lmb = safe_imread('L_miss_banner.png', (80, 200, 4))
        self.l_miss_banner = cv2.resize(lmb, (200, 80)) if lmb is not None else np.zeros((80, 200, 4), dtype=np.uint8)
        bmb = safe_imread('black_miss_banner.png', (80, 200, 4))
        self.black_miss_banner = cv2.resize(bmb, (200, 80)) if bmb is not None else np.zeros((80, 200, 4), dtype=np.uint8)
        self.miss_banner = None  # (img, show_until_time)

    def play_sound(self, sound):
        if sound is None:
            return
        try:
            sound.play()
        except Exception as e:
            print(f"播放音效失敗: {e}")

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

        notes = []
        # 平均30秒2次roll => 每個group出現roll的機率 = group_interval / 15
        roll_prob = min(1.0, self.group_interval / 15.0)
        roll_info = None
        if random.random() < roll_prob:
            roll_duration = random.uniform(2, 4)
            max_roll_start = max_time - roll_duration
            if max_roll_start > 0:
                roll_start = random.uniform(0, max_roll_start)
                roll_end = roll_start + roll_duration
                roll_info = (roll_start, roll_end)
                notes.append({'time': roll_start + 1, 'type': 'roll', 'duration': roll_duration - 2})
        # 產生 A/L 音符，避開 roll 的 0~1, roll本體, roll_end~roll_end+1 區間
        for tt in times:
            overlap = False
            if roll_info:
                r_start, r_end = roll_info
                forbidden = [ (r_start, r_start+1), (r_start+1, r_end), (r_end, r_end+1) ]
                for f_start, f_end in forbidden:
                    if f_start < tt < f_end:
                        overlap = True
                        break
            if not overlap:
                notes.append({'time': tt, 'type': random.choice(['left', 'right'])})
        self.group_notes = [(n['time'], n) for n in notes]
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
            note_info = self.group_notes[self.group_note_idx][1]
            if note_info['type'] == 'roll':
                # 修正 roll note 長度計算
                roll_pixel_len = int(self.note_speed * (note_info['duration'] * 1000 / 30))
                self.notes.append({'x': 800, 'type': 'roll', 'hit': False, 'miss': False, 'roll_hits': 0, 'roll_active': True, 'duration': note_info['duration'], 'start_x': 800, 'end_x': 800 - roll_pixel_len})
            else:
                self.notes.append({'x': 800, 'type': note_info['type'], 'hit': False, 'miss': False})
            self.group_note_idx += 1
        missed = False
        for note in self.notes:
            if note['type'] == 'roll':
                note['x'] -= self.note_speed
                # 判斷 roll note 是否離開判定區
                if note['roll_active'] and note['x'] < self.judge_x - 45:
                    note['roll_active'] = False
                    # 離開時根據 roll_hits 給分
                    self.score += note['roll_hits']
                    self.judge_text = (f"Roll+{note['roll_hits']}", (255,0,255), now + 0.7)
            else:
                note['x'] -= self.note_speed
                if not note['hit'] and not note['miss'] and note['x'] < self.judge_x - 30:
                    note['miss'] = True
                    missed = True
                    if note['type'] == 'left':
                        self.miss_banner = (self.a_miss_banner, now + 0.5)
                    else:
                        self.miss_banner = (self.l_miss_banner, now + 0.5)
        if missed:
            self.combo = 0
            self.play_sound(self.wrong_sound)
            self.judge_text = ("Miss", (0,0,0), now + 0.5)
        # 移除已經完全離開畫面的音符
        self.notes = [n for n in self.notes if n['x'] > 0 and not (n.get('type') == 'roll' and not n['roll_active']) and not n.get('hit', False)]
        if self.miss_banner and now > self.miss_banner[1]:
            self.miss_banner = None
        if self.judge_text and now > self.judge_text[2]:
            self.judge_text = None

    def handle_event(self, key):
        hit = False
        now = time.time()
        self.last_combo_bonus = 0
        if key == ord('a') or key == ord('l'):
            for note in self.notes:
                if note['type'] == 'roll' and note['roll_active']:
                    if abs(note['x'] - self.judge_x) <= 45:
                        note['roll_hits'] += 1
                        self.combo += 1
                        self.last_combo_bonus = 1
                        self.play_sound(self.adrum_sound if key == ord('a') else self.ldrum_sound)
                        self.judge_text = ("Roll!", (255,0,255), now + 0.2)
                        hit = True
                        break
            if not hit:
                for note in self.notes:
                    if not note.get('hit', False) and not note.get('miss', False) and note['type'] != 'roll':
                        dx = abs(note['x'] - self.judge_x)
                        if dx <= 45:
                            if note['type'] == 'left' and key == ord('a'):
                                note['hit'] = True
                                self.combo += 1
                                if dx <= 15:  # perfect
                                    self.score += 3
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Perfect", (0,0,255), now + 0.5)
                                elif dx <= 30:  # cool
                                    self.score += 2
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Cool", (0,128,255), now + 0.5)
                                else:  # good
                                    self.score += 1
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Good", (0,255,255), now + 0.5)
                                hit = True
                                self.play_sound(self.adrum_sound)
                                break
                            elif note['type'] == 'right' and key == ord('l'):
                                note['hit'] = True
                                self.combo += 1
                                if dx <= 15:
                                    self.score += 3
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Perfect", (0,0,255), now + 0.5)
                                elif dx <= 30:
                                    self.score += 2
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Cool", (0,128,255), now + 0.5)
                                else:
                                    self.score += 1
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Good", (0,255,255), now + 0.5)
                                hit = True
                                self.play_sound(self.ldrum_sound)
                                break
                if not hit:
                    self.combo = 0
                    self.last_combo_bonus = 0
                    self.play_sound(self.wrong_sound)
                    self.judge_text = ("Miss", (0,0,0), now + 0.5)
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
        """將 overlay 圖片（含 alpha）貼到 background 上 (左上角 x, y)，自動處理邊界"""
        h, w = overlay.shape[:2]
        bg_h, bg_w = background.shape[:2]
        # 邊界檢查與修正
        if x < 0:
            overlay = overlay[:, -x:]
            w = overlay.shape[1]
            x = 0
        if y < 0:
            overlay = overlay[-y:, :]
            h = overlay.shape[0]
            y = 0
        if x + w > bg_w:
            overlay = overlay[:, :bg_w - x]
            w = overlay.shape[1]
        if y + h > bg_h:
            overlay = overlay[:bg_h - y, :]
            h = overlay.shape[0]
        if w <= 0 or h <= 0:
            return
        if overlay.shape[2] == 4:
            alpha = overlay[:, :, 3] / 255.0
            for c in range(3):
                background[y:y+h, x:x+w, c] = (1 - alpha) * background[y:y+h, x:x+w, c] + alpha * overlay[:, :, c]
        else:
            background[y:y+h, x:x+w] = overlay

    def render(self):
        frame = self.background.copy()
        center_y = self.center_y
        center = (self.judge_x, center_y)
        # 移除miss音符淡出效果與miss_banner顯示
        for note in self.notes:
            if note['type'] == 'roll':
                y = center_y - 30  # roll條置中
                h = 60
                x1 = int(note['x'])
                roll_len = int(self.note_speed * (note['duration'] * 1000 / 30))
                x2 = x1 - roll_len
                radius = h // 2
                cv2.rectangle(frame, (x2 + radius, y), (x1 + 100 - radius, y + h), (255,0,255), -1)
                cv2.ellipse(frame, (x2 + radius, y + radius), (radius, radius), 0, 90, 270, (255,0,255), -1)
                cv2.ellipse(frame, (x1 + 100 - radius, y + radius), (radius, radius), 0, -90, 90, (255,0,255), -1)
                cv2.putText(frame, f"ROLL!", (x1, y-10), self.font, 0.8, (255,0,255), 2)
            else:
                x = int(note['x']) - 40
                y = center_y - 40  # A/L音符置中
                img = self.a_circle if note['type'] == 'left' else self.l_circle
                self.overlay_image(frame, img, x, y)
        # 不再顯示miss_banner
        # 顯示評價文字，增加白色邊框
        if self.judge_text:
            text, color, _ = self.judge_text
            pos = (self.judge_x-30, 220)
            # 先畫白色粗邊框
            for dx in [-2, 0, 2]:
                for dy in [-2, 0, 2]:
                    if dx != 0 or dy != 0:
                        cv2.putText(frame, text, (pos[0]+dx, pos[1]+dy), self.font, 1.5, (255,255,255), 6)
            # 再畫主體文字
            cv2.putText(frame, text, pos, self.font, 1.5, color, 4)
        cv2.putText(frame, f"Score: {self.score}", (10, 40), self.font, 1, (0, 255, 255), 2)
        # 畫combo能量條（下方置中加大，100格，彩虹色）
        max_bar = 100
        bar_w, bar_h = 8, 48
        total_bar_w = max_bar * bar_w
        bar_x = (self.screen_size[0] - total_bar_w) // 2
        bar_y = self.screen_size[1] - 80
        # 彩虹色分布（紅->橙->黃->綠->藍->靛->紫)
        def rainbow_color(i, total):
            # HSV色環: 0(紅)-255(紫)，i/total*255，避免超出uint8
            hsv = np.array([int(i/total*255), 255, 255], dtype=np.uint8)
            rgb = cv2.cvtColor(hsv[np.newaxis, np.newaxis, :], cv2.COLOR_HSV2BGR)[0,0]
            return int(rgb[0]), int(rgb[1]), int(rgb[2])
        for i in range(max_bar):
            color = rainbow_color(i, max_bar-1)
            if i < self.combo:
                cv2.rectangle(frame, (bar_x + i*bar_w, bar_y), (bar_x + (i+1)*bar_w - 1, bar_y + bar_h), color, -1)
            else:
                cv2.rectangle(frame, (bar_x + i*bar_w, bar_y), (bar_x + (i+1)*bar_w - 1, bar_y + bar_h), (80,80,80), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + total_bar_w, bar_y + bar_h), (255,255,255), 2)
        # combo加成顯示
        if self.combo <= 20:
            bonus = 'x1'
        elif self.combo <= 40:
            bonus = 'x2'
        elif self.combo <= 60:
            bonus = 'x3'
        elif self.combo <= 80:
            bonus = 'x4'
        elif self.combo <= 100:
            bonus = 'x5'
        else:
            bonus = 'x10'
        cv2.putText(frame, f"Combo: {self.combo}  Bonus: {bonus}", (bar_x + total_bar_w//2 - 160, bar_y-20), self.font, 1.2, (0,255,255), 3)
        cv2.imshow(WINDOW_NAME, frame)

    def show_result(self):
        # Show result screen in English
        frame = np.ones((600, 800, 3), dtype=np.uint8) * 30
        cv2.putText(frame, "Game Over!", (250, 120), self.font, 2, (255,255,0), 4)
        cv2.putText(frame, f"Score: {self.score}", (250, 220), self.font, 1.5, (0,255,255), 3)
        cv2.putText(frame, f"Max Combo: {getattr(self, 'max_combo', self.combo)}", (250, 300), self.font, 1.2, (0,255,0), 2)
        # Show leaderboard
        try:
            with open("taiko_rank.txt", "r") as f:
                lines = f.readlines()
            ranks = [int(line.strip()) for line in lines]
        except:
            ranks = []
        ranks.append(self.score)
        ranks = sorted(ranks, reverse=True)[:5]
        with open("taiko_rank.txt", "w") as f:
            for s in ranks:
                f.write(f"{s}\n")
        cv2.putText(frame, "Leaderboard Top 5:", (250, 370), self.font, 1, (255,255,255), 2)
        for i, s in enumerate(ranks):
            cv2.putText(frame, f"{i+1}. {s}", (270, 420+i*40), self.font, 1, (255,200,200), 2)
        cv2.putText(frame, "Press any key to return to menu", (180, 550), self.font, 1, (200,255,255), 2)
        cv2.imshow(WINDOW_NAME, frame)
        cv2.waitKey(0)

    def show_difficulty_menu(self):
        img = np.ones((self.screen_size[1], self.screen_size[0], 3), dtype=np.uint8) * 30
        cv2.putText(img, "Select Taiko Drum Difficulty", (80, 120), self.font, 1.2, (255,255,255), 3)
        cv2.putText(img, "1. Easy (Slow)", (200, 220), self.font, 1, (0,255,0), 2)
        cv2.putText(img, "2. Normal (Medium)", (200, 300), self.font, 1, (255,255,0), 2)
        cv2.putText(img, "ESC to back", (100, 550), self.font, 1, (180,180,180), 2)
        cv2.imshow(WINDOW_NAME, img)

    def main_loop(self):
        # 不再呼叫 cv2.namedWindow，主程式已建立
        selecting_difficulty = True
        while selecting_difficulty:
            self.show_difficulty_menu()
            key = cv2.waitKey(30) & 0xFF
            if key == 27:  # ESC
                # 不要 destroyWindow，直接 return
                return  # 返回主選單
            elif key == ord('1'):
                self.note_speed = 4
                self.group_interval = 2.5
                selecting_difficulty = False
            elif key == ord('2'):
                self.note_speed = 6
                self.group_interval = 2.0
                selecting_difficulty = False
        # 遊戲主循環
        self.max_combo = 0
        while True:
            self.update()
            self.render()
            if self.combo > getattr(self, 'max_combo', 0):
                self.max_combo = self.combo
            key = cv2.waitKey(30) & 0xFF
            if key == 27:  # ESC
                break
            elif key != 255:
                self.handle_event(key)
        self.show_result()

