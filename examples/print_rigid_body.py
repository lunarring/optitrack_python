#!/usr/bin/env python3
import time
import argparse
from optitrack_python.NatNetClient import NatNetClient
import sys
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Warning: pygame not found, visualization will be disabled")


# Global variables for tracking
last_position = None
total_frames = 0
frame_positions = []  # Store recent positions for debugging
max_stored_positions = 5
pygame_window = None
font = None
clock = None
position_history = []  # For drawing trajectory
max_history_points = 100
bg_color = (0, 0, 0)  # Black
text_color = (0, 255, 0)  # Green
line_color = (255, 0, 0)  # Red


def init_pygame():
    """Initialize pygame window in fullscreen mode"""
    global pygame_window, font, clock
    
    pygame.init()
    # Get the display info to set up fullscreen at native resolution
    display_info = pygame.display.Info()
    screen_width = display_info.current_w
    screen_height = display_info.current_h
    
    # Set up fullscreen window
    pygame_window = pygame.display.set_mode(
        (screen_width, screen_height), 
        pygame.FULLSCREEN
    )
    pygame.display.set_caption("OptiTrack Position Viewer")
    
    # Use a larger font size for better visibility
    font_size = int(screen_height / 10)  # Scale font with screen height
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
    
    # Clear screen
    pygame_window.fill(bg_color)
    
    # Add current position to history
    if position and isinstance(position, tuple) and len(position) >= 3:
        position_history.append(position)
        if len(position_history) > max_history_points:
            position_history.pop(0)
    
    # Draw text showing position
    width, height = pygame_window.get_size()
    if position and isinstance(position, tuple) and len(position) >= 3:
        x, y, z = position
        
        # Draw only position text, large and centered
        pos_text = f"({x:.4f}, {y:.4f}, {z:.4f})"
        
        # Render the text
        pos_surface = font.render(pos_text, True, text_color)
        
        # Center the text in the window
        text_x = width // 2 - pos_surface.get_width() // 2
        text_y = height // 2 - pos_surface.get_height() // 2
        
        # Draw the text
        pygame_window.blit(pos_surface, (text_x, text_y))
        
        # Draw 2D representation of position (top-down view, swapped X-Y)
        center_x = width // 2
        center_y = height // 2
        
        # Scale positions for visualization (correct X-Y swap)
        scale = 100
        # Use Y as X coordinate and X as Y coordinate for better visualization
        vis_x = center_x + int(y * scale)  # Y → X
        vis_y = center_y + int(x * scale)  # X → Y
        
        # Draw position marker
        pygame.draw.circle(pygame_window, (0, 255, 0), (vis_x, vis_y), 10)
        
        # Draw connecting lines for trajectory
        if len(position_history) > 1:
            points = []
            for pos in position_history:
                # Swap X and Y here too
                px = center_x + int(pos[1] * scale)  # Y → X
                py = center_y + int(pos[0] * scale)  # X → Y
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


