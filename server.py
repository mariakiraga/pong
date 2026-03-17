import socket
import threading
import pickle
import pygame
import random
import math
import sys
import struct

# Konfiguracja bazowa fizyki
WIDTH, HEIGHT = 900, 600
BALL_START_SPEED = 320
BALL_SPEED_INCREMENT = 15
BALL_MAX_SPEED = 650

# ==========================================
# TRYB TESTOWY (Solo + Bot)
# Ustaw na False, gdy chcesz zagrać z prawdziwym znajomym!
TEST_MODE = True  
# ==========================================

def send_msg(sock, msg):
    msg = struct.pack('>I', len(msg)) + msg
    sock.sendall(msg)

def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def recv_msg(sock):
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    return recvall(sock, msglen)

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
        
        # [POWERUP] Lista spadających powerupów u gracza
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
        self.intermission = False
        self.intermission_time = 0.0
        self.stats = {
            0: {"buff_self": 0, "buff_other": 0, "nerf_self": 0, "nerf_other": 0},
            1: {"buff_self": 0, "buff_other": 0, "nerf_self": 0, "nerf_other": 0}
        }

        # --- Zmienne dla systemu dylematów ---
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
        self.dilemma_time = 2.0  # Dokładnie 2 sekundy na decyzję
        
        # Losujemy kategorię modyfikacji
        self.effect_type = random.choice(["PADDLE", "BALL", "SCORE"])
        
        if random.random() < 0.5:
            self.dilemma_scenario = "BUFF"
            if self.effect_type == "PADDLE":
                self.dilemma_texts = ("[1] Paletka +20 (Dla mnie)", "[2] Paletka +60 (Dla rywala)")
            elif self.effect_type == "BALL":
                self.dilemma_texts = ("[1] Piłka wolniej (Dla mnie)", "[2] Piłka b. wolno (Dla rywala)")
            else:
                self.dilemma_texts = ("[1] +2 Punkty (Dla mnie)", "[2] +5 Punktów (Dla rywala)")
        else:
            self.dilemma_scenario = "NERF"
            if self.effect_type == "PADDLE":
                self.dilemma_texts = ("[1] Paletka -20 (Dla mnie)", "[2] Paletka -60 (Dla rywala)")
            elif self.effect_type == "BALL":
                self.dilemma_texts = ("[1] Piłka szybciej (Dla mnie)", "[2] Piłka b. szybko (Dla rywala)")
            else:
                self.dilemma_texts = ("[1] -2 Punkty (Dla mnie)", "[2] -5 Punktów (Dla rywala)")

    def apply_dilemma_choice(self, player_id, choice):
        other_id = 1 if player_id == 0 else 0
        p_game = self.games[player_id]
        o_game = self.games[other_id]

        # --- ZAPISYWANIE STATYSTYK ---
        if self.dilemma_scenario == "BUFF":
            if choice == "1":
                self.stats[player_id]["buff_self"] += 1
            elif choice == "2":
                self.stats[player_id]["buff_other"] += 1
        elif self.dilemma_scenario == "NERF":
            if choice == "1":
                self.stats[player_id]["nerf_self"] += 1
            elif choice == "2":
                self.stats[player_id]["nerf_other"] += 1

        if self.dilemma_scenario == "BUFF":
            target = p_game if choice == "1" else o_game
            power = "SMALL" if choice == "1" else "BIG"
            
            if self.effect_type == "PADDLE":
                target.paddle.width += 20 if power == "SMALL" else 60
            elif self.effect_type == "BALL":
                target.ball.speed = max(150, target.ball.speed - (50 if power == "SMALL" else 150))
            elif self.effect_type == "SCORE":
                target.score += 2 if power == "SMALL" else 5

        elif self.dilemma_scenario == "NERF":
            target = p_game if choice == "1" else o_game
            power = "SMALL" if choice == "1" else "BIG"
            
            if self.effect_type == "PADDLE":
                target.paddle.width = max(40, target.paddle.width - (20 if power == "SMALL" else 60))
            elif self.effect_type == "BALL":
                target.ball.speed = min(BALL_MAX_SPEED, target.ball.speed + (80 if power == "SMALL" else 200))
            elif self.effect_type == "SCORE":
                target.score = max(0, target.score - (2 if power == "SMALL" else 5))

        # Zaktualizuj fizyczne wymiary prostokątów kolizji obu graczy
        p_game.paddle.rect.width = p_game.paddle.width
        o_game.paddle.rect.width = o_game.paddle.width
        self.dilemma_active = False

    def apply_penalty(self, player_id):
        # KARA ZA BRAK DECYZJI
        game = self.games[player_id]
        penalty_type = random.choice(["PADDLE", "BALL", "SCORE"])
        
        if penalty_type == "PADDLE":
            game.paddle.width = max(30, game.paddle.width - 70) # Mikroskopijna paletka
        elif penalty_type == "BALL":
            game.ball.speed = min(BALL_MAX_SPEED, game.ball.speed + 250) # Błyskawiczna piłka
        elif penalty_type == "SCORE":
            game.score = max(0, game.score - 10) # Duża strata punktów
            
        game.paddle.rect.width = game.paddle.width
        self.dilemma_active = False

    def update_physics(self, dt):
        if not self.playing: return

        # --- OBSŁUGA PAUZY MIĘDZY RUNDAMI ---
        if self.intermission:
            self.intermission_time -= dt
            if self.intermission_time <= 0:
                self.intermission = False
                self.start_round()
            return # Zatrzymujemy fizykę podczas pauzy!

        # --- OBSŁUGA AKTYWNEGO DYLEMATU (PAUZA GRY) ---
        if self.dilemma_active:
            self.dilemma_time -= dt
            chooser_game = self.games[self.dilemma_player]
            
            if chooser_game.current_action in ["1", "2"]:
                self.apply_dilemma_choice(self.dilemma_player, chooser_game.current_action)
                chooser_game.current_action = "NONE"
            elif self.dilemma_time <= 0:
                print(f"Gracz {self.dilemma_player} zaspał! Nakładam losową karę.")
                self.apply_penalty(self.dilemma_player)
                
            return # Zatrzymujemy fizykę (pauza)

        # Reszta aktualizacji fizyki
        self.games[0].update(dt)
        self.games[1].update(dt)

        if self.games[0].sabotage_to_send == "MYSTERY_BOX":
            self.trigger_dilemma(0)
            self.games[0].sabotage_to_send = None
        elif self.games[1].sabotage_to_send == "MYSTERY_BOX":
            self.trigger_dilemma(1)
            self.games[1].sabotage_to_send = None

        # WARUNEK KOŃCA RUNDY
        if self.games[0].ball.pos.y > HEIGHT or self.games[1].ball.pos.y > HEIGHT or \
           self.games[0].bricks.remaining() == 0 or self.games[1].bricks.remaining() == 0:
            
            self.round += 1
            if self.round > self.max_rounds:
                self.playing = False
                self.game_over = True
                self.state_msg = "GAME OVER"
                self.print_stats_to_console() # Wypisz statystyki na koniec gry
            else:
                self.intermission = True
                self.intermission_time = 5.0 # 5 sekund przerwy na statystyki
                self.print_stats_to_console() # Wypisz statystyki po rundzie

    def get_state_for_player(self, player_id):
        my_game = self.games[player_id]
        other_game = self.games[1 if player_id == 0 else 0]
        
        return {
            "round": self.round,
            "msg": self.state_msg,
            "my_score": my_game.score,
            "opponent_score": other_game.score,
            "shared_score": my_game.score+other_game.score,
            "ball_pos": (my_game.ball.pos.x, my_game.ball.pos.y),
            "ball_radius": my_game.ball.radius,
            "paddle_rect": my_game.paddle.rect,
            "bricks": my_game.bricks.bricks,
            "powerups": my_game.falling_powerups,
            "playing": self.playing,
            "game_over": self.game_over,
            "dilemma_active": self.dilemma_active,
            "dilemma_player": self.dilemma_player,
            "dilemma_time": self.dilemma_time,
            "dilemma_texts": self.dilemma_texts,
            "dilemma_time": self.dilemma_time,
            "dilemma_texts": self.dilemma_texts,
            "intermission": self.intermission,
            "intermission_time": self.intermission_time
        }
    
    def print_stats_to_console(self):
        runda_nr = self.round - 1 if not self.game_over else self.max_rounds
        print(f"\n{'='*10} STATYSTYKI PO RUNDZIE {runda_nr} {'='*10}")
        for p_id in [0, 1]:
            s = self.stats[p_id]
            my_game = self.games[p_id]
            other_game = self.games[1 if p_id == 0 else 1 - p_id]
            print(f"--- GRACZ {p_id} ---")
            print(f"Ułatwienie dla siebie : {s['buff_self']}")
            print(f"Ułatwienie dla drugiego gracza : {s['buff_other']}")
            print(f"Utrudnienie dla siebie: {s['nerf_self']}")
            print(f"Utrudnienie dla drugiego gracza: {s['nerf_other']}")
            print(f"Twój wynik: {my_game.score}")
            print(f"Wynik drugiego gracza: {other_game.score}")
            print(f"Wspólny wynik: {my_game.score+other_game.score}")

        print("==========================================\n")


