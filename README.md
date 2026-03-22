# Breakout — Cooperative or Competitive?

A two-player networked implementation of the classic arcade game **Breakout**, built with Python and Pygame. The game is designed as a research tool for studying **affective and motivational cognitive enhancement** — specifically, how emotional feedback about another player's strategy influences your own strategic choices over repeated rounds.

## Research Context

The game explores a variant of the **Prisoner's Dilemma** applied to real-time gameplay. Players are not told whether the game is cooperative or competitive — that ambiguity is intentional. Each time a power-up is collected, the player must choose between helping themselves or their opponent, at different costs and benefits. After each round, both players see a breakdown of each other's decisions. The hypothesis is that this feedback triggers an emotional response and causes players to adapt (or entrench) their strategy in the next round.

---

## Prerequisites

- Python 3.8+
- Pygame (`pip install pygame`)
- Two devices on the same network (or both on localhost for testing)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/mariakiraga/pong.git
cd pong
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate       # macOS / Linux
venv\Scripts\activate          # Windows
```

3. Install dependencies:
```bash
pip install pygame
```

---

## Running the Game

### 1. Start the server

The server runs the physics simulation and manages both players' game states. Start it on the machine that will host the session:

```bash
python server.py
```

The server listens on port `5555` by default. You will see a message when each player connects.

> **Test mode:** By default `TEST_MODE = True` in `server.py`, which means a single player can start the game (an AI controls the second paddle). Set `TEST_MODE = False` for a real two-player session.

### 2. Connect as a client

Each player runs the client on their own machine. Before connecting, open `network.py` and set the `server` field to the IP address of the machine running `server.py`:

```python
self.server = "127.0.0.1"   # change to server's IP for LAN play, e.g. "192.168.1.10"
```

Then launch the client:

```bash
python client.py
```

On startup, enter your nickname — this will appear in the stats table and in dilemma prompts. Click **START GRY** from the main menu to connect. Both players must be connected before the first round begins (unless in test mode).

---

## Gameplay

### Controls

| Key | Action |
|-----|--------|
| ← → Arrow keys | Move paddle left / right |
| `1` or numpad `1` | Choose option 1 during a dilemma |
| `2` or numpad `2` | Choose option 2 during a dilemma |
| `R` | Restart after game over |

### Structure

A full game consists of **5 rounds**. Each round ends when all bricks are cleared or the ball is dropped. Points are scored for every brick destroyed.

### Power-ups (Mystery Box)

When a brick is destroyed, there is a 10% chance a green **Mystery Box** falls from it. If your paddle catches the box, the game **pauses for 2 seconds** and presents a dilemma: you must press `1` or `2` to apply an effect. If you do not choose in time, a random **penalty** is applied to you.

The dilemma always presents two options simultaneously — one affecting you and one affecting your opponent — at different magnitudes. The framing varies:

- **Buff dilemma:** a small boost for yourself *or* a larger boost for your opponent
- **Nerf dilemma:** a small penalty for yourself *or* a larger penalty for your opponent

Choosing the option that benefits yourself signals competitive play; choosing the option that benefits your opponent signals cooperative play — but neither player is told this explicitly.

### Available effects

| Type | Effect |
|------|--------|
| Buff | Wider paddle |
| Buff | Ball slows down |
| Buff | Bonus points |
| Nerf | Narrower paddle |
| Nerf | Ball speeds up |
| Nerf | Points deducted |

### Between rounds — stats screen

After each round both players see a **statistics table** showing, for each player, how many buffs and nerfs they applied to themselves vs. their opponent. Individual scores and the shared combined score are displayed. Players must both click **GOTOWE** (Ready) to start the next round.

---

## Project Structure

```
pong/
├── client.py      # Rendering, UI, input handling, state machine
├── server.py      # Physics simulation, game logic, networking
├── network.py     # TCP socket wrapper (send/receive with length-prefix framing)
```
