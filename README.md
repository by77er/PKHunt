# PKHunt is a Discord bot.
Also called Pokéhunter, it's a companion bot for another bot that starts with "Poké."  It:
* Can remember the names of wild pokémon and display them
  * From catches
  * From the info command
* Keeps a counter of wild encounters for each pokémon
* Notifies server members via DM if any of their favorite pokémon appear in the wild

## Installation
Clone the repository: `git clone https://github.com/by77er/PKHunt & cd PKHunt`

Install the required modules: `pip3 install -r requirements.txt`

Fill the `bot_token` variable in `main.py`

You should be ready to roll! Send `h!help` for command details.

### Permissions
The bot needs the following permissions to operate properly:
* Read Text Channels & See Voice Channels
* Embed Links
* Read Message History

For the bot to be able to actively change the topic of a given channel to the name of any wild pokémon that spawn there, it also needs the **Manage Channel** permission for that channel.