# --- PĘTLA SIECIOWA SERWERA ---
server = "0.0.0.0" 
port = 5555

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((server, port))
s.listen(2)
# Przypisujemy timeout tutaj
s.settimeout(1.0)

game_state = ServerGameState()
connected_players = 0

def handle_client(conn, player_id):
    global connected_players
    
    send_msg(conn, pickle.dumps(player_id))
    
    while True:
        try:
            raw_data = recv_msg(conn)
            if not raw_data: 
                break
                
            action = pickle.loads(raw_data)
            game_state.games[player_id].current_action = action
            
            state_data = game_state.get_state_for_player(player_id)
            send_msg(conn, pickle.dumps(state_data))
        except Exception as e:
            print(f"Błąd u Gracza {player_id}: {e}")
            break

    print(f"Utracono połączenie z Graczem {player_id}")
    connected_players -= 1
    conn.close()

# Uruchamiamy fizykę w tle jako osobny wątek
def physics_loop():
    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(60) / 1000.0
        
        # LOGIKA STARTU (TEST MODE LUB NORMALNIE)
        required_players = 1 if TEST_MODE else 2
        
        if connected_players >= required_players and not game_state.playing and not game_state.game_over:
            game_state.start_round()
            
        # AI DLA DRUGIEGO GRACZA W TRYBIE TESTOWYM
        if TEST_MODE and game_state.playing and connected_players == 1:
            p2 = game_state.games[1]
            if p2.paddle.rect.centerx < p2.ball.pos.x - 15:
                p2.current_action = "RIGHT"
            elif p2.paddle.rect.centerx > p2.ball.pos.x + 15:
                p2.current_action = "LEFT"
            else:
                p2.current_action = "NONE"
                
        game_state.update_physics(dt)

threading.Thread(target=physics_loop, daemon=True).start()

print("Serwer wystartował. Oczekiwanie na graczy... (Wciśnij Ctrl+C aby wyłączyć)")

try:
    while True:
        try:
            conn, addr = s.accept()
            print("Połączono z:", addr)
            p_id = connected_players
            connected_players += 1
            threading.Thread(target=handle_client, args=(conn, p_id), daemon=True).start()
        except socket.timeout:
            pass # Ignorujemy timeout, by system mógł przechwycić ewentualne Ctrl+C
            
except KeyboardInterrupt:
    print("\n[!] Wykryto Ctrl+C. Zamykanie serwera...")
    s.close()
    sys.exit()