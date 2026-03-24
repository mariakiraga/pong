# client.py — Breakout multiplayer client

import pygame
import sys
import math

# ================== PYGAME INIT ==================
pygame.init()
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
logical_surface = pygame.Surface((WIDTH, HEIGHT))
pygame.display.set_caption("Breakout")
clock = pygame.time.Clock()

# ================== COLOR PALETTE ==================
BG_COLOR        = (13,  17,  41)
CARD_COLOR      = (19,  23,  51)
CARD_BORDER     = (45,  54, 128)
CARD_BORDER_LT  = (80,  95, 190)
WHITE           = (197, 204, 232)
WHITE_DIM       = (110, 120, 160)
TEXT_MUTED      = ( 85,  95, 135)
RED             = (255,  96,  96)

# Neutral player colors: blue vs amber — equal visual weight, no rivalry implied.
# Player 0 = blue, Player 1 = amber.
PLAYER_COLORS = [
    (100, 160, 255),   # blue
    (255, 185,  60),   # amber
]
PLAYER_COLORS_DIM = [
    ( 30,  60, 140),
    (120,  70,  10),
]

POWERUP_COLOR   = ( 58, 255, 160)
POWERUP_DIM     = ( 30, 180, 110)

BUTTON_BG       = ( 30,  38, 100)
BUTTON_HOVER_BG = ( 50,  62, 145)
BUTTON_BORDER   = ( 80, 100, 200)
BUTTON_TEXT     = (190, 200, 240)

PADDLE_TOP      = (220, 228, 255)
PADDLE_MID      = (150, 168, 240)
PADDLE_BOT      = (100, 118, 200)
BALL_COLOR      = (255,  90,  90)

BRICK_ROWS = [
    ( 80, 140, 255),
    (120, 100, 235),
    (180,  80, 210),
    (230,  80, 125),
    (230, 110,  55),
]

# ================== FONTS ==================
font_sm  = pygame.font.SysFont("arial", 22)
font     = pygame.font.SysFont("arial", 28)
font_md  = pygame.font.SysFont("arial", 32, bold=True)
font_lg  = pygame.font.SysFont("arial", 58, bold=True)
font_xl  = pygame.font.SysFont("arial", 100, bold=True)

# ================== DRAW HELPERS ==================

def get_logical_mouse_pos():
    mx, my = pygame.mouse.get_pos()
    sw, sh = screen.get_size()
    return (mx * WIDTH / sw, my * HEIGHT / sh)


