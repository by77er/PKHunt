#!/usr/bin/python3


import discord
import asyncio
import async_timeout
import aiohttp
from bs4 import BeautifulSoup
import hashlib
import ujson as json
import os
import urllib.request as urllib2


bot_token = "" # put your token here

# the text displayed in the helpbox (h!help)
helptxt = """```
h!help              | command syntax and args
h!info  <name>      | show sha1 and wild counter
h!track <name>      | begin tracking a pokémon
h!del   <name>      | stop tracking a pokémon
h!list              | shows your tracking list```"""


# when a wild pkmn spawns, it will search for members who have tracked them and DM them
async def callout(message, pokemon):
    guild = message.server.id
    with open('flags.json', 'r+') as json_data:
        dat = json.load(json_data)
        if guild in dat.keys():
            for user in dat[guild].keys():
                if pokemon in dat[guild][user]:
                    try:
                        user_object = await client.get_user_info(user)
                        await client.send_message(user_object, "Trainer, a wild **{}** has appeared on {}!".format(pokemon[0].upper()+pokemon[1::].lower(), message.server.name))
                    except:
                        pass
        

# totally not ripped from SO
# stores latest pokemon in tmp.png - will need a better method if this is widely used
async def download_coroutine(session, url):
    with async_timeout.timeout(10):
        async with session.get(url) as response:
            filename = "tmp.png"
            with open(filename, 'wb') as f_handle:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f_handle.write(chunk)
            return await response.release()

client = discord.Client()

info_flag = {} # per-server temp variable that lets the bot learn about new pkmn via p!info
last_wild = {} # per-server temp variable that stores the latest wild spawn - lets the bot learn from catches

# manages the pokedex entry sending - sourced from the official website - NOTE: missing Zeraora
# can't guarantee consistency
async def send_info(msg, name, thumbnail=None):
    name = name.lower().replace("shiny ", "").replace("mega ", "").replace("♂", "-male").replace("♀", "-female").replace(" ", "-").replace(".", "").replace(",", "")
    url = "https://www.pokemon.com/us/pokedex/{}".format(name)
    data = urllib2.urlopen(url)
    page = data.read()
    pagedat = BeautifulSoup(page, 'html.parser')
    pkmn_number = "" # init
    if name.lower() == "bulbasaur":
        pkmn_number = "#1"
    else:
        pkmn_number = pagedat.find('span', class_='pokemon-number').string.strip()[1::]
        pkmn_number = "#{}".format(int(pkmn_number) + 1)
    if (pkmn_number is None):
        print("failed to find pokémon '{}'".format(name))
        return
    pkmn_class = pagedat.find('span', text='Category').find_next('span').string.strip()
    pkmn_dex_1 = pagedat.find('p', class_='version-x').string.strip().replace("\n\n", "\n").replace("\n", " ")
    pkmn_dex_2 = pagedat.find('p', class_='version-y').string.strip().replace("\n\n", "\n").replace("\n", " ")

    if pkmn_dex_1 != pkmn_dex_2:
        pkmn_dex = pkmn_dex_1 + "\n" + pkmn_dex_2
    else:
        pkmn_dex = pkmn_dex_1

        
    # print("{} {} {}".format(pkmn_number, pkmn_class, pkmn_dex))
    # embed test?
    dexbed = discord.Embed()
    icon = client.user.avatar_url
    if icon != '':
        dexbed.set_footer(text="PokéHunter Dex", icon_url=icon) # icon present?
    else:
        dexbed.set_footer(text="PokéHunter Dex")
    if not (thumbnail is None): # thumbnail avail?
        dexbed.set_thumbnail(url=thumbnail)
    dexbed.title = "{} - The {} Pokémon".format(pkmn_number, pkmn_class)
    dexbed.colour = 0xff3232
    dexbed.add_field(name="Pokédex entry:",value=pkmn_dex)
    await client.send_message(msg.channel, embed=dexbed)
    # await client.send_message(msg.channel, "```{} - The {} Pokémon\n   ----\n{}```".format(pkmn_number, pkmn_class, pkmn_dex))

    
