import pygame
import re
import random  # 用於隨機選音

# --- Placeholder GameBase ---
try:
    from game_base import GameBase
except ImportError:
    class GameBase:
        def __init__(self, title): self.title = title

        def update(self): pass

        def render(self): pass

        def handle_event(self, event): pass
# --- Placeholder GameBase End ---

WHITE_KEYS = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
BLACK_KEYS_DISPLAY = ['C#', 'D#', '', 'F#', 'G#', 'A#', '']
WHITE_KEY_CODES = [pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_f, pygame.K_g, pygame.K_h, pygame.K_j]
BLACK_KEY_CODES = [pygame.K_w, pygame.K_e, None, pygame.K_t, pygame.K_y, pygame.K_u, None]

SOUND_FILES = {
    'C': "C.wav", 'D': "D.wav", 'E': "E.wav", 'F': "F.wav", 'G': "G.wav", 'A': "A.wav", 'B': "B.wav",
    'C#': "Cs.wav", 'D#': "Ds.wav", 'F#': "Fs.wav", 'G#': "Gs.wav", 'A#': "As.wav"
}
KEY_NAME_TO_SOUND_INDEX = {
    'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6,
    'C#': 7, 'D#': 8, 'F#': 9, 'G#': 10, 'A#': 11
}
SOUND_INDEX_TO_KEY_NAME = {v: k for k, v in KEY_NAME_TO_SOUND_INDEX.items()}


