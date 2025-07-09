import os
import time
import random
import vlc
from sense_hat import SenseHat, stick
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
import sys

sense = SenseHat()
sense.set_rotation(270)
sense.clear()

# colours
C_WHITE = (255, 255, 255)
C_BLACK = (0, 0, 0)
C_RED = (255, 0, 0)
C_GREEN = (0, 255, 0)
C_BLUE = (0, 0, 255)
C_YELLOW = (255, 255, 0)
C_ORANGE = (255, 165, 0)
C_CYAN = (0, 255, 255)

# configuration
MUSIC_DIR = "/home/manuel/Music" # <--- IMPORTANT: SET YOUR ACTUAL MUSIC FOLDER PATH
DEFAULT_VOLUME = 70              # Default volume percentage (0-100)
DISPLAY_IDLE_INTERVAL = 60       # Show song title every X seconds in Playing Now mode
sense.low_light = True           # Level of brightness (True: Low / False: High)

# global variables
all_music_files = []      # List of all discovered music file paths (sorted for filtering)
current_playlist = []     # The currently active playlist (always shuffled for this version)
current_track_index = -1  # Index of the current song in current_playlist
current_track_metadata = {'title': 'N/A', 'artist': 'N/A', 'album': 'N/A'}

# player mode states
MODE_STARTUP = "STARTUP"
MODE_PLAYING_NOW = "PLAYING_NOW"
MODE_SONG_SELECT_CHAR = "SONG_SELECT_CHAR"
MODE_SONG_SELECT_TITLE = "SONG_SELECT_TITLE"

current_mode = MODE_STARTUP # Initial mode

# playback state
PLAYER_PLAYING = "PLAYING"
PLAYER_PAUSED = "PAUSED"
PLAYER_STOPPED = "STOPPED"
player_state = PLAYER_STOPPED

# vlc player instance
instance = vlc.Instance('--quiet')
vlc_player = instance.media_player_new()
vlc_player.audio_set_volume(DEFAULT_VOLUME)

# sense hat display helpers

def clear_display():
    """Clears the Sense HAT display."""
    sense.clear()

def scroll_text_blocking(message, text_colour=C_WHITE, back_colour=C_BLACK, scroll_speed=0.08):
    """Scrolls a message across the Sense HAT. This function blocks execution."""
    sense.show_message(message, text_colour=text_colour, back_colour=back_colour, scroll_speed=scroll_speed)
    clear_display()

def flash_message(message, text_color, duration_secs=1.5, scroll_speed=0.08):
    """Flashes a message, then attempts to restore previous display (if applicable)."""
    # This function uses blocking scroll_text_blocking, so duration_secs is approximate
    # and it will clear the screen after the message.
    scroll_text_blocking(message, text_colour=text_color, scroll_speed=scroll_speed)
    # The main loop's idle display logic will eventually refresh for Playing Now mode.

def animate_enter_from_left(char_or_text, text_color=C_WHITE):
    """Animates a character or short text entering from the left."""
    # This is a simplified animation for show_message
    if len(char_or_text) > 1: # For longer text, just scroll in
        scroll_text_blocking(char_or_text, text_colour=text_color, scroll_speed=0.04)
        return

    # For single character, simulate slide in
    # This is still a simplification, full pixel animation is more involved
    for i in range(8): # From off-screen left to final position
        sense.clear()
        # Create a simple representation of the character at position 'i'
        # This will need to be replaced with actual pixel data for real character animation
        if i < 8: # Just show character once it's fully on screen or scrolling in
            sense.show_letter(char_or_text, text_colour=text_color)
        time.sleep(0.05)
    sense.show_letter(char_or_text, text_colour=text_color)
    time.sleep(0.5) # Hold briefly
    clear_display()

