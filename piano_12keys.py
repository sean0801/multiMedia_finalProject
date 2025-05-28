import pygame
from game_base import GameBase  # 假設 game_base.py 與此檔案在同一目錄

WHITE_KEYS = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
BLACK_KEYS_DISPLAY = ['C#', 'D#', '', 'F#', 'G#', 'A#', '']  # 用於顯示和定位邏輯
WHITE_KEY_CODES = [pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_t, pygame.K_y, pygame.K_u]
BLACK_KEY_CODES = [pygame.K_2, pygame.K_3, None, pygame.K_5, pygame.K_6, pygame.K_7, None]  # 鍵盤映射

# 音高名稱到音效檔名的映射 (請根據您的實際檔名修改)
# 注意：黑鍵的名稱通常用 's' 代表 sharp，例如 'Cs' 代表 C#
# 您需要確保這些 .wav 檔案存在於程式執行的相同目錄下，或者提供完整路徑
SOUND_FILES = {
    'C': "C.wav", 'D': "D.wav", 'E': "E.wav", 'F': "F.wav",
    'G': "G.wav", 'A': "A.wav", 'B': "B.wav",
    'C#': "Cs.wav", 'D#': "Ds.wav", 'F#': "Fs.wav",
    'G#': "Gs.wav", 'A#': "As.wav"
}

# 將琴鍵名稱和索引映射起來，方便載入和播放音效
# 索引 0-6 為白鍵，7-11 為黑鍵
KEY_NAME_TO_SOUND_INDEX = {
    'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6,
    'C#': 7, 'D#': 8, 'F#': 9, 'G#': 10, 'A#': 11
}
# 反向映射，從 sound_index 到 key_name，主要用於查找檔名
SOUND_INDEX_TO_KEY_NAME = {v: k for k, v in KEY_NAME_TO_SOUND_INDEX.items()}


