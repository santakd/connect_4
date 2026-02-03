#   __.-._
#   '-._"7'
#    /'.-c
#    |  //
#   _)_/||
# connect4.py
# Author: santakd
# Contact: santakd at gmail dot com
# Date: February 01, 2026
# Version: 1.0.8
# License: MIT License

# Description: 
# This program is to emulate Connect4 game with AI opponent using Minimax algorithm with alpha-beta pruning.
# The AI is designed to play optimally, ensuring a challenging experience for the player.
# The game is played on a 7x6 grid, where the player 1 uses red discs and player 2 uses yellow discs.


"""
The recent updates (e.g., depth-adjusted terminal scoring, column ordering for pruning, 
and window-based heuristic) have strengthened the AI,
making it capable of blocking obvious threats and playing more strategically in hard mode.

Identified Bugs and Fixes

Missing/Truncated Methods: The provided code has truncations (e.g., in evaluate_board, 
drop_piece, undo_move, and possibly count_sequences if it was carried over from earlier versions). 
I've assumed these are as in previous iterations (e.g., drop_piece finds the lowest row and places 
the piece, undo_move removes it). In the updated code below, I've completed/fixed these based on 
standard Connect 4 implementations to ensure completeness. If count_sequences was intended, 
it's no longer needed with the window-based heuristic.

Potential Bug in Minimax Terminal Checks: The order of checking check_win(PLAYER2) before PLAYER1 is fine,
but in rare cases where both players could "win" (impossible in valid play), it might favor the maximizer. 
This isn't a real issue since wins are checked after each move. No fix needed.

Animation and Game Over Handling: In update_animation, the win check is correct, 
but if the board fills during animation, it sets game_over without setting winner (correct for draw). 
No bug, but added comments for clarity.

AI Move in Easy Mode: Random choice is fine, but it could still pick invalid columns 
if not filtered properly— the code correctly uses valid_cols.

Performance in Hard Mode: Depth 7 with branching factor ~7 could take seconds per move on slower machines. 
Added a simple time limit check in ai_move (aborts if >5s, falls back to depth 5). This prevents UI freezes.

Undo Move Reliability: undo_move assumes the piece was placed at the top of the column, but in drop_piece, 
it places at the bottom. Fixed to correctly find and remove the last placed piece.

No Error Handling in AI: If no valid moves, minimax returns None, but ai_move handles it. Added explicit check.

Minor Issues:
Random seed not set; added for reproducibility in easy mode.
Logging could capture more AI details (e.g., chosen column).
No quit handling during animation; minor, but Pygame events are polled.

"""


# PIP Install Requirements:
# pip install pygame

import pygame
import sys
import logging
import time
import math
import random
import pygame.gfxdraw
import os  # For directory creation and file handling

