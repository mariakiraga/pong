import socket
import threading
import pickle
import pygame
import random
import math
import time

# Konfiguracja bazowa fizyki
WIDTH, HEIGHT = 900, 600
BALL_START_SPEED = 320
BALL_SPEED_INCREMENT = 15
BALL_MAX_SPEED = 650

# --- KLASY FIZYKI (bez funkcji draw!) ---
class BallLogic:
    def __init__(self):
        self.radius = 10
        self.start_speed = BALL_START_SPEED
        self.speed = self.start_speed
        self.pos = pygame.Vector2(WIDTH // 2, HEIGHT // 2)
        self.direction = pygame.Vector2(1, -1).normalize()

    @property
    def rect(self):
        return pygame.Rect(self.pos.x - self.radius, self.pos.y - self.radius, self.radius * 2, self.radius * 2)

    def reset(self):
        self.pos = pygame.Vector2(WIDTH // 2, HEIGHT // 2)
        self.speed = self.start_speed
        self.direction = pygame.Vector2(random.uniform(-0.5, 0.5), -1).normalize()

    def increase_speed(self):
        self.speed = min(self.speed + BALL_SPEED_INCREMENT, BALL_MAX_SPEED)

    def update(self, dt):
        self.pos += self.direction * self.speed * dt
        if self.pos.x <= self.radius or self.pos.x >= WIDTH - self.radius:
            self.direction.x *= -1
        if self.pos.y <= self.radius:
            self.direction.y *= -1

    def reflect_from_paddle(self, paddle_rect):
        offset = (self.pos.x - paddle_rect.centerx) / (paddle_rect.width / 2)
        angle = offset * 60
        self.direction = pygame.Vector2(math.sin(math.radians(angle)), -abs(math.cos(math.radians(angle)))).normalize()


class PaddleLogic:
    def __init__(self):
        self.width = 130
        self.height = 15
        self.speed = 500
        self.rect = pygame.Rect((WIDTH - self.width) // 2, HEIGHT - 60, self.width, self.height)

    def update(self, dt, action):
        if action == "LEFT":
            self.rect.x -= self.speed * dt
        elif action == "RIGHT":
            self.rect.x += self.speed * dt
        self.rect.x = max(0, min(WIDTH - self.width, self.rect.x))


class BrickFieldLogic:
    def __init__(self):
        self.bricks = []
        self.create()

    def create(self):
        self.bricks.clear()
        rows, cols = random.randint(5, 8), random.randint(6, 10)
        width, height, padding, offset_top = 90, 30, 10, 60
        offset_left = (WIDTH - (width + padding) * cols) // 2

        for row in range(rows):
            for col in range(cols):
                x = col * (width + padding) + offset_left
                y = row * (height + padding) + offset_top
                
                # Zamiast obiektu pygame.Color przesyłamy krotkę RGB, jest bezpieczniejsza dla pickla
                color_obj = pygame.Color(0)
                color_obj.hsva = (row * 30, 80, 100, 100)
                rgb_color = (color_obj.r, color_obj.g, color_obj.b)
                
                self.bricks.append({"rect": pygame.Rect(x, y, width, height), "color": rgb_color, "alive": True})

    def remaining(self):
        return sum(1 for b in self.bricks if b["alive"])


# --- INSTANCJA GRY POJEDYNCZEGO GRACZA ---
class PlayerGame:
    def __init__(self, player_id):
        self.id = player_id
        self.ball = BallLogic()
        self.paddle = PaddleLogic()
        self.bricks = BrickFieldLogic()
        self.score = 0
        self.current_action = "NONE"
        
        # [POWERUP] NASZKICOWANA LOGIKA: Lista spadających powerupów u gracza
        self.falling_powerups = [] 
        # [POWERUP] Flaga informująca, co gracz złapał i co wyślemy rywalowi
        self.sabotage_to_send = None 

    def update(self, dt):
        self.paddle.update(dt, self.current_action)
        self.ball.update(dt)

        # Kolizje z paletką
        if self.ball.rect.colliderect(self.paddle.rect):
            self.ball.reflect_from_paddle(self.paddle.rect)

        # Kolizje z cegłami
        for brick in self.bricks.bricks:
            if brick["alive"] and self.ball.rect.colliderect(brick["rect"]):
                brick["alive"] = False
                self.ball.direction.y *= -1
                self.score += 1
                self.ball.increase_speed()
                
                # [POWERUP] Szansa 10% na wypadnięcie powerupu ze zbitej cegły
                if random.random() < 0.10: 
                    self.falling_powerups.append({
                        "rect": pygame.Rect(brick["rect"].centerx - 10, brick["rect"].bottom, 20, 20),
                        "type": "MYSTERY_BOX"
                    })
                break
        
        # [POWERUP] Aktualizacja spadających powerupów i sprawdzanie kolizji z paletką
        for pu in self.falling_powerups[:]:
            pu["rect"].y += 150 * dt # Prędkość spadania powerupa
            if pu["rect"].colliderect(self.paddle.rect):
                self.sabotage_to_send = pu["type"] # Przekazanie do głównego menedżera
                self.falling_powerups.remove(pu)
            elif pu["rect"].y > HEIGHT:
                self.falling_powerups.remove(pu)


# --- GŁÓWNY ZARZĄDCA (SERWER) ---
class ServerGameState:
    def __init__(self):
        self.round = 1
        self.max_rounds = 5
        self.games = {0: PlayerGame(0), 1: PlayerGame(1)}
        self.state_msg = "WAITING FOR PLAYERS"
        self.playing = False
        self.game_over = False

        # --- NOWE: Zmienne dla systemu dylematów ---
        self.dilemma_active = False
        self.dilemma_player = None # Kto dokonuje wyboru (0 lub 1)
        self.dilemma_time = 0.0
        self.dilemma_scenario = "" # "BUFF" lub "NERF"
        self.dilemma_texts = ("", "") # Teksty opcji 1 i 2

    def start_round(self):
        for p_id in [0, 1]:
            self.games[p_id].ball.reset()
            self.games[p_id].bricks.create()
            self.games[p_id].falling_powerups.clear()
            self.games[p_id].sabotage_to_send = None
            self.games[p_id].paddle.width = 130 
        self.playing = True
        self.dilemma_active = False
        self.state_msg = f"ROUND {self.round}"

    def trigger_dilemma(self, player_id):
        self.dilemma_active = True
        self.dilemma_player = player_id
        self.dilemma_time = 2.0
        
        # Losujemy rodzaj scenariusza
        if random.random() < 0.5:
            self.dilemma_scenario = "BUFF"
            self.dilemma_texts = (
                "[1] Małe ułatwienie dla Ciebie (Konkurencja)",
                "[2] Duże ułatwienie dla rywala (Kooperacja)"
            )
        else:
            self.dilemma_scenario = "NERF"
            self.dilemma_texts = (
                "[1] Małe utrudnienie dla Ciebie (Kooperacja)",
                "[2] Duże utrudnienie dla rywala (Konkurencja)"
            )

    def apply_dilemma_choice(self, player_id, choice):
        other_id = 1 if player_id == 0 else 0
        
        # Przykładowe efekty - modyfikujemy szerokość paletki
        if self.dilemma_scenario == "BUFF":
            if choice == "1":
                self.games[player_id].paddle.width += 20 # Słaby buff dla siebie
            elif choice == "2":
                self.games[other_id].paddle.width += 60  # Silny buff dla drugiego
        elif self.dilemma_scenario == "NERF":
            if choice == "1":
                self.games[player_id].paddle.width = max(50, self.games[player_id].paddle.width - 20) # Słaby nerf dla siebie
            elif choice == "2":
                self.games[other_id].paddle.width = max(50, self.games[other_id].paddle.width - 60) # Silny nerf dla drugiego

        # Zaktualizuj fizyczne wymiary paletek po nałożeniu efektów
        self.games[0].paddle.rect.width = self.games[0].paddle.width
        self.games[1].paddle.rect.width = self.games[1].paddle.width
        self.dilemma_active = False

    def update_physics(self, dt):
        if not self.playing: return

        # --- OBSŁUGA AKTYWNEGO DYLEMATU (PAUZA GRY) ---
        if self.dilemma_active:
            self.dilemma_time -= dt
            chooser_game = self.games[self.dilemma_player]
            
            # Sprawdź, czy gracz coś kliknął (klawisz "1" lub "2")
            if chooser_game.current_action in ["1", "2"]:
                self.apply_dilemma_choice(self.dilemma_player, chooser_game.current_action)
                chooser_game.current_action = "NONE"
            # Sprawdź, czy minął czas (kara!)
            elif self.dilemma_time <= 0:
                print(f"Gracz {self.dilemma_player} zaspał! Nakładam karę.")
                # Sroga kara za brak wyboru - zmniejszenie paletki
                chooser_game.paddle.width = max(40, chooser_game.paddle.width - 50)
                chooser_game.paddle.rect.width = chooser_game.paddle.width
                self.dilemma_active = False
            
            return # Przerwij funkcję - fizyka NIE JEST aktualizowana podczas wyboru!

        # --- NORMALNA AKTUALIZACJA FIZYKI ---
        self.games[0].update(dt)
        self.games[1].update(dt)

        # Sprawdzanie czy ktoś złapał skrzynkę
        if self.games[0].sabotage_to_send == "MYSTERY_BOX":
            self.trigger_dilemma(0)
            self.games[0].sabotage_to_send = None
        elif self.games[1].sabotage_to_send == "MYSTERY_BOX":
            self.trigger_dilemma(1)
            self.games[1].sabotage_to_send = None

        # Sprawdzanie warunków wygranej / przegranej w rundzie
        if self.games[0].ball.pos.y > HEIGHT or self.games[1].ball.pos.y > HEIGHT or \
           self.games[0].bricks.remaining() == 0 or self.games[1].bricks.remaining() == 0:
            self.round += 1
            if self.round > self.max_rounds:
                self.playing = False
                self.game_over = True
                self.state_msg = "GAME OVER"
            else:
                self.start_round()

    def get_state_for_player(self, player_id):
        my_game = self.games[player_id]
        other_game = self.games[1 if player_id == 0 else 0]
        
        # Pakujemy dane, dodając informacje o dylemacie
        return {
            "round": self.round,
            "msg": self.state_msg,
            "my_score": my_game.score,
            "opponent_score": other_game.score,
            "ball_pos": (my_game.ball.pos.x, my_game.ball.pos.y),
            "ball_radius": my_game.ball.radius,
            "paddle_rect": my_game.paddle.rect,
            "bricks": my_game.bricks.bricks,
            "powerups": my_game.falling_powerups,
            "playing": self.playing,
            "game_over": self.game_over,
            
            # Nowe dane wysyłane klientowi do wyświetlenia interfejsu
            "dilemma_active": self.dilemma_active,
            "dilemma_player": self.dilemma_player,
            "dilemma_time": self.dilemma_time,
            "dilemma_texts": self.dilemma_texts
        }


# --- PĘTLA SIECIOWA SERWERA ---
server = "0.0.0.0" # Nasłuchuj na wszystkich interfejsach
port = 5555

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((server, port))
s.listen(2)
print("Serwer wystartował. Oczekiwanie na graczy...")

game_state = ServerGameState()
connected_players = 0

def handle_client(conn, player_id):
    global connected_players
    # Wysyłamy klientowi jego ID (0 lub 1)
    conn.send(pickle.dumps(player_id))
    
    while True:
        try:
            # Odbieramy co gracz klika ("LEFT", "RIGHT", "NONE")
            action = pickle.loads(conn.recv(2048))
            if not action: break
            
            # Zapisujemy akcję do stanu gry
            game_state.games[player_id].current_action = action
            
            # Odsyłamy aktualny widok planszy
            conn.sendall(pickle.dumps(game_state.get_state_for_player(player_id)))
        except:
            break

    print(f"Utracono połączenie z Graczem {player_id}")
    connected_players -= 1
    conn.close()

# Uruchamiamy fizykę w tle jako osobny wątek
def physics_loop():
    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(60) / 1000.0
        if connected_players == 2 and not game_state.playing and not game_state.game_over:
            game_state.start_round()
        game_state.update_physics(dt)

threading.Thread(target=physics_loop, daemon=True).start()

# Akceptowanie połączeń
while True:
    conn, addr = s.accept()
    print("Połączono z:", addr)
    p_id = connected_players
    connected_players += 1
    threading.Thread(target=handle_client, args=(conn, p_id), daemon=True).start()