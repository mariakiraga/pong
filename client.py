import pygame
from network import Network
import sys

# ================== CONFIG WIZUALNY ==================
pygame.init()
WIDTH, HEIGHT = 900, 600
BG_COLOR = (15, 18, 40)
WHITE = (240, 240, 240)
RED = (255, 80, 80)
POWERUP_COLOR = (50, 255, 50)
BUTTON_COLOR = (70, 70, 120)
BUTTON_HOVER = (100, 100, 160)

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
logical_surface = pygame.Surface((WIDTH, HEIGHT))
pygame.display.set_caption("Crashout - Menu")
clock = pygame.time.Clock()

font = pygame.font.SysFont("arial", 24)
title_font = pygame.font.SysFont("arial", 80, bold=True)
big_font = pygame.font.SysFont("arial", 64)

# ================== POMOCNICZE ==================
def draw_center_message(surface, text):
    label = big_font.render(text, True, WHITE)
    rect = label.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    surface.blit(label, rect)

def get_logical_mouse_pos():
    """Tłumaczy pozycję kursora na ekranie na pozycję wirtualnego płótna 900x600"""
    mx, my = pygame.mouse.get_pos()
    sw, sh = screen.get_size()
    return (mx * WIDTH / sw, my * HEIGHT / sh)

def draw_multiline_text(surface, text_list, x, y, font_type, color=WHITE, center_x=False):
    """Rysuje tekst linijka po linijce z podanej listy."""
    for i, line in enumerate(text_list):
        text_surf = font_type.render(line, True, color)
        if center_x:
            rect = text_surf.get_rect(centerx=x, top=y + i * 35) # 35 to odstęp między liniami
            surface.blit(text_surf, rect)
        else:
            surface.blit(text_surf, (x, y + i * 35))

# ================== KLASA PRZYCISKU ==================
class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.is_hovered = False

    def draw(self, surface):
        color = BUTTON_HOVER if self.is_hovered else BUTTON_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, WHITE, self.rect, width=2, border_radius=12) # Ramka
        
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