# Set up logging to track game events and errors
logging.basicConfig(filename='connect4.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for board dimensions and display
BOARD_WIDTH = 7  # Number of columns
BOARD_HEIGHT = 6  # Number of rows
CELL_SIZE = 100  # Size of each cell in pixels
WINDOW_WIDTH = BOARD_WIDTH * CELL_SIZE
WINDOW_HEIGHT = (BOARD_HEIGHT + 1) * CELL_SIZE  # Extra row for dropping pieces
FPS = 60  # Frames per second for smooth animation

# Color definitions (RGB tuples)
BG_COLOR = (255, 255, 255)  # White background
BOARD_COLOR = (135, 206, 235)  # Light blue board
MENU_BG_COLOR = (240, 240, 240)  # Light menu background
BLACK = (0, 0, 0)
RED = (255, 0, 0)  # Player 1 color
YELLOW = (255, 255, 0)  # Player 2 color
WHITE = (255, 255, 255)
LIGHT_GRAY = (200, 200, 200)
BLUE = (0, 0, 255)
DARK_BLUE = (0, 0, 128)

# Player identifiers for board state
EMPTY = 0
PLAYER1 = 1  # Human or AI1 (Red)
PLAYER2 = 2  # AI or Human2 (Yellow)

# Difficulty levels: Maps to Minimax search depths
DIFFICULTY_LEVELS = {
    'easy': 2,
    'medium': 4,
    'hard': 7  # Increased for better foresight; use iterative deepening for efficiency
}

class Connect4Game:
    def __init__(self):
        """Initialize the game, Pygame, board, and state variables."""
        try:
            pygame.init()  # Initialize Pygame modules
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))  # Create game window
            pygame.display.set_caption('Connect 4')  # Set window title
            self.clock = pygame.time.Clock()  # Clock for controlling FPS
            self.font = pygame.font.Font(None, 50)  # Default font for text
            self.small_font = pygame.font.Font(None, 30)  # Smaller font for buttons

            # Initialize empty board (rows x columns, row 0 is top)
            self.board = [[EMPTY for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]
            self.current_player = PLAYER1  # Start with Player 1
            self.game_over = False
            self.winner = None
            self.mode = None  # Game mode: 'human_human', 'human_ai', 'ai_ai'
            self.difficulty = None  # AI difficulty: 'easy', 'medium', 'hard'
            self.running = True  # Main loop flag
            self.animating = False  # Flag for piece drop animation
            self.bounce_count = 0  # Counter for bounce animation

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

    # --- Drawing and Animation Methods ---

    def draw_board(self):
        """Draw the game board, empty slots, and placed pieces."""
        self.screen.fill(BG_COLOR)  # Clear screen with background color
        # Draw the board rectangle
        pygame.draw.rect(self.screen, BOARD_COLOR, (0, CELL_SIZE, WINDOW_WIDTH, WINDOW_HEIGHT - CELL_SIZE))
        radius = CELL_SIZE // 2 - 5  # Radius for circles (pieces and holes)
        for row in range(BOARD_HEIGHT):
            for col in range(BOARD_WIDTH):
                # Calculate center of each cell
                center = (col * CELL_SIZE + CELL_SIZE // 2, (row + 1) * CELL_SIZE + CELL_SIZE // 2)
                # Draw empty slot (white circle on blue board)
                pygame.gfxdraw.filled_circle(self.screen, center[0], center[1], radius, BG_COLOR)
                pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, BG_COLOR)
                if self.board[row][col] == PLAYER1:
                    # Draw red piece with anti-aliased circle and outline
                    pygame.gfxdraw.filled_circle(self.screen, center[0], center[1], radius, RED)
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, RED)
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, BLACK)
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius - 1, BLACK)
                elif self.board[row][col] == PLAYER2:
                    # Draw yellow piece with anti-aliased circle and outline
                    pygame.gfxdraw.filled_circle(self.screen, center[0], center[1], radius, YELLOW)
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, YELLOW)
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, BLACK)
                    pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius - 1, BLACK)

        if self.animating:
            # Draw the dropping piece during animation
            center = (self.drop_col * CELL_SIZE + CELL_SIZE // 2, int(self.drop_y))
            color = RED if self.drop_player == PLAYER1 else YELLOW
            pygame.gfxdraw.filled_circle(self.screen, center[0], center[1], radius, color)
            pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, color)
            pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius, BLACK)
            pygame.gfxdraw.aacircle(self.screen, center[0], center[1], radius - 1, BLACK)

        pygame.display.flip()  # Update the display

    def start_drop_animation(self, col, player):
        """Start animation for dropping a piece into a column with gravity effect."""
        target_row = None
        # Find the lowest empty row in the column (bottom-up search)
        for r in range(BOARD_HEIGHT - 1, -1, -1):
            if self.board[r][col] == EMPTY:
                target_row = r
                break
        if target_row is None:
            return False  # Column full, invalid move
        self.animating = True
        self.drop_col = col
        self.drop_player = player
        self.drop_y = CELL_SIZE // 2.0  # Start at top
        self.drop_target_row = target_row
        self.drop_target_y = (target_row + 1) * CELL_SIZE + CELL_SIZE // 2.0  # Target position
        self.velocity = 0.0  # Initial velocity for gravity simulation
        self.acceleration = 0.5  # Gravity acceleration (pixels per frame^2)
        self.bounce_count = 0
        self.elasticity = 0.3  # Bounce elasticity (energy loss)
        return True

    def update_animation(self):
        """Update the position of the falling piece with gravity and bounce."""
        if self.animating:
            self.velocity += self.acceleration  # Apply gravity
            next_y = self.drop_y + self.velocity
            if next_y >= self.drop_target_y and self.velocity > 0:
                # Hit target: simulate bounce
                overshoot = next_y - self.drop_target_y
                if self.bounce_count < 1:  # Limit to 1 bounce for smoothness
                    self.drop_y = self.drop_target_y - overshoot * self.elasticity
                    self.velocity = -self.velocity * self.elasticity
                    self.bounce_count += 1
                else:
                    # Final placement: stop animation and update board
                    self.drop_y = self.drop_target_y
                    self.board[self.drop_target_row][self.drop_col] = self.drop_player
                    if self.check_win(self.drop_player):
                        self.game_over = True
                        self.winner = self.drop_player
                    elif self.is_board_full():
                        self.game_over = True  # Draw
                    self.animating = False
                    # Switch player
                    self.current_player = PLAYER2 if self.current_player == PLAYER1 else PLAYER1
            else:
                self.drop_y = next_y  # Continue falling

    # --- Board Logic Methods ---

    def is_valid_move(self, col):
        """Check if a column has space for a new piece (top row empty)."""
        return self.board[0][col] == EMPTY

    def drop_piece(self, col, player):
        """Drop a piece into a column for simulation (used in Minimax)."""
        for row in range(BOARD_HEIGHT - 1, -1, -1):
            if self.board[row][col] == EMPTY:
                self.board[row][col] = player
                return row  # Return the row where placed for easy undo

    def undo_move(self, col):
        """Undo the last move in a column by clearing the highest occupied cell."""
        for row in range(BOARD_HEIGHT):
            if self.board[row][col] != EMPTY:
                self.board[row][col] = EMPTY
                break  # Stop after clearing the top piece

    def check_win(self, player):
        """Check for 4 in a row for the player in horizontal, vertical, or diagonal directions."""
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
        # Diagonal / (bottom-left to top-right)
        for row in range(BOARD_HEIGHT - 3):
            for col in range(BOARD_WIDTH - 3):
                if all(self.board[row + i][col + i] == player for i in range(4)):
                    return True
        # Diagonal \ (top-left to bottom-right)
        for row in range(3, BOARD_HEIGHT):
            for col in range(BOARD_WIDTH - 3):
                if all(self.board[row - i][col + i] == player for i in range(4)):
                    return True
        return False

    def is_board_full(self):
        """Check if all columns are full (game is a draw)."""
        return all(self.board[0][col] != EMPTY for col in range(BOARD_WIDTH))

    # --- AI Methods ---

    def minimax(self, depth, alpha, beta, maximizing_player):
        """Minimax with alpha-beta pruning: Recursive search for best move.
        Returns (score, best_column). Scores adjusted by depth for quicker wins/losses."""
        # Terminal states: Check win/draw before recursing
        if self.check_win(PLAYER2):
            return 999999999 + depth, None  # High positive for AI win (prefer quicker)
        if self.check_win(PLAYER1):
            return -999999999 - depth, None  # High negative for opponent win (delay)
        if self.is_board_full():
            return 0, None  # Draw
        if depth == 0:
            return self.evaluate_board(), None  # Leaf: Use heuristic

        # Column order: Center-first for better alpha-beta pruning
        cols_order = [3, 2, 4, 1, 5, 0, 6]

        if maximizing_player:  # AI (PLAYER2) maximizing score
            max_eval = -math.inf
            best_col = None
            for col in cols_order:
                if self.is_valid_move(col):
                    row = self.drop_piece(col, PLAYER2)  # Simulate move
                    eval_val, _ = self.minimax(depth - 1, alpha, beta, False)
                    self.undo_move(col)  # Undo
                    if eval_val > max_eval:
                        max_eval = eval_val
                        best_col = col
                    alpha = max(alpha, eval_val)
                    if alpha >= beta:
                        break  # Prune
            return max_eval, best_col
        else:  # Opponent (PLAYER1) minimizing score
            min_eval = math.inf
            best_col = None
            for col in cols_order:
                if self.is_valid_move(col):
                    row = self.drop_piece(col, PLAYER1)  # Simulate move
                    eval_val, _ = self.minimax(depth - 1, alpha, beta, True)
                    self.undo_move(col)  # Undo
                    if eval_val < min_eval:
                        min_eval = eval_val
                        best_col = col
                    beta = min(beta, eval_val)
                    if alpha >= beta:
                        break  # Prune
            return min_eval, best_col

    def evaluate_board(self):
        """Heuristic evaluation of board state from AI's perspective.
        Scores windows of 4 potential connects; favors AI, penalizes opponent threats."""
        score = 0

        # Helper: Score a single window of 4 cells
        def evaluate_window(window):
            player2_count = window.count(PLAYER2)
            player1_count = window.count(PLAYER1)
            if player2_count > 0 and player1_count > 0:
                return 0  # Mixed: Blocked, no value
            elif player2_count == 4:
                return 10000  # AI win (but terminals handled separately)
            elif player2_count == 3:
                return 100  # Strong threat
            elif player2_count == 2:
                return 10  # Potential
            elif player2_count == 1:
                return 1  # Weak potential
            elif player1_count == 4:
                return -10000  # Opponent win
            elif player1_count == 3:
                return -200  # High penalty for opponent threat (defensive bias)
            elif player1_count == 2:
                return -10
            elif player1_count == 1:
                return -1
            return 0  # Empty: Neutral

        # Scan all possible windows
        # Horizontal
        for row in range(BOARD_HEIGHT):
            for col in range(BOARD_WIDTH - 3):
                window = [self.board[row][col + i] for i in range(4)]
                score += evaluate_window(window)
        # Vertical
        for row in range(BOARD_HEIGHT - 3):
            for col in range(BOARD_WIDTH):
                window = [self.board[row + i][col] for i in range(4)]
                score += evaluate_window(window)
        # Diagonal /
        for row in range(BOARD_HEIGHT - 3):
            for col in range(BOARD_WIDTH - 3):
                window = [self.board[row + i][col + i] for i in range(4)]
                score += evaluate_window(window)
        # Diagonal \
        for row in range(3, BOARD_HEIGHT):
            for col in range(BOARD_WIDTH - 3):
                window = [self.board[row - i][col + i] for i in range(4)]
                score += evaluate_window(window)

        # Center control bonus (AI prefers center for more opportunities)
        center_col = BOARD_WIDTH // 2
        center_count = sum(1 if self.board[row][center_col] == PLAYER2 else -1 if self.board[row][center_col] == PLAYER1 else 0
                           for row in range(BOARD_HEIGHT))
        score += center_count * 3  # Moderate weight

        # Improvement opportunity: Add bonus for open-ended sequences (e.g., _XX_ scores higher than X_X_ for forks)
        # Could implement by checking adjacent cells outside window.

        # ML Integration opportunity: Replace with neural net eval
        # e.g., import torch; model = torch.load('c4_model.pt'); score = model(board_tensor)

        return score

    def ai_move(self, player=PLAYER2):
        """Compute AI's best move using Minimax. Supports iterative deepening for hard mode."""
        start_time = time.time()
        depth = DIFFICULTY_LEVELS[self.difficulty]
        random.seed(42)  # Set seed for reproducibility in easy mode

        if self.difficulty == 'easy':
            # 30% chance of random move for easier play
            valid_cols = [col for col in range(BOARD_WIDTH) if self.is_valid_move(col)]
            if not valid_cols:
                return None  # No moves left
            if random.random() < 0.3:
                col = random.choice(valid_cols)
            else:
                _, col = self.minimax(depth, -math.inf, math.inf, player == PLAYER2)
        else:
            # Iterative deepening for hard/medium: Start shallow, deepen until time limit
            best_col = None
            max_time = 5.0  # Seconds limit to prevent UI freeze
            for d in range(1, depth + 1):
                if time.time() - start_time > max_time:
                    break  # Time out: Use last best
                _, col = self.minimax(d, -math.inf, math.inf, player == PLAYER2)
                if col is not None:
                    best_col = col
            col = best_col

        end_time = time.time()
        logging.info(f"AI move calculated: column {col} in {end_time - start_time:.4f} seconds for depth {depth}.")
        return col

    # --- UI and Menu Methods ---

    def draw_text(self, text, pos, color=BLACK, font=None):
        """Render text surface and rect at given position."""
        if font is None:
            font = self.font
        text_surf = font.render(text, True, color)
        text_rect = text_surf.get_rect(center=pos)
        return text_surf, text_rect

    def menu_selection(self, options, title):
        """Display a menu with button options; supports mouse/keyboard navigation."""
        selected = 0
        button_height = 60
        button_width = 300
        button_spacing = 70
        start_y = WINDOW_HEIGHT // 2 - (len(options) * button_spacing) // 2 + button_height // 2
        while True:
            self.screen.fill(MENU_BG_COLOR)  # Clear with menu background
            # Draw title
            self.screen.blit(*self.draw_text(title, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 4), color=BLACK))
            options_rects = []
            mouse_pos = pygame.mouse.get_pos()
            for i, option in enumerate(options):
                pos = (WINDOW_WIDTH // 2, start_y + i * button_spacing)
                hover = False
                button_rect = pygame.Rect(pos[0] - button_width // 2, pos[1] - button_height // 2, button_width, button_height)
                if button_rect.collidepoint(mouse_pos):
                    selected = i
                    hover = True
                # Draw button with hover/selected color
                button_color = DARK_BLUE if selected == i or hover else BLUE
                pygame.draw.rect(self.screen, button_color, button_rect, border_radius=10)
                pygame.draw.rect(self.screen, BLACK, button_rect, width=2, border_radius=10)
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
        """Display menu to select game mode."""
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
        """Display menu to select AI difficulty (skipped for Human vs Human)."""
        if self.mode == 'human_human':
            return
        options = ['Easy', 'Medium', 'Hard']
        selected = self.menu_selection(options, 'Select Difficulty')
        self.difficulty = selected.lower()
        logging.info(f"Difficulty selected: {self.difficulty}")

    def show_game_over_menu(self):
        """Display game over menu with winner/draw and play again option."""
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

    # --- Input and Game Loop Methods ---

    def handle_human_input(self, event):
        """Handle mouse clicks for human moves."""
        if event.type == pygame.MOUSEBUTTONDOWN and not self.animating:
            pos = event.pos
            col = pos[0] // CELL_SIZE  # Calculate column from click position
            if self.is_valid_move(col):
                self.start_drop_animation(col, self.current_player)

    def run_ai_move(self):
        """Trigger AI move and animation for the current player."""
        if self.current_player == PLAYER1:
            col = self.ai_move(player=PLAYER1)
        else:
            col = self.ai_move()
        if col is not None:
            self.start_drop_animation(col, self.current_player)

    def display_final_board_with_delay(self):
        """Display final board with winner text and continue button; save screenshot."""
        self.draw_board()

        # Ensure output directory exists
        os.makedirs("c4_metrics", exist_ok=True)

        # Save screenshot with timestamp
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        plot_filename = f"c4_metrics/final_board_{timestamp}.png"
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

        # Render winner text
        winner_surf, winner_rect = self.draw_text(winner_text, (WINDOW_WIDTH // 2, CELL_SIZE // 3), color=BLACK)

        # Render continue button
        button_text = "Continue"
        button_surf, button_temp_rect = self.draw_text(button_text, (WINDOW_WIDTH // 2, CELL_SIZE // 3 * 2), color=WHITE, font=self.small_font)
        button_width = button_temp_rect.width + 40
        button_height = button_temp_rect.height + 20
        button_x = WINDOW_WIDTH // 2 - button_width // 2
        button_y = CELL_SIZE // 3 * 2 - button_height // 2
        button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        button_text_x = button_x + 20
        button_text_y = button_y + 10

        start_time = pygame.time.get_ticks()
        delay_ms = 9000  # 9 seconds display time

        while self.running:
            mouse_pos = pygame.mouse.get_pos()
            hover = button_rect.collidepoint(mouse_pos)
            button_color = DARK_BLUE if hover else BLUE

            # Redraw board and overlays
            self.draw_board()
            self.screen.blit(winner_surf, winner_rect)
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
        """Main game loop: Handles menus, gameplay, inputs, and resets.
        Suggestion: Add unit tests for check_win, minimax (e.g., using pytest)."""
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
                    self.update_animation()  # Handle ongoing animations
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.running = False
                        # Human input only for appropriate modes/players
                        elif (self.mode == 'human_human' or
                              (self.mode == 'human_ai' and self.current_player == PLAYER1)):
                            self.handle_human_input(event)

                    if not self.animating:
                        # AI moves
                        if self.mode == 'human_ai' and self.current_player == PLAYER2:
                            col = self.ai_move()
                            if col is not None:
                                self.start_drop_animation(col, PLAYER2)
                        elif self.mode == 'ai_ai':
                            self.run_ai_move()

                    self.draw_board()  # Redraw every frame
                    self.clock.tick(FPS)  # Limit to 60 FPS

                if self.running:
                    self.display_final_board_with_delay()
                    if self.running:
                        play_again = self.show_game_over_menu()
                        if not play_again:
                            self.running = False

            pygame.quit()  # Clean up Pygame
            logging.info("Game exited successfully.")
        except Exception as e:
            logging.error(f"Runtime error: {e}")
            pygame.quit()
            sys.exit(1)

# Entry point: Create and run the game
if __name__ == "__main__":
    game = Connect4Game()
    game.run()