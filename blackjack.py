import functools
import json
import random
import secrets
import urllib.parse
from dataclasses import dataclass, field
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = [
    ("A", 11),
    ("2", 2),
    ("3", 3),
    ("4", 4),
    ("5", 5),
    ("6", 6),
    ("7", 7),
    ("8", 8),
    ("9", 9),
    ("10", 10),
    ("J", 10),
    ("Q", 10),
    ("K", 10),
]


@dataclass
class Card:
    rank: str
    suit: str
    value: int

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


@dataclass
class Deck:
    cards: List[Card] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.cards:
            self.cards = [Card(rank, suit, value) for rank, value in RANKS for suit in SUITS]
        random.shuffle(self.cards)

    def deal(self) -> Card:
        if not self.cards:
            raise ValueError("The deck is empty.")
        return self.cards.pop()


@dataclass
class Hand:
    cards: List[Card] = field(default_factory=list)

    def add_card(self, card: Card) -> None:
        self.cards.append(card)

    @property
    def value(self) -> int:
        total = sum(card.value for card in self.cards)
        aces = sum(1 for card in self.cards if card.rank == "A")
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.value == 21

    def is_bust(self) -> bool:
        return self.value > 21

    def formatted(self, hide_first: bool = False) -> str:
        if hide_first and self.cards:
            return "[hidden] " + " ".join(str(card) for card in self.cards[1:])
        return " ".join(str(card) for card in self.cards)


class BlackjackGame:
    def __init__(self) -> None:
        self.deck = Deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()

    def deal_initial(self) -> None:
        for _ in range(2):
            self.player_hand.add_card(self.deck.deal())
            self.dealer_hand.add_card(self.deck.deal())

    def player_hit(self) -> None:
        self.player_hand.add_card(self.deck.deal())

    def dealer_play(self) -> None:
        while self.dealer_hand.value < 17:
            self.dealer_hand.add_card(self.deck.deal())

    def result(self) -> str:
        player_bust = self.player_hand.is_bust()
        dealer_bust = self.dealer_hand.is_bust()
        player_val = self.player_hand.value
        dealer_val = self.dealer_hand.value

        if player_bust:
            return "Dealer wins! You busted."
        if dealer_bust:
            return "You win! Dealer busted."
        if player_val > dealer_val:
            return "You win!"
        if player_val < dealer_val:
            return "Dealer wins!"
        return "Push! It's a tie."


@dataclass
class GameSession:
    game: BlackjackGame
    finished: bool = False
    result_text: Optional[str] = None
    reveal: bool = False

    def end_round(self) -> None:
        self.reveal = True
        self.finished = True
        self.result_text = self.game.result()


SESSION_STORE: Dict[str, GameSession] = {}
FRONTEND_DIR = Path(__file__).with_name("web")


def _mask_cards(hand: Hand, hide_first: bool) -> List[str]:
    if hide_first and hand.cards:
        return ["??"] + [str(card) for card in hand.cards[1:]]
    return [str(card) for card in hand.cards]


def _hand_state(hand: Hand, hide_first: bool = False) -> Dict[str, object]:
    return {
        "cards": _mask_cards(hand, hide_first),
        "value": None if hide_first else hand.value,
        "isBust": hand.is_bust(),
        "isBlackjack": hand.is_blackjack(),
    }


def session_state(session: GameSession) -> Dict[str, object]:
    hide_dealer = not (session.reveal or session.finished)
    player_value = session.game.player_hand.value
    return {
        "status": "finished" if session.finished else "player-turn",
        "result": session.result_text,
        "player": _hand_state(session.game.player_hand, hide_first=False),
        "dealer": _hand_state(session.game.dealer_hand, hide_first=hide_dealer),
        "canHit": (not session.finished) and player_value < 21,
        "canStand": not session.finished,
    }


def _generate_game_id() -> str:
    while True:
        token = secrets.token_hex(8)
        if token not in SESSION_STORE:
            return token


def _trim_sessions(limit: int = 50) -> None:
    while len(SESSION_STORE) > limit:
        SESSION_STORE.pop(next(iter(SESSION_STORE)))


def create_session() -> Tuple[str, GameSession]:
    game = BlackjackGame()
    game.deal_initial()
    session = GameSession(game=game)
    if game.player_hand.is_blackjack():
        game.dealer_play()
        session.end_round()

    game_id = _generate_game_id()
    SESSION_STORE[game_id] = session
    _trim_sessions()
    return game_id, session


def get_session(game_id: str) -> Optional[GameSession]:
    return SESSION_STORE.get(game_id)


def hit_session(session: GameSession) -> None:
    if session.finished:
        return
    session.game.player_hit()
    if session.game.player_hand.is_bust():
        session.end_round()