def draw_center_message(surface, text, color=WHITE, y=None):
    label = font_lg.render(text, True, color)
    if y is None:
        y = HEIGHT // 2 - label.get_height() // 2
    surface.blit(label, (WIDTH // 2 - label.get_width() // 2, y))


def draw_glow_circle(surface, color, pos, radius, alpha=55, rings=3):
    for i in range(rings, 0, -1):
        r = radius + i * 6
        glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, alpha // i), (r, r), r)
        surface.blit(glow, (pos[0] - r, pos[1] - r))
    pygame.draw.circle(surface, color, pos, radius)


def draw_glow_rect(surface, color, rect, radius=6, alpha=50, spread=8):
    glow = pygame.Surface((rect.width + spread * 2, rect.height + spread * 2), pygame.SRCALPHA)
    pygame.draw.rect(glow, (*color, alpha), glow.get_rect(), border_radius=radius + 4)
    surface.blit(glow, (rect.x - spread, rect.y - spread))


def draw_paddle(surface, rect):
    r = pygame.Rect(rect)
    third = max(r.height // 3, 1)
    pygame.draw.rect(surface, PADDLE_TOP, (r.x, r.y, r.width, third), border_radius=8)
    pygame.draw.rect(surface, PADDLE_MID, (r.x, r.y + third, r.width, third))
    pygame.draw.rect(surface, PADDLE_BOT,
                     (r.x, r.y + third * 2, r.width, r.height - third * 2), border_radius=8)
    shine = pygame.Surface((r.width - 24, 3), pygame.SRCALPHA)
    shine.fill((255, 255, 255, 60))
    surface.blit(shine, (r.x + 12, r.y + 3))
    pygame.draw.rect(surface, PADDLE_TOP, r, width=1, border_radius=8)


def draw_brick(surface, brick):
    rect = pygame.Rect(brick["rect"])
    row = brick.get("row", -1)
    color = BRICK_ROWS[row % len(BRICK_ROWS)] if row >= 0 else tuple(brick["color"][:3])
    draw_glow_rect(surface, color, rect, radius=6, alpha=30, spread=4)
    pygame.draw.rect(surface, color, rect, border_radius=6)
    hl = pygame.Surface((rect.width - 8, 3), pygame.SRCALPHA)
    hl.fill((255, 255, 255, 55))
    surface.blit(hl, (rect.x + 4, rect.y + 3))
    border_color = tuple(min(c + 40, 255) for c in color)
    pygame.draw.rect(surface, border_color, rect, width=1, border_radius=6)


def draw_powerup(surface, rect_data):
    rect = pygame.Rect(rect_data)
    draw_glow_rect(surface, POWERUP_COLOR, rect, radius=4, alpha=60, spread=6)
    pygame.draw.rect(surface, POWERUP_COLOR, rect, border_radius=4)
    inner = pygame.Rect(rect.x + 3, rect.y + 3, rect.width - 6, rect.height - 6)
    pygame.draw.rect(surface, POWERUP_DIM, inner, border_radius=2)
    cx, cy = rect.centerx, rect.centery
    pygame.draw.rect(surface, POWERUP_COLOR, (cx - 1, rect.y + 4, 2, rect.height - 8))
    pygame.draw.rect(surface, POWERUP_COLOR, (rect.x + 4, cy - 1, rect.width - 8, 2))


def draw_multiline(surface, lines, x, y, fnt, color=WHITE, center_x=False, spacing=36):
    for i, line in enumerate(lines):
        s = fnt.render(line, True, color)
        bx = x - s.get_width() // 2 if center_x else x
        surface.blit(s, (bx, y + i * spacing))


def draw_card(surface, x, y, w, h, br=14):
    pygame.draw.rect(surface, CARD_COLOR, (x, y, w, h), border_radius=br)
    pygame.draw.rect(surface, CARD_BORDER, (x, y, w, h), width=2, border_radius=br)


def draw_card_header(surface, x, y, w, h, text, fnt, br=14):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (30, 36, 90, 220), surf.get_rect(), border_radius=br)
    surface.blit(surf, (x, y))
    pygame.draw.line(surface, CARD_BORDER_LT, (x + 8, y + h - 1), (x + w - 8, y + h - 1), 1)
    lbl = fnt.render(text, True, WHITE)
    surface.blit(lbl, (x + w // 2 - lbl.get_width() // 2,
                        y + h // 2 - lbl.get_height() // 2))


def draw_separator(surface, x, y, w, color=CARD_BORDER, alpha=90):
    s = pygame.Surface((w, 1), pygame.SRCALPHA)
    s.fill((*color, alpha))
    surface.blit(s, (x, y))


def draw_stars(surface, tick):
    pts = [(53,211,3),(137,47,7),(239,103,11),(311,67,5),(421,159,9),(573,231,13),
           (641,81,7),(719,347,11),(853,119,5),(967,283,9),(1031,43,13),(1153,391,7),
           (1217,177,11),(83,513,5),(197,463,9),(347,601,13),(463,537,7),(619,483,11),
           (733,657,5),(877,593,9),(1009,641,13),(113,689,7),(251,71,11),(389,143,5)]
    for sx, sy, period in pts:
        b = int(90 + 60 * math.sin(tick / period))
        pygame.draw.circle(surface, (b, b, b + 30), (sx, sy), 1)


# ================== BUTTON ==================
class Button:
    def __init__(self, x, y, w, h, text):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.is_hovered = False

    def draw(self, surface, accent=None):
        bg = BUTTON_HOVER_BG if self.is_hovered else BUTTON_BG
        border = accent or BUTTON_BORDER
        if self.is_hovered:
            draw_glow_rect(surface, border, self.rect, radius=12, alpha=40, spread=7)
        pygame.draw.rect(surface, bg, self.rect, border_radius=12)
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=12)
        hl = pygame.Surface((self.rect.width - 24, 1), pygame.SRCALPHA)
        hl.fill((255, 255, 255, 35 if self.is_hovered else 18))
        surface.blit(hl, (self.rect.x + 12, self.rect.y + 2))
        t = font.render(self.text, True, BUTTON_TEXT)
        surface.blit(t, (self.rect.centerx - t.get_width() // 2,
                         self.rect.centery - t.get_height() // 2))

    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)

    def is_clicked(self, event, pos):
        return (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(pos))


# ================== NICKNAME ENTRY SCREEN ==================
class NicknameScreen:
    MAX_LEN = 16
    PLACEHOLDER = "Wpisz swój nick..."

    def __init__(self):
        self.text = ""
        self.done = False
        self.btn_ok = Button(WIDTH // 2 - 90, 428, 180, 54, "GOTOWE")

    def handle_event(self, event, logical_mouse):
        self.btn_ok.check_hover(logical_mouse)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self.text.strip():
                self.done = True
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif len(self.text) < self.MAX_LEN and event.unicode.isprintable():
                self.text += event.unicode
        if self.btn_ok.is_clicked(event, logical_mouse) and self.text.strip():
            self.done = True

    def get_nick(self):
        return self.text.strip() or "Anonim"

    def draw(self, surface, tick):
        surface.fill(BG_COLOR)
        draw_stars(surface, tick)

        title = font_lg.render("KIM JESTEŚ?", True, WHITE)
        surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 130))
        pygame.draw.rect(surface, CARD_BORDER,
                         (WIDTH // 2 - 160, 196, 320, 2), border_radius=1)

        sub = font_sm.render("Twój nick pojawi się w statystykach i dylematach", True, TEXT_MUTED)
        surface.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 215))

        # Input box
        box = pygame.Rect(WIDTH // 2 - 230, 275, 460, 66)
        draw_glow_rect(surface, CARD_BORDER_LT, box, radius=10, alpha=35, spread=6)
        pygame.draw.rect(surface, CARD_COLOR, box, border_radius=10)
        pygame.draw.rect(surface, CARD_BORDER_LT, box, width=2, border_radius=10)

        if self.text:
            ts = font_md.render(self.text, True, WHITE)
        else:
            ts = font_md.render(self.PLACEHOLDER, True, TEXT_MUTED)
        surface.blit(ts, (box.x + 18, box.centery - ts.get_height() // 2))

        # Blinking cursor
        if self.text and (tick // 18) % 2 == 0:
            cx = box.x + 18 + ts.get_width() + 3
            pygame.draw.rect(surface, WHITE, (cx, box.centery - 18, 2, 36))

        hint = font_sm.render("Naciśnij Enter lub kliknij GOTOWE", True, TEXT_MUTED)
        surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 355))

        self.btn_ok.draw(surface, accent=(70, 190, 120))


# ================== DILEMMA OVERLAY ==================
def draw_dilemma(surface, state, player_id):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 10, 178))
    surface.blit(overlay, (0, 0))

    if state["dilemma_player"] == player_id:
        t = state["dilemma_time"]
        timer_color = (255, 60, 60) if t < 1.0 else (255, 185, 60)
        timer_lbl = font_md.render(f"MASZ {t:.1f}s NA DECYZJĘ", True, timer_color)
        surface.blit(timer_lbl, (WIDTH // 2 - timer_lbl.get_width() // 2, HEIGHT // 2 - 100))

        opp_id = 1 - player_id
        opt = state["dilemma_texts"]

        for i, (text, pid, ox) in enumerate([
            (opt[0], player_id, WIDTH // 2 - 360),
            (opt[1], opp_id,    WIDTH // 2 + 20),
        ]):
            c    = PLAYER_COLORS[pid]
            cdim = PLAYER_COLORS_DIM[pid]
            rect = pygame.Rect(ox, HEIGHT // 2 - 24, 340, 60)
            draw_glow_rect(surface, c, rect, radius=10, alpha=35, spread=8)
            bg_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(bg_surf, (*cdim, 210), bg_surf.get_rect(), border_radius=10)
            surface.blit(bg_surf, (rect.x, rect.y))
            pygame.draw.rect(surface, c, rect, width=2, border_radius=10)
            ts = font_sm.render(text, True, c)
            surface.blit(ts, (rect.centerx - ts.get_width() // 2,
                               rect.centery - ts.get_height() // 2))
    else:
        opp_nick = state.get("opp_nick", "Rywal")
        wait = font_md.render(f"{opp_nick} podejmuje decyzję...", True, WHITE_DIM)
        surface.blit(wait, (WIDTH // 2 - wait.get_width() // 2, HEIGHT // 2 - 20))


# ================== INTERMISSION SCREEN ==================
def draw_intermission(surface, state, player_id, btn_ready, logical_mouse, tick):
    surface.fill(BG_COLOR)
    draw_stars(surface, tick)

    my_nick   = state.get("my_nick",  "Ja")
    opp_nick  = state.get("opp_nick", "Rywal")
    my_color  = PLAYER_COLORS[player_id]
    opp_color = PLAYER_COLORS[1 - player_id]

    title = font_lg.render(f"KONIEC RUNDY {state['round'] - 1}", True, WHITE)
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 26))

    # Stats card
    CW, CH = 840, 310
    CX = WIDTH // 2 - CW // 2
    CY = 108
    draw_card(surface, CX, CY, CW, CH, br=16)
    draw_card_header(surface, CX, CY, CW, 52, "STATYSTYKI RUNDY", font_sm, br=16)

    col_label = CX + 220
    col_self  = CX + 550
    col_other = CX + 730

    def cell(text, cx, cy, color, fnt=font_sm):
        s = fnt.render(text, True, color)
        surface.blit(s, (cx - s.get_width() // 2, cy))

    y_hdr = CY + 66
    cell("Wybory",   col_label, y_hdr, TEXT_MUTED)
    cell(my_nick,    col_self,  y_hdr, my_color)
    cell(opp_nick,   col_other, y_hdr, opp_color)
    draw_separator(surface, CX + 10, CY + 100, CW - 20, CARD_BORDER_LT, 130)

    pygame.draw.line(surface, CARD_BORDER, (CX + 430, CY + 52), (CX + 430, CY + CH - 1), 1)
    pygame.draw.line(surface, CARD_BORDER, (CX + 630, CY + 52), (CX + 630, CY + CH - 1), 1)

    my_s  = state["stats"][player_id]
    opp_s = state["stats"][1 - player_id]

    rows = [
        ("Ułatwienia",              str(my_s["buff_self"]),   str(my_s["buff_other"])),
        ("Utrudnienia",             str(my_s["nerf_self"]),   str(my_s["nerf_other"])),
        None,
        (f"Ułatwienia ({opp_nick})",  str(opp_s["buff_self"]),  str(opp_s["buff_other"])),
        (f"Utrudnienia ({opp_nick})", str(opp_s["nerf_self"]),  str(opp_s["nerf_other"])),
    ]

    y_row = CY + 108
    ROW_H = 46
    for item in rows:
        if item is None:
            draw_separator(surface, CX + 10, y_row + ROW_H // 2, CW - 20, CARD_BORDER, 80)
            y_row += 14
            continue
        label, v_self, v_other = item
        cell(label,   col_label, y_row + 14, WHITE_DIM)
        cell(v_self,  col_self,  y_row + 14, WHITE)
        cell(v_other, col_other, y_row + 14, WHITE)
        y_row += ROW_H

    # Scores
    SY = CY + CH + 18
    my_sc = font_sm.render(f"{my_nick}:  {state['my_score']} pkt", True, my_color)
    sh_sc = font_sm.render(f"Wspólnie: {state['shared_score']}", True, WHITE)
    op_sc = font_sm.render(f"{opp_nick}:  {state['opponent_score']} pkt", True, opp_color)
    surface.blit(my_sc, (CX, SY))
    surface.blit(sh_sc, (WIDTH // 2 - sh_sc.get_width() // 2, SY - 4))
    surface.blit(op_sc, (CX + CW - op_sc.get_width(), SY))

    # Ready button or wait
    if state["my_ready"]:
        wait = font_sm.render("Oczekiwanie na drugiego gracza...", True, TEXT_MUTED)
        surface.blit(wait, (WIDTH // 2 - wait.get_width() // 2, HEIGHT - 72))
    else:
        btn_ready.check_hover(logical_mouse)
        btn_ready.draw(surface, accent=(58, 200, 120))


# ================== GAMEPLAY SCREEN ==================
def draw_gameplay(surface, state, player_id, tick):
    surface.fill(BG_COLOR)

    for i, brick in enumerate(state["bricks"]):
        if brick["alive"]:
            if "row" not in brick:
                brick["row"] = i // max(1, len(state["bricks"]) // len(BRICK_ROWS))
            draw_brick(surface, brick)

    for pu in state["powerups"]:
        draw_powerup(surface, pu["rect"])

    draw_paddle(surface, state["paddle_rect"])

    bx, by = int(state["ball_pos"][0]), int(state["ball_pos"][1])
    draw_glow_circle(surface, BALL_COLOR, (bx, by), state["ball_radius"])

    my_nick   = state.get("my_nick",  f"Gracz {player_id + 1}")
    opp_nick  = state.get("opp_nick", f"Gracz {2 - player_id}")
    my_color  = PLAYER_COLORS[player_id]
    opp_color = PLAYER_COLORS[1 - player_id]

    # HUD
    rnd = font_sm.render(f"Runda {state['round']}/5", True, WHITE_DIM)
    surface.blit(rnd, (WIDTH // 2 - rnd.get_width() // 2, 12))

    my_hud = font_sm.render(f"{my_nick}: {state['my_score']}", True, my_color)
    surface.blit(my_hud, (20, 12))

    op_hud = font_sm.render(f"{opp_nick}: {state['opponent_score']}", True, opp_color)
    surface.blit(op_hud, (WIDTH - op_hud.get_width() - 20, 12))

    if state["dilemma_active"]:
        draw_dilemma(surface, state, player_id)


# ================== MENU SCREENS ==================
def draw_main_menu(surface, buttons, tick):
    surface.fill(BG_COLOR)
    draw_stars(surface, tick)
    aura_alpha = int(25 + 10 * math.sin(tick / 40))
    aura = pygame.Surface((600, 120), pygame.SRCALPHA)
    aura.fill((80, 100, 255, aura_alpha))
    surface.blit(aura, (WIDTH // 2 - 300, 55))
    title = font_xl.render("BREAKOUT", True, RED)
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 52))
    pygame.draw.rect(surface, (80, 100, 200),
                     (WIDTH // 2 - 180, 168, 360, 2), border_radius=2)
    for btn in buttons:
        btn.draw(surface)


def draw_settings(surface, btn_back, tick):
    surface.fill(BG_COLOR)
    draw_stars(surface, tick)
    t = font_lg.render("USTAWIENIA", True, WHITE)
    surface.blit(t, (WIDTH // 2 - t.get_width() // 2, 50))
    info = font_sm.render("Tryb Noc/Dzień — wkrótce!", True, TEXT_MUTED)
    surface.blit(info, (WIDTH // 2 - info.get_width() // 2, HEIGHT // 2))
    btn_back.draw(surface)


def draw_instructions(surface, btn_back, tick):
    surface.fill(BG_COLOR)
    draw_stars(surface, tick)
    t = font_lg.render("ZASADY GRY", True, WHITE)
    surface.blit(t, (WIDTH // 2 - t.get_width() // 2, 36))
    rules = [
        "CEL GRY:",
        "Zbij wszystkie cegiełki nie upuszczając piłki.",
        "",
        "STEROWANIE:",
        "Poruszaj paletką: STRZAŁKA W LEWO / STRZAŁKA W PRAWO",
        "",
        "POWER-UPY (MYSTERY BOX):",
        "Złapanie power-upa zatrzymuje grę na 2 sekundy.",
        "Wciśnij [1] lub [2] aby wybrać efekt dla siebie lub rywala.",
        "",
        "UWAGA: Brak decyzji w czasie = automatyczna KARA!",
    ]
    draw_multiline(surface, rules, WIDTH // 2, 130, font_sm, WHITE, center_x=True, spacing=34)
    draw_powerup(surface, pygame.Rect(WIDTH // 2 - 10, 510, 20, 20))
    btn_back.draw(surface)


# ================== MAIN LOOP ==================
def main():
    APP_STATE = "MAIN_MENU"
    n = None
    player_id = None
    state = {}
    tick = 0
    nickname_screen = None

    btn_start    = Button(WIDTH // 2 - 120, 220, 240, 58, "START GRY")
    btn_settings = Button(WIDTH // 2 - 120, 294, 240, 58, "USTAWIENIA")
    btn_help     = Button(WIDTH // 2 - 120, 368, 240, 58, "INSTRUKCJA")
    btn_quit     = Button(WIDTH // 2 - 120, 442, 240, 58, "WYJŚCIE")
    menu_buttons = [btn_start, btn_settings, btn_help, btn_quit]

    btn_back  = Button(20, 20, 160, 52, "← POWRÓT")
    btn_ready = Button(WIDTH // 2 - 140, HEIGHT - 100, 280, 62, "GOTOWE")

    run = True
    while run:
        tick += 1
        clock.tick(60)
        logical_mouse = get_logical_mouse_pos()
        action = "NONE"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

            if APP_STATE == "NICKNAME":
                nickname_screen.handle_event(event, logical_mouse)
                if nickname_screen.done:
                    nick = nickname_screen.get_nick()
                    print(f"Łączenie z serwerem jako '{nick}'...")
                    from network import Network
                    n = Network()
                    player_id = n.getP()
                    if player_id is not None:
                        # Send nickname to server (one-time handshake)
                        n.send_nick(nick)
                        pygame.display.set_caption(f"Breakout — {nick}")
                        APP_STATE = "PLAYING"
                    else:
                        print("Brak połączenia z serwerem!")
                        APP_STATE = "MAIN_MENU"

            elif APP_STATE == "MAIN_MENU":
                for btn in menu_buttons:
                    btn.check_hover(logical_mouse)
                if btn_start.is_clicked(event, logical_mouse):
                    nickname_screen = NicknameScreen()
                    APP_STATE = "NICKNAME"
                elif btn_settings.is_clicked(event, logical_mouse):
                    APP_STATE = "SETTINGS"
                elif btn_help.is_clicked(event, logical_mouse):
                    APP_STATE = "INSTRUCTIONS"
                elif btn_quit.is_clicked(event, logical_mouse):
                    run = False

            elif APP_STATE in ("SETTINGS", "INSTRUCTIONS"):
                btn_back.check_hover(logical_mouse)
                if btn_back.is_clicked(event, logical_mouse):
                    APP_STATE = "MAIN_MENU"

            elif APP_STATE == "PLAYING" and state and state.get("intermission"):
                if not state.get("my_ready"):
                    if btn_ready.is_clicked(event, logical_mouse):
                        action = "READY"

        # Game logic / network
        if APP_STATE == "PLAYING" and n is not None:
            keys = pygame.key.get_pressed()
            if action != "READY":
                if   keys[pygame.K_1] or keys[pygame.K_KP1]: action = "1"
                elif keys[pygame.K_2] or keys[pygame.K_KP2]: action = "2"
                elif keys[pygame.K_r]:                        action = "RESTART"
                elif keys[pygame.K_LEFT]:                     action = "LEFT"
                elif keys[pygame.K_RIGHT]:                    action = "RIGHT"

            if state and state.get("intermission") and state.get("my_ready"):
                action = "READY"

            state = n.send(action)
            if not state:
                print("Utracono połączenie z serwerem.")
                APP_STATE = "MAIN_MENU"
                n = None
                player_id = None
                pygame.display.set_caption("Breakout")

        # Drawing
        logical_surface.fill(BG_COLOR)

        if APP_STATE == "NICKNAME":
            nickname_screen.draw(logical_surface, tick)

        elif APP_STATE == "MAIN_MENU":
            draw_main_menu(logical_surface, menu_buttons, tick)

        elif APP_STATE == "SETTINGS":
            draw_settings(logical_surface, btn_back, tick)

        elif APP_STATE == "INSTRUCTIONS":
            draw_instructions(logical_surface, btn_back, tick)

        elif APP_STATE == "PLAYING" and state:
            if not state["playing"] and not state["game_over"]:
                logical_surface.fill(BG_COLOR)
                draw_stars(logical_surface, tick)
                draw_center_message(logical_surface, "CZEKANIE NA GRACZA...", WHITE_DIM)

            elif state["game_over"]:
                logical_surface.fill(BG_COLOR)
                draw_stars(logical_surface, tick)
                draw_center_message(logical_surface, "KONIEC GRY!", RED, y=HEIGHT // 2 - 70)
                nicks = state.get("nicknames", ["Gracz 1", "Gracz 2"])
                score_line = (f"{nicks[player_id]}: {state['my_score']} pkt    "
                              f"{nicks[1 - player_id]}: {state['opponent_score']} pkt    "
                              f"Wspólnie: {state['shared_score']}")
                sc = font_sm.render(score_line, True, WHITE_DIM)
                logical_surface.blit(
                    sc, (WIDTH // 2 - sc.get_width() // 2, HEIGHT // 2 + 10))
                hint = font_sm.render("Wciśnij R aby zrestartować", True, TEXT_MUTED)
                logical_surface.blit(
                    hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 60))

            elif state.get("intermission"):
                draw_intermission(
                    logical_surface, state, player_id, btn_ready, logical_mouse, tick)

            else:
                draw_gameplay(logical_surface, state, player_id, tick)

        # Scale to window
        scaled = pygame.transform.smoothscale(logical_surface, screen.get_size())
        screen.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()