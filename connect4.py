# connect4.py
# Author: santakd
# Contact: santakd at gmail dot com
# Date: February 01, 2026
# Version: 1.0.8
# License: MIT License

# Description: 
# This program is to emulate Connect4 game with AI opponent using Minimax algorithm with alpha-beta pruning.
# The AI is designed to play optimally, ensuring a challenging experience for the player.
# The game is played on a 7x6 grid, where the player uses 'X' and the AI uses 'O'.


# PIP Install Requirements:
# pip install pygame

import pygame
import sys
import logging
import time
import math
import random
import pygame.gfxdraw
import os  # Added for directory creation and file handling

# Set up logging
logging.basicConfig(filename='connect4.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for board dimensions and display
BOARD_WIDTH = 7
BOARD_HEIGHT = 6
CELL_SIZE = 100
WINDOW_WIDTH = BOARD_WIDTH * CELL_SIZE
WINDOW_HEIGHT = (BOARD_HEIGHT + 1) * CELL_SIZE  # Extra row for dropping pieces
FPS = 60

# Color definitions
BG_COLOR = (255, 255, 255)  # White background
BOARD_COLOR = (135, 206, 235)  # Light blue board
MENU_BG_COLOR = (240, 240, 240)  # Light menu background
BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
LIGHT_GRAY = (200, 200, 200)
BLUE = (0, 0, 255)
DARK_BLUE = (0, 0, 128)

# Player identifiers
EMPTY = 0
PLAYER1 = 1  # Human or AI1 (Red)
PLAYER2 = 2  # AI or Human2 (Yellow)

# Difficulty levels for AI (minimax depths)
DIFFICULTY_LEVELS = {
    'easy': 2,
    'medium': 4,
    'hard': 6
}

class Connect4Game:
    def __init__(self):
        """Initialize the game, pygame, and menus."""
        try:
            pygame.init()
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
            pygame.display.set_caption('Connect 4')
            self.clock = pygame.time.Clock()
            self.font = pygame.font.Font(None, 50)
            self.small_font = pygame.font.Font(None, 30)
            
            # Initialize game board as a 2D list
            self.board = [[EMPTY for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]
            self.current_player = PLAYER1
            self.game_over = False
            self.winner = None
            self.mode = None  # 'human_human', 'human_ai' or 'ai_ai'
            self.difficulty = None
            self.running = True
            self.animating = False
            self.bounce_count = 0
            
            logging.info("Game initialized successfully.")
        except Exception as e:
            logging.error(f"Initialization error: {e}")
            sys.exit(1)

    def reset_game(self):
        """Reset the board and game state for a new game."""
        self.board = [[EMPTY for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]
        self.current_player = PLAYER1
        self.game_over = False
        self.winner = None
        self.animating = False
        self.bounce_count = 0
        logging.info("Game reset.")

    def draw_board(self):
        """Draw the game board with pieces."""
        self.screen.fill(BG_COLOR)
        pygame.draw.rect(self.screen, BOARD_COLOR, (0, CELL_SIZE, WINDOW_WIDTH, WINDOW_HEIGHT - CELL_SIZE))
        radius = CELL_SIZE // 2 - 5
        for row in range(BOARD_HEIGHT):
            for col in range(BOARD_WIDTH):
                center = (col * CELL_SIZE + CELL_SIZE // 2, (row + 1) * CELL_SIZE + CELL_SIZE // 2)
                # Draw empty slot hole
                pygame.gfxdraw.filled_circle(self.screen, center[0], center[1], radius, BG_COLOR)
                pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, BG_COLOR)
                if self.board[row][col] == PLAYER1:
                    # Draw Player 1 piece (Red)
                    pygame.gfxdraw.filled_circle(self.screen, center[0], center[1], radius, RED)
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, RED)
                    # Add outline
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, BLACK)
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius - 1, BLACK)
                elif self.board[row][col] == PLAYER2:
                    # Draw Player 2 piece (Yellow)
                    pygame.gfxdraw.filled_circle(self.screen, center[0], center[1], radius, YELLOW)
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, YELLOW)
                    # Add outline
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, BLACK)
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius - 1, BLACK)
        
        if self.animating:
            # Draw animating dropping piece
            center = (self.drop_col * CELL_SIZE + CELL_SIZE // 2, int(self.drop_y))
            color = RED if self.drop_player == PLAYER1 else YELLOW
            pygame.gfxdraw.filled_circle(self.screen, center[0], center[1], radius, color)
            pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, color)
            # Add outline
            pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, BLACK)
            pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius - 1, BLACK)
        
        pygame.display.flip()

    def start_drop_animation(self, col, player):
        """Start the animation for dropping a piece with gravity."""
        target_row = None
        for r in range(BOARD_HEIGHT - 1, -1, -1):
            if self.board[r][col] == EMPTY:
                target_row = r
                break
        if target_row is None:
            return False
        self.animating = True
        self.drop_col = col
        self.drop_player = player
        self.drop_y = CELL_SIZE // 2.0
        self.drop_target_row = target_row
        self.drop_target_y = (target_row + 1) * CELL_SIZE + CELL_SIZE // 2.0
        self.velocity = 0.0
        self.acceleration = 0.5  # Reduced for smoother, slower fall
        self.bounce_count = 0
        self.elasticity = 0.3  # Reduced for less bouncy
        return True

    def update_animation(self):
        """Update the falling piece position with acceleration and bounce for smoothness."""
        if self.animating:
            self.velocity += self.acceleration
            next_y = self.drop_y + self.velocity
            if next_y >= self.drop_target_y and self.velocity > 0:
                overshoot = next_y - self.drop_target_y
                if self.bounce_count < 1:  # Reduced bounces
                    self.drop_y = self.drop_target_y - overshoot * self.elasticity
                    self.velocity = -self.velocity * self.elasticity
                    self.bounce_count += 1
                else:
                    self.drop_y = self.drop_target_y
                    self.board[self.drop_target_row][self.drop_col] = self.drop_player
                    if self.check_win(self.drop_player):
                        self.game_over = True
                        self.winner = self.drop_player
                    elif self.is_board_full():
                        self.game_over = True
                    self.animating = False
                    self.current_player = PLAYER2 if self.current_player == PLAYER1 else PLAYER1
            else:
                self.drop_y = next_y

    def is_valid_move(self, col):
        """Check if the column is not full."""
        return self.board[0][col] == EMPTY

    def check_win(self, player):
        """Check if the player has won by looking for four in a row in all directions."""
        # Horizontal check
        for row in range(BOARD_HEIGHT):
            for col in range(BOARD_WIDTH - 3):
                if all(self.board[row][col + i] == player for i in range(4)):
                    return True
        # Vertical check
        for row in range(BOARD_HEIGHT - 3):
            for col in range(BOARD_WIDTH):
                if all(self.board[row + i][col] == player for i in range(4)):
                    return True
        # Diagonal / check
        for row in range(BOARD_HEIGHT - 3):
            for col in range(BOARD_WIDTH - 3):
                if all(self.board[row + i][col + i] == player for i in range(4)):
                    return True
        # Diagonal \ check
        for row in range(3, BOARD_HEIGHT):
            for col in range(BOARD_WIDTH - 3):
                if all(self.board[row - i][col + i] == player for i in range(4)):
                    return True
        return False

    def is_board_full(self):
        """Check if the board is full (draw)."""
        return all(self.board[0][col] != EMPTY for col in range(BOARD_WIDTH))

    def minimax(self, depth, alpha, beta, maximizing_player):
        """Minimax algorithm with alpha-beta pruning for AI decision making."""
        if depth == 0 or self.game_over:
            return self.evaluate_board(), None

        if maximizing_player:
            max_eval = -math.inf
            best_col = None
            for col in range(BOARD_WIDTH):
                if self.is_valid_move(col):
                    self.drop_piece(col, PLAYER2)
                    eval, _ = self.minimax(depth - 1, alpha, beta, False)
                    self.undo_move(col)
                    if eval > max_eval:
                        max_eval = eval
                        best_col = col
                    alpha = max(alpha, eval)
                    if alpha >= beta:
                        break
            return max_eval, best_col
        else:
            min_eval = math.inf
            best_col = None
            for col in range(BOARD_WIDTH):
                if self.is_valid_move(col):
                    self.drop_piece(col, PLAYER1)
                    eval, _ = self.minimax(depth - 1, alpha, beta, True)
                    self.undo_move(col)
                    if eval < min_eval:
                        min_eval = eval
                        best_col = col
                    beta = min(beta, eval)
                    if alpha >= beta:
                        break
            return min_eval, best_col

    def evaluate_board(self):
        """Evaluate the board state for AI using a heuristic score."""
        score = 0
        # Center column preference
        center_col = BOARD_WIDTH // 2
        score += sum(1 if self.board[row][center_col] == PLAYER2 else -1 if self.board[row][center_col] == PLAYER1 else 0
                     for row in range(BOARD_HEIGHT)) * 5
        
        # Score sequences of 2, 3, 4 in a row
        for length in [4, 3, 2]:
            mult = 100 ** (length - 1)  # Higher multiplier for longer sequences
            score += self.count_sequences(PLAYER2, length) * mult
            score -= self.count_sequences(PLAYER1, length) * mult
        return score

    def count_sequences(self, player, length):
        """Count sequences of a given length for the player in all directions."""
        count = 0
        # Horizontal
        for row in range(BOARD_HEIGHT):
            for col in range(BOARD_WIDTH - length + 1):
                if all(self.board[row][col + i] == player for i in range(length)):
                    count += 1
        # Vertical
        for row in range(BOARD_HEIGHT - length + 1):
            for col in range(BOARD_WIDTH):
                if all(self.board[row + i][col] == player for i in range(length)):
                    count += 1
        # Diagonal /
        for row in range(BOARD_HEIGHT - length + 1):
            for col in range(BOARD_WIDTH - length + 1):
                if all(self.board[row + i][col + i] == player for i in range(length)):
                    count += 1
        # Diagonal \
        for row in range(length - 1, BOARD_HEIGHT):
            for col in range(BOARD_WIDTH - length + 1):
                if all(self.board[row - i][col + i] == player for i in range(length)):
                    count += 1
        return count

    def drop_piece(self, col, player):
        """Drop a piece into the column for the player (used in minimax simulation)."""
        for row in range(BOARD_HEIGHT - 1, -1, -1):
            if self.board[row][col] == EMPTY:
                self.board[row][col] = player
                return True
        return False

    def undo_move(self, col):
        """Undo the last move in the specified column."""
        for row in range(BOARD_HEIGHT):
            if self.board[row][col] != EMPTY:
                self.board[row][col] = EMPTY
                break

    def ai_move(self, player=PLAYER2):
        """Calculate AI move based on difficulty level."""
        start_time = time.time()
        depth = DIFFICULTY_LEVELS[self.difficulty]
        if self.difficulty == 'easy':
            # For easy mode, introduce some randomness
            valid_cols = [col for col in range(BOARD_WIDTH) if self.is_valid_move(col)]
            col = random.choice(valid_cols) if random.random() < 0.3 else self.minimax(depth, -math.inf, math.inf, player == PLAYER2)[1]
        else:
            _, col = self.minimax(depth, -math.inf, math.inf, player == PLAYER2)
        end_time = time.time()
        logging.info(f"AI move calculated in {end_time - start_time:.4f} seconds for depth {depth}.")
        return col

    def draw_text(self, text, pos, color=BLACK, font=None):
        """Render text on the screen at the given position."""
        if font is None:
            font = self.font
        text_surf = font.render(text, True, color)
        text_rect = text_surf.get_rect(center=pos)
        return text_surf, text_rect

    def menu_selection(self, options, title):
        """Generic menu for selection with mouse and keyboard support, rendering options as prominent buttons."""
        selected = 0
        button_height = 60
        button_width = 300
        button_spacing = 70
        start_y = WINDOW_HEIGHT // 2 - (len(options) * button_spacing) // 2 + button_height // 2
        while True:
            self.screen.fill(MENU_BG_COLOR)
            # Draw title
            self.screen.blit(*self.draw_text(title, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4), color=BLACK))
            options_rects = []
            mouse_pos = pygame.mouse.get_pos()
            for i, option in enumerate(options):
                pos = (WINDOW_WIDTH // 2, start_y + i * button_spacing)
                hover = False
                # Check if mouse is over this option
                button_rect = pygame.Rect(pos[0] - button_width // 2, pos[1] - button_height // 2, button_width, button_height)
                if button_rect.collidepoint(mouse_pos):
                    selected = i
                    hover = True
                # Draw button background
                button_color = DARK_BLUE if selected == i or hover else BLUE
                pygame.draw.rect(self.screen, button_color, button_rect, border_radius=10)
                # Draw border
                pygame.draw.rect(self.screen, BLACK, button_rect, width=2, border_radius=10)
                # Draw text
                surf, rect = self.draw_text(option, pos, WHITE, self.small_font)
                self.screen.blit(surf, rect)
                options_rects.append(button_rect)
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected = (selected - 1) % len(options)
                    elif event.key == pygame.K_DOWN:
                        selected = (selected + 1) % len(options)
                    elif event.key == pygame.K_RETURN:
                        return options[selected]
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    for i, rect in enumerate(options_rects):
                        if rect.collidepoint(event.pos):
                            return options[i]

    def show_mode_menu(self):
        """Show mode selection menu with added Human vs Human option."""
        options = ['Human vs Human', 'Human vs AI', 'AI vs AI']
        selected = self.menu_selection(options, 'Select Mode')
        if selected == 'Human vs Human':
            self.mode = 'human_human'
        elif selected == 'Human vs AI':
            self.mode = 'human_ai'
        elif selected == 'AI vs AI':
            self.mode = 'ai_ai'
        logging.info(f"Mode selected: {self.mode}")

    def show_difficulty_menu(self):
        """Show difficulty selection menu, skipped for Human vs Human mode."""
        if self.mode == 'human_human':
            return
        options = ['Easy', 'Medium', 'Hard']
        selected = self.menu_selection(options, 'Select Difficulty')
        self.difficulty = selected.lower()
        logging.info(f"Difficulty selected: {self.difficulty}")

    def show_game_over_menu(self):
        """Show game over menu and ask if the player wants to play again."""
        if self.winner:
            if self.mode == 'human_ai':
                winner_text = "Player 1 Wins!" if self.winner == PLAYER1 else "AI Wins!"
            elif self.mode == 'human_human':
                winner_text = "Player 1 Wins!" if self.winner == PLAYER1 else "Player 2 Wins!"
            else:
                winner_text = "AI 1 Wins!" if self.winner == PLAYER1 else "AI 2 Wins!"
        else:
            winner_text = "It's a Draw!"
        options = ['Yes', 'No']
        selected = self.menu_selection(options, winner_text + ' Play Again?')
        return selected == 'Yes'

    def handle_human_input(self, event):
        """Handle mouse input for human player."""
        if event.type == pygame.MOUSEBUTTONDOWN and not self.animating:
            pos = event.pos
            col = pos[0] // CELL_SIZE
            if self.is_valid_move(col):
                self.start_drop_animation(col, self.current_player)

    def run_ai_move(self):
        """Run AI move and start animation for the current player."""
        if self.current_player == PLAYER1:
            col = self.ai_move(player=PLAYER1)
        else:
            col = self.ai_move()
        if col is not None:
            self.start_drop_animation(col, self.current_player)

    def display_final_board_with_delay(self):
        """Display the final board with winner text and a prominent continue button for 5 seconds or until clicked.
        Also saves the final board image to the 'c4_metrics' subdirectory."""
        self.draw_board()

        # Create the output directory if it doesn't exist
        os.makedirs("c4_metrics", exist_ok=True)

        # Generate a unique filename with timestamp
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        plot_filename = f"c4_metrics/final_board_{timestamp}.png"

        # Save the current screen (final board) as an image
        pygame.image.save(self.screen, plot_filename)
        logging.info(f"Final board saved to {plot_filename}")

        if self.winner:
            if self.mode == 'human_ai':
                winner_text = "Player 1 Wins!" if self.winner == PLAYER1 else "AI Wins!"
            elif self.mode == 'human_human':
                winner_text = "Player 1 Wins!" if self.winner == PLAYER1 else "Player 2 Wins!"
            else:
                winner_text = "AI 1 Wins!" if self.winner == PLAYER1 else "AI 2 Wins!"
        else:
            winner_text = "It's a Draw!"

        # Winner text at top
        winner_surf, winner_rect = self.draw_text(winner_text, (WINDOW_WIDTH // 2, CELL_SIZE // 3), color=BLACK)

        # Prominent continue button below winner text
        button_text = "Continue"
        button_surf, button_temp_rect = self.draw_text(button_text, (WINDOW_WIDTH // 2, CELL_SIZE // 3 * 2), color=WHITE, font=self.small_font)
        button_width = button_temp_rect.width + 40  # Increased padding
        button_height = button_temp_rect.height + 20  # Increased padding
        button_x = WINDOW_WIDTH // 2 - button_width // 2
        button_y = CELL_SIZE // 3 * 2 - button_height // 2
        button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        button_text_x = button_x + 20
        button_text_y = button_y + 10

        start_time = pygame.time.get_ticks()
        delay_ms = 9000 # 9 seconds to display final board

        while self.running:
            mouse_pos = pygame.mouse.get_pos()
            hover = button_rect.collidepoint(mouse_pos)
            button_color = DARK_BLUE if hover else BLUE

            # Redraw board to reset any previous overlays
            self.draw_board()

            # Draw winner text
            self.screen.blit(winner_surf, winner_rect)

            # Draw button with border
            pygame.draw.rect(self.screen, button_color, button_rect, border_radius=10)
            pygame.draw.rect(self.screen, BLACK, button_rect, width=2, border_radius=10)
            self.screen.blit(button_surf, (button_text_x, button_text_y))

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if button_rect.collidepoint(event.pos):
                        return

            current_time = pygame.time.get_ticks()
            if current_time - start_time >= delay_ms:
                return

            self.clock.tick(FPS)

    def run(self):
        """Main game loop handling menus, game play, and resets."""
        try:
            while self.running:
                self.show_mode_menu()
                if not self.running:
                    break
                self.show_difficulty_menu()
                if not self.running:
                    break
                self.reset_game()
                
                while not self.game_over and self.running:
                    self.update_animation()
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.running = False
                        # Handle human input based on mode and current player
                        elif (self.mode == 'human_human' or 
                              (self.mode == 'human_ai' and self.current_player == PLAYER1)):
                            self.handle_human_input(event)
                    
                    if not self.animating:
                        if self.mode == 'human_ai' and self.current_player == PLAYER2:
                            col = self.ai_move()
                            if col is not None:
                                self.start_drop_animation(col, PLAYER2)
                        elif self.mode == 'ai_ai':
                            self.run_ai_move()
                    
                    self.draw_board()
                    self.clock.tick(FPS)
                    
                if self.running:
                    self.display_final_board_with_delay()
                    if self.running:
                        play_again = self.show_game_over_menu()
                        if not play_again:
                            self.running = False
            
            pygame.quit()
            logging.info("Game exited successfully.")
        except Exception as e:
            logging.error(f"Runtime error: {e}")
            pygame.quit()
            sys.exit(1)

if __name__ == "__main__":
    game = Connect4Game()
    game.run()