def stand_session(session: GameSession) -> None:
    if session.finished:
        return
    session.game.dealer_play()
    session.end_round()


def print_state(game: BlackjackGame, hide_dealer: bool = True) -> None:
    print(f"Dealer: {game.dealer_hand.formatted(hide_first=hide_dealer)}")
    print(f"Player: {game.player_hand.formatted()} (value: {game.player_hand.value})")


def play_interactive() -> None:
    print("Welcome to Blackjack!\n")
    game = BlackjackGame()
    game.deal_initial()

    print_state(game)
    if game.player_hand.is_blackjack():
        print("Blackjack! Let's see what the dealer has...\n")
    else:
        while True:
            move = input("Hit or stand? [h/s]: ").strip().lower()
            if move not in {"h", "s", "hit", "stand"}:
                print("Please enter 'h' to hit or 's' to stand.\n")
                continue
            if move.startswith("h"):
                game.player_hit()
                print_state(game)
                if game.player_hand.is_bust():
                    print("You busted!\n")
                    break
            else:
                break

    game.dealer_play()
    print("\nDealer reveals:")
    print_state(game, hide_dealer=False)
    print(f"\n{game.result()}")


def play_demo(strategy_threshold: int = 16) -> None:
    game = BlackjackGame()
    game.deal_initial()
    print_state(game)

    while game.player_hand.value <= strategy_threshold and not game.player_hand.is_bust():
        print("\nDemo chooses to hit...")
        game.player_hit()
        print_state(game)

    if not game.player_hand.is_bust():
        print("\nDemo stands. Dealer's turn...\n")
    game.dealer_play()
    print_state(game, hide_dealer=False)
    print(f"\n{game.result()}")


class BlackjackRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: Optional[str] = None, **kwargs) -> None:
        directory = directory or str(FRONTEND_DIR)
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/state":
            params = urllib.parse.parse_qs(parsed.query)
            game_id = (params.get("gameId") or [None])[0]
            session = get_session(game_id or "")
            if not session:
                self.respond_json({"error": "Game not found."}, status=404)
                return
            self.respond_json({"state": session_state(session)})
            return

        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/new":
            game_id, session = create_session()
            self.respond_json({"gameId": game_id, "state": session_state(session)})
            return

        data = self._read_json_body()
        if data is None:
            return

        if parsed.path in {"/api/hit", "/api/stand"}:
            session = self._get_session_or_error(data.get("gameId"))
            if session is None:
                return
            if session.finished:
                self.respond_json({"error": "Game is over. Start a new round."}, status=400)
                return

            if parsed.path == "/api/hit":
                if session.game.player_hand.value >= 21:
                    self.respond_json(
                        {"error": "You are already at 21 or above. Choose stand or start a new round."},
                        status=400,
                    )
                    return
                hit_session(session)
            else:
                stand_session(session)
            self.respond_json({"state": session_state(session)})
            return

        self.respond_json({"error": "Unknown endpoint."}, status=404)

    def _get_session_or_error(self, game_id: Optional[str]) -> Optional[GameSession]:
        if not game_id:
            self.respond_json({"error": "Missing gameId."}, status=400)
            return None
        session = get_session(game_id)
        if not session:
            self.respond_json({"error": "Game not found."}, status=404)
            return None
        return session

    def _read_json_body(self) -> Optional[Dict[str, object]]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0

        if length <= 0:
            return {}

        raw = self.rfile.read(length)
        if not raw:
            return {}

        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.respond_json({"error": "Invalid JSON body."}, status=400)
            return None

    def respond_json(self, payload: Dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve_web(host: str = "127.0.0.1", port: int = 8000) -> None:
    if not FRONTEND_DIR.exists():
        raise FileNotFoundError(f"Frontend directory not found at {FRONTEND_DIR}")

    handler = functools.partial(BlackjackRequestHandler, directory=str(FRONTEND_DIR))
    ThreadingHTTPServer.allow_reuse_address = True
    with ThreadingHTTPServer((host, port), handler) as httpd:
        print(f"Serving Blackjack web UI at http://{host}:{port}")
        print("Press Ctrl+C to stop the server.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Play a simple command-line Blackjack game.")
    parser.add_argument(
        "--web",
        action="store_true",
        help="Run a local web server with a browser-based UI.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind for the web UI (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the web UI (default: 8000).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run an automated demo round instead of the interactive prompt.",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=16,
        help="Hit until this hand value in demo mode. Ignored for interactive games.",
    )
    args = parser.parse_args()

    if args.web and args.demo:
        parser.error("Choose either web mode or demo mode, not both.")

    if args.web:
        serve_web(host=args.host, port=args.port)
    elif args.demo:
        play_demo(args.threshold)
    else:
        play_interactive()