def receive_new_frame(data_dict):
    """Callback function that processes each frame from NatNet"""
    global total_frames, last_position, frame_positions, raw_data_mode
    global use_pygame, rb_name_for_pygame
    
    # Count frames
    total_frames += 1
    frame_number = data_dict.get('frame_number', 'N/A')
    
    # Extract mocap data
    mocap_data = data_dict.get('mocap_data')
    if not mocap_data or not hasattr(mocap_data, "rigid_body_data"):
        return
        
    rigid_body_data = mocap_data.rigid_body_data
    if not hasattr(rigid_body_data, 'rigid_body_list'):
        return
        
    if not rigid_body_data.rigid_body_list:
        return
    
    # Raw data mode - print the entire data structure for debugging
    if raw_data_mode and total_frames % 100 == 0:
        print("\nDEBUG - Raw rigid body data:")
        for i, rb in enumerate(rigid_body_data.rigid_body_list):
            print(f"  Body {i}:")
            # Print all attributes of the rigid body
            for attr in dir(rb):
                if not attr.startswith('__'):
                    try:
                        value = getattr(rb, attr)
                        print(f"    {attr}: {value}")
                    except Exception as e:
                        print(f"    {attr}: Error: {e}")
        print()

    # Process all rigid bodies
    found_target = False
    for i, rb in enumerate(rigid_body_data.rigid_body_list):
        # Get ID and name if available
        rb_id = getattr(rb, 'id_num', f"Unknown-{i}")
        rb_name = None
        
        # Try different possible attribute names for the rigid body name
        for name_attr in ['sz_name', 'name', 'rb_name', 'label']:
            if hasattr(rb, name_attr):
                rb_name = getattr(rb, name_attr)
                if rb_name:
                    break
                    
        if not rb_name:
            rb_name = f"ID_{rb_id}"
            
        # Try to get position data
        position = None
        for pos_attr in ['pos', 'position', 'xyz', 'loc']:
            if hasattr(rb, pos_attr):
                position = getattr(rb, pos_attr)
                if position:
                    break
        
        # Skip if no position data
        if not position:
            continue
            
        # Check if this is our target or first rigid body
        if rb_name == target_rb_name or (not found_target and i == 0):
            found_target = True
            
            # Convert position to a tuple if it's not already
            if not isinstance(position, tuple):
                try:
                    position = tuple(position)
                except Exception:
                    # If conversion fails, use string representation
                    position = str(position)
            
            # Store position for history
            frame_positions.append((frame_number, rb_name, position))
            if len(frame_positions) > max_stored_positions:
                frame_positions.pop(0)
            
            # Print position as a single line (only if pygame is disabled)
            if not use_pygame and isinstance(position, tuple) and len(position) >= 3:
                # Neatly format the position data
                x, y, z = position[0:3]
                print(f"Position: ({x:.4f}, {y:.4f}, {z:.4f})")
            elif not use_pygame:
                print(f"Position: {position}")
                
            # Update pygame window if enabled
            if use_pygame and pygame_window:
                rb_name_for_pygame = rb_name
                # Note: We don't update pygame here to avoid blocking
                
            # Update last position
            last_position = position
            break


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Print rigid body position")
    parser.add_argument(
        "-n", "--name", default="A", 
        help="Name of the rigid body to track (default: 'A')"
    )
    parser.add_argument(
        "-s", "--server", default="10.40.49.47",
        help="IP address of the NatNet server"
    )
    parser.add_argument(
        "-r", "--raw", action="store_true",
        help="Print raw data mode (shows all rigid body attributes)"
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
    
    # Set global variables
    target_rb_name = args.name
    raw_data_mode = args.raw
    use_pygame = args.pygame and PYGAME_AVAILABLE
    rb_name_for_pygame = target_rb_name
    
    # Initialize pygame if enabled
    if use_pygame:
        try:
            init_pygame()
            print("Pygame visualization enabled in fullscreen mode")
            print("Press ESC to exit")
        except Exception as e:
            print(f"Error initializing pygame: {e}")
            use_pygame = False
    
    # Create NatNet client
    client = NatNetClient()
    client.set_server_address(args.server)

    # Set up client
    print(f"Connecting to NatNet server at {args.server}...")
    print(f"Tracking rigid body: '{target_rb_name}'")
    client.new_frame_listener = receive_new_frame
    success = client.run()
    
    if not success:
        print("Error: Failed to start client")
        if pygame_window:
            pygame.quit()
        sys.exit(1)
    
    print("Client running. Press Ctrl+C to exit.")
    
    try:
        # Main loop - update pygame window here
        running = True
        while running:
            time.sleep(0.01)  # Short sleep to prevent CPU hogging
            
            if use_pygame and pygame_window:
                # Update the pygame display from the main thread
                running = update_pygame_display(
                    last_position, rb_name_for_pygame
                )
                
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        client.shutdown()
        if pygame_window:
            pygame.quit()
        print("Exiting script.")