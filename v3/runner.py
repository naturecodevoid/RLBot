import bot_input_struct as bi
import bot_manager
import configparser
import ctypes
import mmap
import multiprocessing as mp

BOT_CONFIGURATION_HEADER = 'Bot Configuration'
BOT_CONFIG_KEY_PREFIX = 'bot_config_'
BOT_TEAM_PREFIX = 'bot_team_'
RLBOT_CONFIG_FILE = 'rlbot.cfg'
RLBOT_CONFIGURATION_HEADER = 'RLBot Configuration'
INPUT_SHARED_MEMORY_TAG = 'Local\\RLBOT_INPUT'
BOT_CONFIG_LOADOUT_HEADER = 'Bot Loadout'
BOT_CONFIG_MODULE_HEADER = 'Bot Location'


def get_bot_config_file_list(botCount, config):
    configFileList = []
    for i in range(botCount):
        configFileList.append(config.get(BOT_CONFIGURATION_HEADER, BOT_CONFIG_KEY_PREFIX + str(i)))
    return configFileList


def run_agent(terminate_event, callback_event, name, team, offset, module_name):
    bm = bot_manager.BotManager(terminate_event, callback_event, name, team, offset, module_name)
    bm.run()


if __name__ == '__main__':
    # Set up RLBot.cfg
    framework_config = configparser.RawConfigParser()
    framework_config.read(RLBOT_CONFIG_FILE)

    # Open anonymous shared memory for entire GameInputPacket and map buffer
    buff = mmap.mmap(-1, ctypes.sizeof(bi.GameInputPacket), INPUT_SHARED_MEMORY_TAG)
    gameInputPacket = bi.GameInputPacket.from_buffer(buff)

    # Determine number of bots which will be playing
    num_bots = framework_config.getint(RLBOT_CONFIGURATION_HEADER, 'num_bots')

    # Retrieve bot config files
    bot_configs = get_bot_config_file_list(num_bots, framework_config)

    # Create empty lists
    bot_names = []
    bot_teams = []
    bot_modules = []
    processes = []
    callbacks = []

    # Set configuration values for bots and store name and team
    for i in range(num_bots):
        bot_config = configparser.RawConfigParser()
        bot_config.read(bot_configs[i])

        gameInputPacket.sPlayerConfiguration[i].ePlayerController = 0
        gameInputPacket.sPlayerConfiguration[i].wName = bot_config.get(BOT_CONFIG_LOADOUT_HEADER,
                                                                       'name')  # Should check name is < 32 chars!
        gameInputPacket.sPlayerConfiguration[i].ucTeam = framework_config.getint(BOT_CONFIGURATION_HEADER,
                                                                                 BOT_TEAM_PREFIX + str(i))
        gameInputPacket.sPlayerConfiguration[i].ucTeamColorID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER,
                                                                                  'team_color_id')
        gameInputPacket.sPlayerConfiguration[i].ucCustomColorID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER,
                                                                                    'custom_color_id')
        gameInputPacket.sPlayerConfiguration[i].iCarID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER, 'car_id')
        gameInputPacket.sPlayerConfiguration[i].iDecalID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER, 'decal_id')
        gameInputPacket.sPlayerConfiguration[i].iWheelsID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER, 'wheels_id')
        gameInputPacket.sPlayerConfiguration[i].iBoostID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER, 'boost_id')
        gameInputPacket.sPlayerConfiguration[i].iAntennaID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER, 'antenna_id')
        gameInputPacket.sPlayerConfiguration[i].iHatID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER, 'hat_id')
        gameInputPacket.sPlayerConfiguration[i].iPaintFinish1ID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER,
                                                                                    'paint_finish_1_id')
        gameInputPacket.sPlayerConfiguration[i].iPaintFinish2ID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER,
                                                                                    'paint_finish_2_id')
        gameInputPacket.sPlayerConfiguration[i].iEngineAudioID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER,
                                                                                   'engine_audio_id')
        gameInputPacket.sPlayerConfiguration[i].iTrailsID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER, 'trails_id')
        gameInputPacket.sPlayerConfiguration[i].iGoalExplosionID = bot_config.getint(BOT_CONFIG_LOADOUT_HEADER,
                                                                                     'goal_explosion_id')

        bot_names.append(bot_config.get(BOT_CONFIG_LOADOUT_HEADER, 'name'))
        bot_teams.append(framework_config.getint(BOT_CONFIGURATION_HEADER, BOT_TEAM_PREFIX + str(i)))
        bot_modules.append(bot_config.get(BOT_CONFIG_MODULE_HEADER, 'agent_module'))

    # Create Quit event
    quit_event = mp.Event()

    # Launch processes
    for i in range(num_bots):
        callbacks.append(mp.Event())
        process = mp.Process(target=run_agent, args=(quit_event, callbacks[i], bot_names[i], bot_teams[i], i, bot_modules[i]))
        process.start()

    print("Successfully configured bots. Setting flag for injected dll.")
    gameInputPacket.bStartMatch = True

    input("Press enter key to exit\n")

    # Send quit event to all processes
    quit_event.set()

    # Wait for all processes to terminate before terminating main process
    terminated = False
    while not terminated:
        terminated = True
        for callback in callbacks:
            if not callback.is_set():
                terminated = False