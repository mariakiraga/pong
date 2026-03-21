# This file contains implementation of visual elements onto a gaming surface. 
# The game is designed as a state machine.
import pygame
from network import Network
import sys

# ================== VISUAL CONFIG ==================
pygame.init()
WIDTH, HEIGHT = 1280, 720 # set the same as in server
BG_COLOR = (15, 18, 40)
WHITE = (240, 240, 240)
RED = (255, 80, 80)
POWERUP_COLOR = (50, 255, 50)
BUTTON_COLOR = (70, 70, 120)
BUTTON_HOVER = (100, 100, 160)

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
logical_surface = pygame.Surface((WIDTH, HEIGHT))
pygame.display.set_caption("Breakout - Menu")
clock = pygame.time.Clock()

font = pygame.font.SysFont("arial", 32)
medium_font = pygame.font.SysFont("arial", 32, bold=True)
title_font = pygame.font.SysFont("arial", 100, bold=True)
big_font = pygame.font.SysFont("arial", 74)

# ================== HELPER FUNCTIONS ==================
def draw_center_message(surface, text):
    """Renders message in the middle of the screen surface."""
    label = big_font.render(text, True, WHITE)
    rect = label.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    surface.blit(label, rect)

def get_logical_mouse_pos():
    """Translates mouse position on actual surface to the virtual surface."""
    mx, my = pygame.mouse.get_pos()
    sw, sh = screen.get_size()
    return (mx * WIDTH / sw, my * HEIGHT / sh)

def draw_multiline_text(surface, text_list, x, y, font_type, color=WHITE, center_x=False):
    """Renders text line by line from an input list."""
    for i, line in enumerate(text_list):
        text_surf = font_type.render(line, True, color)
        if center_x:
            rect = text_surf.get_rect(centerx=x, top=y + i * 35)
            surface.blit(text_surf, rect)
        else:
            surface.blit(text_surf, (x, y + i * 35))

