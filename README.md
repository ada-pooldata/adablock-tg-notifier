# adablock-tg-notifier
Telegram bot to notify and check interactively the slot leader log of a Cardano staking pool.

## Installation
### Requirements:
- a running cardano node with cncli and leaderlog up to date and synchronized.
- The bot requires outbound access via port  443. No inbound connection is required
- It is recommended to copy programmatically the cncli.db SQLite database to a box with open outbound connection or to run the leaderlog process on one of your relays.
- Python >= 3.8 is required, as well as PIP

You need to run the following commands - can also be executed in a virtual python environment, as you prefer.

    git clone https://github.com/ada-pooldata/adablock-tg-notifier
    cd adablock-tg-notifier
    pip install -r requirements.txt
    cp config.yaml.default config.yaml

After this, edit the config.yaml file. The following options need to be set

- **localdb_path**: path to a local db that will store chat ids with notification option selected. Can be left to default.
- **cnclidb_path**: path to the CNCLI SQLite database. If you are running your node through cntools, this will be in */opt/cardano/cnode/guild-db/cncli/cncli.db*
- **tgbot_token**:  the telegram token for your bot. Follow the instructions on how to use BotFather on telegram https://core.telegram.org/bots#6-botfather to create your bot and retrieve the token
- **log_path**:  path to the log files. can be left default or you can set a folder. The log is rotating on a daily basis, only 10 days of log are kept.
- **notification_minutes**: an array representing when you will be receiving notifications about a leader slot, in minutes. Default is *[180, 90, 45, 15, 1]* - which means you will receive a notification 180 minutes before, 90 minutes before, etc....
- **slot_time_format**: the default string format for the datetime used in notification messages. Default is "%a %d-%m-%Y %H:%M:%S" (e.g. Sun 25-10-2021 10:00:03)
    
Once done, you can then run the script adablock.py by typing:

    python3 adablock.py
    
You can run it in a screen session, or set it up as a service, to have it running in the background. Will be writing a dockerfile and a bash script to install as a service as soon as possible.

## Usage

The following commands are available: 

- **enable**: enables notifications for leader slots
- **disable**: disables notifications for leader slots
- **nextslot**: shows information on the next leader slot assigned to your pool
- **leaderlog**: shows the number of leader slots assigned in the last available epoch

## Todo

- filter for valid chat ids (to prevent people from using your bot and retrieving leader slot timestamps)
- additional notification options
- more logging options
- some icons / emojis for the messages
