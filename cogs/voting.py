import discord
import time
from main import db, randomHexGen
from datetime import datetime, timedelta
from discord.ext import commands
from collections import defaultdict, Counter
import random
import re

from typing import List

#➥ humanTime
def humantimeTranslator(s):
    d = {
      'w':      7*24*60*60,
      'week':   7*24*60*60,
      'weeks':  7*24*60*60,
      'd':      24*60*60,
      'day':    24*60*60,
      'days':   24*60*60,
      'h':      60*60,
      'hr':     60*60,
      'hour':   60*60,
      'hours':  60*60,
      'm':      60,
      'minute': 60,
      'minutes':60,
    }
    mult_items = defaultdict(lambda: 1).copy()
    mult_items.update(d)

    parts = re.search(r'^(\d+)([^\d]*)', s.lower().replace(' ', ''))
    if parts:
        return int(parts.group(1)) * mult_items[parts.group(2)] + humantimeTranslator(re.sub(r'^(\d+)([^\d]*)', '', s.lower()))
    else:
        return 0
##

#➥ formatContent
def formatContent(options, emojis):
    pairedList = []
    optionList = options.split("\n")
    emojiList = emojis.split("\n")
    
    for option, emoji in zip(optionList, emojiList):
        pairedList.append(f"{emoji} {option}")
        
    return "\n".join(pairedList)
##

#➥ remove spaces
def makeList_removeSpaces(string):
    spaceless = [s for s in string if s != ' ']
    spaceString = "".join(spaceless)
    spaceList = spaceString.split("\n")
    return spaceList
##
#➥ Create Results Embed
def createResultsEmbed(ctx, newPoll, isAnon):
    results = []
    winners = []
    if newPoll:
        #➥ Winner Logic
        freqDict = Counter(newPoll.values())
        maxNum = list(freqDict.values())[0]
        winnerDict = {k: v for k, v in freqDict.items() if v == maxNum}
        
        for key in winnerDict:
            winners.append(key)
        ##
        
        #➥ Results
        if not isAnon:
            for key, values in newPoll.items():
                member = ctx.guild.get_member(key)
                results.append(f"[{member.display_name}](https://www.youtube.com/watch?v=dQw4w9WgXcQ \"{member.name}\") ➙ {values}")
        else:
            for key, values in winnerDict.items():
                if values != 1:
                    results.append(f"{key} has {values} votes")
                else:
                    results.append(f"{key} has {values} vote")
        ##
    
    #➥ Forming the embed
    pollResults = discord.Embed (
        title = "Here are the Results!",
        description = "\n".join(results) if results else "No one voted!",
        color = randomHexGen(),
    )
    pollResults.add_field(name = "The winner is:" if len(winners) == 1 else "The winners are:", value = "\n".join(winners), inline = False)
    if not results:
        pollResults.remove_field(0)
    ##
    return pollResults
##

#➥ Poll View Class
class Poll(discord.ui.View):    
    def __init__(self, ctx, pollEmojiList, dictionary, embed):
        super().__init__(timeout = 15)
        self.dictionary = dictionary
        self.embed = embed
        self.ctx = ctx
        self.isAnon = True if str(self.embed.author.name) == "Poll is Anonymous" else False
        
        for emoji in pollEmojiList:
            self.add_item(PollButton(ctx, emoji, self.isAnon, dictionary, embed))
    
    async def on_timeout(self):
        #await self.message.delete()
        #await self.ctx.send(embed = createResultsEmbed(self.ctx, self.dictionary, self.isAnon))
        await self.message.edit(embed = createResultsEmbed(self.ctx, self.dictionary, self.isAnon))
##

#➥ Custom Button for Polls
class PollButton(discord.ui.Button['Poll']):
    def __init__(self, ctx, emoji, isAnon, dictionary, embed):
        super().__init__(style=discord.ButtonStyle.gray, emoji = emoji)
        self.ctx = ctx
        self.emoji = emoji
        self.isAnon = isAnon
        self.dictionary = dictionary
        self.pollEmbed = embed

    async def callback(self, interaction: discord.Interaction):
        newPoll = self.dictionary
    #➥ Settings Embed
        if self.ctx.author.id == interaction.user.id: 
            content = ":pencil2: ➙ Edit the Poll \n:grey_question: ➙ Check Your Vote \n:repeat: ➙ Clear your vote\n:closed_lock_with_key: ➙ Toggle if voters are allowed to clear their vote \n:alarm_clock: ➙ Change the timelimit (Default is 3 Days)\n<:cancel:851278899270909993> ➙ Close the Poll & Show results"
            isAuthor = True
        else:
            content = """:grey_question: ➙ Check Your Vote \n:repeat: ➙ Clear your vote """
            isAuthor = False
        settingsEmbed = discord.Embed (
            title = "Settings & Poll Info",
            description = content,
            color = randomHexGen()
        )
        settingsEmbed.add_field(name = "You haven't voted yet!", value = '\u200b')
    ##
        if self.emoji.name == 'settings':
            if interaction.user.id in newPoll:
                settingsEmbed.set_field_at(0, name = "Your vote is:", value = str(newPoll.get(interaction.user.id)))
            await interaction.response.send_message(embed = settingsEmbed, view = Settings(self.ctx, isAuthor, self.isAnon, newPoll, self.pollEmbed, settingsEmbed, self.view.message), ephemeral = True)
            return
        
        if interaction.user.id not in newPoll:
            newPoll[interaction.user.id] = self.emoji.name
            numVotes = len(newPoll)
            self.pollEmbed.set_field_at(0, name = "Votes Recorded: ", value = numVotes)
            await interaction.response.edit_message(embed = self.pollEmbed, view = self.view)
            return
