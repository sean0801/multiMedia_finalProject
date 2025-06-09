import cv2
import numpy as np
import pygame

pygame.init()
pygame.display.flip = lambda: None  # 讓 flip 變成 no-op，避免未 set_mode crash
# 延遲導入，在需要時再載入
# from whac_a_mole import WhacAMole
# from taiko_drum import TaikoDrum
# from piano_12keys import Piano12Keys
from whac_a_mole import MoleState

WINDOW_NAME = "MultiMedia Game"
SCREEN_SIZE = (800, 600)

# 初始化 OpenCV 畫布
blank_bg = lambda: np.ones((SCREEN_SIZE[1], SCREEN_SIZE[0], 3), dtype=np.uint8) * 30

# 新增：建立一個 pygame Surface 給 Piano12Keys 用
piano_surface = pygame.Surface(SCREEN_SIZE)

games = {
    "1. Whac-A-Mole": None,  # 延遲初始化
    "2. Taiko Drum": None,  # 進入時再根據難度建立
    "3. 12-Key Piano": None  # 延遲初始化
}
current_game = None
font = cv2.FONT_HERSHEY_SIMPLEX


def draw_rounded_rect(img, top_left, bottom_right, radius, color, thickness=-1):
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


def show_lobby():
    # 嘗試載入 main_bg.png 作為主選單背景
    bg_img = cv2.imread("main_bg.png")
    if bg_img is not None:
        img = cv2.resize(bg_img, SCREEN_SIZE)
    else:
        img = blank_bg()
    button_width, button_height = 350, 70
    spacing = 40
    labels = list(games.keys())
    # 個別設定每個按鈕的位置偏移
    button_positions = [
        # (x_offset, y_offset)
        # x大->右移 y大->下移
        (-200, 320),   # 1. Whac-A-Mole
        (40, 110),     # 2. Taiko Drum
        (250, 165),    # 3. 12-Key Piano
    ]
    # 個別設定每個按鈕的寬高（以裝得下文字為前提）
    button_sizes = []
    font_scale = 0.8
    font_thickness = 2
    padding_x = 32
    padding_y = 16
    for label in labels:
        text_size, _ = cv2.getTextSize(label, font, font_scale, font_thickness)
        w = text_size[0] + padding_x * 2
        h = text_size[1] + padding_y * 2
        button_sizes.append((w, h))
    y_start = 180
    for i, label in enumerate(labels):
        button_width, button_height = button_sizes[i]
        x = (SCREEN_SIZE[0] - button_width) // 2 + button_positions[i][0]
        y = y_start + i * (button_height + spacing) + button_positions[i][1]
        # 黑底白字
        color = (0, 0, 0)
        self_text_color = (255, 255, 255)
        draw_rounded_rect(img, (x, y), (x + button_width, y + button_height), 15, color)
        text_size, _ = cv2.getTextSize(label, font, font_scale, font_thickness)
        text_x = x + (button_width - text_size[0]) // 2
        text_y = y + (button_height + text_size[1]) // 2
        cv2.putText(img, label, (text_x, text_y), font, font_scale, self_text_color, font_thickness)
    # ESC to quit 也用黑底白字，並自動根據文字大小決定背景大小
    esc_text = "ESC to quit"
    esc_font_scale = 0.8
    esc_font_thickness = 2
    esc_padding_x = 32
    esc_padding_y = 16
    (esc_text_size, _) = cv2.getTextSize(esc_text, font, esc_font_scale, esc_font_thickness)
    esc_w2 = esc_text_size[0] + esc_padding_x * 2
    esc_h2 = esc_text_size[1] + esc_padding_y * 2
    esc_x = SCREEN_SIZE[0] - esc_w2 - 50  # 右邊留 50px 邊距
    esc_y = 30  # 上方留 30px 邊距
    color = (0, 0, 0)
    self_text_color = (255, 255, 255)
    draw_rounded_rect(img, (esc_x, esc_y), (esc_x + esc_w2, esc_y + esc_h2), 15, color)
    text_x = esc_x + (esc_w2 - esc_text_size[0]) // 2
    text_y = esc_y + (esc_h2 + esc_text_size[1]) // 2
    cv2.putText(img, esc_text, (text_x, text_y), font, esc_font_scale, self_text_color, esc_font_thickness)
    cv2.imshow(WINDOW_NAME, img)