class Piano12Keys(GameBase):
    CV_CHAR_TO_PYGAME_KEY_MAP = {
        ord('a'): pygame.K_a, ord('s'): pygame.K_s, ord('d'): pygame.K_d, ord('f'): pygame.K_f,
        ord('g'): pygame.K_g, ord('h'): pygame.K_h, ord('j'): pygame.K_j,
        ord('w'): pygame.K_w, ord('e'): pygame.K_e, ord('t'): pygame.K_t, ord('y'): pygame.K_y, ord('u'): pygame.K_u,
        ord('i'): pygame.K_i, ord('o'): pygame.K_o, ord('p'): pygame.K_p,
        ord('m'): pygame.K_m,
        ord('='): pygame.K_EQUALS, ord('+'): pygame.K_PLUS,
        ord('-'): pygame.K_MINUS, ord('_'): pygame.K_UNDERSCORE,
        ord('r'): pygame.K_r,
        ord('l'): pygame.K_l,
        ord('.'): pygame.K_PERIOD,
        27: pygame.K_ESCAPE
    }

    NUM_TO_NOTE_MAP = {'1': 'C', '2': 'D', '3': 'E', '4': 'F', '5': 'G', '6': 'A', '7': 'B', '0': ' '}

    def _convert_num_score_to_phrases(self, num_score_string):
        phrases = []
        potential_phrases_lines = re.split(r'\s{2,}|[\n\r]+', num_score_string.strip())
        for line in potential_phrases_lines:
            if not line.strip(): continue
            note_groups = line.strip().split(' ')
            converted_note_groups_for_phrase = []
            for group in note_groups:
                if not group: continue
                converted_group = "".join([self.NUM_TO_NOTE_MAP.get(char, char) for char in group])
                converted_note_groups_for_phrase.append(converted_group)
            if converted_note_groups_for_phrase:
                phrases.append(" ".join(converted_note_groups_for_phrase))
        return phrases if phrases else [num_score_string]

    def __init__(self, screen):
        try:
            super().__init__("12-Key Piano")
        except Exception as e:
            print(f"錯誤：GameBase __init__ 調用失敗: {e}")
        self.screen = screen
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 28)
        self.sheet_music_font = pygame.font.SysFont(None, 24)
        self.ui_font = pygame.font.SysFont(None, 22)

        self.instruction_font_ingame = None
        font_paths_to_try = ["Microsoft YaHei", "SimHei", "WenQuanYi Micro Hei", None]
        target_font_size = 12
        for font_name_try in font_paths_to_try:
            try:
                temp_font = pygame.font.SysFont(font_name_try, target_font_size)
                if temp_font: self.instruction_font_ingame = temp_font; break
            except Exception:
                continue
        if not self.instruction_font_ingame:
            self.instruction_font_ingame = pygame.font.Font(None, target_font_size)

        self.pressed = [False] * 12
        self.key_sounds = [None] * 12
        self.key_white_width, self.key_white_height, self.key_white_y = 80, 200, 200
        self.key_black_width, self.key_black_height, self.key_black_y = 60, 100, 100
        self.black_key_x_offset_in_slot = 10
        num_white_keys = len(WHITE_KEYS)
        self.piano_total_width_of_white_keys_area = num_white_keys * self.key_white_width
        if self.screen:
            self.piano_origin_x = (self.screen.get_width() - self.piano_total_width_of_white_keys_area) // 2
        else:
            self.piano_origin_x = (800 - self.piano_total_width_of_white_keys_area) // 2
        self.white_key_label_y = self.key_white_y + self.key_white_height - 50
        self.black_key_label_y = self.key_black_y + self.key_black_height - 40

        little_star_nums = "1155665 4433221  5544332 5544332  1155665 4433221"
        jingle_bells_nums = "333 333 35123  4444433322325  333 333 35123  444443355421"
        little_bee_nums = "533 422 1234555  533 422 13553  2222234 3333345  533 422 13551"
        self.song_data = {
            "Little Bee": {"phrases": self._convert_num_score_to_phrases(little_bee_nums),
                           "display_name": "Little Bee"},
            "Little Star": {"phrases": self._convert_num_score_to_phrases(little_star_nums),
                            "display_name": "Little Star"},
            "Jingle Bells": {"phrases": self._convert_num_score_to_phrases(jingle_bells_nums),
                             "display_name": "Jingle Bells"}
        }
        self.active_song_notes_key, self.show_sheet_music = None, False
        self.song_keys_ordered_for_shortcuts = ["Little Bee", "Little Star", "Jingle Bells"]
        piano_actual_bottom_y = self.key_white_y + self.key_white_height
        btn_w, btn_h, btn_sp = 120, 35, 10
        num_btns = len(self.song_keys_ordered_for_shortcuts)
        total_btns_w = (btn_w * num_btns) + (btn_sp * (num_btns - 1))
        btn_y = piano_actual_bottom_y + 25
        cur_btn_x = self.piano_origin_x + (self.piano_total_width_of_white_keys_area - total_btns_w) // 2
        self.song_buttons = {}
        for skey in self.song_keys_ordered_for_shortcuts:
            if skey in self.song_data:
                data = self.song_data[skey]
                self.song_buttons[skey] = {"rect": pygame.Rect(cur_btn_x, btn_y, btn_w, btn_h),
                                           "label": data["display_name"], "key": skey}
                cur_btn_x += btn_w + btn_sp
        self.song_button_color, self.song_button_text_color, self.song_button_border_color = (0, 100, 180), (255, 255,
                                                                                                             255), (200,
                                                                                                                    200,
                                                                                                                    200)

        self.mixer_ok = False
        try:
            if not pygame.mixer.get_init(): pygame.mixer.init()
            if pygame.mixer.get_init(): self.mixer_ok = True
        except Exception as e:
            print(f"警告：Piano12Keys：pygame.mixer 初始化時發生錯誤: {e}")

        if self.mixer_ok:
            for idx, name in SOUND_INDEX_TO_KEY_NAME.items():
                if name in SOUND_FILES:
                    try:
                        self.key_sounds[idx] = pygame.mixer.Sound(SOUND_FILES[name])
                    except Exception as e:
                        print(f"警告：Piano12Keys：載入音效 '{SOUND_FILES[name]}' 時發生錯誤: {e}")

        self.bpm = 120;
        self.min_bpm = 40;
        self.max_bpm = 240;
        self.bpm_step = 5
        self._recalculate_beat_interval()
        self.last_beat_time_ms = 0;
        self.metronome_on = False;
        self.metronome_sound = None
        if self.mixer_ok:
            try:
                self.metronome_sound = pygame.mixer.Sound("metronome_tick.wav")
            except (pygame.error, FileNotFoundError):
                self.metronome_sound = None
            except Exception:
                self.metronome_sound = None
        self.metronome_visual_flash = False;
        self.metronome_visual_flash_duration_ms = 60;
        self.metronome_visual_flash_end_time_ms = 0

        self.playback_state = "IDLE";
        self.recorded_events = [];
        self.recording_start_time_ms = 0
        self.playback_start_time_ms = 0;
        self.next_event_index_to_play = 0
        self.playback_key_flash_duration_ms = 150;
        self.playback_flashing_keys = {}
        self.ear_training_active = False
        self.ear_training_current_key_index = None
        self.ear_training_player_has_answered = False
        self.ear_training_feedback_message = ""
        self.ear_training_feedback_end_time_ms = 0
        self.ear_training_score = 0
        self.ear_training_total_questions = 0
        self.ear_training_feedback_duration_ms = 2500
        # --- ---

    def _recalculate_beat_interval(self):
        if self.bpm > 0:
            self.beat_interval_ms = 60000.0 / self.bpm
        else:
            self.beat_interval_ms = float('inf')

    def _play_sound(self, idx, for_playback=False, for_ear_training_question=False, for_ear_training_answer=False):
        should_play = False
        if for_playback or for_ear_training_question:
            should_play = True
        elif self.ear_training_active and for_ear_training_answer:
            should_play = True
        elif not self.ear_training_active and self.playback_state != "PLAYBACK":
            should_play = True

        if should_play:
            if 0 <= idx < len(self.key_sounds) and self.key_sounds[idx] and self.mixer_ok:
                try:
                    self.key_sounds[idx].play()
                except pygame.error as e:
                    print(f"錯誤：播放音效索引 {idx} 時: {e}")

    def _record_key_event(self, key_index):
        if self.playback_state == "RECORDING" and not self.ear_training_active:
            current_time_ms = pygame.time.get_ticks()
            timestamp = current_time_ms - self.recording_start_time_ms
            self.recorded_events.append({'time': timestamp, 'key_index': key_index})

    def _trigger_playback_key_visual(self, key_index):
        self.playback_flashing_keys[key_index] = pygame.time.get_ticks() + self.playback_key_flash_duration_ms

    def _toggle_song_sheet_music(self, skey_or_index):
        actual_song_key = None
        if isinstance(skey_or_index, int):
            if 0 <= skey_or_index < len(self.song_keys_ordered_for_shortcuts):
                actual_song_key = self.song_keys_ordered_for_shortcuts[skey_or_index]
        elif isinstance(skey_or_index, str):
            actual_song_key = skey_or_index
        if not actual_song_key or actual_song_key not in self.song_data: return

        if self.ear_training_active: self.ear_training_active = False; self.ear_training_feedback_message = ""
        if self.playback_state != "IDLE": self.playback_state = "IDLE"; print("已退出錄製/回放模式")

        if self.show_sheet_music and self.active_song_notes_key == actual_song_key:
            self.show_sheet_music, self.active_song_notes_key = False, None
        else:
            self.active_song_notes_key, self.show_sheet_music = actual_song_key, True

    def _start_new_ear_training_question(self):
        if not self.ear_training_active: return
        self.ear_training_current_key_index = random.choice(range(12))
        self._play_sound(self.ear_training_current_key_index, for_ear_training_question=True)
        self.ear_training_player_has_answered = False
        self.ear_training_feedback_message = "What the sound is..."
        self.ear_training_feedback_end_time_ms = 0

    def _check_ear_training_answer(self, player_key_index):
        if not self.ear_training_active or self.ear_training_player_has_answered: return

        self.ear_training_player_has_answered = True
        self.ear_training_total_questions += 1
        correct_note_name = SOUND_INDEX_TO_KEY_NAME.get(self.ear_training_current_key_index, "未知")
        player_note_name = SOUND_INDEX_TO_KEY_NAME.get(player_key_index, "未知")
        if player_key_index == self.ear_training_current_key_index:
            self.ear_training_feedback_message = f"Correct!Is {correct_note_name}"
            self.ear_training_score += 1
        else:
            self.ear_training_feedback_message = f"Wrong! Answer: {correct_note_name}, Not: {player_note_name}"
        self.ear_training_feedback_end_time_ms = pygame.time.get_ticks() + self.ear_training_feedback_duration_ms

    def handle_event(self, event):
        actual_pygame_key = None
        if hasattr(event, 'key') and isinstance(event.key, int) and \
                (event.key in WHITE_KEY_CODES or \
                 event.key in BLACK_KEY_CODES or \
                 event.key in [pygame.K_ESCAPE, pygame.K_i, pygame.K_o, pygame.K_p, pygame.K_m,
                               pygame.K_EQUALS, pygame.K_MINUS, pygame.K_PLUS, pygame.K_UNDERSCORE,
                               pygame.K_r, pygame.K_l, pygame.K_PERIOD]):
            actual_pygame_key = event.key
        elif hasattr(event, 'key') and event.key is not None and event.key in self.CV_CHAR_TO_PYGAME_KEY_MAP:
            if event.key == ord('.'):
                actual_pygame_key = pygame.K_PERIOD
            else:
                actual_pygame_key = self.CV_CHAR_TO_PYGAME_KEY_MAP.get(event.key)
        if event.type == pygame.KEYDOWN and actual_pygame_key:
            if actual_pygame_key == pygame.K_PERIOD:
                self.ear_training_active = not self.ear_training_active
                if self.ear_training_active:
                    self.playback_state = "IDLE"
                    self.metronome_on = False;
                    self.metronome_visual_flash = False
                    self.show_sheet_music = False;
                    self.active_song_notes_key = None
                    self.ear_training_score = 0;
                    self.ear_training_total_questions = 0
                    self._start_new_ear_training_question()
                    print("練耳模式已開啟。")
                else:
                    self.ear_training_feedback_message = ""
                    print("練耳模式已關閉。")
                return

            if self.ear_training_active:
                if not self.ear_training_player_has_answered:
                    key_index_answered = -1
                    if actual_pygame_key in WHITE_KEY_CODES:
                        key_index_answered = WHITE_KEY_CODES.index(actual_pygame_key)
                    else:
                        bk_map_idx = 0
                        for i, kc in enumerate(BLACK_KEY_CODES):
                            if kc and actual_pygame_key == kc:
                                key_index_answered = 7 + bk_map_idx
                                break
                            if kc: bk_map_idx += 1
                    if key_index_answered != -1:
                        self._play_sound(key_index_answered, for_ear_training_answer=True)
                        self._check_ear_training_answer(key_index_answered)
                return
            if actual_pygame_key == pygame.K_m:
                self.metronome_on = not self.metronome_on
                if self.metronome_on:
                    self.last_beat_time_ms = pygame.time.get_ticks()
                else:
                    self.metronome_visual_flash = False
                return
            elif actual_pygame_key == pygame.K_EQUALS or actual_pygame_key == pygame.K_PLUS:
                self.bpm = min(self.max_bpm, self.bpm + self.bpm_step);
                self._recalculate_beat_interval();
                return
            elif actual_pygame_key == pygame.K_MINUS or actual_pygame_key == pygame.K_UNDERSCORE:
                self.bpm = max(self.min_bpm, self.bpm - self.bpm_step);
                self._recalculate_beat_interval();
                return
            elif actual_pygame_key == pygame.K_r:
                if self.playback_state == "IDLE":
                    self.playback_state = "RECORDING";
                    self.recorded_events = [];
                    self.recording_start_time_ms = pygame.time.get_ticks();
                    print("開始錄製...")
                elif self.playback_state == "RECORDING":
                    self.playback_state = "IDLE";
                    print(f"停止錄製。共錄製 {len(self.recorded_events)} 個音符。")
                return
            elif actual_pygame_key == pygame.K_l:
                if self.playback_state == "IDLE" and self.recorded_events:
                    self.playback_state = "PLAYBACK";
                    self.playback_start_time_ms = pygame.time.get_ticks();
                    self.next_event_index_to_play = 0;
                    self.playback_flashing_keys.clear();
                    print("開始回放...")
                elif not self.recorded_events:
                    print("沒有錄音可供回放。")
                return

            if actual_pygame_key == pygame.K_ESCAPE:
                if self.show_sheet_music: self.show_sheet_music, self.active_song_notes_key = False, None; return
            elif actual_pygame_key == pygame.K_i:
                self._toggle_song_sheet_music(0); return
            elif actual_pygame_key == pygame.K_o:
                self._toggle_song_sheet_music(1); return
            elif actual_pygame_key == pygame.K_p:
                self._toggle_song_sheet_music(2); return

            key_index_pressed = -1
            is_down, processed = True, False
            for i, kc in enumerate(WHITE_KEY_CODES):
                if actual_pygame_key == kc:
                    if not self.pressed[i]: self.pressed[i] = is_down; self._play_sound(i); key_index_pressed = i
                    processed = True;
                    break
            if not processed:
                bk_map_idx = 0
                for i, kc in enumerate(BLACK_KEY_CODES):
                    if kc and actual_pygame_key == kc:
                        target_idx = 7 + bk_map_idx
                        if not self.pressed[target_idx]: self.pressed[target_idx] = is_down; self._play_sound(
                            target_idx); key_index_pressed = target_idx
                        processed = True;
                        break
                    if kc: bk_map_idx += 1
            if key_index_pressed != -1: self._record_key_event(key_index_pressed)

        elif event.type == pygame.KEYUP and actual_pygame_key:
            if self.playback_state != "PLAYBACK" and not self.ear_training_active:  # 回放和練耳模式不處理玩家的 keyup 以改變 pressed 狀態
                is_down, processed = False, False
                for i, kc in enumerate(WHITE_KEY_CODES):
                    if actual_pygame_key == kc: self.pressed[i] = is_down; processed = True; break
                if not processed:
                    bk_map_idx = 0
                    for i, kc in enumerate(BLACK_KEY_CODES):
                        if kc and actual_pygame_key == kc: self.pressed[
                            7 + bk_map_idx] = is_down; processed = True; break
                        if kc: bk_map_idx += 1

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.ear_training_active:
                if not self.ear_training_player_has_answered:
                    key_index_clicked_answer = -1
                    (x, y) = event.pos;
                    mouse_processed_answer = False
                    bk_map_idx_answer = 0
                    for i_layout, bk_name in enumerate(BLACK_KEYS_DISPLAY):
                        if bk_name:
                            rect_x = self.piano_origin_x + self.black_key_x_offset_in_slot + i_layout * self.key_white_width
                            bk_rect = pygame.Rect(rect_x, self.key_black_y, self.key_black_width, self.key_black_height)
                            target_idx = 7 + bk_map_idx_answer
                            if bk_rect.collidepoint(x, y):
                                self._play_sound(target_idx, for_ear_training_answer=True)
                                self._check_ear_training_answer(target_idx)
                                mouse_processed_answer = True;
                                break
                            bk_map_idx_answer += 1
                    if not mouse_processed_answer:
                        for i, wk_name in enumerate(WHITE_KEYS):
                            rect_x = self.piano_origin_x + i * self.key_white_width
                            wk_rect = pygame.Rect(rect_x, self.key_white_y, self.key_white_width, self.key_white_height)
                            if wk_rect.collidepoint(x, y):
                                self._play_sound(i, for_ear_training_answer=True)
                                self._check_ear_training_answer(i)
                                break
                return
            for sk, bi in self.song_buttons.items():
                if bi["rect"].collidepoint(event.pos): self._toggle_song_sheet_music(bi["key"]); return
            key_index_clicked = -1
            is_down, (x, y), mouse_processed = True, event.pos, False
            bk_map_idx = 0
            for i_layout, bk_name in enumerate(BLACK_KEYS_DISPLAY):
                if bk_name:
                    rect_x = self.piano_origin_x + self.black_key_x_offset_in_slot + i_layout * self.key_white_width
                    bk_rect = pygame.Rect(rect_x, self.key_black_y, self.key_black_width, self.key_black_height)
                    target_idx = 7 + bk_map_idx
                    if bk_rect.collidepoint(x, y):
                        if not self.pressed[target_idx]: self.pressed[target_idx] = is_down; self._play_sound(
                            target_idx); key_index_clicked = target_idx
                        mouse_processed = True;
                        break
                    bk_map_idx += 1
            if not mouse_processed:
                for i, wk_name in enumerate(WHITE_KEYS):
                    rect_x = self.piano_origin_x + i * self.key_white_width
                    wk_rect = pygame.Rect(rect_x, self.key_white_y, self.key_white_width, self.key_white_height)
                    if wk_rect.collidepoint(x, y):
                        if not self.pressed[i]: self.pressed[i] = is_down; self._play_sound(i); key_index_clicked = i
                        break
            if key_index_clicked != -1: self._record_key_event(key_index_clicked)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.playback_state != "PLAYBACK" and not self.ear_training_active:
                for i in range(len(self.pressed)): self.pressed[i] = False

    def _draw_ingame_instructions(self, surface):
        if not self.instruction_font_ingame: return
        instructions = [
            "操作說明:", "白鍵:A,S,D,F,G,H,J", "黑鍵:W,E,T,Y,U",
            "樂譜:I,O,P(開/關)", "節拍器:M (BPM: +/-)",
            "錄製:R", "回放:L",
            "練耳: . (句號)",
            "ESC:返回"
        ]
        text_color = (220, 220, 220)
        if not surface: return
        surface_width = surface.get_width()
        max_instr_width = 0
        rendered_surfaces = []
        for text_line in instructions:
            try:
                s = self.instruction_font_ingame.render(text_line, True, text_color)
                rendered_surfaces.append(s)
                if s.get_width() > max_instr_width: max_instr_width = s.get_width()
            except Exception:
                rendered_surfaces.append(None)
        padding_x_right = 8;
        padding_y_top = 3
        start_x = surface_width - max_instr_width - padding_x_right
        if start_x < 5: start_x = 5
        start_y = padding_y_top
        line_height = self.instruction_font_ingame.get_linesize()
        bg_padding_around_text = 2
        bg_width = max_instr_width + 2 * bg_padding_around_text
        bg_height = (line_height * len(rendered_surfaces)) + (2 * bg_padding_around_text) - (
                    line_height - self.instruction_font_ingame.get_linesize()) if rendered_surfaces else 0

        if bg_width > 0 and bg_height > 0:
            try:
                instr_bg_surf = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
                instr_bg_surf.fill((20, 20, 20, 160))
                surface.blit(instr_bg_surf, (start_x - bg_padding_around_text, start_y - bg_padding_around_text))
            except Exception:
                pass
        current_y = start_y
        for text_surf in rendered_surfaces:
            if text_surf:
                try:
                    surface.blit(text_surf, (start_x, current_y))
                except Exception:
                    pass
            current_y += line_height

    def update(self):
        super().update()
        current_time_ms = pygame.time.get_ticks()
        if self.ear_training_active:
            if self.ear_training_player_has_answered and \
                    self.ear_training_feedback_end_time_ms != 0 and \
                    current_time_ms >= self.ear_training_feedback_end_time_ms:
                self._start_new_ear_training_question()
        if self.metronome_on and self.playback_state != "PLAYBACK" and not self.ear_training_active:
            if current_time_ms - self.last_beat_time_ms >= self.beat_interval_ms:
                if self.metronome_sound:
                    try:
                        self.metronome_sound.play()
                    except pygame.error:
                        self.metronome_sound = None
                self.last_beat_time_ms = current_time_ms
                self.metronome_visual_flash = True
                self.metronome_visual_flash_end_time_ms = current_time_ms + self.metronome_visual_flash_duration_ms
        if self.metronome_visual_flash and current_time_ms >= self.metronome_visual_flash_end_time_ms:
            self.metronome_visual_flash = False
        if self.playback_state == "PLAYBACK" and not self.ear_training_active:
            current_playback_time_ms = current_time_ms - self.playback_start_time_ms
            keys_to_remove_from_flash = [k for k, end_time in self.playback_flashing_keys.items() if
                                         current_time_ms >= end_time]
            for k_idx in keys_to_remove_from_flash: del self.playback_flashing_keys[k_idx]
            if self.next_event_index_to_play < len(self.recorded_events):
                next_event = self.recorded_events[self.next_event_index_to_play]
                if current_playback_time_ms >= next_event['time']:
                    key_to_play = next_event['key_index']
                    self._play_sound(key_to_play, for_playback=True)
                    self._trigger_playback_key_visual(key_to_play)
                    self.next_event_index_to_play += 1
            elif not self.playback_flashing_keys:
                self.playback_state = "IDLE";
                print("回放結束。")

    def render(self):
        if not self.screen: return
        self.screen.fill((60, 60, 60))
        for i in range(len(WHITE_KEYS)):
            is_playback_flashing = i in self.playback_flashing_keys
            key_is_pressed = self.pressed[i] or (self.playback_state == "PLAYBACK" and is_playback_flashing)
            color = (220, 220, 220) if not key_is_pressed else (180, 180, 255)
            wk_rx = self.piano_origin_x + i * self.key_white_width
            pygame.draw.rect(self.screen, color, (wk_rx, self.key_white_y, self.key_white_width, self.key_white_height))
            pygame.draw.rect(self.screen, (0, 0, 0),
                             (wk_rx, self.key_white_y, self.key_white_width, self.key_white_height), 2)
            try:
                lbl_s = self.font.render(WHITE_KEYS[i], True, (0, 0, 0)); self.screen.blit(lbl_s, (wk_rx + (
                            self.key_white_width - lbl_s.get_width()) // 2, self.white_key_label_y))
            except Exception as e:
                print(f"渲染白鍵標籤'{WHITE_KEYS[i]}'錯誤:{e}")
        bk_actual_idx = 0
        for i_layout, bk_name in enumerate(BLACK_KEYS_DISPLAY):
            if bk_name:
                target_idx = 7 + bk_actual_idx
                is_playback_flashing_bk = target_idx in self.playback_flashing_keys
                key_is_pressed_bk = self.pressed[target_idx] or (
                            self.playback_state == "PLAYBACK" and is_playback_flashing_bk)
                color = (30, 30, 30) if not key_is_pressed_bk else (80, 80, 180)
                bk_rx = self.piano_origin_x + self.black_key_x_offset_in_slot + i_layout * self.key_white_width
                pygame.draw.rect(self.screen, color,
                                 (bk_rx, self.key_black_y, self.key_black_width, self.key_black_height))
                pygame.draw.rect(self.screen, (0, 0, 0),
                                 (bk_rx, self.key_black_y, self.key_black_width, self.key_black_height), 2)
                try:
                    lbl_s = self.font.render(bk_name, True, (255, 255, 255)); self.screen.blit(lbl_s, (bk_rx + (
                                self.key_black_width - lbl_s.get_width()) // 2, self.black_key_label_y))
                except Exception as e:
                    print(f"渲染黑鍵標籤'{bk_name}'錯誤:{e}")
                bk_actual_idx += 1
        for sk, bi in self.song_buttons.items():
            try:
                pygame.draw.rect(self.screen, self.song_button_color, bi["rect"])
                pygame.draw.rect(self.screen, self.song_button_border_color, bi["rect"], 2)
                tc = (255, 223,
                      0) if self.show_sheet_music and self.active_song_notes_key == sk else self.song_button_text_color
                btn_txt_s = self.font.render(bi["label"], True, tc);
                self.screen.blit(btn_txt_s, btn_txt_s.get_rect(center=bi["rect"].center))
            except Exception as e:
                print(f"渲染歌曲按鈕'{bi['label']}'錯誤:{e}")
        if self.show_sheet_music and self.active_song_notes_key and self.active_song_notes_key in self.song_data:
            song_phrases_to_display = self.song_data[self.active_song_notes_key]["phrases"]
            first_button_rect = None
            if self.song_buttons and self.song_keys_ordered_for_shortcuts:
                first_button_key = self.song_keys_ordered_for_shortcuts[0]
                if first_button_key in self.song_buttons: first_button_rect = self.song_buttons[first_button_key][
                    "rect"]
            sheet_music_y_start = first_button_rect.bottom + 15 if first_button_rect else self.screen.get_height() // 2
            line_h = self.sheet_music_font.get_linesize() + 3
            current_y = sheet_music_y_start
            center_x_for_sheet = self.screen.get_width() // 2
            for phrase_string in song_phrases_to_display:
                if not phrase_string.strip(): continue
                try:
                    sheet_text_surf = self.sheet_music_font.render(phrase_string, True, (220, 220, 220))
                    text_rect = sheet_text_surf.get_rect();
                    text_rect.top = current_y;
                    text_rect.centerx = center_x_for_sheet
                    self.screen.blit(sheet_text_surf, text_rect)
                except Exception as e:
                    print(f"渲染樂譜行'{phrase_string}'錯誤:{e}")
                current_y += line_h
                if current_y > self.screen.get_height() - line_h: break
        visual_rect_size = 25
        visual_rect_pos_x = 10;
        visual_rect_pos_y = 10
        if self.metronome_on and not self.ear_training_active:
            if self.metronome_visual_flash and self.playback_state != "PLAYBACK":
                pygame.draw.rect(self.screen, (255, 255, 0),
                                 (visual_rect_pos_x, visual_rect_pos_y, visual_rect_size, visual_rect_size))
            elif self.playback_state != "PLAYBACK":
                pygame.draw.rect(self.screen, (180, 180, 0),
                                 (visual_rect_pos_x, visual_rect_pos_y, visual_rect_size, visual_rect_size))
            try:
                bpm_text = f"BPM: {self.bpm}"
                bpm_surf = self.ui_font.render(bpm_text, True, (220, 220, 220))
                bpm_pos_x = visual_rect_pos_x + visual_rect_size + 10
                bpm_pos_y = visual_rect_pos_y + (visual_rect_size - bpm_surf.get_height()) // 2
                if self.playback_state != "PLAYBACK":
                    self.screen.blit(bpm_surf, (bpm_pos_x, bpm_pos_y))
            except Exception:
                pass
        status_text = ""
        if not self.ear_training_active:
            if self.playback_state == "RECORDING":
                status_text = "RECORDING..."
            elif self.playback_state == "PLAYBACK":
                status_text = "PLAYING..."
        if status_text:
            try:
                status_surf = self.ui_font.render(status_text, True, (255, 100, 100))
                status_pos_x = visual_rect_pos_x
                status_pos_y = visual_rect_pos_y + visual_rect_size + 5
                self.screen.blit(status_surf, (status_pos_x, status_pos_y))
            except Exception:
                pass
        if self.ear_training_active:
            title_text = "Ear_Training"
            score_text = f"Score: {self.ear_training_score} / {self.ear_training_total_questions}"
            try:
                title_surf = self.ui_font.render(title_text, True, (100, 255, 100))
                score_surf = self.ui_font.render(score_text, True, (200, 200, 255))
                title_rect = title_surf.get_rect(centerx=self.screen.get_width() // 2, top=visual_rect_pos_y + 5)
                self.screen.blit(title_surf, title_rect)
                score_rect = score_surf.get_rect(centerx=self.screen.get_width() // 2, top=title_rect.bottom + 5)
                self.screen.blit(score_surf, score_rect)
                if self.ear_training_feedback_message:
                    feedback_surf = self.ui_font.render(self.ear_training_feedback_message, True, (255, 255, 100))
                    feedback_rect = feedback_surf.get_rect(centerx=self.screen.get_width() // 2,
                                                           top=score_rect.bottom + 10)
                    self.screen.blit(feedback_surf, feedback_rect)
            except Exception as e:
                print(f"渲染練耳UI失敗: {e}")
        self._draw_ingame_instructions(self.screen)


if __name__ == '__main__':
    pygame.init()
    pygame.font.init()
    if not pygame.mixer.get_init(): pygame.mixer.init()
    SCREEN_WIDTH_STANDALONE = 800
    SCREEN_HEIGHT_STANDALONE = 600
    standalone_screen = pygame.display.set_mode((SCREEN_WIDTH_STANDALONE, SCREEN_HEIGHT_STANDALONE))
    pygame.display.set_caption("Piano12Keys - Standalone Test")
    piano_game_standalone = Piano12Keys(standalone_screen)
    running_standalone = True
    clock_standalone = pygame.time.Clock()
    while running_standalone:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running_standalone = False
            piano_game_standalone.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not piano_game_standalone.show_sheet_music and not piano_game_standalone.ear_training_active:
                running_standalone = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and piano_game_standalone.ear_training_active:
                piano_game_standalone.ear_training_active = False
                piano_game_standalone.ear_training_feedback_message = ""
        piano_game_standalone.update()
        piano_game_standalone.render()

        pygame.display.flip()
        clock_standalone.tick(60)

    pygame.quit()