# ================== GŁÓWNA PĘTLA ==================
def main():
    # Zmienne Maszyny Stanów
    APP_STATE = "MAIN_MENU"  # Dostępne stany: MAIN_MENU, SETTINGS, PLAYING
    
    # Zmienne Sieciowe (Inicjalizowane dopiero po kliknięciu START)
    n = None
    player_id = None
    
    # Inicjalizacja Przycisków dla Menu
    btn_start = Button(WIDTH//2 - 100, 220, 200, 55, "START GRY")
    btn_settings = Button(WIDTH//2 - 100, 290, 200, 55, "USTAWIENIA")
    btn_help = Button(WIDTH//2 - 100, 360, 200, 55, "INSTRUKCJA") # NOWY PRZYCISK
    btn_quit = Button(WIDTH//2 - 100, 430, 200, 55, "WYJŚCIE")

    # Inicjalizacja Przycisków powrotu
    btn_back = Button(20, 20, 150, 50, "POWRÓT")

    run = True
    while run:
        clock.tick(60)
        logical_mouse = get_logical_mouse_pos()

        # ================== OBSŁUGA ZDARZEŃ (W ZALEŻNOŚCI OD STANU) ==================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

            if APP_STATE == "MAIN_MENU":
                # Aktualizacja hover
                btn_start.check_hover(logical_mouse)
                btn_settings.check_hover(logical_mouse)
                btn_help.check_hover(logical_mouse) # NOWE
                btn_quit.check_hover(logical_mouse)

                # Kliknięcia
                if btn_start.is_clicked(event, logical_mouse):
                    print("Łączenie z serwerem...")
                    # ... (reszta kodu startu zostaje bez zmian) ...
                
                elif btn_settings.is_clicked(event, logical_mouse):
                    APP_STATE = "SETTINGS"
                
                elif btn_help.is_clicked(event, logical_mouse): # NOWE
                    APP_STATE = "INSTRUCTIONS"
                
                elif btn_quit.is_clicked(event, logical_mouse):
                    run = False

            elif APP_STATE == "SETTINGS" or APP_STATE == "INSTRUCTIONS": # ZMODYFIKOWANE
                btn_back.check_hover(logical_mouse)
                if btn_back.is_clicked(event, logical_mouse):
                    APP_STATE = "MAIN_MENU"

        # ================== LOGIKA GRY (TYLKO JEŚLI GRAMY) ==================
        if APP_STATE == "PLAYING" and n is not None:
            keys = pygame.key.get_pressed()
            action = "NONE"
            
            if keys[pygame.K_1] or keys[pygame.K_KP1]: action = "1"
            elif keys[pygame.K_2] or keys[pygame.K_KP2]: action = "2"
            elif keys[pygame.K_r]: action = "RESTART"
            elif keys[pygame.K_LEFT]: action = "LEFT"
            elif keys[pygame.K_RIGHT]: action = "RIGHT"

            state = n.send(action)
            if not state:
                print("Utracono połączenie z serwerem, powrót do Menu.")
                APP_STATE = "MAIN_MENU"
                n = None
                pygame.display.set_caption("Crashout - Menu")


        # ================== RYSOWANIE (W ZALEŻNOŚCI OD STANU) ==================
        logical_surface.fill(BG_COLOR)

        if APP_STATE == "MAIN_MENU":
            # Tytuł gry
            title_surf = title_font.render("CRASHOUT", True, RED)
            title_rect = title_surf.get_rect(center=(WIDTH//2, 120))
            logical_surface.blit(title_surf, title_rect)
            
            # Przyciski
            btn_start.draw(logical_surface)
            btn_settings.draw(logical_surface)
            btn_help.draw(logical_surface) # NIE ZAPOMNIJ GO NARYSOWAĆ!
            btn_quit.draw(logical_surface)

        elif APP_STATE == "SETTINGS":
            title_surf = big_font.render("USTAWIENIA", True, WHITE)
            logical_surface.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, 50))
            btn_back.draw(logical_surface)
            
            # Miejsce na przyszłe opcje
            info_surf = font.render("Tutaj dodamy tryb Noc/Dzień i wpisywanie Nicku!", True, (150, 150, 150))
            logical_surface.blit(info_surf, (WIDTH//2 - info_surf.get_width()//2, HEIGHT//2))

        elif APP_STATE == "INSTRUCTIONS":
            title_surf = big_font.render("ZASADY GRY", True, WHITE)
            logical_surface.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, 40))
            btn_back.draw(logical_surface)
            
            # Tekst instrukcji
            rules_text = [
                "CEL GRY:",
                "Zbicie wszystkich cegiełek przed przeciwnikiem i nie upuszczenie piłki.",
                "",
                "STEROWANIE:",
                "Poruszaj paletką używając STRZAŁKI W LEWO i STRZAŁKI W PRAWO.",
                "",
                "POWER-UPY (MYSTERY BOX):",
                "Gdy zbijesz cegiełkę, może z niej wypaść zielony power-up.",
                "Złapanie go ZATRZYMUJE GRĘ na 2 sekundy. Pojawi się DYLEMAT.",
                "Musisz szybko wcisnąć klawisz [1] lub [2] na klawiaturze,",
                "aby nałożyć ułatwienie lub utrudnienie na siebie lub rywala.",
                "",
                "UWAGA: Jeśli nie podejmiesz decyzji w 2 sekundy, otrzymasz KARĘ!"
            ]
            
            # Rysujemy przygotowany tekst na środku ekranu
            draw_multiline_text(logical_surface, rules_text, WIDTH//2, 140, font, WHITE, center_x=True)
            
            # Ozdobny zielony power-up jako ikonka
            pygame.draw.rect(logical_surface, POWERUP_COLOR, (WIDTH//2 - 10, 520, 20, 20))

        elif APP_STATE == "PLAYING" and state:
            if not state["playing"] and not state["game_over"]:
                draw_center_message(logical_surface, "CZEKANIE NA DRUGIEGO GRACZA")
                
            elif state["game_over"]:
                draw_center_message(logical_surface, "KONIEC GRY! (Wciśnij R aby zrestartować)")
                
            elif state.get("intermission"):
                draw_center_message(logical_surface, f"KONIEC RUNDY! Następna za: {int(state['intermission_time'])}s")
                
            else:
                for brick in state["bricks"]:
                    if brick["alive"]:
                        pygame.draw.rect(logical_surface, brick["color"], brick["rect"], border_radius=6)
                
                pygame.draw.rect(logical_surface, WHITE, state["paddle_rect"], border_radius=8)
                pygame.draw.circle(logical_surface, RED, state["ball_pos"], state["ball_radius"])

                for pu in state["powerups"]:
                    pygame.draw.rect(logical_surface, POWERUP_COLOR, pu["rect"])

                round_txt = font.render(f"Runda: {state['round']}/5", True, WHITE)
                # score_txt = font.render(f"Ja: {state['my_score']} | Rywal: {state['opponent_score']}", True, WHITE)
                logical_surface.blit(round_txt, (20, 20))
                # logical_surface.blit(score_txt, (WIDTH - 200, 20))

                # --- INTERFEJS DYLEMATU ---
                if state["dilemma_active"]:
                    overlay = pygame.Surface((WIDTH, HEIGHT))
                    overlay.set_alpha(150)
                    overlay.fill((0, 0, 0))
                    logical_surface.blit(overlay, (0, 0))

                    if state["dilemma_player"] == player_id:
                        timer_text = font.render(f"MASZ {state['dilemma_time']:.1f}s NA WYBÓR (1 lub 2) ALBO KARA!", True, RED)
                        opt1_text = font.render(state["dilemma_texts"][0], True, WHITE)
                        opt2_text = font.render(state["dilemma_texts"][1], True, WHITE)
                        
                        logical_surface.blit(timer_text, (WIDTH // 2 - timer_text.get_width() // 2, HEIGHT // 2 - 60))
                        logical_surface.blit(opt1_text, (WIDTH // 2 - opt1_text.get_width() // 2, HEIGHT // 2))
                        logical_surface.blit(opt2_text, (WIDTH // 2 - opt2_text.get_width() // 2, HEIGHT // 2 + 40))
                    else:
                        wait_text = font.render("PRZECIWNIK PODEJMUJE DECYZJĘ... CZEKAJ", True, WHITE)
                        logical_surface.blit(wait_text, (WIDTH // 2 - wait_text.get_width() // 2, HEIGHT // 2))


        # ================== SKALOWANIE WIDOKU ==================
        current_window_size = screen.get_size()
        scaled_surface = pygame.transform.scale(logical_surface, current_window_size)
        screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()