# totally not ripped from SO
def sha1(fname):
    hash_sha1 = hashlib.sha1()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha1.update(chunk)
    return hash_sha1.hexdigest()

@client.event
async def on_ready():
    print('Logged in as {} @ {}'.format(client.user.name, client.user.id))
    game = discord.Game()
    game.name = "Pokécord"
    game.type = 0
    await client.change_presence(game=game)
    print("Serving:")
    for i in client.servers: # lists servers
        print("> {} - {}".format(i.name, i.member_count))


# this can definitely be further optimized - especially file reads and writes
# expect a slight degree of inconsistency
@client.event
async def on_message(message):
    if message.author.bot and message.author.name == "Pokécord":
        if "You caught a level" in message.content:
            print("Collecting data from catch")
            mon = ""
            shiny = False
            if message.content.split(" ")[7].lower() == "shiny":
                mon = "shiny " + message.content.split(" ")[8][0:-1].lower()
                shiny = True
            else:
                mon = message.content.split(" ")[7][0:-1].lower()
            with open('pokemon.json', 'r+') as json_data:
                d = json.load(json_data)
                if d[last_wild[message.server.id]]["name"] == '' and not shiny:
                    d[last_wild[message.server.id]]["name"] = mon
                    await client.send_message(message.channel, "Documented entry.")
                    # soup time
                json_data.seek(0)
                json_data.write(json.dumps(d, indent=3)) # write to file without closing
                json_data.truncate()
            try:
                if message.content.split(" ")[6].lower() == "shiny":
                    await send_info(message, mon[6::])
                else:
                    await send_info(message, mon)
            except:
                pass

        url = ""
        global info_flag
        if message.server.id in info_flag.keys():
            if info_flag[message.server.id][0]:
                if "doesn't seem" in message.content:
                    await client.send_message(message.channel, ":(")
                    info_flag[message.server.id] = [0, '']
                    return
                url = message.embeds[0]['image']['url']
                async with aiohttp.ClientSession(loop=asyncio.get_event_loop()) as session:
                    await download_coroutine(session, url)
                hsh = sha1("tmp.png")
                with open('pokemon.json', 'r+') as json_data:
                    d = json.load(json_data)
                    if hsh in d:
                        if d[hsh]["name"] == '':
                            d[hsh]["name"] = info_flag[message.server.id][1]
                            await client.send_message(message.channel, "Documented existing entry.") 
                        else:
                            await client.send_message(message.channel, "Entry is already documented.")
                    else:
                        d[hsh] = {'num': 0, 'name': info_flag[message.server.id][1]}
                        await client.send_message(message.channel, "Documented new entry.")
                    json_data.seek(0)
                    json_data.write(json.dumps(d, indent=3))
                    json_data.truncate()
                try:
                    await send_info(message, info_flag[message.server.id][1].lower(), thumbnail=url)
                except:
                    pass
                info_flag[message.server.id] = [0, '']
                return # info filled out
        print("Bot message detected")
        wild = False
        try:
            if "wild pokémon" in message.embeds[0]['title']:
                wild = True
                url = message.embeds[0]['image']['url']
            else:
                url = message.embeds[0]['image']['url']
                print("Not a wild message")
                return
        except (KeyError):
            print("Non-image embed")
        except (IndexError):
            pass
        if url == "":
            return
        async with aiohttp.ClientSession(loop=asyncio.get_event_loop()) as session:
            await download_coroutine(session, url)
        hsh = sha1("tmp.png")
        if wild:
            last_wild[message.server.id] = hsh
        print(hsh)
        d = {}
        pkmn_name = ''
        with open('pokemon.json', 'r+') as json_data:
            d = json.load(json_data)
            if hsh in d:
                if d[hsh]["name"] != '':
                    try:
                        pkmn = d[hsh]["name"]
                        pkmn_name = pkmn.lower()
                        pkmn = pkmn[0].upper() + pkmn[1::].lower()
                        print("Changing channel topic to {}.".format(pkmn))
                        await client.edit_channel(message.channel, topic=pkmn)
                    except:
                        pass
                d[hsh]["num"] = d[hsh]["num"] + 1
            else:
                d[hsh] = {'num': 1, 'name': ""}
            json_data.seek(0)
            json_data.write(json.dumps(d, indent=3))  
            json_data.truncate()
        if wild:
            await callout(message, pkmn_name)

    elif message.content.startswith('h!help'): # sends help message
        # await client.send_message(message.channel, helptxt)
        helpbed = discord.Embed()
        helpbed.title = "PokéHunter Help"
        helpbed.colour = 0x78E3E4
        helpbed.add_field(name="PokéHunter will DM hunters if their desired pokémon appears in the wild. All tracking lists are personal and per-server.", value=helptxt)
        """
        # helpbed.add_field(name="h!help", value="Shows command syntax and args")
        helpbed.add_field(name="h!list", value="Shows your current tracking list")
        # helpbed.add_field(name="h!track <pokémon>", value="Adds a pokémon to your tracking list")
        helpbed.add_field(name="h!del <pokémon>", value="Deletes a pokémon from your tracking list")
        helpbed.add_field(name="h!info <pokémon>", value ="Shows the sha1 hash and counter of a pokémon")
        """
	# originally intended to have a neater help box, but I had no clue how embeds worked
        await client.send_message(message.channel, embed=helpbed)

    elif message.content.startswith('h!sim'): # testing command. does nothing.
        dummy = message.content[6::]
        """
        with open('pokemon.json', 'r') as json_data:
            d = json.load(json_data)
            for i in d:
                if d[i]["name"].lower() == dummy:
                    try:
                        pkmn = d[i]["name"]
                        pkmn = pkmn[0].upper() + pkmn[1::].lower()
                        print("Changing channel topic to {}.".format(pkmn))
                        await client.edit_channel(message.channel, topic=pkmn)
                    except:
                        pass
        """
        # print("Changing channel topic to {}.".format(dummy))
        # await client.edit_channel(message.channel, topic=dummy)
        # await send_info(message, dummy)
        # await callout(message, dummy)

    elif message.content.startswith('p!info'):
        info_flag[message.server.id] = [1, message.content[7::].lower().strip()]
        try:
            int(info_flag[message.server.id][1])
            info_flag[message.server.id] = [0, '']
            return
        except:
            pass
        if info_flag[message.server.id] == [1, 'latest']:
            info_flag[message.server.id] = [0, '']
        if info_flag[message.server.id] == [1, '']:
            info_flag[message.server.id] = [0, '']

    elif message.content.startswith('h!info'):
        mon = message.content[7::].lower()
        with open('pokemon.json', 'r+') as json_data:
            d = json.load(json_data)
            for i in d.keys():
                if d[i]["name"].lower() == mon:
                    infoembed = discord.Embed()
                    infoembed.add_field(name="Info for {}:".format(mon[0].upper()+mon[1::].lower()), value="```yaml\nSHA1: {}\n\nSeen in the wild: {}```".format(i, d[i]["num"]))
                    await client.send_message(message.channel, embed=infoembed)
                    return
            await client.send_message(message.channel, "This pokémon has yet to be documented. Please enter: `p!info {}`.".format(mon))
   
    elif message.content.startswith('h!track'): # adds an entry to the .json
        wantedname = message.content[8::].strip().lower()
        with open('flags.json', 'r+') as json_data:
            dat = json.load(json_data)
            if not message.server.id in dat.keys():
                print("server not found. creating.")
                dat[message.server.id] = {}
                dat[message.server.id][message.author.id] = []
                json_data.seek(0)
                json_data.write(json.dumps(dat, indent=3))  
                json_data.truncate()
                json_data.seek(0)
                dat = json.load(json_data)
            if not message.author.id in dat[message.server.id].keys():
                print("user not found. creating.")
                dat[message.server.id][message.author.id] = []
                json_data.seek(0)
                json_data.write(json.dumps(dat, indent=3))  
                json_data.truncate()
                json_data.seek(0)
                dat = json.load(json_data)
            with open('pokemon.json', 'r+') as json_data_2:
                pokedat = json.load(json_data_2)
                for poke_id in pokedat:
                    if wantedname in dat[message.server.id][message.author.id]:
                        await client.send_message(message.channel, "You have already added {} to your tracking list.".format(wantedname[0].upper()+wantedname[1::].lower()))
                        return
                    if wantedname == pokedat[poke_id]["name"].strip().lower():
                        dat[message.server.id][message.author.id].extend([wantedname])
                        print(dat[message.server.id][message.author.id])
                        await client.send_message(message.channel, "Added {} to your tracking list.".format(wantedname[0].upper()+wantedname[1::].lower()))
                        json_data.seek(0)
                        json_data.write(json.dumps(dat, indent=3))  
                        json_data.truncate()
                        return
                await client.send_message(message.channel, "{} has not yet been documented. Please run `p!info {}` before adding it to your tracking list.".format(wantedname[0].upper()+wantedname[1::].lower(), wantedname[0].upper()+wantedname[1::].lower()))
            json_data.seek(0)
            json_data.write(json.dumps(dat, indent=3))  
            json_data.truncate()
    elif message.content.startswith('h!del'): # removes an entry from the .json
        wantedname = message.content[6::].strip().lower()
        with open('flags.json', 'r+') as json_data:
            dat = json.load(json_data)
            if not message.server.id in dat.keys():
                print("server not found. creating.")
                dat[message.server.id] = {}
                dat[message.server.id][message.author.id] = []
                json_data.seek(0)
                json_data.write(json.dumps(dat, indent=3))  
                json_data.truncate()
                json_data.seek(0)
                dat = json.load(json_data)
            if not message.author.id in dat[message.server.id].keys():
                print("user not found. creating.")
                dat[message.server.id][message.author.id] = []
                json_data.seek(0)
                json_data.write(json.dumps(dat, indent=3))  
                json_data.truncate()
                json_data.seek(0)
                dat = json.load(json_data)
            if wantedname in dat[message.server.id][message.author.id]:
                dat[message.server.id][message.author.id].remove(wantedname)
                json_data.seek(0)
                json_data.write(json.dumps(dat, indent=3))  
                json_data.truncate()
                await client.send_message(message.channel, "Removed {} from your tracking list.".format(wantedname[0].upper()+wantedname[1::].lower()))
    
    elif message.content.startswith('h!list'): # lists an individual's entries in the .json
        with open('flags.json', 'r+') as json_data:
            print("getting data")
            dat = json.load(json_data)
            if not message.server.id in dat.keys():
                print("server not found. creating.")
                dat[message.server.id] = {}
                dat[message.server.id][message.author.id] = []
                json_data.seek(0)
                json_data.write(json.dumps(dat, indent=3))  
                json_data.truncate()
                json_data.seek(0)
                dat = json.load(json_data)
            if not message.author.id in dat[message.server.id].keys():
                print("user not found. creating.")
                dat[message.server.id][message.author.id] = []
                json_data.seek(0)
                json_data.write(json.dumps(dat, indent=3))  
                json_data.truncate()
                json_data.seek(0)
                dat = json.load(json_data)
            listbed = discord.Embed()
            listbed.title = "{}'s Tracked Pokémon:".format(message.author.name)
            listbed.colour = 0xB8D3E4
            # listbed.set_thumbnail(url=message.author.avatar_url)
            amount = 0
            allnames = ""
            for name in dat[message.server.id][message.author.id]:
                nicename = name[0].upper()+name[1::].lower()
                allnames = allnames + "\n {}".format(nicename)
                amount = amount + 1
            print(allnames)
            if allnames == "":
                allnames = "\nNone!"
            listbed.add_field(name=str(amount), value=allnames)
            await client.send_message(message.channel, embed=listbed)
        pass

client.run(bot_token)