def animate_slide_out_left(char_or_text, text_color=C_WHITE):
    """Animates a character or short text sliding out to the left."""
    # Simplified animation for show_message
    if len(char_or_text) > 1: # For longer text, just scroll out
        scroll_text_blocking(char_or_text, text_colour=text_color, scroll_speed=0.08) # Will just scroll then clear
        return
    
    sense.show_letter(char_or_text, text_colour=text_color)
    time.sleep(0.2) # Show briefly
    # For a single letter, a scroll-out animation isn't directly supported by show_letter.
    # We'll just clear it after a short delay for simplicity.
    time.sleep(0.5)
    clear_display()


# --- Startup Animation ---
def startup_animation():
    """A cool startup animation."""
    # Example: Simple growing square from center
    colors = [C_BLUE, C_GREEN, C_YELLOW, C_RED]
    
    for i in range(4): # Loop to grow the square
        sense.clear()
        for x_offset in range(-i, i + 1):
            for y_offset in range(-i, i + 1):
                px, py = 3 + x_offset, 3 + y_offset
                if 0 <= px < 8 and 0 <= py < 8:
                    sense.set_pixel(px, py, *colors[i % len(colors)])
        time.sleep(0.15)
    sense.clear() # Clear after animation ends

    scroll_text_blocking("MPi3", text_colour=C_GREEN, scroll_speed=0.05)
    scroll_text_blocking("PLAYER", text_colour=C_WHITE, scroll_speed=0.05)
    scroll_text_blocking("LOADING...", text_colour=C_YELLOW, scroll_speed=0.05)


# --- Music Management ---
def scan_music_directory(path):
    """Scans the music directory and populates all_music_files."""
    global all_music_files, current_playlist

    all_music_files = []
    print(f"Scanning music directory: {path}")

    if not os.path.exists(path):
        print(f"ERROR: Music directory '{path}' does NOT exist!")
        flash_message("NO DIR!", text_color=C_RED, scroll_speed=0.05)
        time.sleep(1)
        sys.exit()

    found_supported_audio = False
    for root, _, files in os.walk(path):
        for file in files:
            file_lower = file.lower()
            full_path = os.path.join(root, file)
            if file_lower.endswith(('.mp3', '.wav', '.ogg', '.flac')):
                all_music_files.append(full_path)
                found_supported_audio = True

    if not found_supported_audio:
        print("ERROR: No supported audio files (.mp3, .flac, .wav, .ogg) found.")
        flash_message("NO MUSIC!", text_color=C_RED, scroll_speed=0.05)
        time.sleep(1)
        sys.exit()

    all_music_files.sort(key=lambda x: os.path.basename(x).lower()) # Keep a sorted list for filtering consistency
    current_playlist = list(all_music_files) # Initialize playlist with all scanned music
    random.shuffle(current_playlist) # Shuffle the main playlist on startup

    print(f"Found {len(all_music_files)} music files. Playlist shuffled.")
    return all_music_files

def get_track_metadata(filepath):
    """Retrieves title, artist, album from audio file metadata."""
    try:
        file_lower = filepath.lower()
        if file_lower.endswith('.mp3'):
            audio = MP3(filepath)
            title = audio.get("TIT2", ["Unknown Title"])[0]
            artist = audio.get("TPE1", ["Unknown Artist"])[0]
            album = audio.get("TALB", ["Unknown Album"])[0]
        elif file_lower.endswith('.flac'):
            audio = FLAC(filepath)
            title = audio.get("title", ["Unknown Title"])[0] if "title" in audio else "Unknown Title"
            artist = audio.get("artist", ["Unknown Artist"])[0] if "artist" in audio else "Unknown Artist"
            album = audio.get("album", ["Unknown Album"])[0] if "album" in audio else "Unknown Album"
        else:
            title = os.path.splitext(os.path.basename(filepath))[0]
            artist = "Various"
            album = "Various"
        return {'title': title, 'artist': artist, 'album': album}
    except Exception as e:
        print(f"Warning: Could not read metadata for {os.path.basename(filepath)}: {e}")
        return {'title': os.path.splitext(os.path.basename(filepath))[0], 'artist': 'Unknown', 'album': 'Unknown'}