# ================== BUTTON ==================
class Button:
    """Class for rendering buttons and manage button events."""
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.is_hovered = False

    def draw(self, surface):
        color = BUTTON_HOVER if self.is_hovered else BUTTON_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, WHITE, self.rect, width=2, border_radius=12) 
        
        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def check_hover(self, logical_mouse_pos):
        self.is_hovered = self.rect.collidepoint(logical_mouse_pos)

    def is_clicked(self, event, logical_mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(logical_mouse_pos):
                return True
        return False


# ================== MAIN LOOP ==================
def main():
    # State machine variable
    APP_STATE = "MAIN_MENU"  
    
    # Network variables
    n = None
    player_id = None
    state = {}
    
    # Main menu buttons
    btn_start = Button(WIDTH//2 - 100, 220, 200, 55, "START GRY")
    btn_settings = Button(WIDTH//2 - 100, 290, 200, 55, "USTAWIENIA")
    btn_help = Button(WIDTH//2 - 100, 360, 200, 55, "INSTRUKCJA")
    btn_quit = Button(WIDTH//2 - 100, 430, 200, 55, "WYJŚCIE")
    # Back button
    btn_back = Button(20, 20, 150, 50, "POWRÓT")
    # Next round readiness button
    btn_ready = Button(WIDTH//2 - 125, HEIGHT - 100, 250, 60, "GOTOWE")

    # main loop
    run = True
    while run: 
        clock.tick(60)
        logical_mouse = get_logical_mouse_pos()
        
        action = "NONE"

        # ================== STATE HANDLING ==================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

            if APP_STATE == "MAIN_MENU":
                btn_start.check_hover(logical_mouse)
                btn_settings.check_hover(logical_mouse)
                btn_help.check_hover(logical_mouse)
                btn_quit.check_hover(logical_mouse)

                if btn_start.is_clicked(event, logical_mouse):
                    print("Łączenie z serwerem...")
                    n = Network()
                    player_id = n.getP()
                    if player_id is not None:
                        pygame.display.set_caption(f"Breakout - GRACZ {player_id + 1}")
                        APP_STATE = "PLAYING"
                    else:
                        print("Brak połączenia z serwerem!")
                
                elif btn_settings.is_clicked(event, logical_mouse):
                    APP_STATE = "SETTINGS"
                
                elif btn_help.is_clicked(event, logical_mouse):
                    APP_STATE = "INSTRUCTIONS"
                
                elif btn_quit.is_clicked(event, logical_mouse):
                    run = False

            elif APP_STATE == "SETTINGS" or APP_STATE == "INSTRUCTIONS":
                btn_back.check_hover(logical_mouse)
                if btn_back.is_clicked(event, logical_mouse):
                    APP_STATE = "MAIN_MENU"
            
            elif APP_STATE == "PLAYING" and state and state.get("intermission"):
                if not state.get("my_ready"):
                    if btn_ready.is_clicked(event, logical_mouse):
                        action = "READY"
       
        # Aktualizujemy podświetlenie guzika GOTOWE poza pętlą eventów
        if APP_STATE == "PLAYING" and state and state.get("intermission"):
            if not state.get("my_ready"):
                btn_ready.check_hover(logical_mouse)

        # ================== GAME LOGIC ==================
        if APP_STATE == "PLAYING" and n is not None:
            keys = pygame.key.get_pressed()

            if action != "READY":
                if keys[pygame.K_1] or keys[pygame.K_KP1]: action = "1" # choose buff/nerf for player
                elif keys[pygame.K_2] or keys[pygame.K_KP2]: action = "2" # choose buff/nerf for other player
                elif keys[pygame.K_r]: action = "RESTART"
                elif keys[pygame.K_LEFT]: action = "LEFT"
                elif keys[pygame.K_RIGHT]: action = "RIGHT"

            # UWAGA: Jeśli klient raz już był READY na serwerze, musimy podtrzymać ten stan,
            # by nie nadpisać go przez "NONE", dopóki trwa pauza.
            if state and state.get("intermission") and state.get("my_ready"):
                action = "READY"

            state = n.send(action)
            if not state:
                print("Utracono połączenie z serwerem, powrót do Menu.")
                APP_STATE = "MAIN_MENU"
                n = None
                pygame.display.set_caption("Breakout - Menu")

        # ================== DRAWING OBJECTS ON SURFACE ==================
        logical_surface.fill(BG_COLOR)

        if APP_STATE == "MAIN_MENU":
            title_surf = title_font.render("BREAKOUT", True, RED)
            title_rect = title_surf.get_rect(center=(WIDTH//2, 120))
            logical_surface.blit(title_surf, title_rect)
            
            btn_start.draw(logical_surface)
            btn_settings.draw(logical_surface)
            btn_help.draw(logical_surface)
            btn_quit.draw(logical_surface)

        elif APP_STATE == "SETTINGS":
            title_surf = big_font.render("USTAWIENIA", True, WHITE)
            logical_surface.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, 50))
            btn_back.draw(logical_surface)
            
            info_surf = font.render("Tutaj dodamy tryb Noc/Dzień i wpisywanie Nicku!", True, (150, 150, 150))
            logical_surface.blit(info_surf, (WIDTH//2 - info_surf.get_width()//2, HEIGHT//2))

        elif APP_STATE == "INSTRUCTIONS":
            title_surf = big_font.render("ZASADY GRY", True, WHITE)
            logical_surface.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, 40))
            btn_back.draw(logical_surface)
            
            rules_text = [
                "CEL GRY:",
                "Zbicie wszystkich cegiełek i nie upuszczenie piłki.",
                "",
                "STEROWANIE:",
                "Poruszaj paletką używając [STRZAŁKI W LEWO] i [STRZAŁKI W PRAWO].",
                "",
                "POWER-UPY (MYSTERY BOX):",
                "Gdy zbijesz cegiełkę, może z niej wypaść zielony power-up.",
                "Złapanie go ZATRZYMUJE GRĘ na 2 sekundy. Pojawi się DYLEMAT.",
                "Musisz szybko wcisnąć klawisz [1] lub [2] na klawiaturze,",
                "aby nałożyć ułatwienie lub utrudnienie na siebie lub drugiego gracza.",
                "",
                "UWAGA: Jeśli nie podejmiesz decyzji w 2 sekundy, otrzymasz KARĘ!"
            ]
            draw_multiline_text(logical_surface, rules_text, WIDTH//2, 140, font, WHITE, center_x=True)
            pygame.draw.rect(logical_surface, POWERUP_COLOR, (WIDTH//2 - 10, 520, 20, 20))

        elif APP_STATE == "PLAYING" and state:
            if not state["playing"] and not state["game_over"]:
                draw_center_message(logical_surface, "CZEKANIE NA DRUGIEGO GRACZA")
                
            elif state["game_over"]:
                draw_center_message(logical_surface, "KONIEC GRY! (Wciśnij R aby zrestartować)")
                
            # logic of the intermission between rounds
            elif state.get("intermission"):
                title_txt = big_font.render(f"KONIEC RUNDY {state['round'] - 1}", True, WHITE)
                logical_surface.blit(title_txt, (WIDTH // 2 - title_txt.get_width() // 2, 60))

                my_stats = state["stats"][player_id]
                opp_id = 1 if player_id == 0 else 0
                opp_stats = state["stats"][opp_id]

                # table for stats
                table_w, table_h = 800, 350
                table_x, table_y = WIDTH//2 - table_w//2, 160
                
                # Tło tabeli z obramowaniem
                pygame.draw.rect(logical_surface, (25, 30, 50), (table_x, table_y, table_w, table_h), border_radius=15)
                pygame.draw.rect(logical_surface, (100, 150, 255), (table_x, table_y, table_w, table_h), width=3, border_radius=15)
                
                # Kolumny (pozycje X dla centrowania tekstu)
                col1_x = table_x + 150 # Kategoria
                col2_x = table_x + 450 # Dla siebie
                col3_x = table_x + 650 # Dla rywala
                
                # Rysowanie linii podziału pionowego i poziomego
                pygame.draw.line(logical_surface, (70, 80, 110), (col1_x + 150, table_y), (col1_x + 150, table_y + table_h), 2)
                pygame.draw.line(logical_surface, (70, 80, 110), (col2_x + 100, table_y), (col2_x + 100, table_y + table_h), 2)
                pygame.draw.line(logical_surface, (100, 150, 255), (table_x, table_y + 60), (table_x + table_w, table_y + 60), 3)

                # Nagłówki
                def draw_cell(text, x, y, color=WHITE, f=font):
                    txt_surf = f.render(text, True, color)
                    logical_surface.blit(txt_surf, (x - txt_surf.get_width()//2, y))

                draw_cell("Wybory", col1_x, table_y + 15, (200, 200, 200))
                draw_cell("Dla Siebie", col2_x, table_y + 15, POWERUP_COLOR)
                draw_cell("Dla Rywala", col3_x, table_y + 15, RED)

                # Wiersze z danymi
                y_start = table_y + 80
                gap = 50
                
                # Moje decyzje
                draw_cell("Twoje Ułatwienia", col1_x, y_start)
                draw_cell(str(my_stats['buff_self']), col2_x, y_start)
                draw_cell(str(my_stats['buff_other']), col3_x, y_start)

                draw_cell("Twoje Utrudnienia", col1_x, y_start + gap)
                draw_cell(str(my_stats['nerf_self']), col2_x, y_start + gap)
                draw_cell(str(my_stats['nerf_other']), col3_x, y_start + gap)
                
                pygame.draw.line(logical_surface, (70, 80, 110), (table_x, y_start + gap + 40), (table_x + table_w, y_start + gap + 40), 1)

                # Decyzje rywala
                draw_cell("Drugi gracz: Ułatwienia", col1_x, y_start + gap*2)
                draw_cell(str(opp_stats['buff_self']), col2_x, y_start + gap*2)
                draw_cell(str(opp_stats['buff_other']), col3_x, y_start + gap*2)

                draw_cell("Drugi gracz: Utrudnienia", col1_x, y_start + gap*3)
                draw_cell(str(opp_stats['nerf_self']), col2_x, y_start + gap*3)
                draw_cell(str(opp_stats['nerf_other']), col3_x, y_start + gap*3)

                # --- WYNIKI: NEUTRALNE POZYCJONOWANIE ---
                y_scores = table_y + table_h + 35 # Pozycja Y dla wyników pod tabelą

                # 1. Indywidualne wyniki (mniejsze, po bokach)
                my_score_txt = font.render(f"Twój wynik: {state['my_score']}", True, WHITE)
                opp_score_txt = font.render(f"Wynik rywala: {state['opponent_score']}", True, WHITE)
                
                # 2. Wspólny wynik (większy, wyśrodkowany, neutralny kolor)
                shared_score_txt = medium_font.render(f"Wspólny wynik: {state['shared_score']}", True, (255, 255, 255))

                # Pozycjonowanie: Lewo, Środek, Prawo (wyrównane do krawędzi tabeli)
                logical_surface.blit(my_score_txt, (table_x, y_scores + 10)) # Do lewej krawędzi
                logical_surface.blit(shared_score_txt, (WIDTH // 2 - shared_score_txt.get_width() // 2, y_scores)) # Idealnie na środku
                logical_surface.blit(opp_score_txt, (table_x + table_w - opp_score_txt.get_width(), y_scores + 10)) # Do prawej krawędzi
                
                # Przycisk Gotowe lub tekst oczekiwania (ten kod już masz poniżej)
                if state["my_ready"]:
                    wait_txt = font.render("Oczekiwanie na drugiego gracza...", True, (150, 150, 150))
                    logical_surface.blit(wait_txt, (WIDTH // 2 - wait_txt.get_width() // 2, HEIGHT - 70))
                else:
                    btn_ready.draw(logical_surface)

            else:
                for brick in state["bricks"]:
                    if brick["alive"]:
                        pygame.draw.rect(logical_surface, brick["color"], brick["rect"], border_radius=6)
                
                pygame.draw.rect(logical_surface, WHITE, state["paddle_rect"], border_radius=8)
                pygame.draw.circle(logical_surface, RED, state["ball_pos"], state["ball_radius"])

                for pu in state["powerups"]:
                    pygame.draw.rect(logical_surface, POWERUP_COLOR, pu["rect"])

                round_txt = font.render(f"Runda: {state['round']}/5", True, WHITE)
                logical_surface.blit(round_txt, (20, 20))

                # logic for the dilemma intermission
                if state["dilemma_active"]:
                    overlay = pygame.Surface((WIDTH, HEIGHT))
                    overlay.set_alpha(150)
                    overlay.fill((0, 0, 0))
                    logical_surface.blit(overlay, (0, 0))

                    if state["dilemma_player"] == player_id:
                        timer_text = font.render(f"MASZ {state['dilemma_time']:.1f}s NA PODJĘCIE DECYZJI", True, RED)
                        # opt1_text = font.render(state["dilemma_texts"][0], True, WHITE)
                        # opt2_text = font.render(state["dilemma_texts"][1], True, WHITE)
                        opt1_text = font.render(state["dilemma_texts"][0], True, (0, 255, 0))
                        opt2_text = font.render(state["dilemma_texts"][1], True, (0, 0, 255))
                        
                        logical_surface.blit(timer_text, (WIDTH // 2 - timer_text.get_width() // 2, HEIGHT // 2 - 60))
                        logical_surface.blit(opt1_text, (WIDTH // 2 - opt1_text.get_width() // 2, HEIGHT // 2))
                        logical_surface.blit(opt2_text, (WIDTH // 2 - opt2_text.get_width() // 2, HEIGHT // 2 + 40))
                    else:
                        wait_text = font.render("PRZECIWNIK PODEJMUJE DECYZJĘ... CZEKAJ", True, WHITE)
                        logical_surface.blit(wait_text, (WIDTH // 2 - wait_text.get_width() // 2, HEIGHT // 2))


        # ================== SCREEN SCALING ==================
        current_window_size = screen.get_size()
        scaled_surface = pygame.transform.smoothscale(logical_surface, current_window_size)
        screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()