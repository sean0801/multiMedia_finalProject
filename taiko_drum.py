import cv2
import numpy as np
import random
import time
from game_base import GameBase
from threading import Thread
import simpleaudio as sa

class TaikoDrum(GameBase):
    def __init__(self, screen_size=(800, 600), speed=5, interval=2.0):
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
        self.group_interval = interval  # 秒
        self.last_time = time.time()
        self.window_name = "Taiko Drum"
        self.note_speed = speed
        self.judge_text = None  # (text, color, show_until_time)

        # 載入音效
        self.adrum_sound = "Adrum.mp3"
        self.ldrum_sound = "Ldrum.mp3"
        self.wrong_sound = "Wrong.mp3"

        # 載入圖片
        self.background = cv2.resize(cv2.imread("taiko_drum_bgi.png"), self.screen_size)
        self.a_circle = cv2.resize(cv2.imread('A_circle.png', cv2.IMREAD_UNCHANGED), (100, 60))
        self.l_circle = cv2.resize(cv2.imread('L_circle.png', cv2.IMREAD_UNCHANGED), (100, 60))
        self.a_miss = cv2.resize(cv2.imread('A_miss.png', cv2.IMREAD_UNCHANGED), (100, 60))
        self.l_miss = cv2.resize(cv2.imread('L_miss.png', cv2.IMREAD_UNCHANGED), (100, 60))
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
        notes = []
        roll_intervals = []
        roll_prob = 0.04
        for tt in times:
            if random.random() < roll_prob:
                roll_duration = 1.0
                roll_start = tt
                roll_end = tt + roll_duration
                overlap = False
                # 檢查與現有 roll 是否重疊
                for r_start, r_end in roll_intervals:
                    if not (roll_end <= r_start or roll_start >= r_end):
                        overlap = True
                        break
                # 檢查範圍內有無 A/L 音符，且roll區間內不能有A/L
                for n in notes:
                    if n['type'] in ['left', 'right']:
                        n_time = n['time']
                        if roll_start <= n_time < roll_end:
                            overlap = True
                            break
                if not overlap:
                    notes.append({'time': tt, 'type': 'roll', 'duration': roll_duration})
                    roll_intervals.append((roll_start, roll_end))
        # 確保 roll 區間內不會有 A/L 音符
        for tt in times:
            in_roll = False
            for r_start, r_end in roll_intervals:
                if r_start <= tt < r_end:
                    in_roll = True
                    break
            if not in_roll:
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
                self.notes.append({'x': 800, 'type': 'roll', 'hit': False, 'miss': False, 'roll_hits': 0, 'roll_active': True, 'duration': note_info['duration'], 'start_x': 800, 'end_x': 800 - self.note_speed * (note_info['duration'] * 1000 // 30)})
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
        # Draw three judge circles
        center = (self.judge_x, 300)
        cv2.circle(frame, center, 45, (0, 255, 255), 2)  # good (outer)
        cv2.circle(frame, center, 30, (0, 128, 255), 2)  # cool (middle)
        cv2.circle(frame, center, 15, (0, 0, 255), 2)    # perfect (inner)
        # 畫 combo 能量條（下方置中加大）
        max_bar = 20
        bar_w, bar_h = 32, 48
        total_bar_w = max_bar * bar_w
        bar_x = (self.screen_size[0] - total_bar_w) // 2
        bar_y = self.screen_size[1] - 80
        for i in range(max_bar):
            color = (0,255,0) if i < self.combo else (80,80,80)
            cv2.rectangle(frame, (bar_x + i*bar_w, bar_y), (bar_x + (i+1)*bar_w - 4, bar_y + bar_h), color, -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + total_bar_w, bar_y + bar_h), (255,255,255), 3)
        cv2.putText(frame, f"Combo: {self.combo}", (bar_x + total_bar_w//2 - 90, bar_y-20), self.font, 1.5, (0,255,0), 3)
        for note in self.notes:
            if note['type'] == 'roll':
                # 畫圓頭圓尾的 roll 條，並調整高度較小
                y = 275
                h = 60
                x1 = int(note['x'])
                roll_len = int(self.note_speed * (note['duration'] * 1000 // 30)) + 100
                x2 = x1 - roll_len
                radius = h // 2
                cv2.rectangle(frame, (x2 + radius, y), (x1 + 100 - radius, y + h), (255,0,255), -1)
                cv2.ellipse(frame, (x2 + radius, y + radius), (radius, radius), 0, 90, 270, (255,0,255), -1)
                cv2.ellipse(frame, (x1 + 100 - radius, y + radius), (radius, radius), 0, -90, 90, (255,0,255), -1)
                cv2.putText(frame, f"ROLL!", (x1, y-10), self.font, 0.8, (255,0,255), 2)
            else:
                img = self.a_miss if note['type'] == 'left' and note['miss'] else \
                      self.l_miss if note['type'] == 'right' and note['miss'] else \
                      self.a_circle if note['type'] == 'left' else self.l_circle
                x = int(note['x']) - 50
                y = 250
                # miss音符淡出效果
                if note['miss']:
                    if 'fade' not in note:
                        note['fade'] = 1.0
                    else:
                        note['fade'] -= 0.05
                    if note['fade'] > 0:
                        overlay = img.copy()
                        if overlay.shape[2] == 4:
                            overlay = overlay.astype(float)
                            overlay[:,:,3] = overlay[:,:,3] * note['fade']
                            overlay = overlay.astype(np.uint8)
                        self.overlay_image(frame, overlay, x, y)
                else:
                    self.overlay_image(frame, img, x, y)
        if self.miss_banner:
            banner_img = self.miss_banner[0]
            self.overlay_image(frame, banner_img, self.judge_x-100, 120)
        if self.judge_text:
            text, color, _ = self.judge_text
            cv2.putText(frame, text, (self.judge_x-30, 220), self.font, 1.5, color, 4)
        cv2.putText(frame, f"Score: {self.score}", (10, 40), self.font, 1, (0, 255, 255), 2)
        # 顯示 combo 加成
        if hasattr(self, 'last_combo_bonus') and self.last_combo_bonus > 0:
            cv2.putText(frame, f"+{self.last_combo_bonus} Combo Bonus!", (bar_x + total_bar_w//2 - 120, bar_y + bar_h + 40), self.font, 1.2, (0,128,255), 3)
        cv2.imshow(self.window_name, frame)

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
        cv2.imshow(self.window_name, frame)
        cv2.waitKey(0)
        cv2.destroyWindow(self.window_name)

    def main_loop(self):
        cv2.namedWindow(self.window_name)
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
