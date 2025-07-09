#!/usr/bin/env python3
import time
import argparse
from optitrack_python.motive_receiver import MotiveReceiver
from optitrack_python.rigid_body import RigidBody
import sys
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Warning: pygame not found, visualization will be disabled")


# Global variables for tracking
pygame_window = None
font = None
clock = None
position_history = []  # For drawing trajectory
max_history_points = 100
bg_color = (0, 0, 0)  # Black
text_color = (0, 255, 0)  # Green
line_color = (255, 0, 0)  # Red


def init_pygame():
    """Initialize pygame window in maximized mode"""
    global pygame_window, font, clock
    
    pygame.init()
    # Get the display info to set up a window that fills the screen
    display_info = pygame.display.Info()
    screen_width = display_info.current_w
    screen_height = display_info.current_h
    
    # Account for taskbar/dock by reducing height slightly
    window_width = screen_width
    window_height = screen_height - 60  # Reduce height to account for taskbars
    
    # Set up window that fills the screen but isn't fullscreen
    pygame_window = pygame.display.set_mode(
        (window_width, window_height), 
        pygame.RESIZABLE
    )
    pygame.display.set_caption("OptiTrack Position Viewer")
    
    # Try to maximize the window using OS-specific methods
    try:
        import platform
        if platform.system() == "Windows":
            # On Windows, we can use SDL2 to maximize
            import ctypes
            hwnd = pygame.display.get_wm_info()["window"]
            ctypes.windll.user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE = 3
    except Exception:
        pass  # Fail silently if maximize doesn't work
    
    # Use a larger font size for better visibility
    font_size = int(window_height / 10)  # Scale font with window height
    font = pygame.font.SysFont("monospace", font_size, bold=True)
    clock = pygame.time.Clock()
    
    
def update_pygame_display(position, rb_name):
    """Update the pygame window with position data"""
    global pygame_window, font, position_history
    
    # Handle pygame events to prevent window from becoming unresponsive
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:  # Allow ESC to exit
                return False
        elif event.type == pygame.VIDEORESIZE:
            # Handle window resize events
            pygame_window = pygame.display.set_mode(
                (event.w, event.h), pygame.RESIZABLE)
    
    # Clear screen
    pygame_window.fill(bg_color)
    
    # Add current position to history
    if position is not None and len(position) >= 3:
        position_history.append(tuple(position))
        if len(position_history) > max_history_points:
            position_history.pop(0)
    
    # Draw text showing position
    width, height = pygame_window.get_size()
    if position is not None and len(position) >= 3:
        x, y, z = position[0:3]
        
        # Draw only position text, large and centered
        pos_text = f"({x:.4f}, {y:.4f}, {z:.4f})"
        
        # Render the text
        pos_surface = font.render(pos_text, True, text_color)
        
        # Center the text in the window
        text_x = width // 2 - pos_surface.get_width() // 2
        text_y = height // 2 - pos_surface.get_height() // 2
        
        # Draw the text
        pygame_window.blit(pos_surface, (text_x, text_y))
        
        # Draw 2D representation of position using X and Z components
        center_x = width // 2
        center_y = height // 2
        
        # Scale positions for visualization
        scale = 100
        # Use X and Z components for visualization (floor plane view)
        vis_x = center_x + int(x * scale)  # X → X
        vis_y = center_y + int(z * scale)  # Z → Y
        
        # Draw position marker
        pygame.draw.circle(pygame_window, (0, 255, 0), (vis_x, vis_y), 10)
        
        # Draw connecting lines for trajectory
        if len(position_history) > 1:
            points = []
            for pos in position_history:
                # Use first and third components (X and Z)
                px = center_x + int(pos[0] * scale)  # X → X
                py = center_y + int(pos[2] * scale)  # Z → Y
                points.append((px, py))
            
            if len(points) > 1:
                pygame.draw.lines(pygame_window, line_color, False, points, 2)
    
    else:
        # No position data
        no_data = "No position data"
        no_data_surface = font.render(no_data, True, text_color)
        
        # Center the text
        text_x = width // 2 - no_data_surface.get_width() // 2
        text_y = height // 2 - no_data_surface.get_height() // 2
        
        pygame_window.blit(no_data_surface, (text_x, text_y))
    
    # Update display
    pygame.display.flip()
    clock.tick(60)  # Limit to 60 FPS
    
    return True


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Print rigid body position using RigidBody class")
    parser.add_argument(
        "-n", "--name", default="A", 
        help="Name of the rigid body to track (default: 'A')"
    )
    parser.add_argument(
        "-s", "--server", default="10.40.49.47",
        help="IP address of the NatNet server"
    )
    parser.add_argument(
        "-p", "--pygame", action="store_true", default=True,
        help="Display position in a pygame window (default: True)"
    )
    parser.add_argument(
        "--no-pygame", dest="pygame", action="store_false",
        help="Disable pygame visualization"
    )
    args = parser.parse_args()
    
    # Set variables
    target_rb_name = args.name
    use_pygame = args.pygame and PYGAME_AVAILABLE
    
    # Initialize pygame if enabled
    if use_pygame:
        try:
            init_pygame()
            print("Pygame visualization enabled in maximized window mode")
            print("Press ESC to exit")
        except Exception as e:
            print(f"Error initializing pygame: {e}")
            use_pygame = False
    
    # Create MotiveReceiver and RigidBody
    print(f"Connecting to OptiTrack server at {args.server}...")
    motive = MotiveReceiver(server_ip=args.server)
    rigid_body = RigidBody(motive, target_rb_name)
    
    print(f"Tracking rigid body: '{target_rb_name}'")
    print("Client running. Press Ctrl+C to exit.")
    
    # Wait for initial connection
    print("Waiting for data connection...")
    for i in range(50):  # Try for 5 seconds
        latest_data = motive.get_last()
        if latest_data:
            print(f"✓ Connection established! Frame ID: {latest_data['frame_id']}")
            break
        time.sleep(0.1)
    else:
        print("✗ No data received. Check OptiTrack connection.")
        motive.stop()
        if pygame_window:
            pygame.quit()
        sys.exit(1)
    
    try:
        # Main loop
        running = True
        frame_count = 0
        while running:
            time.sleep(0.01)  # Short sleep to prevent CPU hogging
            frame_count += 1
            
            # Update rigid body data
            rigid_body.update()
            
            # Get current position
            position = rigid_body.positions.get_last()
            
            # Print position every 10 frames if pygame is disabled
            if not use_pygame and frame_count % 10 == 0:
                if position is not None and not all(p == 0 for p in position):
                    x, y, z = position[0:3]
                    print(f"Position: ({x:.4f}, {y:.4f}, {z:.4f})")
                    
                    # Also print velocity if available
                    if len(rigid_body.velocities.buffer) > 0:
                        velocity = rigid_body.velocities.get_last()
                        vx, vy, vz = velocity[0:3]
                        print(f"Velocity: ({vx:.4f}, {vy:.4f}, {vz:.4f})")
                else:
                    print("No position data available")
                
            # Update pygame window if enabled
            if use_pygame and pygame_window:
                running = update_pygame_display(position, target_rb_name)
                
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        motive.stop()
        if pygame_window:
            pygame.quit()
        print("Exiting script.")