def main_loop():
    global current_game
    pressed_keys = set()  # 追蹤目前按下的 key
    while True:
        if current_game is None:
            show_lobby()
        else:
            if current_game == "2. Taiko Drum":
                from taiko_drum import TaikoDrum
                TaikoDrum().main_loop()
                current_game = None
                continue
            elif current_game == games["1. Whac-A-Mole"]:
                frame = current_game.render()
                cv2.imshow(WINDOW_NAME, frame)
                current_game.update()
            elif current_game == games["3. 12-Key Piano"]:
                piano_surface.fill((60, 60, 60))
                # 確保 piano game 物件有 screen surface
                if games["3. 12-Key Piano"].screen is None:
                    games["3. 12-Key Piano"].screen = piano_surface
                games["3. 12-Key Piano"].update()
                games["3. 12-Key Piano"].render()
                piano_array = pygame.surfarray.array3d(piano_surface)
                piano_array = np.transpose(piano_array, (1, 0, 2))
                cv2.imshow(WINDOW_NAME, cv2.cvtColor(piano_array, cv2.COLOR_RGB2BGR))

        key = cv2.waitKey(30) & 0xFF

        # --- 全域按鍵處理 (ESC) ---
        if key == 27:  # ESC
            if current_game is None:
                break  # 在大廳按 ESC，離開程式
            else:
                if hasattr(current_game, "stop_music"):
                    current_game.stop_music()
                # 在遊戲中按 ESC，返回大廳
                # 清理鋼琴遊戲可能殘留的按鍵狀態
                if current_game == games["3. 12-Key Piano"] and pressed_keys:
                    class DummyEvent:
                        def __init__(self, type_, key_):
                            self.type = type_
                            self.key = key_

                    for k in pressed_keys:
                        current_game.handle_event(DummyEvent(pygame.KEYUP, k))

                # 銷毀遊戲實例，確保下次是全新的
                if isinstance(current_game, object):
                    game_key_to_reset = None
                    for name, game_instance in games.items():
                        if current_game == game_instance:
                            game_key_to_reset = name
                            break
                    if game_key_to_reset:
                        games[game_key_to_reset] = None

                cv2.setMouseCallback(WINDOW_NAME, lambda *args: None)
                current_game = None
                pressed_keys.clear()
                continue  # 返回主迴圈頂部，顯示大廳

        # --- 根據當前狀態處理按鍵 ---
        if current_game is None:  # --- 在大廳時 ---
            if key == ord('1'):
                if games["1. Whac-A-Mole"] is None:
                    from whac_a_mole import WhacAMole
                    games["1. Whac-A-Mole"] = WhacAMole()
                current_game = games["1. Whac-A-Mole"]
                cv2.setMouseCallback(WINDOW_NAME, current_game.on_mouse_click)
            elif key == ord('2'):
                current_game = "2. Taiko Drum"
            elif key == ord('3'):
                if games["3. 12-Key Piano"] is None:
                    from piano_12keys import Piano12Keys
                    games["3. 12-Key Piano"] = Piano12Keys(piano_surface)
                current_game = games["3. 12-Key Piano"]

        else:  # --- 在遊戲中時 ---
            if current_game == games["3. 12-Key Piano"]:
                class DummyEvent:
                    def __init__(self, type_, key_):
                        self.type = type_
                        self.key = key_

                # --- 全新且更穩定的按鍵處理邏輯 ---
                # 1. 處理按下按鍵 (Key Down)
                if key != 255:  # 255 代表沒有按鍵
                    if key not in pressed_keys:
                        pressed_keys.add(key)
                        current_game.handle_event(DummyEvent(pygame.KEYDOWN, key))

                # 2. 處理放開按鍵 (Key Up)
                # 找出已經不在 OpenCV 回報中，卻還在我們紀錄裡的按鍵
                released_keys = pressed_keys.copy()
                if key != 255:
                    released_keys.discard(key)  # 如果有按鍵，從待釋放清單中移除

                if released_keys:
                    for k in released_keys:
                        current_game.handle_event(DummyEvent(pygame.KEYUP, k))
                        pressed_keys.discard(k)

    # --- 程式結束前的清理 ---
    pygame.quit()  # 正常關閉  Pygame
    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main_loop()
    except Exception as e:
        import traceback

        print("主程式發生例外：")
        traceback.print_exc()
        input("按 Enter 結束...")