import pygame
import random
import sys
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional

# ============================================================================
# CONSTANTS & ENUMS
# ============================================================================

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60
CARD_WIDTH = 60
CARD_HEIGHT = 90

class Suit(Enum):
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"

class Rank(Enum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

class GamePhase(Enum):
    PRE_FLOP = 1
    FLOP = 2
    TURN = 3
    RIVER = 4
    SHOWDOWN = 5
    HAND_OVER = 6

class ActionType(Enum):
    FOLD = 1
    CHECK = 2
    CALL = 3
    RAISE = 4
    ALL_IN = 5

# ============================================================================
# CARD & DECK
# ============================================================================

@dataclass
class Card:
    suit: Suit
    rank: Rank
    
    def __str__(self):
        rank_names = {
            2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9",
            10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"
        }
        return f"{rank_names[self.rank.value]}{self.suit.value}"
    
    def __eq__(self, other):
        return self.suit == other.suit and self.rank == other.rank

class Deck:
    def __init__(self):
        self.cards = [Card(suit, rank) for suit in Suit for rank in Rank]
        random.shuffle(self.cards)
    
    def draw(self) -> Card:
        return self.cards.pop() if self.cards else None

# ============================================================================
# HAND EVALUATION
# ============================================================================

class HandEvaluator:
    @staticmethod
    def evaluate(cards: List[Card]) -> Tuple[int, str]:
        """
        Evaluates a 7-card hand and returns (score, hand_name).
        Higher score = better hand.
        """
        if len(cards) < 5:
            return (0, "")
        
        # Generate all 5-card combinations
        from itertools import combinations
        best_score = 0
        best_name = ""
        
        for combo in combinations(cards, 5):
            score, name = HandEvaluator._evaluate_five(list(combo))
            if score > best_score:
                best_score = score
                best_name = name
        
        return (best_score, best_name)
    
    @staticmethod
    def _evaluate_five(cards: List[Card]) -> Tuple[int, str]:
        """Evaluate a specific 5-card hand."""
        ranks = sorted([c.rank.value for c in cards], reverse=True)
        suits = [c.suit for c in cards]
        
        is_flush = len(set(suits)) == 1
        is_straight, straight_high = HandEvaluator._check_straight(ranks)
        
        rank_counts = {}
        for r in ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1
        
        counts = sorted(rank_counts.values(), reverse=True)
        
        # Royal Flush
        if is_flush and is_straight and ranks == [14, 13, 12, 11, 10]:
            return (10000000, "Royal Flush")
        
        # Straight Flush
        if is_flush and is_straight:
            return (9000000 + straight_high * 1000, "Straight Flush")
        
        # Four of a Kind
        if counts == [4, 1]:
            quad_rank = [r for r, c in rank_counts.items() if c == 4][0]
            return (8000000 + quad_rank * 1000, "Four of a Kind")
        
        # Full House
        if counts == [3, 2]:
            trip_rank = [r for r, c in rank_counts.items() if c == 3][0]
            pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
            return (7000000 + trip_rank * 1000 + pair_rank, "Full House")
        
        # Flush
        if is_flush:
            return (6000000 + sum(ranks) * 10, "Flush")
        
        # Straight
        if is_straight:
            return (5000000 + straight_high * 1000, "Straight")
        
        # Three of a Kind
        if counts == [3, 1, 1]:
            trip_rank = [r for r, c in rank_counts.items() if c == 3][0]
            return (4000000 + trip_rank * 1000, "Three of a Kind")
        
        # Two Pair
        if counts == [2, 2, 1]:
            pairs = sorted([r for r, c in rank_counts.items() if c == 2], reverse=True)
            return (3000000 + pairs[0] * 1000 + pairs[1] * 100, "Two Pair")
        
        # One Pair
        if counts == [2, 1, 1, 1]:
            pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
            return (2000000 + pair_rank * 1000, "Pair")
        
        # High Card
        return (1000000 + sum(ranks) * 10, "High Card")
    
    @staticmethod
    def _check_straight(ranks: List[int]) -> Tuple[bool, int]:
        """Returns (is_straight, high_card)"""
        if ranks == list(range(ranks[0], ranks[0] - 5, -1)):
            return (True, ranks[0])
        
        # Check for A-2-3-4-5 (wheel)
        if ranks == [14, 5, 4, 3, 2]:
            return (True, 5)
        
        return (False, 0)

# ============================================================================
# PLAYER & AI
# ============================================================================

@dataclass
class Player:
    name: str
    stack: int
    hole_cards: List[Card]
    position: Tuple[int, int]
    is_human: bool = False
    
    def __post_init__(self):
        self.current_bet = 0
        self.total_bet = 0
        self.folded = False
        self.all_in = False
    
    def reset_hand(self):
        self.hole_cards = []
        self.current_bet = 0
        self.total_bet = 0
        self.folded = False
        self.all_in = False
    
    def can_act(self) -> bool:
        return not self.folded and not self.all_in and self.stack > 0

class AIPlayer(Player):
    """Simple AI that uses hand strength and position to decide actions."""
    
    def decide_action(self, current_bet: int, phase: GamePhase, 
                     community_cards: List[Card]) -> Tuple[ActionType, int]:
        """AI decision logic."""
        
        if self.stack == 0:
            return (ActionType.FOLD, 0)
        
        amount_to_call = current_bet - self.current_bet
        
        # Check hand strength
        all_cards = self.hole_cards + community_cards
        score, hand_name = HandEvaluator.evaluate(all_cards)
        hand_strength = (score % 10000000) / 10000000
        
        # Aggression increases as hand gets stronger and as we progress
        phase_factor = {GamePhase.PRE_FLOP: 0.7, GamePhase.FLOP: 0.8, 
                       GamePhase.TURN: 0.9, GamePhase.RIVER: 0.95}.get(phase, 0.5)
        
        aggression = hand_strength * phase_factor
        
        # Decision tree
        if amount_to_call == 0:
            # Can check
            if aggression > 0.6:
                raise_amount = int(self.stack * 0.2) if self.stack > 20 else self.stack
                return (ActionType.RAISE, raise_amount)
            return (ActionType.CHECK, 0)
        
        if amount_to_call > self.stack * 0.3:
            # Expensive bet
            if aggression > 0.75:
                return (ActionType.ALL_IN, self.stack)
            elif aggression > 0.4:
                return (ActionType.CALL, amount_to_call)
            else:
                return (ActionType.FOLD, 0)
        
        # Normal bet
        if aggression > 0.6:
            raise_amount = min(int(amount_to_call * 1.5), self.stack - amount_to_call)
            return (ActionType.RAISE, raise_amount)
        elif aggression > 0.3:
            return (ActionType.CALL, amount_to_call)
        else:
            return (ActionType.FOLD, 0)

# ============================================================================
# GAME ENGINE
# ============================================================================

class PokerGame:
    def __init__(self):
        self.players = []
        self.dealer_button = 0
        self.small_blind = 1
        self.big_blind = 2
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.current_player_idx = 0
        self.phase = GamePhase.PRE_FLOP
        self.deck = None
        self.action_history = []
        
        # Create players
        self.players = [
            Player("You", 1000, [], (200, 650), is_human=True),
            AIPlayer("NPC (Alex)", 1000, [], (600, 100)),
            Player("Dealer", 1000, [], (1000, 650), is_human=False),
        ]
        
        self.start_hand()
    
    def start_hand(self):
        """Initialize a new hand."""
        self.deck = Deck()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.phase = GamePhase.PRE_FLOP
        self.action_history = []
        
        # Reset player state
        for p in self.players:
            p.reset_hand()
        
        # Post blinds
        self.small_blind_idx = (self.dealer_button + 1) % 3
        self.big_blind_idx = (self.dealer_button + 2) % 3
        
        sb_amount = 10
        bb_amount = 20
        
        self.players[self.small_blind_idx].current_bet = sb_amount
        self.players[self.small_blind_idx].total_bet = sb_amount
        self.players[self.small_blind_idx].stack -= sb_amount
        
        self.players[self.big_blind_idx].current_bet = bb_amount
        self.players[self.big_blind_idx].total_bet = bb_amount
        self.players[self.big_blind_idx].stack -= bb_amount
        
        self.pot = sb_amount + bb_amount
        self.current_bet = bb_amount
        
        # Deal hole cards
        for _ in range(2):
            for p in self.players:
                p.hole_cards.append(self.deck.draw())
        
        # First to act is small blind in heads-up, else UTG
        self.current_player_idx = (self.big_blind_idx + 1) % 3
        self.action_history = []
    
    def advance_phase(self):
        """Move to next betting phase."""
        if self.phase == GamePhase.PRE_FLOP:
            # Flop: 3 cards
            for _ in range(3):
                self.community_cards.append(self.deck.draw())
            self.phase = GamePhase.FLOP
        elif self.phase == GamePhase.FLOP:
            # Turn: 1 card
            self.community_cards.append(self.deck.draw())
            self.phase = GamePhase.TURN
        elif self.phase == GamePhase.TURN:
            # River: 1 card
            self.community_cards.append(self.deck.draw())
            self.phase = GamePhase.RIVER
        elif self.phase == GamePhase.RIVER:
            self.phase = GamePhase.SHOWDOWN
        
        # Reset bets for new phase
        self.current_bet = 0
        for p in self.players:
            p.current_bet = 0
        
        # Next to act is first non-folded after button
        self.current_player_idx = (self.dealer_button + 1) % 3
    
    def get_active_players(self) -> List[Player]:
        """Get players still in the hand."""
        return [p for p in self.players if not p.folded]
    
    def player_action(self, action: ActionType, amount: int = 0):
        """Process a player action."""
        player = self.players[self.current_player_idx]
        
        if action == ActionType.FOLD:
            player.folded = True
        
        elif action == ActionType.CHECK:
            pass
        
        elif action == ActionType.CALL:
            amount_to_call = self.current_bet - player.current_bet
            actual_amount = min(amount_to_call, player.stack)
            player.stack -= actual_amount
            player.current_bet += actual_amount
            player.total_bet += actual_amount
            self.pot += actual_amount
        
        elif action == ActionType.RAISE:
            amount_to_call = self.current_bet - player.current_bet
            actual_raise = min(amount, player.stack - amount_to_call)
            total_amount = amount_to_call + actual_raise
            
            player.stack -= total_amount
            player.current_bet += total_amount
            player.total_bet += total_amount
            self.pot += total_amount
            
            self.current_bet = player.current_bet
        
        elif action == ActionType.ALL_IN:
            amount_to_call = self.current_bet - player.current_bet
            actual_amount = min(amount_to_call + amount, player.stack)
            
            player.stack -= actual_amount
            player.current_bet += actual_amount
            player.total_bet += actual_amount
            self.pot += actual_amount
            player.all_in = True
            
            if actual_amount > amount_to_call:
                self.current_bet = player.current_bet
        
        self.action_history.append((player.name, action.name, amount))
        self.next_player()
    
    def next_player(self):
        """Move to next player who can act."""
        active = self.get_active_players()
        
        if len(active) == 1:
            # Only one player left, award pot
            self.phase = GamePhase.HAND_OVER
            return
        
        # Check if betting round is over
        bets_equal = all(p.current_bet == self.current_bet for p in active)
        all_in_or_acted = all(p.all_in or p.current_bet == self.current_bet for p in active)
        
        if bets_equal and all_in_or_acted:
            # Round over
            if self.phase == GamePhase.RIVER or len(active) == 1:
                self.phase = GamePhase.SHOWDOWN
            else:
                self.advance_phase()
            return
        
        # Next player in rotation
        start_idx = self.current_player_idx
        self.current_player_idx = (start_idx + 1) % 3
        
        while not self.players[self.current_player_idx].can_act():
            self.current_player_idx = (self.current_player_idx + 1) % 3
            if self.current_player_idx == start_idx:
                break
    
    def resolve_hand(self):
        """Determine winner(s) and award pot."""
        active = self.get_active_players()
        
        if len(active) == 1:
            active[0].stack += self.pot
            self.phase = GamePhase.HAND_OVER
            return active[0]
        
        # Showdown: evaluate all hands
        best_score = -1
        winner = None
        
        for player in active:
            all_cards = player.hole_cards + self.community_cards
            score, hand_name = HandEvaluator.evaluate(all_cards)
            if score > best_score:
                best_score = score
                winner = player
        
        winner.stack += self.pot
        self.phase = GamePhase.HAND_OVER
        return winner

# ============================================================================
# PYGAME RENDERING & GAME LOOP
# ============================================================================

class PokerUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Poker: You vs Dealer & NPC")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 20)
        
        self.game = PokerGame()
        self.selected_action = None
        self.raise_amount = 0
        self.message = "Game started! Blinds posted."
        self.message_timer = 0
    
    def handle_events(self):
        """Handle user input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                player = self.game.players[0]
                
                if player != self.game.players[self.game.current_player_idx]:
                    continue
                
                if event.key == pygame.K_f:  # Fold
                    self.game.player_action(ActionType.FOLD)
                    self.message = f"{player.name} folded."
                    self.message_timer = 120
                
                elif event.key == pygame.K_c:  # Check/Call
                    amount_to_call = self.game.current_bet - player.current_bet
                    if amount_to_call == 0:
                        self.game.player_action(ActionType.CHECK)
                        self.message = f"{player.name} checked."
                    else:
                        self.game.player_action(ActionType.CALL, amount_to_call)
                        self.message = f"{player.name} called ${amount_to_call}."
                    self.message_timer = 120
                
                elif event.key == pygame.K_r:  # Raise
                    amount_to_call = self.game.current_bet - player.current_bet
                    raise_amt = 50
                    self.game.player_action(ActionType.RAISE, raise_amt)
                    self.message = f"{player.name} raised ${raise_amt}."
                    self.message_timer = 120
                
                elif event.key == pygame.K_a:  # All-in
                    self.game.player_action(ActionType.ALL_IN, player.stack)
                    self.message = f"{player.name} went all-in!"
                    self.message_timer = 120
        
        return True
    
    def update(self):
        """Update game state."""
        if self.game.phase == GamePhase.HAND_OVER:
            # Wait before starting new hand
            if self.message_timer == 0:
                self.game.dealer_button = (self.game.dealer_button + 1) % 3
                self.game.start_hand()
                self.message = "New hand started!"
                self.message_timer = 120
        
        elif self.game.phase == GamePhase.SHOWDOWN:
            if self.message_timer == 0:
                winner = self.game.resolve_hand()
                self.message = f"{winner.name} won ${self.game.pot}!"
                self.message_timer = 300
        
        elif self.game.current_player_idx > 0:
            # NPC or Dealer turn
            player = self.game.players[self.game.current_player_idx]
            if not player.is_human and player.can_act():
                action, amount = player.decide_action(
                    self.game.current_bet,
                    self.game.phase,
                    self.game.community_cards
                )
                self.game.player_action(action, amount)
                self.message = f"{player.name}: {action.name}"
                if amount > 0:
                    self.message += f" (${amount})"
                self.message_timer = 180
        
        if self.message_timer > 0:
            self.message_timer -= 1
    
    def draw(self):
        """Render game state."""
        self.screen.fill((34, 139, 34))  # Green felt
        
        # Draw community cards
        self._draw_community_cards()
        
        # Draw players
        for i, player in enumerate(self.game.players):
            self._draw_player(player, i == self.game.current_player_idx)
        
        # Draw pot
        pot_text = self.font_large.render(f"Pot: ${self.game.pot}", True, (255, 215, 0))
        self.screen.blit(pot_text, (500, 350))
        
        # Draw current bet
        bet_text = self.font_medium.render(f"Current bet: ${self.game.current_bet}", True, (255, 255, 255))
        self.screen.blit(bet_text, (450, 300))
        
        # Draw phase
        phase_text = self.font_medium.render(f"Phase: {self.game.phase.name}", True, (255, 255, 255))
        self.screen.blit(phase_text, (10, 10))
        
        # Draw message
        if self.message_timer > 0:
            msg = self.font_small.render(self.message, True, (255, 255, 0))
            self.screen.blit(msg, (400, 50))
        
        # Draw controls (for human player)
        controls_text = self.font_small.render("F: Fold | C: Call/Check | R: Raise | A: All-in", True, (200, 200, 200))
        self.screen.blit(controls_text, (10, WINDOW_HEIGHT - 30))
        
        pygame.display.flip()
    
    def _draw_community_cards(self):
        """Draw community cards in the center."""
        start_x = 350
        y = 200
        
        for i, card in enumerate(self.game.community_cards):
            x = start_x + i * 70
            self._draw_card(card, x, y)
    
    def _draw_player(self, player: Player, is_current: bool):
        """Draw a player's info and cards."""
        x, y = player.position
        
        # Player name
        color = (255, 215, 0) if is_current else (255, 255, 255)
        name_text = self.font_medium.render(player.name, True, color)
        self.screen.blit(name_text, (x - 50, y - 120))
        
        # Stack
        stack_text = self.font_small.render(f"${player.stack}", True, (100, 255, 100))
        self.screen.blit(stack_text, (x - 30, y - 90))
        
        # Current bet
        if player.current_bet > 0:
            bet_text = self.font_small.render(f"Bet: ${player.current_bet}", True, (255, 100, 100))
            self.screen.blit(bet_text, (x - 40, y - 60))
        
        # Folded indicator
        if player.folded:
            fold_text = self.font_small.render("FOLDED", True, (100, 100, 100))
            self.screen.blit(fold_text, (x - 40, y - 30))
        
        # All-in indicator
        if player.all_in:
            allin_text = self.font_small.render("ALL-IN", True, (255, 0, 0))
            self.screen.blit(allin_text, (x - 40, y - 30))
        
        # Hole cards (only show for human or in showdown)
        if (player.is_human or self.game.phase == GamePhase.SHOWDOWN) and player.hole_cards:
            for i, card in enumerate(player.hole_cards):
                self._draw_card(card, x - 40 + i * 70, y + 20)
        elif player.hole_cards:
            # Draw card back
            for i in range(len(player.hole_cards)):
                self._draw_card_back(x - 40 + i * 70, y + 20)
    
    def _draw_card(self, card: Card, x: int, y: int):
        """Draw a card."""
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, CARD_WIDTH, CARD_HEIGHT))
        pygame.draw.rect(self.screen, (0, 0, 0), (x, y, CARD_WIDTH, CARD_HEIGHT), 2)
        
        card_text = self.font_medium.render(str(card), True, (0, 0, 0))
        self.screen.blit(card_text, (x + 10, y + 10))
    
    def _draw_card_back(self, x: int, y: int):
        """Draw card back (for hidden cards)."""
        pygame.draw.rect(self.screen, (0, 0, 150), (x, y, CARD_WIDTH, CARD_HEIGHT))
        pygame.draw.rect(self.screen, (100, 100, 200), (x, y, CARD_WIDTH, CARD_HEIGHT), 2)
    
    def run(self):
        """Main game loop."""
        running = True
        
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    ui = PokerUI()
    ui.run()