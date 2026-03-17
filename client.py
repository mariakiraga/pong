import pygame
from network import Network

# ================== CONFIG WIZUALNY ==================
pygame.init()
WIDTH, HEIGHT = 900, 600
BG_COLOR = (15, 18, 40)
WHITE = (240, 240, 240)
RED = (255, 80, 80)
POWERUP_COLOR = (50, 255, 50) # Zielony kolor dla powerupów

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Breakout - Tryb Multiplayer Sabotaż")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 24)
big_font = pygame.font.SysFont("arial", 64)

def draw_center_message(text):
    label = big_font.render(text, True, WHITE)
    rect = label.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(label, rect)

def main():
    n = Network()
    player_id = n.getP()
    if player_id is None:
        print("Nie udało się połączyć z serwerem!")
        return
        
    print(f"Zalogowano jako Gracz {player_id}")
    pygame.display.set_caption(f"Breakout - GRACZ {player_id + 1}")

    run = True
    while run:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        # --- ZBIERANIE KLAWISZY ---
        # --- ZBIERANIE KLAWISZY ---
        keys = pygame.key.get_pressed()
        action = "NONE"
        
        # Priorytet mają klawisze wyboru (1 i 2)
        if keys[pygame.K_1] or keys[pygame.K_KP1]: 
            action = "1"
        elif keys[pygame.K_2] or keys[pygame.K_KP2]: 
            action = "2"
        # Jeśli nie wciskamy cyfr, sprawdzamy strzałki
        elif keys[pygame.K_LEFT]: 
            action = "LEFT"
        elif keys[pygame.K_RIGHT]: 
            action = "RIGHT"

        # Komunikacja z serwerem
        state = n.send(action)
        if not state:
            break

        # ================== RYSOWANIE ==================
        screen.fill(BG_COLOR)

        if not state["playing"] and not state["game_over"]:
            draw_center_message("CZEKANIE NA DRUGIEGO GRACZA")
            
        elif state["game_over"]:
            draw_center_message("KONIEC GRY! Zobacz konsolę.") # Możesz to rozbudować

        else:
            # 1. Rysowanie cegieł, paletki i piłki
            for brick in state["bricks"]:
                if brick["alive"]:
                    pygame.draw.rect(screen, brick["color"], brick["rect"], border_radius=6)
            
            pygame.draw.rect(screen, WHITE, state["paddle_rect"], border_radius=8)
            pygame.draw.circle(screen, RED, state["ball_pos"], state["ball_radius"])

            for pu in state["powerups"]:
                pygame.draw.rect(screen, POWERUP_COLOR, pu["rect"])

            # 2. UI: Runda i Punkty
            round_txt = font.render(f"Runda: {state['round']}/5", True, WHITE)
            score_txt = font.render(f"Ja: {state['my_score']} | Rywal: {state['opponent_score']}", True, WHITE)
            screen.blit(round_txt, (20, 20))
            screen.blit(score_txt, (WIDTH - 200, 20))

            # --- 3. RYSOWANIE INTERFEJSU DYLEMATU ---
            if state["dilemma_active"]:
                # Półprzezroczyste tło przyciemniające grę podczas wyboru
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.set_alpha(150)
                overlay.fill((0, 0, 0))
                screen.blit(overlay, (0, 0))

                if state["dilemma_player"] == player_id:
                    # Ja wybieram!
                    timer_text = font.render(f"MASZ {state['dilemma_time']:.1f}s NA WYBÓR (1 lub 2) ALBO KARA!", True, RED)
                    opt1_text = font.render(state["dilemma_texts"][0], True, WHITE)
                    opt2_text = font.render(state["dilemma_texts"][1], True, WHITE)
                    
                    screen.blit(timer_text, (WIDTH // 2 - timer_text.get_width() // 2, HEIGHT // 2 - 60))
                    screen.blit(opt1_text, (WIDTH // 2 - opt1_text.get_width() // 2, HEIGHT // 2))
                    screen.blit(opt2_text, (WIDTH // 2 - opt2_text.get_width() // 2, HEIGHT // 2 + 40))
                else:
                    # Przeciwnik wybiera!
                    wait_text = font.render("PRZECIWNIK PODEJMUJE DECYZJĘ... CZEKAJ", True, WHITE)
                    screen.blit(wait_text, (WIDTH // 2 - wait_text.get_width() // 2, HEIGHT // 2))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()