# --- Player Controls ---
def play_track(index):
    """Plays the track at the given index in the current_playlist."""
    global current_track_index, player_state, current_track_metadata

    if not current_playlist or not (0 <= index < len(current_playlist)):
        print("Error: No valid track to play or index out of bounds.")
        player_state = PLAYER_STOPPED
        return

    current_track_index = index
    filepath = current_playlist[current_track_index]
    current_track_metadata = get_track_metadata(filepath)

    print(f"Playing: {current_track_metadata['title']} by {current_track_metadata['artist']}")
    media = instance.media_new(filepath)
    vlc_player.set_media(media)
    vlc_player.play()
    player_state = PLAYER_PLAYING
    flash_message("PLAY", C_GREEN, duration_secs=1.5) # Flash play sign

def play_pause():
    """Toggles play/pause state."""
    global player_state
    if vlc_player.is_playing():
        vlc_player.pause()
        player_state = PLAYER_PAUSED
        print("Paused.")
        flash_message("PAUSE", C_BLUE, duration_secs=1.5) # Flash pause sign
    else:
        if player_state == PLAYER_PAUSED:
            vlc_player.play()
            player_state = PLAYER_PLAYING
            print("Resumed.")
            flash_message("PLAY", C_GREEN, duration_secs=1.5) # Flash play sign
        elif player_state == PLAYER_STOPPED and len(current_playlist) > 0:
            play_track(0) # Start from first song if stopped and no track loaded
        else:
            print("No track to resume/play.")

def play_next_song():
    """Plays the next song in the playlist (repeats all)."""
    global current_track_index
    if not current_playlist: return
    next_index = (current_track_index + 1) % len(current_playlist)
    play_track(next_index)

def play_previous_song():
    """Plays the previous song in the playlist (repeats all)."""
    global current_track_index
    if not current_playlist: return
    prev_index = (current_track_index - 1 + len(current_playlist)) % len(current_playlist)
    play_track(prev_index)

def change_volume(delta):
    """Adjusts volume by delta and displays it."""
    current_vol = vlc_player.audio_get_volume()
    new_vol = max(0, min(100, current_vol + delta))
    vlc_player.audio_set_volume(new_vol)
    print(f"Volume: {new_vol}%")
    flash_message(f"Vol {new_vol}%", C_CYAN, duration_secs=1.5)

def stop_player():
    """Stops the current playback."""
    global player_state
    vlc_player.stop()
    player_state = PLAYER_STOPPED
    print("Stopped.")
    clear_display()

# --- Joystick Rotation Mapping ---
# Maps physical joystick directions to logical directions after 270-degree rotation
def get_rotated_direction(original_direction):
    """
    Translates physical joystick direction to logical direction after a 270-degree clockwise rotation.
    Physical UP (top of HAT)    -> Logical RIGHT
    Physical DOWN (bottom of HAT) -> Logical LEFT
    Physical LEFT (left of HAT) -> Logical UP
    Physical RIGHT (right of HAT) -> Logical DOWN
    """
    if original_direction == "up":
        return "right"
    elif original_direction == "down":
        return "left"
    elif original_direction == "left":
        return "up"
    elif original_direction == "right":
        return "down"
    else: # middle
        return original_direction

# --- Playing Now Mode Display & Input ---
last_display_idle_time = 0

def handle_playing_now_display():
    """Manages display in Playing Now mode."""
    global last_display_idle_time

    # Display song name periodically if not flashing other messages
    if player_state == PLAYER_PLAYING and time.time() - last_display_idle_time > DISPLAY_IDLE_INTERVAL:
        message = f"{current_track_metadata['title']}"
        if current_track_metadata['artist'] and current_track_metadata['artist'] != 'Unknown':
            message += f" - {current_track_metadata['artist']}"
        print(f"Displaying idle: {message}")
        scroll_text_blocking(message, text_colour=C_YELLOW, scroll_speed=0.08)
        last_display_idle_time = time.time()
    elif player_state == PLAYER_STOPPED:
        clear_display()

