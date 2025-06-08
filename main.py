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
    "Whac-A-Mole": None,  # 延遲初始化
    "Taiko Drum": None,  # 進入時再根據難度建立
    "12-Key Piano": None  # 延遲初始化
}
current_game = None
font = cv2.FONT_HERSHEY_SIMPLEX


def show_lobby():
    # 嘗試載入 main_bg.png 作為主選單背景
    bg_img = cv2.imread("main_bg.png")
    if bg_img is not None:
        img = cv2.resize(bg_img, SCREEN_SIZE)
    else:
        img = blank_bg()
    y = 150
    for i, name in enumerate(games):
        text = f"{i + 1}. {name}"
        cv2.putText(img, text, (100, y), font, 1.5, (255, 255, 255), 3)
        y += 80
    cv2.putText(img, "ESC to quit", (100, 550), font, 1, (180, 180, 180), 2)
    cv2.imshow(WINDOW_NAME, img)


def main_loop():
    global current_game
    pressed_keys = set()  # 追蹤目前按下的 key
    while True:
        if current_game is None:
            show_lobby()
        else:
            if current_game == "Taiko Drum":
                from taiko_drum import TaikoDrum
                TaikoDrum().main_loop()
                current_game = None
                continue
            elif current_game == games["Whac-A-Mole"]:
                frame = current_game.render()
                cv2.imshow(WINDOW_NAME, frame)
                current_game.update()
                # current_game.render() # render() 已在上面調用，避免重複
            elif current_game == games["12-Key Piano"]:
                piano_surface.fill((60, 60, 60))
                # 確保 piano game 物件有 screen surface
                if games["12-Key Piano"].screen is None:
                    games["12-Key Piano"].screen = piano_surface
                games["12-Key Piano"].update()
                games["12-Key Piano"].render()
                piano_array = pygame.surfarray.array3d(piano_surface)
                piano_array = np.transpose(piano_array, (1, 0, 2))
                cv2.imshow(WINDOW_NAME, cv2.cvtColor(piano_array, cv2.COLOR_RGB2BGR))

        key = cv2.waitKey(30) & 0xFF

        # --- 全域按鍵處理 (ESC) ---
        if key == 27:  # ESC
            if current_game is None:
                break  # 在大廳按 ESC，離開程式
            else:
                # 在遊戲中按 ESC，返回大廳
                # 清理鋼琴遊戲可能殘留的按鍵狀態
                if current_game == games["12-Key Piano"] and pressed_keys:
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
                if games["Whac-A-Mole"] is None:
                    from whac_a_mole import WhacAMole
                    games["Whac-A-Mole"] = WhacAMole()
                current_game = games["Whac-A-Mole"]
                cv2.setMouseCallback(WINDOW_NAME, current_game.on_mouse_click)
            elif key == ord('2'):
                current_game = "Taiko Drum"
            elif key == ord('3'):
                if games["12-Key Piano"] is None:
                    from piano_12keys import Piano12Keys
                    games["12-Key Piano"] = Piano12Keys(piano_surface)
                current_game = games["12-Key Piano"]

        else:  # --- 在遊戲中時 ---
            if current_game == games["12-Key Piano"]:
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
    pygame.quit()  # 正常關閉 Pygame
    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main_loop()
    except Exception as e:
        import traceback

        print("主程式發生例外：")
        traceback.print_exc()
        input("按 Enter 結束...")