class Piano12Keys(GameBase):
    def __init__(self, screen):
        try:
            super().__init__("12-Key Piano (Expanded Sounds)")
            print("GameBase __init__ 調用成功。")
        except Exception as e:
            print(f"錯誤：GameBase __init__ 調用失敗: {e}")
        self.screen = screen
        self.font = pygame.font.SysFont(None, 32)
        self.pressed = [False] * 12  # 7 白鍵 + 5 黑鍵
        self.key_sounds = [None] * 12

        print("Piano12Keys：開始初始化音效系統...")
        mixer_initialized_successfully = False
        try:
            pygame.mixer.init()
            if pygame.mixer.get_init():
                print("Piano12Keys：音效系統 pygame.mixer.init() 初始化成功。")
                mixer_initialized_successfully = True
            else:
                print("警告：Piano12Keys：pygame.mixer.init() 執行完畢，但音效系統未能成功初始化。")
        except pygame.error as e:
            print(f"警告：Piano12Keys：pygame.mixer.init() 執行時發生 Pygame 錯誤: {e}")
        except Exception as e_gen:
            print(f"警告：Piano12Keys：pygame.mixer.init() 執行時發生未知錯誤: {e_gen}")

        if mixer_initialized_successfully:
            print("Piano12Keys：開始載入所有琴鍵音效...")
            for sound_idx, key_name in SOUND_INDEX_TO_KEY_NAME.items():
                if key_name in SOUND_FILES:
                    sound_path = SOUND_FILES[key_name]
                    try:
                        self.key_sounds[sound_idx] = pygame.mixer.Sound(sound_path)
                        print(f"Piano12Keys：音效 '{sound_path}' (對應琴鍵 {key_name}, 索引 {sound_idx}) 載入成功。")
                    except pygame.error as e:
                        print(f"警告：Piano12Keys：載入音效 '{sound_path}' 時發生 Pygame 錯誤: {e}")
                    except Exception as e_gen:
                        print(f"警告：Piano12Keys：載入音效 '{sound_path}' 時發生未知錯誤: {e_gen}")
                else:
                    print(f"警告：Piano12Keys：琴鍵 {key_name} (索引 {sound_idx}) 未在 SOUND_FILES 中定義音效檔。")
        else:
            print("Piano12Keys：由於音效系統未能初始化，跳過載入所有音效。")

        print("Piano12Keys __init__ 完成。")

    def _play_sound(self, key_index):
        """根據琴鍵索引播放聲音（如果已載入）"""
        if 0 <= key_index < len(self.key_sounds) and self.key_sounds[key_index]:
            self.key_sounds[key_index].play()
            # print(f"播放音效：索引 {key_index}, 名稱 {SOUND_INDEX_TO_KEY_NAME.get(key_index, '未知')}") # 用於調試
        # else:
        # print(f"無法播放音效：索引 {key_index} 無效或音效未載入。") # 用於調試

    def handle_event(self, event):
        global current_game  # 建議後續版本移除 global 依賴
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            current_game = None
            return

        if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
            is_down = event.type == pygame.KEYDOWN
            key_event_processed = False

            # 處理白鍵
            for i, key_code in enumerate(WHITE_KEY_CODES):
                if event.key == key_code:
                    if self.pressed[i] != is_down:  # 狀態改變才更新和播放
                        self.pressed[i] = is_down
                        if is_down:
                            self._play_sound(i)  # 白鍵索引 0-6 直接對應
                    key_event_processed = True
                    break

            # 處理黑鍵
            if not key_event_processed:
                actual_black_key_idx = 0  # 實際的黑鍵索引 (0-4)
                for key_code_from_list in BLACK_KEY_CODES:  # 遍歷鍵盤映射
                    if key_code_from_list:  # 如果是有效的鍵碼 (非 None)
                        if event.key == key_code_from_list:
                            target_pressed_idx = 7 + actual_black_key_idx  # 黑鍵在 pressed 和 sounds 列表中的索引
                            if self.pressed[target_pressed_idx] != is_down:  # 狀態改變
                                self.pressed[target_pressed_idx] = is_down
                                if is_down:
                                    self._play_sound(target_pressed_idx)
                            key_event_processed = True  # 即使沒播放聲音，事件也處理了
                            break
                        actual_black_key_idx += 1  # 只有當 key_code_from_list 有效時才增加

        elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEBUTTONUP:
            is_down = event.type == pygame.MOUSEBUTTONDOWN
            x, y = event.pos
            key_processed_by_mouse = False

            # 優先處理黑鍵點擊
            actual_black_key_idx = 0  # 實際的黑鍵索引 (0-4)
            # BLACK_KEYS_DISPLAY 用於確定黑鍵的繪製位置和數量
            for i in range(len(BLACK_KEYS_DISPLAY)):  # i 是黑鍵的顯示/佈局位置索引
                if BLACK_KEYS_DISPLAY[i]:  # 如果此位置有黑鍵
                    black_key_rect = pygame.Rect(110 + i * 80, 100, 60, 100)
                    target_pressed_idx = 7 + actual_black_key_idx  # 黑鍵在 pressed 和 sounds 列表中的索引

                    if black_key_rect.collidepoint(x, y):
                        if self.pressed[target_pressed_idx] != is_down or not is_down:  # 狀態改變，或鼠標彈起時強制更新
                            self.pressed[target_pressed_idx] = is_down
                            if is_down:  # 只在按下時播放聲音
                                self._play_sound(target_pressed_idx)
                        key_processed_by_mouse = True
                        break
                    actual_black_key_idx += 1  # 只有當 BLACK_KEYS_DISPLAY[i] 有效時才增加索引

            # 如果沒有點擊到黑鍵，再處理白鍵
            if not key_processed_by_mouse:
                for i in range(len(WHITE_KEYS)):  # i 是白鍵索引 (0-6)
                    white_key_rect = pygame.Rect(100 + i * 80, 200, 80, 200)
                    if white_key_rect.collidepoint(x, y):
                        if self.pressed[i] != is_down or not is_down:  # 狀態改變，或鼠標彈起時強制更新
                            self.pressed[i] = is_down
                            if is_down:  # 只在按下時播放聲音
                                self._play_sound(i)
                        # key_processed_by_mouse = True # 此處不需要，因為這是最後的檢查
                        break

    def update(self):
        pass  # 鋼琴主要由事件驅動

    def render(self):
        self.screen.fill((60, 60, 60))
        # 繪製白鍵
        for i in range(len(WHITE_KEYS)):
            color = (220, 220, 220) if not self.pressed[i] else (180, 180, 255)
            pygame.draw.rect(self.screen, color, (100 + i * 80, 200, 80, 200))
            pygame.draw.rect(self.screen, (0, 0, 0), (100 + i * 80, 200, 80, 200), 2)  # 邊框
            label = self.font.render(WHITE_KEYS[i], True, (0, 0, 0))
            self.screen.blit(label, (130 + i * 80, 350))

        # 繪製黑鍵
        actual_black_key_render_idx = 0  # 實際的黑鍵索引 (0-4)，用於 self.pressed
        # BLACK_KEYS_DISPLAY 用於確定黑鍵的繪製位置和顯示名稱
        for i in range(len(BLACK_KEYS_DISPLAY)):  # i 是黑鍵的顯示/佈局位置索引
            if BLACK_KEYS_DISPLAY[i]:  # 如果此位置有黑鍵
                target_pressed_idx = 7 + actual_black_key_render_idx
                color = (30, 30, 30) if not self.pressed[target_pressed_idx] else (80, 80, 180)
                pygame.draw.rect(self.screen, color, (110 + i * 80, 100, 60, 100))
                pygame.draw.rect(self.screen, (0, 0, 0), (110 + i * 80, 100, 60, 100), 2)  # 邊框
                label = self.font.render(BLACK_KEYS_DISPLAY[i], True, (255, 255, 255))
                self.screen.blit(label, (125 + i * 80, 160))
                actual_black_key_render_idx += 1  # 只有當 BLACK_KEYS_DISPLAY[i] 有效時才增加索引

        pygame.display.flip()


# --- 假設的主遊戲迴圈 (用於測試) ---
# 如果您有自己的主迴圈，請確保 Piano12Keys 被正確實例化和調用
if __name__ == '__main__':
    pygame.init()


    # 簡易 GameBase 替代，如果 game_base.py 不可用
    class GameBasePlaceholder:
        def __init__(self, title):
            print(f"GameBasePlaceholder initialized with title: {title}")


    # 如果 game_base.py 不可用，則使用 GameBasePlaceholder
    if 'GameBase' not in globals():
        print("警告：game_base.GameBase 未找到，使用 GameBasePlaceholder。")
        GameBase = GameBasePlaceholder  # type: ignore

    SCREEN_WIDTH = 100 + 7 * 80 + 100  # 根據琴鍵數量和邊距調整
    SCREEN_HEIGHT = 450
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("12鍵鋼琴 - 擴展音效")

    piano_game = Piano12Keys(screen)
    current_game = piano_game  # 為了匹配 handle_event 中的 global current_game

    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if current_game:  # 如果 current_game 不是 None (例如按下 ESC 後)
                current_game.handle_event(event)
            else:  # 如果 current_game 為 None，則退出
                running = False
                break

        if not current_game:  # 再次檢查，如果 ESC 被按下，退出循環
            running = False

        if running and current_game:
            current_game.update()
            current_game.render()

        clock.tick(60)

    pygame.quit()
    print("Pygame 已退出。")