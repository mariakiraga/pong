# server.py — Breakout multiplayer server

import socket
import threading
import pickle
import pygame
import random
import math
import sys
import struct

# ================== BASE CONFIG ==================
WIDTH, HEIGHT = 1280, 720
BALL_START_SPEED = 450
BALL_SPEED_INCREMENT = 20
BALL_MAX_SPEED = 900

TEST_MODE = False # for code testing set to True

DEFAULT_NICKNAMES = ["Gracz 1", "Gracz 2"]

# ================== HELPERS ==================
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

# ================== OBJECT CLASSES ==================
class BallLogic:
    def __init__(self):
        self.radius = 14
        self.start_speed = BALL_START_SPEED
        self.speed = self.start_speed
        self.pos = pygame.Vector2(WIDTH // 2, HEIGHT // 2)
        self.direction = pygame.Vector2(1, -1).normalize()

    @property
    def rect(self):
        return pygame.Rect(
            self.pos.x - self.radius, self.pos.y - self.radius,
            self.radius * 2, self.radius * 2)

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
        self.direction = pygame.Vector2(
            math.sin(math.radians(angle)),
            -abs(math.cos(math.radians(angle)))).normalize()


class PaddleLogic:
    def __init__(self):
        self.width = 120
        self.height = 20
        self.speed = 750
        self.rect = pygame.Rect((WIDTH - self.width) // 2, HEIGHT - 60,
                                 self.width, self.height)

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
        rows = random.randint(5, 8)
        cols = random.randint(10, 11)
        width, height, padding, offset_top = 100, 35, 15, 80
        offset_left = (WIDTH - (width + padding) * cols) // 2

        for row in range(rows):
            for col in range(cols):
                x = col * (width + padding) + offset_left
                y = row * (height + padding) + offset_top
                color_obj = pygame.Color(0)
                color_obj.hsva = (row * 30, 80, 100, 100)
                rgb = (color_obj.r, color_obj.g, color_obj.b)
                self.bricks.append({
                    "rect": pygame.Rect(x, y, width, height),
                    "color": rgb,
                    "alive": True,
                    "row": row,       # sent to client for row-based coloring
                })

    def remaining(self):
        return sum(1 for b in self.bricks if b["alive"])


class PlayerGame:
    def __init__(self, player_id):
        self.id = player_id
        self.ball = BallLogic()
        self.paddle = PaddleLogic()
        self.bricks = BrickFieldLogic()
        self.score = 0
        self.current_action = "NONE"
        self.falling_powerups = []
        self.sabotage_to_send = None

    def update(self, dt):
        self.paddle.update(dt, self.current_action)
        self.ball.update(dt)

        if self.ball.rect.colliderect(self.paddle.rect):
            self.ball.reflect_from_paddle(self.paddle.rect)

        for brick in self.bricks.bricks:
            if brick["alive"] and self.ball.rect.colliderect(brick["rect"]):
                brick["alive"] = False
                self.ball.direction.y *= -1
                self.score += 1
                self.ball.increase_speed()
                if random.random() < 0.10:
                    self.falling_powerups.append({
                        "rect": pygame.Rect(
                            brick["rect"].centerx - 10,
                            brick["rect"].bottom, 20, 20),
                        "type": "MYSTERY_BOX"
                    })
                break

        for pu in self.falling_powerups[:]:
            pu["rect"].y += 150 * dt
            if pu["rect"].colliderect(self.paddle.rect):
                self.sabotage_to_send = pu["type"]
                self.score += 1
                self.falling_powerups.remove(pu)
            elif pu["rect"].y > HEIGHT:
                self.falling_powerups.remove(pu)


# ================== SERVER GAME STATE ==================
class ServerGameState:
    def __init__(self, nicknames=None):
        self.round = 1
        self.max_rounds = 5
        self.games = {0: PlayerGame(0), 1: PlayerGame(1)}
        self.state_msg = "WAITING FOR PLAYERS"
        self.playing = False
        self.game_over = False

        self.intermission = False
        self.players_ready = {0: False, 1: False}
        self.stats = {
            0: {"buff_self": 0, "buff_other": 0, "nerf_self": 0, "nerf_other": 0},
            1: {"buff_self": 0, "buff_other": 0, "nerf_self": 0, "nerf_other": 0},
        }

        self.dilemma_active = False
        self.dilemma_player = None
        self.dilemma_time = 0.0
        self.dilemma_scenario = ""
        self.dilemma_texts = ("", "")

        # Nicknames: list of 2 strings, index = player_id
        self.nicknames = nicknames if nicknames else list(DEFAULT_NICKNAMES)

    # ---- Nicknames ----
    def set_nickname(self, player_id, name):
        """Sanitise and store a nickname for player_id."""
        name = name.strip()[:20] or DEFAULT_NICKNAMES[player_id]
        self.nicknames[player_id] = name
        print(f"Gracz {player_id} ustawił nick: '{name}'")

    # ---- Round management ----
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

    # ---- Dilemma ----
    def trigger_dilemma(self, player_id):
        self.dilemma_active = True
        self.dilemma_player = player_id
        self.dilemma_time = 2.0
        self.effect_type = random.choice(["PADDLE", "BALL", "SCORE"])

        # Use actual nicknames in the dilemma text
        my_nick  = self.nicknames[player_id]
        opp_nick = self.nicknames[1 - player_id]

        if random.random() < 0.5:
            self.dilemma_scenario = "BUFF"
            if self.effect_type == "PADDLE":
                self.dilemma_texts = (
                    f"[1] Paletka +20 ({my_nick})",
                    f"[2] Paletka +60 ({opp_nick})")
            elif self.effect_type == "BALL":
                self.dilemma_texts = (
                    f"[1] Piłka wolniej ({my_nick})",
                    f"[2] Piłka b. wolno ({opp_nick})")
            else:
                self.dilemma_texts = (
                    f"[1] +2 Punkty ({my_nick})",
                    f"[2] +5 Punktów ({opp_nick})")
        else:
            self.dilemma_scenario = "NERF"
            if self.effect_type == "PADDLE":
                self.dilemma_texts = (
                    f"[1] Paletka -20 ({my_nick})",
                    f"[2] Paletka -60 ({opp_nick})")
            elif self.effect_type == "BALL":
                self.dilemma_texts = (
                    f"[1] Piłka szybciej ({my_nick})",
                    f"[2] Piłka b. szybko ({opp_nick})")
            else:
                self.dilemma_texts = (
                    f"[1] -2 Punkty ({my_nick})",
                    f"[2] -5 Punktów ({opp_nick})")

    def apply_dilemma_choice(self, player_id, choice):
        other_id = 1 - player_id
        p_game = self.games[player_id]
        o_game = self.games[other_id]

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

        p_game.paddle.rect.width = p_game.paddle.width
        o_game.paddle.rect.width = o_game.paddle.width
        self.dilemma_active = False

    def apply_penalty(self, player_id):
        game = self.games[player_id]
        penalty_type = random.choice(["PADDLE", "BALL", "SCORE"])
        if penalty_type == "PADDLE":
            game.paddle.width = max(30, game.paddle.width - 70)
        elif penalty_type == "BALL":
            game.ball.speed = min(BALL_MAX_SPEED, game.ball.speed + 250)
        elif penalty_type == "SCORE":
            game.score = max(0, game.score - 10)
        game.paddle.rect.width = game.paddle.width
        self.dilemma_active = False

    # ---- Physics tick ----
    def update_physics(self, dt):
        if not self.playing:
            return

        if self.intermission:
            required_ready = 1 if TEST_MODE else 2
            ready_count = sum(1 for p_id in self.players_ready if self.players_ready[p_id])
            if ready_count >= required_ready:
                self.intermission = False
                self.players_ready = {0: False, 1: False}
                self.start_round()
            return

        if self.dilemma_active:
            self.dilemma_time -= dt
            chooser_game = self.games[self.dilemma_player]
            if chooser_game.current_action in ["1", "2"]:
                self.apply_dilemma_choice(self.dilemma_player, chooser_game.current_action)
                chooser_game.current_action = "NONE"
            elif self.dilemma_time <= 0:
                print(f"Gracz {self.dilemma_player} zaspał! Nakładam karę.")
                self.apply_penalty(self.dilemma_player)
            return

        self.games[0].update(dt)
        self.games[1].update(dt)

        if self.games[0].sabotage_to_send == "MYSTERY_BOX":
            self.trigger_dilemma(0)
            self.games[0].sabotage_to_send = None
        elif self.games[1].sabotage_to_send == "MYSTERY_BOX":
            self.trigger_dilemma(1)
            self.games[1].sabotage_to_send = None

        if (self.games[0].ball.pos.y > HEIGHT or self.games[1].ball.pos.y > HEIGHT or
                self.games[0].bricks.remaining() == 0 or self.games[1].bricks.remaining() == 0):
            self.round += 1
            if self.round > self.max_rounds:
                self.playing = False
                self.game_over = True
                self.state_msg = "GAME OVER"
                self.print_stats_to_console()
            else:
                self.intermission = True
                self.players_ready = {0: False, 1: False}
                self.print_stats_to_console()

    # ---- State snapshot for client ----
    def get_state_for_player(self, player_id):
        my_game  = self.games[player_id]
        opp_game = self.games[1 - player_id]
        return {
            "round":            self.round,
            "msg":              self.state_msg,
            "my_score":         my_game.score,
            "opponent_score":   opp_game.score,
            "shared_score":     my_game.score + opp_game.score,
            "ball_pos":         (my_game.ball.pos.x, my_game.ball.pos.y),
            "ball_radius":      my_game.ball.radius,
            "paddle_rect":      my_game.paddle.rect,
            "bricks":           my_game.bricks.bricks,
            "powerups":         my_game.falling_powerups,
            "playing":          self.playing,
            "game_over":        self.game_over,
            "dilemma_active":   self.dilemma_active,
            "dilemma_player":   self.dilemma_player,
            "dilemma_time":     self.dilemma_time,
            "dilemma_texts":    self.dilemma_texts,
            "intermission":     self.intermission,
            "my_ready":         self.players_ready[player_id],
            "stats":            self.stats,
            # Nicknames — client uses these for all labels
            "my_nick":          self.nicknames[player_id],
            "opp_nick":         self.nicknames[1 - player_id],
            "nicknames":        list(self.nicknames),  # full list, useful for game-over screen
        }

    def print_stats_to_console(self):
        runda_nr = self.round - 1 if not self.game_over else self.max_rounds
        print(f"\n{'='*10} STATYSTYKI PO RUNDZIE {runda_nr} {'='*10}")
        for p_id in [0, 1]:
            s = self.stats[p_id]
            my_game  = self.games[p_id]
            opp_game = self.games[1 - p_id]
            nick = self.nicknames[p_id]
            print(f"--- {nick} (Gracz {p_id}) ---")
            print(f"  Ułatwienie dla siebie:          {s['buff_self']}")
            print(f"  Ułatwienie dla drugiego gracza: {s['buff_other']}")
            print(f"  Utrudnienie dla siebie:         {s['nerf_self']}")
            print(f"  Utrudnienie dla drugiego gracza:{s['nerf_other']}")
            print(f"  Wynik: {my_game.score}  |  Rywal: {opp_game.score}  |  Wspólny: {my_game.score + opp_game.score}")
        print("=" * 42 + "\n")


# ================== NETWORKING ==================
server_addr = "0.0.0.0"
port = 5555

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((server_addr, port))
s.listen(2)
s.settimeout(1.0)

game_state = ServerGameState()
connected_players = 0
state_lock = threading.Lock()


def handle_client(conn, player_id):
    """
    Handshake protocol (before game loop):
      1. Server sends player_id  (pickle int)
      2. Client sends nickname   (pickle str, e.g. "NICK:Kowalski")
      3. Server sends ACK        (pickle "OK")
    Then normal action/state loop begins.
    """
    global connected_players, game_state

    # Step 1 — send player id
    send_msg(conn, pickle.dumps(player_id))

    # Step 2 — receive nickname
    try:
        raw = recv_msg(conn)
        if raw:
            payload = pickle.loads(raw)
            if isinstance(payload, str) and payload.startswith("NICK:"):
                nick = payload[5:]
                with state_lock:
                    game_state.set_nickname(player_id, nick)
            # Step 3 — ACK
            send_msg(conn, pickle.dumps("OK"))
    except Exception as e:
        print(f"Błąd podczas handshake gracza {player_id}: {e}")

    # Main game loop
    while True:
        try:
            raw_data = recv_msg(conn)
            if not raw_data:
                break

            action = pickle.loads(raw_data)

            with state_lock:
                if action == "RESTART" and game_state.game_over:
                    # Preserve nicknames across restart
                    old_nicks = list(game_state.nicknames)
                    game_state = ServerGameState(nicknames=old_nicks)
                    print(f"Gracz {player_id} zrestartował serwer!")
                elif action == "READY" and game_state.intermission:
                    game_state.players_ready[player_id] = True
                else:
                    game_state.games[player_id].current_action = action

                state_data = game_state.get_state_for_player(player_id)

            send_msg(conn, pickle.dumps(state_data))

        except Exception as e:
            print(f"Błąd u Gracza {player_id}: {e}")
            break

    print(f"Utracono połączenie z Graczem {player_id} ({game_state.nicknames[player_id]})")
    with state_lock:
        connected_players -= 1
        old_nicks = list(game_state.nicknames)
        game_state = ServerGameState(nicknames=old_nicks)
    conn.close()


def physics_loop():
    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(60) / 1000.0
        required_players = 1 if TEST_MODE else 2

        with state_lock:
            if (connected_players >= required_players
                    and not game_state.playing
                    and not game_state.game_over):
                game_state.start_round()

            if game_state.playing and game_state.intermission:
                ready_count = sum(
                    1 for p_id in game_state.players_ready
                    if game_state.players_ready[p_id])
                if ready_count >= required_players:
                    game_state.intermission = False
                    game_state.players_ready = {0: False, 1: False}
                    game_state.start_round()
                continue

            # AI paddle for test mode (player 2)
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
print("Serwer wystartował. Oczekiwanie na graczy...")

try:
    while True:
        try:
            conn, addr = s.accept()
            with state_lock:
                p_id = connected_players
                connected_players += 1
            print(f"Połączono z: {addr}  →  Gracz {p_id}")
            threading.Thread(
                target=handle_client, args=(conn, p_id), daemon=True).start()
        except socket.timeout:
            pass
except KeyboardInterrupt:
    print("\n[!] Zamykanie serwera...")
    s.close()
    sys.exit()