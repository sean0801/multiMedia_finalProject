import pygame
import cv2
import numpy as np
import random
import time
import math
from enum import Enum, auto
from game_base import GameBase

class GameMode(Enum):
    NONE = auto()
    DIFFICULTY = auto()
    TIMER = auto()

class Difficulty(Enum):
    NONE = auto()
    EASY = auto()
    HARD = auto()

class MoleState(Enum):
    HIDDEN = 0
    APPEARING = 1
    FULL = 2
    DISAPPEARING = 3

class WhacAMole(GameBase):
    def __init__(self):
        super().__init__("Whac-A-Mole")
        self.font = pygame.font.SysFont(None, 60)

        self.mode = GameMode.NONE
        self.difficulty = Difficulty.NONE
        self.state = "select_mode"

        self.mode_buttons = [(400, 300), (400, 400)]
        self.difficulty_buttons = [(400, 300), (400, 400)]
        self.countdown_start = None
        self.start_time = 0

        self.positions = self.generate_positions()
        self.moles = []
        self.mole_anim_duration = 500

        self.score = 0
        self.high_score = 0
        self.lives = 3
        self.duration = 60
        self.victory = False

        self.mole_img = self.load_image("mole.png", (150, 150))
        self.background = self.load_image("background.jpg", (1152, 768), color=(80, 80, 80))
        self.hammer_img = self.load_image("hammer.png", (100, 100))
        self.heart_img = self.load_image("heart.png", (40, 40))
        self.bomb_img = self.load_image("bomb.png", (150, 150))
        self.menu_bg = self.load_image("menu_bg.png", (1152, 768), color=(120, 120, 120))
        self.hammer_swinging = False
        self.hammer_swing_time = 0
        self.mouse_x, self.mouse_y = 0, 0

        try:
            self.hit_sound = pygame.mixer.Sound("hit.wav")
        except:
            self.hit_sound = None

        try:
            self.mole_hit_sound = pygame.mixer.Sound("bee.wav")
        except:
            self.mole_hit_sound = None
        try:
            self.bomb_sound = pygame.mixer.Sound("bomb.wav")  # ← 檔名可替換為你自己的爆炸音檔
        except:
            self.bomb_sound = None

        for pos in self.positions:
            self.moles.append({
                'pos': pos,
                'state': MoleState.HIDDEN,
                'start': 0,
                'hit': False,
                'type': 'mole'  # 新增 type 欄位
            })

    def draw_rounded_rect(self, img, top_left, bottom_right, radius, color, thickness=-1):
        x1, y1 = top_left
        x2, y2 = bottom_right
        if thickness < 0:
            overlay = img.copy()
            cv2.rectangle(overlay, (x1 + radius, y1), (x2 - radius, y2), color, -1)
            cv2.rectangle(overlay, (x1, y1 + radius), (x2, y2 - radius), color, -1)
            cv2.circle(overlay, (x1 + radius, y1 + radius), radius, color, -1)
            cv2.circle(overlay, (x2 - radius, y1 + radius), radius, color, -1)
            cv2.circle(overlay, (x1 + radius, y2 - radius), radius, color, -1)
            cv2.circle(overlay, (x2 - radius, y2 - radius), radius, color, -1)
            cv2.addWeighted(overlay, 1, img, 0, 0, img)
        else:
            cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, thickness)
            cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, thickness)
            cv2.ellipse(img, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness)
            cv2.ellipse(img, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness)
            cv2.ellipse(img, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness)
            cv2.ellipse(img, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness)

    def generate_positions(self):
        return [
            (250, 180), (576, 180), (900, 180),
            (250, 370), (576, 370), (900, 370),
            (250, 570), (576, 570), (900, 570),
        ]

    def load_image(self, path, size, color=(100, 100, 100)):
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            img = np.ones((size[1], size[0], 4), dtype=np.uint8)
            img[:, :, :3] = color
            img[:, :, 3] = 255
        else:
            img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
        return img

    def draw_button(self, frame, text, rect, hover):
        x, y, w, h = rect
        color = (200, 200, 255) if hover else (255, 255, 255)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        text_x = x + (w - text_size[0]) // 2
        text_y = y + (h + text_size[1]) // 2
        cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    def rotate_image(self, image, angle):
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
        if image.shape[2] == 4:
            alpha = image[:, :, 3]
            alpha_rotated = cv2.warpAffine(alpha, M, (w, h))
            rotated = np.dstack([rotated[:, :, :3], alpha_rotated])
        return rotated

    def on_mouse_click(self, event, x, y, flags, param):
        self.mouse_x, self.mouse_y = x, y
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if 50 <= self.mouse_x <= 170 and 50 <= self.mouse_y <= 100:
            self.state = "select_mode"
            return

        if self.state == "select_mode":
            button_width, button_height = 300, 60
            spacing = 40
            labels = ["Difficulty", "Timer"]
            for i, label in enumerate(labels):
                x = (1152 - button_width) // 2
                y = 350 + i * (button_height + spacing)
                if x <= self.mouse_x <= x + button_width and y <= self.mouse_y <= y + button_height:
                    if label == "Difficulty":
                        self.mode = GameMode.DIFFICULTY
                        self.state = "select_difficulty"
                    elif label == "Timer":
                        self.mode = GameMode.TIMER
                        self.score = 0
                        self.victory = False
                        self.countdown_start = time.time()
                        for mole in self.moles:
                            mole['state'] = MoleState.HIDDEN

                        self.countdown_start = time.time()
                        self.state = "countdown"

        elif self.state == "select_difficulty":
            button_width, button_height = 300, 60
            spacing = 40
            labels = ["Easy", "Hard"]
            for i, label in enumerate(labels):
                x = (1152 - button_width) // 2
                y = 350 + i * (button_height + spacing)
                if x <= self.mouse_x <= x + button_width and y <= self.mouse_y <= y + button_height:
                    if label == "Easy":
                        self.difficulty = Difficulty.EASY
                    elif label == "Hard":
                        self.difficulty = Difficulty.HARD

                    # reset game state
                    self.score = 0
                    self.lives = 3
                    self.victory = False
                    for mole in self.moles:
                        mole['state'] = MoleState.HIDDEN

                    self.countdown_start = time.time()
                    self.state = "countdown"

        elif self.state == "end":
            # 檢查是否點擊「返回鍵」
            if 50 <= self.mouse_x <= 170 and 50 <= self.mouse_y <= 100:
                self.state = "select_mode"
                self.score = 0
                self.lives = 3
                self.victory = False
                for mole in self.moles:
                    mole['state'] = MoleState.HIDDEN

        elif self.state == "game":
            self.hammer_swinging = True
            self.hammer_swing_time = pygame.time.get_ticks()
            for mole in self.moles:
                if mole['state'] in (MoleState.FULL, MoleState.DISAPPEARING, MoleState.APPEARING):
                    # 計算目前地鼠露出高度區域
                    x0, y0 = mole['pos']
                    now = pygame.time.get_ticks()
                    progress = (now - mole['start']) / self.mole_anim_duration
                    if mole['state'] == MoleState.APPEARING:
                        ratio = min(progress, 1.0)
                    elif mole['state'] == MoleState.DISAPPEARING:
                        ratio = max(1.0 - progress, 0.0)
                    else:
                        ratio = 1.0
                    full_h = self.mole_img.shape[0]
                    visible_h = int(full_h * ratio)
                    h, w = visible_h, self.mole_img.shape[1]
                    rect = pygame.Rect(x0 - w // 2, y0 - h, w, h)
                    if rect.collidepoint(self.mouse_x, self.mouse_y) and not mole['hit']:
                        mole['hit'] = True
                        if mole.get('type') == 'bomb':
                            self.score = max(0, self.score - 1)
                            if self.mode == GameMode.DIFFICULTY and self.difficulty == Difficulty.HARD:
                                self.lives -= 1
                            if self.bomb_sound:
                                self.bomb_sound.play()
                        else:
                            self.score += 1
                            if self.mole_hit_sound:
                                self.mole_hit_sound.play()

                        if mole['state'] != MoleState.DISAPPEARING:
                            mole['state'] = MoleState.DISAPPEARING
                            mole['start'] = pygame.time.get_ticks()

    def update(self):
        if self.state != "game":
            return

        now = pygame.time.get_ticks()

        if self.hammer_swinging and now - self.hammer_swing_time > 200:
            self.hammer_swinging = False

        if pygame.mouse.get_focused():
            self.mouse_x, self.mouse_y = pygame.mouse.get_pos()

        active_count = 0

        for mole in self.moles:
            elapsed = now - mole['start']
            if mole['state'] == MoleState.APPEARING and elapsed >= self.mole_anim_duration:
                mole['state'] = MoleState.FULL
                mole['start'] = now
            elif mole['state'] == MoleState.FULL and elapsed >= 1000:
                mole['state'] = MoleState.DISAPPEARING
                mole['start'] = now
            elif mole['state'] == MoleState.DISAPPEARING and elapsed >= self.mole_anim_duration:
                mole['state'] = MoleState.HIDDEN
                if not mole['hit'] and self.mode != GameMode.TIMER and mole.get('type') != 'bomb':
                    self.lives -= 1
                mole['hit'] = False

            if mole['state'] in [MoleState.APPEARING, MoleState.FULL, MoleState.DISAPPEARING]:
                active_count += 1

        if active_count == 0:
            count = 1 if self.mode == GameMode.DIFFICULTY and self.difficulty == Difficulty.EASY else random.randint(1,
                                                                                                                     3)
            for mole in self.moles:
                mole['state'] = MoleState.HIDDEN
            for mole in random.sample(self.moles, count):
                mole['state'] = MoleState.APPEARING
                mole['start'] = now
                mole['hit'] = False
                if self.mode == GameMode.TIMER or (
                        self.mode == GameMode.DIFFICULTY and self.difficulty == Difficulty.HARD):
                    mole['type'] = 'bomb' if random.random() < 0.3 else 'mole'
                else:
                    mole['type'] = 'mole'

        if self.mode == GameMode.DIFFICULTY:
            if self.score >= 30:
                self.victory = True
                self.state = "end"
            elif self.lives <= 0:
                self.victory = False
                self.state = "end"

        elif self.mode == GameMode.TIMER:
            if int(self.duration - (time.time() - self.start_time)) <= 0:
                self.state = "end"
                self.victory = False
                if self.score > self.high_score:
                    self.high_score = self.score

    def render(self, frame=None):
        if frame is None:
            frame = np.ones((600, 800, 3), dtype=np.uint8) * 30

        if self.state in ["select_mode", "select_difficulty", "end"]:
            frame = self.menu_bg.copy()
        else:
            frame = self.background.copy()

        if self.state == "select_mode":

            button_width, button_height = 300, 60
            spacing = 40
            labels = ["Difficulty", "Timer"]
            for i, label in enumerate(labels):
                x = (1152 - button_width) // 2
                y = 350 + i * (button_height + spacing)
                hover = x <= self.mouse_x <= x + button_width and y <= self.mouse_y <= y + button_height
                color = (200, 200, 255) if hover else (255, 255, 255)
                self.draw_rounded_rect(frame, (x, y), (x + button_width, y + button_height), 20, color)
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
                text_x = x + (button_width - text_size[0]) // 2
                text_y = y + (button_height + text_size[1]) // 2
                cv2.putText(frame, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)


        elif self.state == "select_difficulty":

            button_width, button_height = 300, 60

            spacing = 40

            labels = ["Easy", "Hard1"]

            for i, label in enumerate(labels):
                x = (1152 - button_width) // 2

                y = 350 + i * (button_height + spacing)

                hover = x <= self.mouse_x <= x + button_width and y <= self.mouse_y <= y + button_height

                color = (200, 200, 255) if hover else (255, 255, 255)

                self.draw_rounded_rect(frame, (x, y), (x + button_width, y + button_height), 20, color)
                back_x, back_y, back_w, back_h = 50, 50, 120, 50
                hover = back_x <= self.mouse_x <= back_x + back_w and back_y <= self.mouse_y <= back_y + back_h
                color = (200, 200, 255) if hover else (255, 255, 255)
                self.draw_rounded_rect(frame, (back_x, back_y), (back_x + back_w, back_y + back_h), 20, color)
                text_size = cv2.getTextSize("Back", cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
                text_x = back_x + (back_w - text_size[0]) // 2
                text_y = back_y + (back_h + text_size[1]) // 2
                cv2.putText(frame, "Back", (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]

                text_x = x + (button_width - text_size[0]) // 2

                text_y = y + (button_height + text_size[1]) // 2

                cv2.putText(frame, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        elif self.state == "countdown":
            seconds = int(5 - (time.time() - self.countdown_start))
            if seconds <= 0:
                self.start_time = time.time()
                self.state = "game"
            else:
                cv2.putText(frame, str(seconds), (520, 400), cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 0, 0), 5)

        elif self.state == "game":
            now = pygame.time.get_ticks()
            for mole in self.moles:
                x, y = mole['pos']
                progress = (now - mole['start']) / self.mole_anim_duration
                if mole['state'] == MoleState.APPEARING:
                    ratio = min(progress, 1.0)
                elif mole['state'] == MoleState.DISAPPEARING:
                    ratio = max(1.0 - progress, 0.0)
                elif mole['state'] == MoleState.FULL:
                    ratio = 1.0
                else:
                    continue
                full_h = self.mole_img.shape[0]
                visible_h = int(full_h * ratio)
                if visible_h > 0:
                    img = self.bomb_img if mole.get('type') == 'bomb' else self.mole_img
                    img_crop = img[0:visible_h, :, :]
                    h, w = img_crop.shape[:2]
                    top_left = (int(x - w / 2), int(y - h))
                    frame = self.overlay_image(frame, img_crop, top_left)

            cv2.putText(frame, f"Score: {self.score}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
            if self.mode == GameMode.TIMER:
                remaining = int(self.duration - (time.time() - self.start_time))
                cv2.putText(frame, f"Time: {remaining}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
                text = f"High Score: {self.high_score}"
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
                x = frame.shape[1] - text_size[0] - 20  # 右邊往左推 20 px
                y = 50
                cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)

            else:
                for i in range(self.lives):
                    x = 20 + i * 50  # 每顆愛心間距 50px
                    y = 50
                    frame = self.overlay_image(frame, self.heart_img, (x, y))

        elif self.state == "end":
            if self.mode == GameMode.DIFFICULTY and self.victory:
                cv2.putText(frame, "Congratulations!", (350, 350), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 150, 0), 4)
            else:
                cv2.putText(frame, "Game Over", (420, 350), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
            cv2.putText(frame, f"Score: {self.score}", (450, 420), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
            if self.mode == GameMode.TIMER:
                cv2.putText(frame, f"High Score: {self.high_score}", (420, 470), cv2.FONT_HERSHEY_SIMPLEX, 1.2,
                            (0, 0, 0), 3)
            # 返回鍵動畫（與選單一致）
            back_x, back_y, back_w, back_h = 50, 50, 120, 50
            hover = back_x <= self.mouse_x <= back_x + back_w and back_y <= self.mouse_y <= back_y + back_h
            color = (200, 200, 255) if hover else (255, 255, 255)
            self.draw_rounded_rect(frame, (back_x, back_y), (back_x + back_w, back_y + back_h), 20, color)
            text_size = cv2.getTextSize("Back", cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
            text_x = back_x + (back_w - text_size[0]) // 2
            text_y = back_y + (back_h + text_size[1]) // 2
            cv2.putText(frame, "Back", (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        hammer_to_draw = self.rotate_image(self.hammer_img, -30) if self.hammer_swinging else self.hammer_img
        h, w = hammer_to_draw.shape[:2]
        top_left = (self.mouse_x - w // 2, self.mouse_y - h // 2)
        frame = self.overlay_image(frame, hammer_to_draw, top_left)

        return frame

    def overlay_image(self, background, overlay, position):
        x, y = position
        bh, bw = background.shape[:2]
        oh, ow = overlay.shape[:2]
        if x < 0 or y < 0 or x + ow > bw or y + oh > bh:
            return background
        if overlay.shape[2] == 4:
            alpha = overlay[:, :, 3] / 255.0
            for c in range(3):
                background[y:y+oh, x:x+ow, c] = (
                    (1 - alpha) * background[y:y+oh, x:x+ow, c] + alpha * overlay[:, :, c]
                )
        else:
            background[y:y+oh, x:x+ow] = overlay[:, :, :3]
        return background #abd

