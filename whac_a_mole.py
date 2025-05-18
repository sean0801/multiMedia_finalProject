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
        self.screen = pygame.display.set_mode((1152, 768))
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
        self.lives = 3
        self.duration = 60
        self.victory = False

        self.mole_img = self.load_image("mole.png", (150, 150))
        self.background = self.load_image("background.jpg", (1152, 768), color=(80, 80, 80))
        self.hammer_img = self.load_image("hammer.png", (100, 100))
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

        for pos in self.positions:
            self.moles.append({
                'pos': pos,
                'state': MoleState.HIDDEN,
                'start': 0,
                'hit': False
            })

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

        if self.state == "select_mode":
            if 400 <= x <= 600 and 300 <= y <= 360:
                self.mode = GameMode.DIFFICULTY
                self.state = "select_difficulty"
            elif 400 <= x <= 600 and 400 <= y <= 460:
                self.mode = GameMode.TIMER
                self.countdown_start = time.time()
                self.state = "countdown"

        elif self.state == "select_difficulty":
            if 400 <= x <= 600 and 300 <= y <= 360:
                self.difficulty = Difficulty.EASY
            elif 400 <= x <= 600 and 400 <= y <= 460:
                self.difficulty = Difficulty.HARD
            self.countdown_start = time.time()
            self.state = "countdown"

        elif self.state == "game":
            self.hammer_swinging = True
            self.hammer_swing_time = pygame.time.get_ticks()
            for mole in self.moles:
                if mole['state'] == MoleState.FULL:
                    x0, y0 = mole['pos']
                    h, w = self.mole_img.shape[:2]
                    rect = pygame.Rect(x0 - w // 2, y0 - h, w, h)
                    if rect.collidepoint(x, y):
                        self.score += 1
                        mole['hit'] = True
                        mole['state'] = MoleState.DISAPPEARING
                        mole['start'] = pygame.time.get_ticks()
                        if self.mole_hit_sound:
                            self.mole_hit_sound.play()

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
                if not mole['hit'] and self.mode != GameMode.TIMER:
                    self.lives -= 1
                mole['hit'] = False

            if mole['state'] in [MoleState.APPEARING, MoleState.FULL, MoleState.DISAPPEARING]:
                active_count += 1

        if active_count == 0:
            count = 1 if self.mode == GameMode.DIFFICULTY and self.difficulty == Difficulty.EASY else random.randint(1, 3)
            for mole in self.moles:
                mole['state'] = MoleState.HIDDEN
            for mole in random.sample(self.moles, count):
                mole['state'] = MoleState.APPEARING
                mole['start'] = now
                mole['hit'] = False

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

    def render(self):
        frame = self.background.copy()

        if self.state == "select_mode":
            cv2.rectangle(frame, (400, 300), (600, 360), (255, 255, 255), -1)
            cv2.putText(frame, "Difficulty", (410, 345), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.rectangle(frame, (400, 400), (600, 460), (255, 255, 255), -1)
            cv2.putText(frame, "Timer", (440, 445), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        elif self.state == "select_difficulty":
            cv2.rectangle(frame, (400, 300), (600, 360), (255, 255, 255), -1)
            cv2.putText(frame, "Easy", (450, 345), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.rectangle(frame, (400, 400), (600, 460), (255, 255, 255), -1)
            cv2.putText(frame, "Hard", (450, 445), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

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
                    img_crop = self.mole_img[0:visible_h, :, :]
                    h, w = img_crop.shape[:2]
                    top_left = (int(x - w / 2), int(y - h))
                    frame = self.overlay_image(frame, img_crop, top_left)

            cv2.putText(frame, f"Score: {self.score}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
            if self.mode == GameMode.TIMER:
                remaining = int(self.duration - (time.time() - self.start_time))
                cv2.putText(frame, f"Time: {remaining}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
            else:
                cv2.putText(frame, f"Lives: {self.lives}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)

        elif self.state == "end":
            if self.mode == GameMode.DIFFICULTY and self.victory:
                cv2.putText(frame, "Congratulations!", (350, 350), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 150, 0), 4)
            else:
                cv2.putText(frame, "Game Over", (420, 350), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
            cv2.putText(frame, f"Score: {self.score}", (450, 420), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)

        hammer_to_draw = self.rotate_image(self.hammer_img, -30) if self.hammer_swinging else self.hammer_img
        h, w = hammer_to_draw.shape[:2]
        top_left = (self.mouse_x - w // 2, self.mouse_y - h // 2)
        frame = self.overlay_image(frame, hammer_to_draw, top_left)

        cv2.imshow("Whac-A-Mole", frame)
        cv2.setMouseCallback("Whac-A-Mole", self.on_mouse_click)
        cv2.waitKey(1)
        return True

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
        return background
