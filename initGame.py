# -*- coding: utf-8 -*-

#!/usr/bin/python
#####################################################################
# This script presents how to use the most basic features of the environment.
# It configures the engine, and makes the agent perform random actions.
# It also gets current state and reward earned with the action.
# <episodes> number of episodes are played. 
# Random combination of buttons is chosen for every action.
# Game variables from state and last reward are printed.
# To see the scenario description go to "../../scenarios/README.md"
# 
#####################################################################
from __future__ import print_function
from vizdoom import *
def initgame(evaluate):
# Create DoomGame instance. It will run the game and communicate with you.
    game = DoomGame()

# Now it's time for configuration!
# load_config could be used to load configuration instead of doing it here with code.
# If load_config is used in-code configuration will work. Note that the most recent changes will add to previous ones.
#game.load_config("../../examples/config/basic.cfg")

    #vizdoom_path = "/home/tbfk/Mount/intHDD/Documents/Studium/TU_Berlin/Elektrotechnik_Master/SS16/Projekt_Nachrichtenuebertragung/ViZDoom"
    #vizdoom_path = "/home/martin/python/ViZDoom"
    vizdoom_path = "../ViZDoom"

# Sets path to vizdoom engine executive which will be spawned as a separate process. Default is "./vizdoom".
    game.load_config(vizdoom_path + "/examples/config/health_gathering.cfg")

# Sets path to vizdoom engine executive which will be spawned as a separate process. Default is "./vizdoom".
    game.set_vizdoom_path(vizdoom_path + "/bin/vizdoom")

# Sets path to doom2 iwad resource file which contains the actual doom game. Default is "./doom2.wad".
    game.set_doom_game_path(vizdoom_path + "/scenarios/freedoom2.wad")
#game.set_doom_game_path("../../scenarios/doom2.wad")  # Not provided with environment due to licences.

# Sets path to additional resources iwad file which is basically your scenario iwad.
# If not specified default doom2 maps will be used and it's pretty much useles... unless you want to play doom.
    game.set_doom_scenario_path(vizdoom_path + "/scenarios/health_gathering.wad")

# Sets map to start (scenario .wad files can contain many maps).
    game.set_doom_map("map01")

# Sets resolution. Default is 320X240
    game.set_screen_resolution(ScreenResolution.RES_640X480)

# Sets the screen buffer format. Not used here but now you can change it. Defalut is CRCGCB.
    game.set_screen_format(ScreenFormat.CRCGCBDB)

# Sets other rendering options
    game.set_render_hud(False)
    game.set_render_crosshair(False)
    game.set_render_weapon(True)
    game.set_render_decals(False)
    game.set_render_particles(False)

# Adds buttons that will be allowed. 
    game.add_available_button(Button.TURN_LEFT)
    game.add_available_button(Button.TURN_RIGHT)
    game.add_available_button(Button.MOVE_FORWARD)

# Adds game variables that will be included in state.
#    game.add_available_game_variable(GameVariable.AMMO2)
    game.add_available_game_variable(GameVariable.HEALTH)
    game.add_available_game_variable(GameVariable.DEATHCOUNT)
# Causes episodes to finish after 200 tics (actions)
    #game.set_episode_timeout(200)

# Makes episodes start after 10 tics (~after raising the weapon)
    #game.set_episode_start_time(10)

# Makes the window appear (turned on by default)
    if evaluate:
        game.set_window_visible(True)
    else:
        game.set_window_visible(False)

# Turns on the sound. (turned off by default)
    game.set_sound_enabled(False)

# Sets the livin reward (for each move) to -1
    game.set_living_reward(-1)
    game.set_death_penalty(100)
# Sets ViZDoom mode (PLAYER, ASYNC_PLAYER, SPECTATOR, ASYNC_SPECTATOR, PLAYER mode is default)
    game.set_mode(Mode.PLAYER)

# Initialize the game. Further configuration won't take any effect from now on.
    game.init()

# Define some actions. Each list entry corresponds to declared buttons:
# MOVE_LEFT, MOVE_RIGHT, MOVE_FORWARD
# 5 more combinations are naturally possible but only 3 are included for transparency when watching.	
    #actions = [[True,False,False],[False,True,False],[False,False,True]]
    #actions = [[1,0,0],[0,1,0],[0,0,1],[1,0,1],[0,1,1]]
    actions = [[1,0,1],[0,1,1],[0,0,1]]
    

    num_actions = len(actions)
    return actions, num_actions, game