##

#➥ Custom Button for Settings
class SettingsButton(discord.ui.Button['Settings']):
    def __init__(self, ctx, emoji, isAnon, dictionary, pollEmbed, settingsEmbed, pollMessage):
        super().__init__(style=discord.ButtonStyle.gray, emoji = emoji)
        self.ctx = ctx
        self.emoji = emoji
        self.isAnon = isAnon
        self.dictionary = dictionary
        self.pollEmbed = pollEmbed
        self.settingsEmbed = settingsEmbed
        self.pollMessage = pollMessage
            
    async def callback(self, interaction: discord.Interaction):
        try:
            newPoll = self.dictionary
            isLocked_bool = True if self.pollEmbed.fields[2].value == ":unlock:" else False
            
            if self.emoji.name in ['\U00002754', '\U0001f501'] and self.closedPoll:
                self.settingsEmbed.set_field_at(0, name = "The poll is now", value = '<:cancel:851278899270909993>')
                await interaction.response.edit_message(embed = self.settingsEmbed, view = None)
                return
            
            if self.emoji.name == '🔐':
                #if poll is "locked" isLocked_str = "unlocked"
                isLocked_str = ":lock:" if self.pollEmbed.fields[2].value == ":unlock:" else ":unlock:"
                
                self.label = "Unlock" if isLocked_bool else "Lock"
                self.settingsEmbed.set_field_at(0, name = "The poll is now", value = isLocked_str)
                self.pollEmbed.set_field_at(2, name = "Poll is", value = isLocked_str)
                await self.pollMessage.edit(embed = self.pollEmbed)        
                
                #➥ Locked Repeat logic
                for button in self.view.children:
                    if isLocked_bool and str(button.emoji) == '🔁':
                        button.disabled = True
                        button.style = discord.ButtonStyle.danger
                    elif str(button.emoji) == '🔁':
                        button.disabled = False
                        button.style = discord.ButtonStyle.success
                ##
                await interaction.response.edit_message(embed = self.settingsEmbed, view = self.view)
                return
            
            if str(self.emoji) == '<:cancel:851278899270909993>':
                self.settingsEmbed.set_field_at(0, name = "The poll is now", value = '<:cancel:851278899270909993>')
                await self.pollMessage.edit(embed = createResultsEmbed(self.ctx, self.dictionary, self.isAnon), view = None)
                await interaction.response.edit_message(embed = self.settingsEmbed, view = None)
            
            # Buttons non-authors can click on    
            if interaction.user.id in newPoll:  
                if self.emoji.name == '❔':
                    self.settingsEmbed.set_field_at(0, name = "Your vote is:", value = str(newPoll.get(interaction.user.id)))
                    await interaction.response.edit_message(embed = self.settingsEmbed, view = self.view) 
                    return
                if self.emoji.name == '🔁' and isLocked_bool:
                    del newPoll[interaction.user.id]
                    self.pollEmbed.set_field_at(0, name = "Votes Recorded: ", value = len(newPoll))
                    self.settingsEmbed.set_field_at(0, name = "You haven't voted yet!", value = "\u200b")
                    await self.pollMessage.edit(embed = self.pollEmbed)
                    await interaction.response.edit_message(embed = self.settingsEmbed, view = self.view)     
                    return 
                else:
                    self.settingsEmbed.set_field_at(0, name = "Poll is :lock:", value = "You cannot change your vote")
                    await interaction.response.edit_message(embed = self.settingsEmbed, view = self.view) 
                    return
            else:
                if self.emoji.name == '❔' or self.emoji.name == '🔁':
                    self.settingsEmbed.set_field_at(0, name = "You haven't voted yet!", value = "\u200b")
                    await interaction.response.edit_message(embed = self.settingsEmbed, view = self.view) 
                    return
        except Exception as e:
            await self.ctx.send(e)