def handle_playing_now_input(event):
    """Handles joystick input in Playing Now mode."""
    global current_mode # Need to be able to change mode

    rotated_direction = get_rotated_direction(event.direction)
    print(f"Playing Now: Physical {event.direction} -> Logical {rotated_direction}") # Debug print

    if event.action == "pressed":
        if rotated_direction == "up":
            change_volume(10)
        elif rotated_direction == "down":
            change_volume(-10)
        elif rotated_direction == "right":
            play_next_song()
        elif rotated_direction == "left":
            # Transition to Song Select Character menu
            print("Changing to Song Select (Character) Mode")
            animate_enter_from_left("#", C_WHITE) # Animation for menu change
            init_song_select_char_mode()
            current_mode = MODE_SONG_SELECT_CHAR
        elif rotated_direction == "middle":
            play_pause()

# --- Song Select (Characters) Mode ---
CHAR_LIST = ['#', '1', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
current_char_index = 0
filtered_song_paths = [] # Songs that start with selected character/type
last_selected_char_display = None # To re-display when returning from title select

def init_song_select_char_mode():
    """Initializes state for Character Selection mode."""
    global current_char_index, filtered_song_paths, last_selected_char_display
    current_char_index = 0 # Reset to first character
    filtered_song_paths = [] # Clear previous filters
    last_selected_char_display = CHAR_LIST[current_char_index] # Initial display
    display_current_char(animate=False) # Display without animation initially
    print("Entered Song Select (Character) Mode")

def display_current_char(animate=True, direction=None):
    """Displays the current character on Sense HAT with optional animation."""
    global last_selected_char_display
    char_to_display = CHAR_LIST[current_char_index]
    
    # Simplified animation: show the letter directly
    clear_display()
    sense.show_letter(char_to_display, text_colour=C_ORANGE) # Show character brightly
    last_selected_char_display = char_to_display # Update last displayed char

def handle_song_select_char_input(event):
    """Handles joystick input in Character Selection mode."""
    global current_mode, current_char_index, filtered_song_paths

    rotated_direction = get_rotated_direction(event.direction)
    print(f"Char Select: Physical {event.direction} -> Logical {rotated_direction}") # Debug print

    if event.action == "pressed":
        if rotated_direction == "up":
            # Back to Playing Now
            print("Changing to Playing Now Mode from Char Select")
            animate_slide_out_left(CHAR_LIST[current_char_index], C_ORANGE) # Animation
            current_mode = MODE_PLAYING_NOW
            handle_playing_now_display() # Re-display current song info (idle)
        elif rotated_direction == "down":
            # Down idea: Go directly to 'All Songs' list (bypassing initial char filter)
            print("Direct to All Songs from Char Select")
            # Ensure filtered_song_paths is updated correctly
            filtered_song_paths[:] = list(all_music_files) # Set to all music files
            if filtered_song_paths:
                init_song_select_title_mode()
                current_mode = MODE_SONG_SELECT_TITLE
            else:
                flash_message("No Songs!", C_RED)
                display_current_char(animate=False) # Remain on char select
        elif rotated_direction == "left":
            # Previous Character
            current_char_index = (current_char_index - 1 + len(CHAR_LIST)) % len(CHAR_LIST)
            display_current_char(animate=True, direction="right") # Animate entry from right
        elif rotated_direction == "right":
            # Next Character
            current_char_index = (current_char_index + 1) % len(CHAR_LIST)
            display_current_char(animate=True, direction="left") # Animate entry from left
        elif rotated_direction == "middle":
            # Select Character
            selected_char = CHAR_LIST[current_char_index]
            print(f"Selected character: {selected_char}")
            
            # Animation: Character zooms (simplified)
            clear_display()
            sense.show_letter(selected_char, text_colour=C_GREEN)
            time.sleep(0.3) # "Zoom" effect pause
            clear_display()
            time.sleep(0.1)
            sense.show_letter(selected_char, text_colour=C_GREEN)
            time.sleep(0.3)
            clear_display()

            # Filter songs based on selected character (using song title metadata)
            temp_filtered_songs = []
            for s in all_music_files:
                metadata = get_track_metadata(s)
                title_lower = metadata['title'].lower()
                
                if selected_char == '#': # Symbols/Numbers
                    if title_lower and not title_lower[0].isalpha() and not title_lower[0].isdigit():
                        temp_filtered_songs.append(s)
                elif selected_char == '1': # Numbers
                    if title_lower and title_lower[0].isdigit():
                        temp_filtered_songs.append(s)
                else: # Alphabetical
                    if title_lower and title_lower.startswith(selected_char.lower()):
                        temp_filtered_songs.append(s)
            
            # Assign to global only after processing all
            filtered_song_paths[:] = temp_filtered_songs # Use slice assignment to modify list in place
            filtered_song_paths.sort(key=lambda x: get_track_metadata(x)['title'].lower()) # Sort by title

            if filtered_song_paths:
                print(f"Found {len(filtered_song_paths)} songs for character '{selected_char}'")
                init_song_select_title_mode()
                current_mode = MODE_SONG_SELECT_TITLE
            else:
                flash_message("No Match!", C_RED, duration_secs=1)
                display_current_char(animate=False) # Go back to character selection if no match

# --- Song Select (Title) Mode ---
current_filtered_index = 0

def init_song_select_title_mode():
    """Initializes state for Title Selection mode."""
    global current_filtered_index
    current_filtered_index = 0
    print("Entered Song Select (Title) Mode")
    if filtered_song_paths:
        display_current_title()
    else:
        clear_display()
        flash_message("No Songs!", C_RED, duration_secs=1)
        # If no songs in filter, go back to character select
        init_song_select_char_mode()
        current_mode = MODE_SONG_SELECT_CHAR 

def display_current_title():
    """Displays the current title from the filtered list on Sense HAT."""
    if filtered_song_paths and 0 <= current_filtered_index < len(filtered_song_paths):
        filepath = filtered_song_paths[current_filtered_index]
        metadata = get_track_metadata(filepath)
        message = f"{metadata['title']}"
        print(f"Displaying title: {message}")
        scroll_text_blocking(message, text_colour=C_YELLOW, scroll_speed=0.08)
    else:
        clear_display() # No title to display

def handle_song_select_title_input(event):
    """Handles joystick input in Title Selection mode."""
    global current_mode, current_filtered_index, current_playlist, current_track_index

    rotated_direction = get_rotated_direction(event.direction)
    print(f"Title Select: Physical {event.direction} -> Logical {rotated_direction}") # Debug print

    if event.action == "pressed":
        if rotated_direction == "up":
            # Back to Character Selection
            print("Changing to Song Select (Character) Mode from Title Select")
            # Animation: Last character zooms out (simplified)
            if last_selected_char_display:
                flash_message(last_selected_char_display, C_ORANGE, duration_secs=0.5, scroll_speed=0.05)
            init_song_select_char_mode()
            current_mode = MODE_SONG_SELECT_CHAR
        elif rotated_direction == "down":
            # Next Title (scrolling through filtered list)
            if filtered_song_paths:
                current_filtered_index = (current_filtered_index + 1) % len(filtered_song_paths)
                display_current_title()
            else:
                flash_message("No Titles!", C_RED, duration_secs=1)
        elif rotated_direction == "left":
            # Previous Title (scrolling through filtered list)
            if filtered_song_paths:
                current_filtered_index = (current_filtered_index - 1 + len(filtered_song_paths)) % len(filtered_song_paths)
                display_current_title()
            else:
                flash_message("No Titles!", C_RED, duration_secs=1)
        elif rotated_direction == "right":
            # Next Title (same as down for now, can be for paging later)
            if filtered_song_paths:
                current_filtered_index = (current_filtered_index + 1) % len(filtered_song_paths)
                display_current_title()
            else:
                flash_message("No Titles!", C_RED, duration_secs=1)
        elif rotated_direction == "middle":
            # Select Title - go back to Playing Now and play selected song
            if filtered_song_paths and 0 <= current_filtered_index < len(filtered_song_paths):
                selected_song_path = filtered_song_paths[current_filtered_index]
                
                # To play selected song, re-shuffle current_playlist to put it first,
                # then play it from index 0. This ensures "next/previous" after selection
                # still works on a full (but re-shuffled) playlist.
                # Remove selected song from its current position, then re-insert at beginning
                current_playlist.remove(selected_song_path) 
                random.shuffle(current_playlist) # Shuffle the remaining
                current_playlist.insert(0, selected_song_path) # Insert selected at beginning

                play_track(0) # Play the selected song (now at index 0)
                current_mode = MODE_PLAYING_NOW # Back to playing mode
                handle_playing_now_display() # Force immediate song info display
            else:
                flash_message("Select Song!", C_RED, duration_secs=1)


# --- Main Program Logic ---
def main():
    global current_mode, player_state

    # Startup Sequence
    startup_animation()
    print("MP3 Player Starting...")

    # Scan Music
    scanned_music = scan_music_directory(MUSIC_DIR)
    if not scanned_music:
        print("No music found. Exiting.")
        sys.exit()

    scroll_text_blocking("READY!", text_colour=C_GREEN, scroll_speed=0.05)

    # Initial Playback
    if current_playlist:
        play_track(0) # Start playing the first song in the shuffled playlist
        current_mode = MODE_PLAYING_NOW # Set initial mode
        # Ensure initial track info is displayed after player starts
        handle_playing_now_display()
    else:
        print("No music in playlist. Exiting.")
        sys.exit()

    # Main Event Loop
    try:
        while True:
            # Handle joystick input based on current mode
            for event in sense.stick.get_events():
                # Wrap event handling in a try-except to catch and report errors
                # that might cause silent exits.
                try:
                    if event.action == "pressed": # Only react to 'pressed' for main controls
                        if current_mode == MODE_PLAYING_NOW:
                            handle_playing_now_input(event)
                        elif current_mode == MODE_SONG_SELECT_CHAR:
                            handle_song_select_char_input(event)
                        elif current_mode == MODE_SONG_SELECT_TITLE:
                            handle_song_select_title_input(event)
                except Exception as e:
                    print(f"!!! ERROR during joystick event handling in {current_mode} mode: {e}")
                    # Optionally flash an error message on Sense HAT
                    flash_message("ERROR!", C_RED)
                    # Decide if you want to exit or try to recover. For now, log and continue.
                    time.sleep(2) # Pause to let message be seen

            # Auto-advance track if current song finishes
            if player_state == PLAYER_PLAYING and vlc_player.get_state() == vlc.State.Ended:
                print("Current track ended. Playing next.")
                play_next_song()

            # Handle mode-specific display updates (e.g., idle scrolling for Playing Now)
            if current_mode == MODE_PLAYING_NOW:
                handle_playing_now_display()
            # Other modes (Char Select, Title Select) are mostly event-driven for display updates
            # so no continuous 'display_idle' needed here.

            time.sleep(0.05) # Small delay to prevent burning CPU

    except KeyboardInterrupt:
        print("\nExiting player due to KeyboardInterrupt.")
    except Exception as e:
        print(f"\n!!! UNEXPECTED CRITICAL ERROR IN MAIN LOOP: {e}")
        flash_message("FATAL ERROR!", C_RED)
        time.sleep(3)
    finally:
        stop_player()
        sense.clear()
        print("Player gracefully shut down.")
        sys.exit(0) # Explicitly exit with 0 after graceful shutdown

if __name__ == "__main__":
    main()