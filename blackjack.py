import random
from dataclasses import dataclass, field
from typing import List

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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Play a simple command-line Blackjack game.")
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

    if args.demo:
        play_demo(args.threshold)
    else:
        play_interactive()
