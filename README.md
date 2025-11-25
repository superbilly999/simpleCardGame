# simpleCardGame

A quick command-line Blackjack game with a demo mode for automated play.

## Play in the browser

Launch the built-in web UI and open it in your browser:

```bash
python blackjack.py --web --port 8000
```

Then visit [http://127.0.0.1:8000](http://127.0.0.1:8000) to hit, stand, and deal new rounds. Change the host or port with `--host` and `--port` if needed.

## How to play

Run the game with Python 3:

```bash
python blackjack.py
```

Choose whether to **hit** or **stand** until you stay under 21. The dealer draws until reaching 17, and the script announces the winner.

## Demo mode

To see a hands-off round that hits until the player's hand reaches 16 by default:

```bash
python blackjack.py --demo
```

Use `--threshold` to change when the demo player stands.
