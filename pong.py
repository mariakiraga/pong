import pygame
import random
import sys
import math

pygame.init()

# ================== CONFIG ==================
WIDTH, HEIGHT = 900, 600
FPS = 60

BG_COLOR = (15, 18, 40)
WHITE = (240, 240, 240)
RED = (255, 80, 80)

START_LIVES = 3
BALL_START_SPEED = 320
BALL_SPEED_INCREMENT = 15
BALL_MAX_SPEED = 650

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Breakout OOP Deluxe")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 28)
big_font = pygame.font.SysFont("arial", 64)


# ================== BALL ==================
class Ball:
    def __init__(self):
        self.radius = 10
        self.start_speed = BALL_START_SPEED
        self.speed = self.start_speed
        self.pos = pygame.Vector2(WIDTH // 2, HEIGHT // 2)
        self.direction = pygame.Vector2(1, -1).normalize()

    @property
    def rect(self):
        return pygame.Rect(
            self.pos.x - self.radius,
            self.pos.y - self.radius,
            self.radius * 2,
            self.radius * 2
        )

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
            -abs(math.cos(math.radians(angle)))
        ).normalize()

    def draw(self, surface):
        pygame.draw.circle(surface, RED, self.pos, self.radius)


# ================== PADDLE ==================
class Paddle:
    def __init__(self):
        self.width = 130
        self.height = 15
        self.speed = 500
        self.rect = pygame.Rect(
            (WIDTH - self.width) // 2,
            HEIGHT - 60,
            self.width,
            self.height
        )

    def update(self, dt, keys):
        moved = False

        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed * dt
            moved = True
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed * dt
            moved = True

        self.rect.x = max(0, min(WIDTH - self.width, self.rect.x))
        return moved

    def draw(self, surface):
        pygame.draw.rect(surface, WHITE, self.rect, border_radius=8)


# ================== BRICK ==================
class Brick:
    def __init__(self, rect, color):
        self.rect = rect
        self.color = color
        self.alive = True

    def draw(self, surface):
        if self.alive:
            pygame.draw.rect(surface, self.color, self.rect, border_radius=6)


class BrickField:
    def __init__(self):
        self.bricks = []
        self.create()

    def create(self):
        rows = random.randint(5, 8)
        cols = random.randint(6, 10)

        width, height = 90, 30
        padding = 10
        offset_top = 60
        offset_left = (WIDTH - (width + padding) * cols) // 2

        self.bricks.clear()

        for row in range(rows):
            for col in range(cols):
                x = col * (width + padding) + offset_left
                y = row * (height + padding) + offset_top

                color = pygame.Color(0)
                color.hsva = (row * 30, 80, 100, 100)

                self.bricks.append(
                    Brick(pygame.Rect(x, y, width, height), color)
                )

    def remaining_bricks(self):
        return sum(1 for b in self.bricks if b.alive)

    def draw(self, surface):
        for brick in self.bricks:
            brick.draw(surface)


# ================== GAME ==================
class Game:
    PLAYING = 0
    PAUSED = 1
    WON = 2
    GAME_OVER = 3

    def __init__(self):
        self.ball = Ball()
        self.paddle = Paddle()
        self.bricks = BrickField()
        self.score = 0
        self.lives = START_LIVES
        self.state = Game.PLAYING
        self.running = True

    def handle_collisions(self):
        if self.ball.rect.colliderect(self.paddle.rect):
            self.ball.reflect_from_paddle(self.paddle.rect)

        for brick in self.bricks.bricks:
            if brick.alive and self.ball.rect.colliderect(brick.rect):
                brick.alive = False
                self.ball.direction.y *= -1
                self.score += 1
                self.ball.increase_speed()
                break

    def update(self, dt):
        keys = pygame.key.get_pressed()

        if self.state == Game.PLAYING:
            self.paddle.update(dt, keys)
            self.ball.update(dt)
            self.handle_collisions()

            if self.ball.pos.y > HEIGHT:
                self.lives -= 1
                if self.lives > 0:
                    self.ball.reset()
                    self.state = Game.PAUSED
                else:
                    self.state = Game.GAME_OVER

            if self.bricks.remaining_bricks() == 0:
                self.state = Game.WON

        elif self.state == Game.PAUSED:
            moved = self.paddle.update(dt, keys)
            if moved:
                self.state = Game.PLAYING

    def draw_center_message(self, text):
        label = big_font.render(text, True, WHITE)
        rect = label.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(label, rect)

    def draw(self):
        screen.fill(BG_COLOR)

        self.bricks.draw(screen)
        self.paddle.draw(screen)
        self.ball.draw(screen)

        score_text = font.render(f"Score: {self.score}", True, WHITE)
        lives_text = font.render(f"Lives: {self.lives}", True, WHITE)

        screen.blit(score_text, (20, 20))
        screen.blit(lives_text, (WIDTH - 140, 20))

        if self.state == Game.PAUSED:
            self.draw_center_message("Life Lost - Move Paddle")

        if self.state == Game.WON:
            self.draw_center_message(f"YOU WON! Score: {self.score}")

        if self.state == Game.GAME_OVER:
            self.draw_center_message(f"GAME OVER - Score: {self.score}")

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = clock.tick(FPS) / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.update(dt)
            self.draw()


# ================== START ==================
if __name__ == "__main__":
    Game().run()