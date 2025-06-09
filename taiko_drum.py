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
        try:
            self.taiko_select_sound = pygame.mixer.Sound("taiko_select_sound.wav")
        except Exception as e:
            print(f"警告：taiko_select_sound.wav 載入失敗: {e}")
            self.taiko_select_sound = None

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
        self.last_roll_time = 0
        self.roll_cooldown = 4.0  # 最短間隔，避免太密集

        self.bgm_path = "bgm_moonheart.wav"
        self.bgm_length = 0
        try:
            bgm_sound = pygame.mixer.Sound(self.bgm_path)
            self.bgm_length = bgm_sound.get_length()
        except Exception as e:
            print(f"警告：背景音樂載入失敗: {e}")
            self.bgm_length = 0
        self.bgm_start_time = None

    def play_sound(self, sound, volume=1.0):
        if sound is None:
            return
        try:
            sound.set_volume(volume)
            sound.play()
        except Exception as e:
            print(f"播放音效失敗: {e}")

    def play_select_sound(self):
        self.play_sound(self.taiko_select_sound, 0.7)

    def start_new_group(self):
        if not hasattr(self, 'roll_groups'):
            self.roll_groups = set()
        if not hasattr(self, 'forbidden_groups'):
            self.forbidden_groups = set()
        if not hasattr(self, 'last_roll_group'):
            self.last_roll_group = -10

        now = time.time()
        group_idx = int(now // self.group_interval)
        roll_prob = 1.0 / 10.0
        # 只在間隔夠遠時才產生 roll
        if (group_idx - self.last_roll_group >= 4) and (random.random() < roll_prob):
            # forbidden(預備)-roll本體-forbidden
            self.forbidden_groups.update([group_idx, group_idx+2])
            self.roll_groups.add(group_idx+1)  # 只記錄本體group
            self.last_roll_group = group_idx+1

        notes = []
        # roll本體group才產生roll條
        if group_idx in self.roll_groups:
            notes.append({'time': 0.0, 'type': 'roll', 'duration': self.group_interval, 'group_idx': group_idx})
        # forbidden group 什麼都不產生
        elif group_idx in self.forbidden_groups:
            pass
        # 其他 group 才產生 A/L 音符
        else:
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
            for tt in times:
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
                # roll條本體只在本體group產生，x從右側進場，移動到左側
                roll_pixel_len = int(self.note_speed * (note_info['duration'] * 1000 / 30))
                self.notes.append({'x': 800, 'type': 'roll', 'hit': False, 'miss': False, 'roll_hits': 0, 'roll_active': True, 'duration': note_info['duration'], 'start_x': 800, 'end_x': 800 - roll_pixel_len, 'group_idx': note_info['group_idx']})
            else:
                self.notes.append({'x': 800, 'type': note_info['type'], 'hit': False, 'miss': False})
            self.group_note_idx += 1
        missed = False
        for note in self.notes:
            if note['type'] == 'roll':
                note['x'] -= self.note_speed
                note['end_x'] -= self.note_speed
                # 只在roll本體group期間才允許判定
                if note['roll_active'] and note['x'] < self.judge_x - 45:
                    note['roll_active'] = False
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
        self.notes = [n for n in self.notes if n['x'] > 0 and not (n.get('type') == 'roll' and not n['roll_active']) and not n.get('hit', False)]
        if self.miss_banner and now > self.miss_banner[1]:
            self.miss_banner = None
        if self.judge_text and now > self.judge_text[2]:
            self.judge_text = None

    def get_bonus(self):
        # 根據 combo 決定 bonus 倍率
        if self.combo <= 9:
            return 0
        elif self.combo <= 19:
            return 1
        elif self.combo <= 39:
            return 2
        elif self.combo <= 59:
            return 3
        elif self.combo <= 79:
            return 4
        elif self.combo <= 99:
            return 5
        else:
            return 10

    def handle_event(self, key):
        hit = False
        now = time.time()
        self.last_combo_bonus = 0
        bonus = self.get_bonus()  # 取得當前bonus
        if key == ord('a') or key == ord('l'):
            for note in self.notes:
                if note['type'] == 'roll' and note['roll_active']:
                    # Debug: 印出group_idx與now//group_interval
                    print(f"[DEBUG] 判定時: note['group_idx']={note.get('group_idx')}, now_group={int(now // self.group_interval)}, note['x']={note['x']}, note['end_x']={note['end_x']}, judge_x={self.judge_x}")
                    # 僅根據 roll note 的 x~end_x 是否覆蓋判定區來判斷
                    roll_left = min(note['x'], note['end_x'])
                    roll_right = max(note['x'], note['end_x'])
                    print(f"[DEBUG] 判定區間: roll_left={roll_left}, roll_right={roll_right}, judge_x={self.judge_x}")
                    if roll_left - 45 <= self.judge_x <= roll_right + 45:
                        note['roll_hits'] += 1
                        self.combo += 1
                        self.score += 3 + bonus  # 加上bonus
                        self.last_combo_bonus = self.combo
                        self.play_sound(self.adrum_sound if key == ord('a') else self.ldrum_sound, 0.25)
                        self.judge_text = ("Perfect", (0,0,255), now + 0.2)
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
                                    self.score += 3 + bonus
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Perfect", (0,0,255), now + 0.5)
                                    self.play_sound(self.adrum_sound, 0.25)
                                elif dx <= 30:  # cool
                                    self.score += 2 + bonus
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Cool", (0,128,255), now + 0.5)
                                    self.play_sound(self.adrum_sound, 0.5)
                                else:  # good
                                    self.score += 1 + bonus
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Good", (0,255,255), now + 0.5)
                                    self.play_sound(self.adrum_sound, 1.0)
                                hit = True
                                break
                            elif note['type'] == 'right' and key == ord('l'):
                                note['hit'] = True
                                self.combo += 1
                                if dx <= 15:
                                    self.score += 3 + bonus
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Perfect", (0,0,255), now + 0.5)
                                    self.play_sound(self.ldrum_sound, 0.25)
                                elif dx <= 30:
                                    self.score += 2 + bonus
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Cool", (0,128,255), now + 0.5)
                                    self.play_sound(self.ldrum_sound, 0.5)
                                else:
                                    self.score += 1 + bonus
                                    self.last_combo_bonus = self.combo
                                    self.judge_text = ("Good", (0,255,255), now + 0.5)
                                    self.play_sound(self.ldrum_sound, 1.0)
                                hit = True
                                break
                            else:
                                note['miss'] = True
                                self.combo = 0
                                self.last_combo_bonus = 0
                                self.play_sound(self.wrong_sound, 1.0)
                                self.judge_text = ("Miss", (0,0,0), now + 0.5)
                                if note['type'] == 'left':
                                    self.miss_banner = (self.a_miss_banner, now + 0.5)
                                else:
                                    self.miss_banner = (self.l_miss_banner, now + 0.5)
                                hit = True
                                break
        # 如果沒有音符進入判定區，什麼都不做，不 miss，不重置 combo

    def overlay_image(self, background, overlay, x, y):
        """將 overlay 圖片（含 alpha）貼到 background 上 (左上角 x, y)，自動處理邊界"""
        h, w = overlay.shape[:2]
        bg_h, bg_w = background.shape[:2]
        # 邊界檢查與修正
        if (x < 0):
            overlay = overlay[:, -x:]
            w = overlay.shape[1]
            x = 0
        if (y < 0):
            overlay = overlay[-y:, :]
            h = overlay.shape[0]
            y = 0
        if (x + w > bg_w):
            overlay = overlay[:, :bg_w - x]
            w = overlay.shape[1]
        if (y + h > bg_h):
            overlay = overlay[:bg_h - y, :]
            h = overlay.shape[0]
            y = 0
        if (w <= 0 or h <= 0):
            return
        if (overlay.shape[2] == 4):
            alpha = overlay[:, :, 3] / 255.0
            for c in range(3):
                background[y:y + h, x:x + w, c] = (1 - alpha) * background[y:y + h, x:x + w, c] + alpha * overlay[:, :, c]
        else:
            background[y:y + h, x:x + w] = overlay

    def draw_text_with_outline(self, img, text, pos, font, font_scale=1.5, color=(255,255,255), thickness=3, outline_color=(0,0,0), outline_thickness=6, mode=None):
        # 只有當 color 沒有特別指定時才根據 mode 設定預設色
        if mode == 'black_white' and color == (255,255,255):
            outline_color = (0,0,0)
            color = (255,255,255)
        elif mode == 'white_black' and color == (255,255,255):
            outline_color = (255,255,255)
            color = (0,0,0)
        cv2.putText(img, text, pos, font, font_scale, outline_color, outline_thickness, cv2.LINE_AA)
        cv2.putText(img, text, pos, font, font_scale, color, thickness, cv2.LINE_AA)

    def render(self):
        frame = self.background.copy()
        center_y = self.center_y
        center = (self.judge_x, center_y)
        # 顯示右上角剩餘時間
        if self.bgm_length > 0 and self.bgm_start_time is not None:
            elapsed = time.time() - self.bgm_start_time
            remain = max(0, int(self.bgm_length - elapsed))
            min_sec = f"{remain//60:02d}:{remain%60:02d}"
            # 根據bgm_path顯示曲名
            if 'moonlight' in self.bgm_path:
                song_name = 'moonlight'
            else:
                song_name = 'moonheart'
            self.draw_text_with_outline(frame, f"{song_name} {min_sec}", (self.screen_size[0]-380, 50), self.font, 1.2, (255,225,225), 3, outline_color=(0,0,0), outline_thickness=6)
        # 移除miss音符淡出效果與miss_banner顯示
        for note in self.notes:
            if note['type'] == 'roll':
                y = center_y - 16  # roll條置中, 高度減半
                h = 32
                x1 = int(note['x'])
                roll_len = int(self.note_speed * (note['duration'] * 1000 / 30))
                x2 = x1 - roll_len
                color = (255,0,255)
                # 畫主體矩形（不含頭尾半圓區域）
                if x1 - h//2 > x2 + h//2:
                    cv2.rectangle(frame, (x2 + h//2, y), (x1 - h//2, y + h), color, -1)
                # 畫左側半圓（頭）
                cv2.ellipse(frame, (x2 + h//2, y + h//2), (h//2, h//2), 0, 90, 270, color, -1)
                # 畫右側半圓（尾）
                cv2.ellipse(frame, (x1 - h//2, y + h//2), (h//2, h//2), 0, 270, 450, color, -1)
                cv2.putText(frame, f"ROLL!", (x1, y-10), self.font, 0.8, color, 2)
            else:
                x = int(note['x']) - 40
                y = center_y - 40  # A/L音符置中
                img = self.a_circle if note['type'] == 'left' else self.l_circle
                self.overlay_image(frame, img, x, y)
        # 不再顯示miss_banner
        # 顯示評價文字分色
        if self.judge_text:
            text, color, _ = self.judge_text
            pos = (self.judge_x-30, 220)
            # 分色顯示
            if text == "Perfect":
                color = (0,0,255)
            elif text == "Cool":
                color = (0,128,255)
            elif text == "Good":
                color = (0,255,255)
            elif text == "Miss":
                color = (255,255,255)
            self.draw_text_with_outline(frame, text, pos, self.font, 1.5, color, 3, outline_color=(0,0,0), outline_thickness=6)
        # Score
        self.draw_text_with_outline(frame, f"Score: {self.score}", (10, 40), self.font, 1.5, (255,255,255), 3, outline_color=(0,0,0), outline_thickness=6)
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
        # combo加成顯示（置中）
        if self.combo <= 9:
            bonus = '0'
        elif self.combo <= 19:
            bonus = '1'
        elif self.combo <= 39:
            bonus = '2'
        elif self.combo <= 59:
            bonus = '3'
        elif self.combo <= 79:
            bonus = '4'
        elif self.combo <= 99:
            bonus = '5'
        else:
            bonus = '10'
        combo_text = f"Combo: {self.combo}  Bonus: {bonus}"
        (text_w, text_h), _ = cv2.getTextSize(combo_text, self.font, 1.5, 3)
        combo_x = (self.screen_size[0] - text_w) // 2
        combo_y = bar_y - 20
        self.draw_text_with_outline(frame, combo_text, (combo_x, combo_y), self.font, 1.5, (255,255,255), 3, outline_color=(0,0,0), outline_thickness=6)
        cv2.imshow(WINDOW_NAME, frame)

    def show_result(self):
        # 使用 taikodrum_diff_select.png 作為背景
        bg_img = cv2.imread("taikodrum_diff_select.png")
        if bg_img is not None:
            frame = cv2.resize(bg_img, (800, 600))
        else:
            frame = np.ones((600, 800, 3), dtype=np.uint8) * 30
        # 左2/5區塊半透明白色背景
        left_width = int(800 * 2 / 5)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (left_width, 600), (255, 255, 255), -1)
        alpha = 0.7
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        # 內容區域
        content_x = 0
        content_y = 0
        content_w = left_width
        content_h = 600
        # 主要資訊頂部對齊於白色區塊，Game Over!頂部，分數與Max Combo上下至中，內容超出寬度自動換行
        lines = [
            ("Game Over!", 1.5, (255,255,0)),
            (f"Score: {self.score}", 1.5, (255,255,255)),
            (f"Max Combo: {getattr(self, 'max_combo', self.combo)}", 1.2, (0,255,0)),
        ]
        # Game Over!頂部顯示
        go_text, go_scale, go_color = lines[0]
        # 換行處理
        go_words = go_text.split(' ')
        go_lines = []
        line = ''
        for word in go_words:
            test_line = (line + ' ' + word).strip()
            (w, h), _ = cv2.getTextSize(test_line, self.font, go_scale, 3)
            if w > content_w - 40 and line != '':
                go_lines.append(line)
                line = word
            else:
                line = test_line
        if line:
            go_lines.append(line)
        go_y = content_y + 40
        for go_line in go_lines:
            (go_w, go_h), _ = cv2.getTextSize(go_line, self.font, go_scale, 3)
            go_x = content_x + (content_w - go_w) // 2
            self.draw_text_with_outline(frame, go_line, (go_x, go_y + go_h), self.font, go_scale, go_color, 3, outline_color=(0,0,0), outline_thickness=6)
            go_y += go_h + 18
        # 分數與Max Combo上下至中，並自動換行
        info_lines = lines[1:]
        rendered_lines = []
        for text, scale, color in info_lines:
            words = text.split(' ')
            line = ''
            for word in words:
                test_line = (line + ' ' + word).strip()
                (w, h), _ = cv2.getTextSize(test_line, self.font, scale, 3)
                if w > content_w - 40 and line != '':
                    rendered_lines.append((line, scale, color))
                    line = word
                else:
                    line = test_line
            if line:
                rendered_lines.append((line, scale, color))
        # 新增：Leaderboard 行
        leaderboard_text = "Leaderboard ->"
        leaderboard_scale = 1.0
        leaderboard_color = (120, 120, 255)
        (w, h), _ = cv2.getTextSize(leaderboard_text, self.font, leaderboard_scale, 3)
        rendered_lines.append((leaderboard_text, leaderboard_scale, leaderboard_color))
        # 計算分數與Max Combo+Leaderboard總高度
        total_height = 0
        heights = []
        for text, scale, _ in rendered_lines:
            (w, h), _ = cv2.getTextSize(text, self.font, scale, 3)
            heights.append(h + 18)
            total_height += h + 18
        # 垂直至中（不含Game Over!）
        start_y = content_y + (content_h - total_height) // 2
        y = start_y
        for idx, (text, scale, color) in enumerate(rendered_lines):
            (w, h), _ = cv2.getTextSize(text, self.font, scale, 3)
            x = content_x + (content_w - w) // 2
            if y + h > content_y + content_h - 50:
                break
            self.draw_text_with_outline(frame, text, (x, y + h), self.font, scale, color, 3, outline_color=(0,0,0), outline_thickness=6)
            y += heights[idx]
        # 取得top3分數，顯示於與難度選單相同位置
        try:
            with open("taiko_rank.txt", "r") as f:
                ranks = [int(line.strip()) for line in f.readlines()]
        except:
            ranks = []
        ranks.append(self.score)
        ranks = sorted(ranks, reverse=True)[:3]
        with open("taiko_rank.txt", "w") as f:
            for s in ranks:
                f.write(f"{s}\n")
        # 難度選單的 x, y
        top3_x = 385
        top3_ys = [265, 395, 525]
        top3_colors = [ (0,215,255), (192,192,192), (205,127,50) ]  # 金、銀、銅
        for i, (y_pos, s) in enumerate(zip(top3_ys, ranks)):
            self.draw_text_with_outline(frame, f"{i+1}. {s}", (top3_x, y_pos), self.font, 1.2, top3_colors[i], 3, outline_color=(0,0,0), outline_thickness=6)
        # "Press any key to return to menu" 對齊白色底部，超出寬度自動換行
        press_text = "Press any key to return to menu"
        press_scale = 1
        # 自動換行
        press_words = press_text.split(' ')
        press_lines = []
        line = ''
        for word in press_words:
            test_line = (line + ' ' + word).strip()
            (w, h), _ = cv2.getTextSize(test_line, self.font, press_scale, 3)
            if w > content_w - 40 and line != '':
                press_lines.append(line)
                line = word
            else:
                line = test_line
        if line:
            press_lines.append(line)
        # 計算總高度
        total_press_height = 0
        press_heights = []
        for text in press_lines:
            (w, h), _ = cv2.getTextSize(text, self.font, press_scale, 3)
            press_heights.append(h + 8)
            total_press_height += h + 8
        # 最底部對齊
        press_y = content_y + content_h - 30 - total_press_height + 8
        for idx, text in enumerate(press_lines):
            (w, h), _ = cv2.getTextSize(text, self.font, press_scale, 3)
            press_x = content_x + (content_w - w) // 2
            self.draw_text_with_outline(frame, text, (press_x, press_y + h), self.font, press_scale, (200,255,255), 3, outline_color=(0,0,0), outline_thickness=6)
            press_y += press_heights[idx]
        cv2.imshow(WINDOW_NAME, frame)
        cv2.waitKey(0)

    def show_difficulty_menu(self):
        # 嘗試載入 taikodrum_diff_select.png 作為背景
        bg_img = cv2.imread("taikodrum_diff_select.png")
        if bg_img is not None:
            img = cv2.resize(bg_img, self.screen_size)
        else:
            img = np.ones((self.screen_size[1], self.screen_size[0], 3), dtype=np.uint8) * 30
        def draw_text_with_outline(img, text, pos, font, font_scale, color, thickness=3, outline_color=(0,0,0), outline_thickness=6):
            cv2.putText(img, text, pos, font, font_scale, outline_color, outline_thickness, cv2.LINE_AA)
            cv2.putText(img, text, pos, font, font_scale, color, thickness, cv2.LINE_AA)
        # y座標分別為265, 295, 525
        draw_text_with_outline(img, "1. Easy (Slow)", (385, 265), self.font, 1.0, (0,255,0), 3)
        draw_text_with_outline(img, "2. Normal (Medium)", (385, 395), self.font, 1.0, (255,255,0), 3)
        draw_text_with_outline(img, "3. Difficult (Fast)", (385, 525), self.font, 1.0, (255,0,0), 3)
        draw_text_with_outline(img, "ESC to back", (125, 650), self.font, 1, (180,180,180), 2)
        cv2.imshow(WINDOW_NAME, img)

    def show_music_menu(self):
        # 使用 taikodrum_diff_select.png 作為背景
        bg_img = cv2.imread("taikodrum_diff_select.png")
        if bg_img is not None:
            img = cv2.resize(bg_img, self.screen_size)
        else:
            img = np.ones((self.screen_size[1], self.screen_size[0], 3), dtype=np.uint8) * 30
        def draw_text_with_outline(img, text, pos, font, font_scale, color, thickness=3, outline_color=(0,0,0), outline_thickness=6):
            cv2.putText(img, text, pos, font, font_scale, outline_color, outline_thickness, cv2.LINE_AA)
            cv2.putText(img, text, pos, font, font_scale, color, thickness, cv2.LINE_AA)
        # y座標分別為265, 295, 525
        draw_text_with_outline(img, "Song Select", (385, 265), self.font, 1.0, (255,255,255), 3)
        draw_text_with_outline(img, "1. Moon Heart", (385, 395), self.font, 1.0, (255,200,200), 3)
        draw_text_with_outline(img, "2. Moonlight", (385, 525), self.font, 1.0, (200,200,255), 3)
        draw_text_with_outline(img, "ESC to back", (125, 650), self.font, 1, (180,180,180), 2)
        cv2.imshow(WINDOW_NAME, img)

    def show_crush_question(self):
        # 使用 taikodrum_diff_select.png 作為背景
        bg_img = cv2.imread("taikodrum_diff_select.png")
        if bg_img is not None:
            img = cv2.resize(bg_img, self.screen_size)
        else:
            img = np.ones((self.screen_size[1], self.screen_size[0], 3), dtype=np.uint8) * 30
        def draw_text_with_outline(img, text, pos, font, font_scale, color, thickness=3, outline_color=(0,0,0), outline_thickness=6):
            cv2.putText(img, text, pos, font, font_scale, outline_color, outline_thickness, cv2.LINE_AA)
            cv2.putText(img, text, pos, font, font_scale, color, thickness, cv2.LINE_AA)
        # y座標分別為265, 295, 525
        draw_text_with_outline(img, "Crush watching?", (385, 265), self.font, 1.0, (255,255,255), 3)
        draw_text_with_outline(img, "1. Yes", (385, 395), self.font, 1.0, (255,255,0), 3)
        draw_text_with_outline(img, "2. No", (385, 525), self.font, 1.0, (255,255,0), 3)
        cv2.imshow(WINDOW_NAME, img)

    def main_loop(self):
        # 不再呼叫 cv2.namedWindow，主程式已建立
        selecting_difficulty = True
        while selecting_difficulty:
            self.show_difficulty_menu()
            key = cv2.waitKey(10) & 0xFF
            if key == 27:  # ESC
                self.play_select_sound()
                return  # 返回主選單
            elif key == ord('1'):
                self.play_select_sound()
                self.note_speed = 2
                self.group_interval = 2.5
                selecting_difficulty = False
            elif key == ord('2'):
                self.play_select_sound()
                self.note_speed = 4
                self.group_interval = 1.5
                selecting_difficulty = False
            elif key == ord('3'):
                self.play_select_sound()
                self.note_speed = 7
                self.group_interval = 1.2
                selecting_difficulty = False
        # 新增：音樂選擇
        selecting_music = True
        while selecting_music:
            self.show_music_menu()
            key = cv2.waitKey(10) & 0xFF
            if key == 27:  # ESC
                self.play_select_sound()
                return  # 返回主選單
            elif key == ord('1'):
                self.play_select_sound()
                self.bgm_path = "bgm_moonheart.wav"
                try:
                    bgm_sound = pygame.mixer.Sound(self.bgm_path)
                    self.bgm_length = bgm_sound.get_length()
                except Exception as e:
                    print(f"警告：背景音樂載入失敗: {e}")
                    self.bgm_length = 0
                selecting_music = False
            elif key == ord('2'):
                self.play_select_sound()
                self.bgm_path = "bgm_moonlight.wav"
                try:
                    bgm_sound = pygame.mixer.Sound(self.bgm_path)
                    self.bgm_length = bgm_sound.get_length()
                except Exception as e:
                    print(f"警告：背景音樂載入失敗: {e}")
                    self.bgm_length = 0
                selecting_music = False
        # 新增：詢問 crush 是否在看
        selecting_crush = True
        self.crush_mode = False  # 新增：記錄crush模式
        while selecting_crush:
            self.show_crush_question()
            key = cv2.waitKey(10) & 0xFF
            if key == ord('1'):
                self.play_select_sound()
                self.crush_mode = True
                selecting_crush = False
            elif key == ord('2'):
                self.play_select_sound()
                self.crush_mode = False
                selecting_crush = False
            elif key == 27:  # ESC
                self.play_select_sound()
                return  # 返回主選單
        # 播放背景音樂
        if self.bgm_length > 0:
            try:
                pygame.mixer.music.load(self.bgm_path)
                pygame.mixer.music.play()
                self.bgm_start_time = time.time()
            except Exception as e:
                print(f"背景音樂播放失敗: {e}")
                self.bgm_start_time = None
        else:
            self.bgm_start_time = None
        # 遊戲主循環
        self.max_combo = 0
        auto_roll_timer = 0
        auto_roll_last = 0
        auto_roll_key = 'a'  # 交替A/L
        while True:
            self.update()
            # crush模式自動判定
            if self.crush_mode:
                now = time.time()
                bonus = self.get_bonus()
                # 處理普通音符
                for note in self.notes:
                    if note['type'] != 'roll' and not note.get('hit', False) and not note.get('miss', False):
                        dx = abs(note['x'] - self.judge_x)
                        if dx <= 15:
                            note['hit'] = True
                            self.combo += 1
                            self.score += 3 + bonus
                            self.last_combo_bonus = self.combo
                            self.judge_text = ("Perfect", (0,0,255), now + 0.5)
                            if note['type'] == 'left':
                                self.play_sound(self.adrum_sound, 0.25)
                            else:
                                self.play_sound(self.ldrum_sound, 0.25)
                    if note['type'] == 'roll' and note.get('roll_active', False):
                        roll_left = min(note['x'], note['end_x'])
                        roll_right = max(note['x'], note['end_x'])
                        if roll_left - 45 <= self.judge_x <= roll_right + 45:
                            if now - auto_roll_last > 0.1:
                                note['roll_hits'] += 1
                                self.combo += 1
                                self.score += 3 + bonus
                                self.last_combo_bonus = self.combo
                                self.judge_text = ("Perfect", (0,0,255), now + 0.2)
                                if auto_roll_key == 'a':
                                    self.play_sound(self.adrum_sound, 0.25)
                                    auto_roll_key = 'l'
                                else:
                                    self.play_sound(self.ldrum_sound, 0.25)
                                    auto_roll_key = 'a'
                                auto_roll_last = now
            self.render()
            if self.combo > getattr(self, 'max_combo', 0):
                self.max_combo = self.combo
            # 判斷剩餘時間
            if self.bgm_length > 0 and self.bgm_start_time is not None:
                elapsed = time.time() - self.bgm_start_time
                if elapsed >= self.bgm_length:
                    break
            key = cv2.waitKey(10) & 0xFF
            if key == 27:  # ESC
                break
            if not self.crush_mode:
                if key != 255:
                    self.handle_event(key)
            # crush模式下A/L無效，只能ESC
        pygame.mixer.music.stop()
        self.show_result()
