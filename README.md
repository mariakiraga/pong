# Breakout

A Python pygame implementation of the classic arcade game Breakout. Built with an Object-Oriented approach, this version features dynamic ball physics, scaling difficulty, and vibrant procedural brick layouts.

# Getting started
## Prerequisites
- Python 3.8+
- Pygame CE (or standard Pygame)

## Installation
1. Clone the repository in desired directory:
``` {bash}
git clone https://github.com/mariakiraga/pong.git
cd pong
```
2. Create a virtual environment:
In the directory of the project:
``` {bash}
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. Install dependencies:
``` {bash}
pip install pygame
```

## Running the game
Execute the main script from the project directory:
``` {bash}
python pong.py
```

# Gameplay & Mechanics
- Controls: Left/Right Arrow Keys for paddle movement.

- Difficulty: Ball velocity increases by 15 units per brick destroyed, capped at 650 units/s.

- Lives: Players start with 3 lives. The game enters a PAUSED state upon life loss to allow for player repositioning.
