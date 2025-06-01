import cv2
import numpy as np
import pygame
pygame.init()
pygame.display.flip = lambda: None  # 讓 flip 變成 no-op，避免未 set_mode crash
from whac_a_mole import WhacAMole
from taiko_drum import TaikoDrum

WINDOW_NAME = "MultiMedia Game"
SCREEN_SIZE = (800, 600)

# 初始化 OpenCV 畫布
blank_bg = lambda: np.ones((SCREEN_SIZE[1], SCREEN_SIZE[0], 3), dtype=np.uint8) * 30

# 新增：建立一個 pygame Surface 給 Piano12Keys 用
piano_surface = pygame.Surface(SCREEN_SIZE)

games = {
    "Whac-A-Mole": None,  # 延遲初始化
    "Taiko Drum": None,  # 進入時再根據難度建立
    "12-Key Piano": None  # 延遲初始化
}
current_game = None
font = cv2.FONT_HERSHEY_SIMPLEX

def show_lobby():
    img = blank_bg()
    y = 150
    for i, name in enumerate(games):
        text = f"{i + 1}. {name}"
        cv2.putText(img, text, (100, y), font, 1.5, (255, 255, 255), 3)
        y += 80
    cv2.putText(img, "ESC to quit", (100, 550), font, 1, (180,180,180), 2)
    cv2.imshow(WINDOW_NAME, img)

def show_taiko_difficulty():
    img = blank_bg()
    cv2.putText(img, "Select Taiko Drum Difficulty", (80, 120), font, 1.2, (255,255,255), 3)
    cv2.putText(img, "1. Easy (Slow)", (200, 220), font, 1, (0,255,0), 2)
    cv2.putText(img, "2. Normal (Medium)", (200, 300), font, 1, (255,255,0), 2)
    cv2.putText(img, "ESC to back", (100, 550), font, 1, (180,180,180), 2)
    cv2.imshow(WINDOW_NAME, img)

def main_loop():
    global current_game
    taiko_selecting = False
    taiko_params = None
    pressed_keys = set()  # 新增：追蹤目前按下的 key
    while True:
        if current_game is None:
            if not taiko_selecting:
                show_lobby()
            else:
                show_taiko_difficulty()
        else:
            if current_game == "Taiko Drum":
                TaikoDrum(*taiko_params).main_loop()
                current_game = None
                continue
            elif current_game == games["Whac-A-Mole"]:
                frame = current_game.render()
                cv2.imshow(WINDOW_NAME, frame)
                current_game.update()
                current_game.render()
            elif current_game == games["12-Key Piano"]:
                piano_surface.fill((60, 60, 60))
                games["12-Key Piano"].screen = piano_surface
                games["12-Key Piano"].update()
                games["12-Key Piano"].render()
                piano_array = pygame.surfarray.array3d(piano_surface)
                piano_array = np.transpose(piano_array, (1, 0, 2))
                cv2.imshow(WINDOW_NAME, cv2.cvtColor(piano_array, cv2.COLOR_RGB2BGR))
        key = cv2.waitKey(30) & 0xFF
        if key == 27:  # ESC
            if current_game is None:
                break
            elif taiko_selecting:
                taiko_selecting = False
            else:
                cv2.setMouseCallback(WINDOW_NAME, lambda *args: None)
                current_game = None
                pressed_keys.clear()
        elif key == ord('1'):
            if current_game is None:
                if not taiko_selecting:
                    if games["Whac-A-Mole"] is None:
                        from whac_a_mole import WhacAMole
                        games["Whac-A-Mole"] = WhacAMole()
                    current_game = games["Whac-A-Mole"]
                    cv2.setMouseCallback(WINDOW_NAME, current_game.on_mouse_click)
                else:
                    taiko_params = (SCREEN_SIZE, 4, 2.5)
                    current_game = "Taiko Drum"
                    taiko_selecting = False
        elif key == ord('2'):
            if current_game is None:
                if not taiko_selecting:
                    taiko_selecting = True
                else:
                    taiko_params = (SCREEN_SIZE, 6, 2.0)
                    current_game = "Taiko Drum"
                    taiko_selecting = False
        elif key == ord('3'):
            if current_game is None and not taiko_selecting:
                if games["12-Key Piano"] is None:
                    from piano_12keys import Piano12Keys
                    games["12-Key Piano"] = Piano12Keys(piano_surface)
                current_game = games["12-Key Piano"]
        elif current_game == games["12-Key Piano"] and current_game is not None:
            class DummyEvent:
                def __init__(self, type_, key_):
                    self.type = type_
                    self.key = key_
            # 處理 keydown
            if key != 255:
                if key not in pressed_keys:
                    pressed_keys.add(key)
                    current_game.handle_event(DummyEvent(pygame.KEYDOWN, key))
            # 處理 keyup
            keys_to_remove = set()
            for k in pressed_keys:
                if k != key:
                    current_game.handle_event(DummyEvent(pygame.KEYUP, k))
                    keys_to_remove.add(k)
            pressed_keys -= keys_to_remove
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main_loop()
    except Exception as e:
        import traceback
        print("主程式發生例外：")
        traceback.print_exc()
        input("按 Enter 結束...")