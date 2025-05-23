import pygame
from whac_a_mole import WhacAMole
from taiko_drum import TaikoDrum
from piano_12keys import Piano12Keys

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

games = {
    "Whac-A-Mole": WhacAMole(),
    # Taiko Drum 不要傳 screen，直接用 OpenCV 版本
    "Taiko Drum": None,
    "12-Key Piano": Piano12Keys(screen)
}
current_game = None
font = pygame.font.SysFont(None, 48)

def show_lobby():
    screen.fill((30, 30, 30))
    y = 150
    for i, name in enumerate(games):
        text = font.render(f"{i + 1}. {name}", True, (255, 255, 255))
        screen.blit(text, (100, y))
        y += 80
    pygame.display.flip()

def main_loop():
    global current_game

    while True:
        if current_game is None:
            show_lobby()
        else:
            # 特別處理 Taiko Drum
            if current_game == "Taiko Drum":
                TaikoDrum().main_loop()
                current_game = None
                continue
            else:
                current_game.update()
                current_game.render()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if current_game is None:
                    if event.key == pygame.K_1:
                        current_game = games["Whac-A-Mole"]
                    elif event.key == pygame.K_2:
                        current_game = "Taiko Drum"
                    elif event.key == pygame.K_3:
                        current_game = games["12-Key Piano"]
                else:
                    if event.key == pygame.K_ESCAPE:
                        current_game = None  # 回到選單
                    else:
                        if current_game != "Taiko Drum":
                            current_game.handle_event(event)
            elif event.type == pygame.KEYUP:
                if current_game and current_game != "Taiko Drum":
                    current_game.handle_event(event)

        clock.tick(30)

if __name__ == "__main__":
    main_loop()

