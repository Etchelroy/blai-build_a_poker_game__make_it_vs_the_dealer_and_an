import pygame
import random
from enum import Enum
from collections import defaultdict

pygame.init()

# Constants
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
FPS = 60

# Colors
COLOR_BG = (34, 139, 34)
COLOR_CARD_BG = (220, 220, 220)
COLOR_TEXT = (255, 255, 255)
COLOR_BUTTON = (70, 130, 180)
COLOR_BUTTON_HOVER = (100, 160, 210)
COLOR_BUTTON_PRESS = (50, 100, 150)
COLOR_CHIP_PLAYER = (255, 100, 100)
COLOR_CHIP_NPC = (100, 100, 255)
COLOR_CHIP_DEALER = (255, 215, 0)
COLOR_POT = (255, 200, 0)

class GamePhase(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"
    GAME_OVER = "game_over"

class Suit(Enum):
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"

class Card:
    RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    RANK_VALUES = {rank: 14 - i for i, rank in enumerate(RANKS)}
    
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
    
    def __repr__(self):
        return f"{self.rank}{self.suit.value}"
    
    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit

class HandEvaluator:
    @staticmethod
    def evaluate(cards):
        """Evaluate 5-card hand, return score (higher is better)"""
        if len(cards) != 5:
            return 0
        
        ranks = [Card.RANK_VALUES[card.rank] for card in cards]
        suits = [card.suit for card in cards]
        
        is_flush = len(set(suits)) == 1
        sorted_ranks = sorted(ranks, reverse=True)
        is_straight = sorted_ranks == list(range(sorted_ranks[0], sorted_ranks[0]-5, -1))
        
        # Ace-low straight (A-2-3-4-5)
        if sorted_ranks == [14, 5, 4, 3, 2]:
            is_straight = True
            sorted_ranks = [5, 4, 3, 2, 1]
        
        rank_counts = defaultdict(int)
        for rank in ranks:
            rank_counts[rank] += 1
        
        counts = sorted(rank_counts.values(), reverse=True)
        
        # Score: 1M-10M range (higher = better hand)
        score = 0
        
        if is_straight and is_flush:
            score = 8000000 + sorted_ranks[0] * 1000  # Royal/Straight Flush
        elif counts == [4, 1]:
            score = 7000000 + max(rank_counts, key=lambda k: rank_counts[k] if rank_counts[k] == 4 else 0) * 1000  # Four of a Kind
        elif counts == [3, 2]:
            score = 6000000 + max(rank_counts, key=lambda k: rank_counts[k] if rank_counts[k] == 3 else 0) * 1000  # Full House
        elif is_flush:
            score = 5000000 + sum(sorted_ranks) * 10  # Flush
        elif is_straight:
            score = 4000000 + sorted_ranks[0] * 1000  # Straight
        elif counts == [3, 1, 1]:
            score = 3000000 + max(rank_counts, key=lambda k: rank_counts[k] if rank_counts[k] == 3 else 0) * 1000  # Three of a Kind
        elif counts == [2, 2, 1]:
            score = 2000000 + sum([k for k in rank_counts if rank_counts[k] == 2]) * 1000  # Two Pair
        elif counts == [2, 1, 1, 1]:
            score = 1000000 + max(rank_counts, key=lambda k: rank_counts[k] if rank_counts[k] == 2 else 0) * 1000  # One Pair
        else:
            score = sorted_ranks[0] * 10000 + sum(sorted_ranks) * 100  # High Card
        
        return score
    
    @staticmethod
    def best_hand(hole_cards, community_cards):
        """Find best 5-card hand from 7 cards"""
        from itertools import combinations
        all_cards = hole_cards + community_cards
        best_score = 0
        best = None
        
        for combo in combinations(all_cards, 5):
            score = HandEvaluator.evaluate(list(combo))
            if score > best_score:
                best_score = score
                best = combo
        
        return best, best_score

class Player:
    def __init__(self, name, is_ai=False):
        self.name = name
        self.stack = 1000
        self.hole_cards = []
        self.current_bet = 0
        self.total_bet = 0
        self.is_folded = False
        self.is_ai = is_ai
        self.position = 0
    
    def reset_hand(self):
        self.hole_cards = []
        self.current_bet = 0
        self.is_folded = False

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Texas Hold'em Poker")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        self.font_tiny = pygame.font.Font(None, 20)
        
        # Game state
        self.players = [
            Player("You", is_ai=False),
            Player("NPC", is_ai=True),
            Player("Dealer", is_ai=True)
        ]
        self.current_player_idx = 0
        self.dealer_idx = 2
        self.button_idx = 2
        self.small_blind_idx = 0
        self.big_blind_idx = 1
        
        self.deck = []
        self.community_cards = []
        self.pot = 0
        self.current_bet_level = 20  # BB amount
        self.phase = GamePhase.PREFLOP
        self.round_complete = False
        self.game_message = ""
        self.message_timer = 0
        
        # UI State
        self.action_buttons = {
            'fold': pygame.Rect(150, 750, 100, 50),
            'check': pygame.Rect(300, 750, 100, 50),
            'call': pygame.Rect(450, 750, 100, 50),
            'raise': pygame.Rect(600, 750, 100, 50),
            'all_in': pygame.Rect(750, 750, 100, 50),
        }
        self.raise_amount = 20
        self.game_over = False
        self.winner = None
        
        self.start_new_game()
    
    def start_new_game(self):
        """Initialize a new hand"""
        if self.game_over:
            return
        
        for player in self.players:
            player.reset_hand()
        
        self.community_cards = []
        self.pot = 0
        self.phase = GamePhase.PREFLOP
        self.round_complete = False
        self.game_message = ""
        
        # Post blinds
        self.players[self.small_blind_idx].stack -= 10
        self.players[self.big_blind_idx].stack -= 20
        self.pot = 30
        self.current_bet_level = 20
        
        self.players[self.small_blind_idx].total_bet = 10
        self.players[self.big_blind_idx].total_bet = 20
        
        # Deal hole cards
        self.deck = self.create_deck()
        for player in self.players:
            player.hole_cards = [self.deck.pop(), self.deck.pop()]
        
        # Start with player to act after BB (UTG in 3-player)
        self.current_player_idx = 0
        self.action_buttons['raise'].rect = pygame.Rect(600, 750, 100, 50)
    
    def create_deck(self):
        """Create and shuffle deck"""
        deck = []
        for suit in Suit:
            for rank in Card.RANKS:
                deck.append(Card(rank, suit))
        random.shuffle(deck)
        return deck
    
    def advance_phase(self):
        """Move to next phase and deal community cards"""
        if self.phase == GamePhase.PREFLOP:
            self.phase = GamePhase.FLOP
            self.community_cards.extend([self.deck.pop(), self.deck.pop(), self.deck.pop()])
        elif self.phase == GamePhase.FLOP:
            self.phase = GamePhase.TURN
            self.community_cards.append(self.deck.pop())
        elif self.phase == GamePhase.TURN:
            self.phase = GamePhase.RIVER
            self.community_cards.append(self.deck.pop())
        elif self.phase == GamePhase.RIVER:
            self.phase = GamePhase.SHOWDOWN
        
        self.current_bet_level = 0
        for player in self.players:
            player.current_bet = 0
    
    def next_player(self):
        """Move to next player who hasn't folded"""
        players_in = sum(1 for p in self.players if not p.is_folded)
        
        if players_in <= 1:
            self.end_hand()
            return
        
        for _ in range(len(self.players)):
            self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
            if not self.players[self.current_player_idx].is_folded:
                break
        
        # Check if betting round is complete
        betting_complete = True
        for i, player in enumerate(self.players):
            if not player.is_folded:
                if player.current_bet < self.current_bet_level and player.stack > 0:
                    betting_complete = False
                    break
        
        if betting_complete:
            self.round_complete = True
    
    def player_action(self, action, amount=0):
        """Process player action"""
        player = self.players[self.current_player_idx]
        
        if action == "fold":
            player.is_folded = True
            self.game_message = f"{player.name} folds"
            self.message_timer = 60
        
        elif action == "check":
            self.game_message = f"{player.name} checks"
            self.message_timer = 60
        
        elif action == "call":
            call_amount = min(self.current_bet_level - player.current_bet, player.stack)
            player.stack -= call_amount
            player.current_bet += call_amount
            self.pot += call_amount
            self.game_message = f"{player.name} calls {call_amount}"
            self.message_timer = 60
        
        elif action == "raise":
            raise_amount = min(amount, player.stack)
            total_bet = self.current_bet_level - player.current_bet + raise_amount
            total_bet = min(total_bet, player.stack)
            
            player.stack -= total_bet
            self.pot += total_bet
            player.current_bet = self.current_bet_level + raise_amount
            self.current_bet_level = player.current_bet
            self.game_message = f"{player.name} raises to {self.current_bet_level}"
            self.message_timer = 60
        
        elif action == "all_in":
            all_in_amount = player.stack
            player.stack = 0
            player.current_bet += all_in_amount
            self.pot += all_in_amount
            if player.current_bet > self.current_bet_level:
                self.current_bet_level = player.current_bet
            self.game_message = f"{player.name} goes all in!"
            self.message_timer = 60
        
        self.next_player()
    
    def npc_action(self):
        """AI decision making"""
        player = self.players[self.current_player_idx]
        if not player.is_ai:
            return
        
        # Calculate hand strength
        best_hand, score = HandEvaluator.best_hand(player.hole_cards, self.community_cards)
        hand_strength = score / 10000000.0
        
        # Phase aggression factor
        phase_factors = {
            GamePhase.PREFLOP: 1.2,
            GamePhase.FLOP: 1.0,
            GamePhase.TURN: 0.9,
            GamePhase.RIVER: 0.8
        }
        aggression = hand_strength * phase_factors.get(self.phase, 1.0)
        
        call_amount = self.current_bet_level - player.current_bet
        
        if call_amount == 0:
            self.player_action("check")
        elif aggression < 0.3:
            self.player_action("fold")
        elif aggression < 0.6:
            if call_amount <= player.stack * 0.1:
                self.player_action("call")
            else:
                self.player_action("fold")
        elif aggression < 0.8:
            self.player_action("call")
        else:
            raise_amount = int(self.current_bet_level * 0.5)
            if player.stack > raise_amount:
                self.player_action("raise", raise_amount)
            else:
                self.player_action("all_in")
    
    def end_hand(self):
        """Determine winner and award pot"""
        players_in = [p for p in self.players if not p.is_folded]
        
        if len(players_in) == 1:
            winner = players_in[0]
            self.game_message = f"{winner.name} wins {self.pot}!"
        else:
            # Showdown
            best_score = -1
            winner = None
            
            for player in players_in:
                _, score = HandEvaluator.best_hand(player.hole_cards, self.community_cards)
                if score > best_score:
                    best_score = score
                    winner = player
            
            self.game_message = f"{winner.name} wins {self.pot}!"
        
        winner.stack += self.pot
        self.message_timer = 120
        
        # Check game over
        active_players = sum(1 for p in self.players if p.stack > 0)
        if active_players <= 1:
            self.game_over = True
            self.winner = [p for p in self.players if p.stack > 0][0]
            self.game_message = f"GAME OVER - {self.winner.name} wins!"
        else:
            # Reset for next hand
            pygame.time.set_timer(pygame.USEREVENT, 2000)
    
    def draw_card(self, card, x, y, hidden=False):
        """Draw a single card"""
        card_width, card_height = 60, 90
        rect = pygame.Rect(x, y, card_width, card_height)
        
        if hidden:
            pygame.draw.rect(self.screen, COLOR_BUTTON, rect)
            pygame.draw.rect(self.screen, COLOR_TEXT, rect, 2)
            self.screen.blit(self.font_tiny.render("?", True, COLOR_TEXT), (x + 20, y + 35))
        else:
            pygame.draw.rect(self.screen, COLOR_CARD_BG, rect)
            pygame.draw.rect(self.screen, (0, 0, 0), rect, 2)
            
            color = (255, 0, 0) if card.suit in [Suit.HEARTS, Suit.DIAMONDS] else (0, 0, 0)
            rank_text = self.font_small.render(card.rank, True, color)
            suit_text = self.font_medium.render(card.suit.value, True, color)
            
            self.screen.blit(rank_text, (x + 5, y + 5))
            self.screen.blit(suit_text, (x + 20, y + 55))
    
    def draw_player_info(self, player, x, y, is_current=False):
        """Draw player information"""
        bg_color = (100, 100, 100) if is_current else (50, 50, 50)
        pygame.draw.rect(self.screen, bg_color, (x - 80, y - 60, 160, 120), border_radius=10)
        
        name_text = self.font_medium.render(player.name, True, COLOR_TEXT)
        stack_text = self.font_small.render(f"${player.stack}", True, COLOR_CHIP_PLAYER)
        bet_text = self.font_small.render(f"Bet: ${player.current_bet}", True, COLOR_CHIP_PLAYER)
        
        self.screen.blit(name_text, (x - 60, y - 50))
        self.screen.blit(stack_text, (x - 60, y - 10))
        self.screen.blit(bet_text, (x - 60, y + 20))
        
        if player.is_folded:
            fold_text = self.font_small.render("FOLDED", True, (255, 0, 0))
            self.screen.blit(fold_text, (x - 60, y + 50))
    
    def draw_button(self, button_rect, text, is_hover=False):
        """Draw button with hover effect"""
        color = COLOR_BUTTON_HOVER if is_hover else COLOR_BUTTON
        pygame.draw.rect(self.screen, color, button_rect, border_radius=5)
        pygame.draw.rect(self.screen, COLOR_TEXT, button_rect, 2, border_radius=5)
        
        text_surface = self.font_small.render(text, True, COLOR_TEXT)
        text_rect = text_surface.get_rect(center=button_rect.center)
        self.screen.blit(text_surface, text_rect)
    
    def draw(self):
        """Render entire game"""
        self.screen.fill(COLOR_BG)
        
        # Draw community cards
        com_x = 500
        com_y = 150
        self.screen.blit(self.font_medium.render("Community Cards", True, COLOR_TEXT), (com_x - 50, com_y - 50))
        
        for i in range(5):
            if i < len(self.community_cards):
                self.draw_card(self.community_cards[i], com_x + i * 80, com_y)
            else:
                pygame.draw.rect(self.screen, (100, 100, 100), (com_x + i * 80, com_y, 60, 90))
        
        # Draw pot
        pot_text = self.font_large.render(f"Pot: ${self.pot}", True, COLOR_POT)
        self.screen.blit(pot_text, (550, 50))
        
        # Draw phase
        phase_text = self.font_medium.render(f"Phase: {self.phase.value.upper()}", True, COLOR_TEXT)
        self.screen.blit(phase_text, (1100, 50))
        
        # Draw players
        # Player (bottom center)
        player = self.players[0]
        self.draw_player_info(player, 700, 800, is_current=(self.current_player_idx == 0))
        self.draw_card(player.hole_cards[0], 620, 700)
        self.draw_card(player.hole_cards[1], 700, 700)
        
        # NPC (left)
        player = self.players[1]
        self.draw_player_info(player, 150, 300, is_current=(self.current_player_idx == 1))
        self.draw_card(player.hole_cards[0], 50, 350, hidden=not self.game_over and self.phase != GamePhase.SHOWDOWN)
        self.draw_card(player.hole_cards[1], 130, 350, hidden=not self.game_over and self.phase != GamePhase.SHOWDOWN)
        
        # Dealer (right)
        player = self.players[2]
        self.draw_player_info(player, 1250, 300, is_current=(self.current_player_idx == 2))
        self.draw_card(player.hole_cards[0], 1170, 350, hidden=not self.game_over and self.phase != GamePhase.SHOWDOWN)
        self.draw_card(player.hole_cards[1], 1250, 350, hidden=not self.game_over and self.phase != GamePhase.SHOWDOWN)
        
        # Draw action buttons (only for current player if human)
        if self.current_player_idx == 0 and not self.players[0].is_folded and self.phase != GamePhase.SHOWDOWN:
            player = self.players[0]
            call_amount = self.current_bet_level - player.current_bet
            
            mouse_pos = pygame.mouse.get_pos()
            
            # Fold
            self.draw_button(self.action_buttons['fold'], "Fold", self.action_buttons['fold'].collidepoint(mouse_pos))
            
            # Check/Call
            if call_amount == 0:
                self.draw_button(self.action_buttons['check'], "Check", self.action_buttons['check'].collidepoint(mouse_pos))
            else:
                self.draw_button(self.action_buttons['call'], f"Call {call_amount}", self.action_buttons['call'].collidepoint(mouse_pos))
            
            # Raise
            self.draw_button(self.action_buttons['raise'], f"Raise", self.action_buttons['raise'].collidepoint(mouse_pos))
            
            # All in
            self.draw_button(self.action_buttons['all_in'], "All In", self.action_buttons['all_in'].collidepoint(mouse_pos))
        
        # Draw messages
        if self.game_message and self.message_timer > 0:
            msg_text = self.font_medium.render(self.game_message, True, (255, 255, 100))
            self.screen.blit(msg_text, (400, 450))
            self.message_timer -= 1
        
        # Draw game over screen
        if self.game_over:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            overlay.set_alpha(200)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            
            winner_text = self.font_large.render(f"{self.winner.name} Wins!", True, (255, 215, 0))
            final_stack = self.font_medium.render(f"Final Stack: ${self.winner.stack}", True, COLOR_TEXT)
            
            self.screen.blit(winner_text, (WINDOW_WIDTH // 2 - 200, WINDOW_HEIGHT // 2 - 50))
            self.screen.blit(final_stack, (WINDOW_WIDTH // 2 - 150, WINDOW_HEIGHT // 2 + 50))
        
        pygame.display.flip()
    
    def update(self):
        """Update game logic"""
        if self.game_over:
            return
        
        # Handle end of phase
        if self.round_complete and self.phase != GamePhase.SHOWDOWN:
            self.round_complete = False
            self.advance_phase()
        elif self.phase == GamePhase.SHOWDOWN:
            self.end_hand()
            return
        
        # NPC turn
        if self.current_player_idx != 0 and not self.players[self.current_player_idx].is_folded:
            self.npc_action()
    
    def handle_event(self, event):
        """Handle user input"""
        if event.type == pygame.QUIT:
            return False
        
        if event.type == pygame.USEREVENT:
            self.start_new_game()
        
        if event.type == pygame.MOUSEBUTTONDOWN and self.current_player_idx == 0:
            player = self.players[0]
            
            if self.action_buttons['fold'].collidepoint(event.pos):
                self.player_action("fold")
            elif self.action_buttons['check'].collidepoint(event.pos):
                call_amount = self.current_bet_level - player.current_bet
                if call_amount == 0:
                    self.player_action("check")
                else:
                    self.player_action("call")
            elif self.action_buttons['raise'].collidepoint(event.pos):
                raise_amount = int(self.current_bet_level * 0.5)
                self.player_action("raise", raise_amount)
            elif self.action_buttons['all_in'].collidepoint(event.pos):
                self.player_action("all_in")
        
        return True
    
    def run(self):
        """Main game loop"""
        running = True
        while running:
            for event in pygame.event.get():
                running = self.handle_event(event)
            
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()