##
#➥ Settings View Class
class Settings(discord.ui.View):    
    children: List[SettingsButton]
    def __init__(self, ctx, isAuthor, isAnon, dictionary, pollEmbed, settingsEmbed, pollMessage):
        super().__init__()       
        isLocked = False if pollEmbed.fields[2].value == ":unlock:" else True
        if isAuthor:
            settings = ['\U0000270f', '\U00002754', '\U0001f510', '\U0001f501', '\U000023f0', '<:cancel:851278899270909993>']
        else: settings = ['\U00002754', '\U0001f501']
            
        for emoji in settings:
            button = SettingsButton(ctx, emoji, isAnon, dictionary, pollEmbed, settingsEmbed, pollMessage)
            if isLocked and str(button.emoji) == '\U0001f501':
                button.disabled = True
                button.style = discord.ButtonStyle.danger
            elif str(button.emoji) == '\U0001f501':
                button.style = discord.ButtonStyle.success
            self.add_item(button)      
##

#➥ Setting up Cog   
class voting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        print("voting is Ready")
        
    @commands.group(aliases = ["poll"])
    async def vote(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Please specify what you'd like to do. \nEx: `{ctx.prefix}poll create` \nSee `{ctx.prefix}poll help` for a list of examples!")
##        
    
    #➥ poll help menu
    @vote.command()
    async def help(self, ctx):
        await ctx.send("""
                       """)
    ##
    
#➥ ------------   Create Poll   ------------
    @vote.command(aliases = ["create", "start", "new"])
    async def make(self, ctx, *, title = None):
        await ctx.trigger_typing() 
        
    #➥ Setting up the variables for the embed
        if title is None:
            await ctx.send("What would you like the **Title** of your poll to be?")
            title = await self.bot.get_command('waitCheck')(ctx, 100)
            
        await ctx.send("Enter the options for your poll seperated by new lines")
        msg = await self.bot.get_command('waitCheck')(ctx, 200)
        await ctx.send("Enter the emojis you wish to use for your poll seperated by new lines")
        emojis = await self.bot.get_command('waitCheck')(ctx, 300)
        await ctx.channel.purge(limit = 4)
        emojiList = makeList_removeSpaces(emojis)
        if len(emojiList) > 25:
            return await ctx.send("Polls may only have up to 25 options. Try again.")
    ##
        pollEmojiList = emojiList + ['<a:settings:845834409869180938>']
        
    #➥ Forming the embed
        pairedList = formatContent(msg, emojis)
        embed = discord.Embed(
            title = title,
            description = "React with the corresponding emote to cast a vote. \n\n" + pairedList,
            color = randomHexGen(),
            timestamp = discord.utils.utcnow()
        )
        embed.add_field(name = "Votes Recorded:", value = 0)
        embed.add_field(name = "Poll Closes on", value="May 8th")
        embed.add_field(name = "Poll is", value = ":unlock:")
        
        embed.set_author(name = "Poll is Anonymous")
        #➥ Footer
        tips = ["Tip #1: Does not work with emojis from outside the current server",
        f"Tip #2: You can create polls using \"{ctx.prefix}poll create <Title>\" to speed things up",
        "Tip #3: You can set your cooldown using human words, like \"1 week 2 days 3 hours\"",
        "Tip #4: This embed color has been randomly generated",
        "Tip #5: Only the poll creator can edit or close the poll",
        "Tip #6: The default time limit for a poll is 3 days",
        "Tip #7: Polls can have up to 25 options",
        f"Tip #8: During Poll Creation dialogue you can input \"{ctx.prefix}cancel\" to exit",
        "Tip #9: Locked polls can not have their votes changed",
        "Tip #10: Click on the settings button to find out more information about this poll",
        "Tip #11: You can hover over the nicknames in the results to see their username"]
        # Get my current profile pic
        member = ctx.guild.get_member(ctx.author.id)
        embed.set_footer(text = random.choice(tips), icon_url = member.avatar.url)
        ##
    ##  
        try:
            newPoll = {}
            pollView = Poll(ctx, pollEmojiList, newPoll, embed)
            pollView.message = await ctx.send(embed = embed, view = pollView) 
        except Exception as e:
            print(e)
            return await ctx.send("One of your emojis is invalid! Try again.")        
##            
    
    @vote.command(aliases=["append"])
    async def add(self, ctx, embed):
        embed.edit(description = embed.description + "Fleas")

    #➥ timeConvert
    @commands.command()
    async def timeConvert(self, ctx, *, inp: str):
        await ctx.send(humantimeTranslator(inp))
    ##  

def setup(bot):
    bot.add_cog(voting(bot))