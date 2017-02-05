# Game states
GMST_ENDED = 0
GMST_START = 1
GMST_CHECK_CHIPS = 2
GMST_DEAL_CARDS = 3
GMST_BET = 4
GMST_END_HAND = 5
GMST_END_HAND_PREMATURE = 6

# Games
GM_NONE = 0
GM_HOLDEM = 1

# Player game states
ST_IDLE = 0         # In main menu
ST_SEARCHING = 1    # Searching for a game
ST_LOADED_GAME = 2  # Finished loading the game
ST_IN_GAME = 3      # Spectating a game
ST_PLAYING = 4      # Playing/sitting on a table