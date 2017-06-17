import contextlib
import sys
import inspect
import os
import shutil
import appuselfbot
import glob
import math
from PythonGists import PythonGists
from discord.ext import commands
from appuselfbot import bot_prefix
from io import StringIO
from cogs.utils.checks import *

# Common imports that can be used by the debugger.
import requests
import json
import gc
import datetime
import time
import traceback
import prettytable
import re
import io
import asyncio
import discord
import random
import subprocess
from bs4 import BeautifulSoup
import urllib
import psutil

'''Module for the python interpreter as well as saving, loading, viewing, etc. the cmds/scripts ran with the interpreter.'''


# Used to get the output of exec()
@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


class Debugger:

    def __init__(self, bot):
        self.bot = bot

    # Executes/evaluates code. Got the idea from RoboDanny bot by Rapptz. RoboDanny uses eval() but I use exec() to cover a wider scope of possible inputs.
    async def interpreter(self, env, code):
        if code.startswith('[m]'):
            code = code[3:].strip()
            code_block = False
        else:
            code_block = True
        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
            if not result:
                try:
                    with stdoutIO() as s:
                        result = exec(code, env)
                        if inspect.isawaitable(result):
                            result = await result
                    result = s.getvalue()
                except Exception as g:
                    return appuselfbot.bot_prefix + '```{}```'.format(type(g).__name__ + ': ' + str(g))
        except SyntaxError:
            try:
                with stdoutIO() as s:
                    result = exec(code, env)
                    if inspect.isawaitable(result):
                        result = await result
                result = s.getvalue()
            except Exception as g:
                return appuselfbot.bot_prefix + '```{}```'.format(type(g).__name__ + ': ' + str(g))

        except Exception as e:
            return appuselfbot.bot_prefix + '```{}```'.format(type(e).__name__ + ': ' + str(e))

        if len(str(result)) > 1950:
            url = PythonGists.Gist(description='Py output', content=str(result), name='output.txt')
            return appuselfbot.bot_prefix + 'Large output. Posted to Gist: %s' % url
        else:
            if code_block:
                return appuselfbot.bot_prefix + '```py\n{}\n```'.format(result)
            else:
                return result

    @commands.group(pass_context=True)
    async def py(self, ctx):
        """Python interpreter. See the wiki for more info."""

        if ctx.invoked_subcommand is None:
            pre = cmd_prefix_len()
            code = ctx.message.content[2 + pre:].strip().strip('` ')

            env = {
                'bot': self.bot,
                'ctx': ctx,
                'message': ctx.message,
                'server': ctx.message.server,
                'channel': ctx.message.channel,
                'author': ctx.message.author
            }
            env.update(globals())

            result = await self.interpreter(env, code)

            os.chdir(os.getcwd())
            with open('%s/cogs/utils/temp.txt' % os.getcwd(), 'w') as temp:
                temp.write(ctx.message.content[2 + pre:].strip())

            await self.bot.send_message(ctx.message.channel, result)

    # Save last >py cmd/script.
    @py.command(pass_context=True)
    async def save(self, ctx, *, msg):
        """Save the code you last ran. Ex: >py save stuff"""
        msg = msg.strip()[:-4] if msg.strip().endswith('.txt') else msg.strip()
        os.chdir(os.getcwd())
        if not os.path.exists('%s/cogs/utils/temp.txt' % os.getcwd()):
            return await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Nothing to save. Run a ``>py`` cmd/script first.')
        if not os.path.isdir('%s/cogs/utils/save/' % os.getcwd()):
            os.makedirs('%s/cogs/utils/save/' % os.getcwd())
        if os.path.exists('%s/cogs/utils/save/%s.txt' % (os.getcwd(), msg)):
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + '``%s.txt`` already exists. Overwrite? ``y/n``.' % msg)
            reply = await self.bot.wait_for_message(author=ctx.message.author)
            if reply.content.lower().strip() != 'y':
                return await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Cancelled.')
            if os.path.exists('%s/cogs/utils/save/%s.txt' % (os.getcwd(), msg)):
                os.remove('%s/cogs/utils/save/%s.txt' % (os.getcwd(), msg))

        try:
            shutil.move('%s/cogs/utils/temp.txt' % os.getcwd(), '%s/cogs/utils/save/%s.txt' % (os.getcwd(), msg))
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Saved last run cmd/script as ``%s.txt``' % msg)
        except:
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Error saving file as ``%s.txt``' % msg)

    # Load a cmd/script saved with the >save cmd
    @py.command(aliases=['start'], pass_context=True)
    async def run(self, ctx, *, msg):
        """Run code that you saved with the save commmand. Ex: >py run stuff"""
        save_file = msg[:-4].strip() if msg.endswith('.txt') else msg.strip()
        if not os.path.exists('%s/cogs/utils/save/%s.txt' % (os.getcwd(), save_file)):
            return await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Could not find file ``%s.txt``' % save_file)

        script = open('%s/cogs/utils/save/%s.txt' % (os.getcwd(), save_file)).read()

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'message': ctx.message,
            'server': ctx.message.server,
            'channel': ctx.message.channel,
            'author': ctx.message.author
        }
        env.update(globals())

        result = await self.interpreter(env, script.strip('` '))

        await self.bot.send_message(ctx.message.channel, result)

    # List saved cmd/scripts
    @py.command(aliases=['ls'], pass_context=True)
    async def list(self, ctx, txt: str = None):
        """List all saved scripts. Ex: >py list or >py ls"""
        os.chdir('%s/cogs/utils/save/' % os.getcwd())
        try:
            if txt:
                numb = txt.strip()
                if numb.isdigit():
                    numb = int(numb)
                else:
                    await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Invalid syntax. Ex: ``>py list 1``')
            else:
                numb = 1
            filelist = glob.glob('*.txt')
            if len(filelist) == 0:
                return await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'No saved cmd/scripts.')
            filelist.sort()
            msg = ''
            pages = int(math.ceil(len(filelist) / 10))
            if numb < 1:
                numb = 1
            elif numb > pages:
                numb = pages

            for i in range(10):
                try:
                    msg += filelist[i + (10 * (numb-1))] + '\n'
                except:
                    break

            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'List of saved cmd/scripts. Page ``%s of %s`` ```%s```' % (numb, pages, msg))
        except Exception as e:
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Error, something went wrong: ``%s``' % e)
        finally:
            os.chdir('..')
            os.chdir('..')
            os.chdir('..')

    # View a saved cmd/script
    @py.group(aliases=['vi', 'vim'], pass_context=True)
    async def view(self, ctx, *, msg: str):
        """View a saved script's contents. Ex: >py view stuff"""
        msg = msg.strip()[:-4] if msg.strip().endswith('.txt') else msg.strip()
        os.chdir('%s/cogs/utils/save/' % os.getcwd())
        try:
            if os.path.exists('%s.txt' % msg):
                f = open('%s.txt' % msg, 'r').read()
                await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Viewing ``%s.txt``: ```%s```' % (msg, f.strip('` ')))
            else:
                await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + '``%s.txt`` does not exist.' % msg)

        except Exception as e:
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Error, something went wrong: ``%s``' % e)
        finally:
            os.chdir('..')
            os.chdir('..')
            os.chdir('..')

    # Delete a saved cmd/script
    @py.group(aliases=['rm'], pass_context=True)
    async def delete(self, ctx, *, msg: str):
        """Delete a saved script. Ex: >py delete stuff"""
        msg = msg.strip()[:-4] if msg.strip().endswith('.txt') else msg.strip()
        os.chdir('%s/cogs/utils/save/' % os.getcwd())
        try:
            if os.path.exists('%s.txt' % msg):
                os.remove('%s.txt' % msg)
                await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Deleted ``%s.txt`` from saves.' % msg)
            else:
                await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + '``%s.txt`` does not exist.' % msg)
        except Exception as e:
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Error, something went wrong: ``%s``' % e)
        finally:
            os.chdir('..')
            os.chdir('..')
            os.chdir('..')

    @commands.command(pass_context=True)
    async def load(self, ctx, *, msg):
        """Load a module"""
        try:
            self.bot.load_extension(msg)
        except Exception as e:
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Failed to load module: `{}`'.format(msg))
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + '{}: {}'.format(type(e).__name__, e))
        else:
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Loaded module: `{}`'.format(msg))
        await self.bot.delete_message(ctx.message)

    @commands.command(pass_context=True)
    async def unload(self, ctx, *, msg):
        """Unload a module"""
        try:
            self.bot.unload_extension(msg)
        except Exception as e:
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Failed to unload module: `{}`'.format(msg))
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + '{}: {}'.format(type(e).__name__, e))
        else:
            await self.bot.send_message(ctx.message.channel, appuselfbot.bot_prefix + 'Unloaded module: `{}`'.format(msg))
        await self.bot.delete_message(ctx.message)
        
    @commands.group(pass_context=True)
    async def cog(self, ctx):
        """Manage custom cogs. >help cog for more information.
        >cog install <cog> - Install a custom cog from the server.
        >cog uninstall <cog> - Uninstall one of your custom cogs.
        >cog list - List all cogs on the server.
        >cog view <cog> - View information about a cog.
        If you would like to add a custom cog to the server, see http://appucogs.tk
        """
        if ctx.invoked_subcommand is None:
            await self.bot.delete_message(ctx.message)
            await self.bot.send_message(ctx.message.channel, bot_prefix + "Invalid usage. >cog <install/uninstall> <cog>")
        
                
    @cog.command(pass_context=True)
    async def install(self, ctx, cog):
        """Install a custom cog from the server."""
        def check(msg):
            if msg:
                return msg.content.lower().strip() == 'y' or msg.content.lower().strip() == 'n'
            else:
                return False
                
        await self.bot.delete_message(ctx.message)
        response = requests.get("http://appucogs.tk/cogs/{}.json".format(cog))
        if response.status_code == 404:
            await self.bot.send_message(ctx.message.channel, bot_prefix + "That cog couldn't be found on the network. Check your spelling and try again.")
        else:
            cog = response.json()
            embed = discord.Embed(title=cog["title"], description=cog["description"])
            embed.set_author(name=cog["author"])
            await self.bot.send_message(ctx.message.channel, bot_prefix + "Are you sure you want to download this cog? (y/n)", embed=embed)
            reply = await self.bot.wait_for_message(author=ctx.message.author, check=check)
            if reply.content.lower() == "y":
                download = requests.get(cog["link"]).text
                filename = cog["link"].rsplit("/", 1)[1]
                with open("cogs/" + filename, "wb+") as f:
                    f.write(download.encode("utf-8"))
                await self.bot.send_message(ctx.message.channel, bot_prefix + "Successfully downloaded `{}` to your cogs folder. Run the `load cogs.{}` command to load in your cog.".format(cog["title"], filename.rsplit(".", 1)[0]))
            else:
                await self.bot.send_message(ctx.message.channel, bot_prefix + "Didn't download `{}`: user cancelled.".format(cog["title"]))
    
    @cog.command(pass_context=True)
    async def uninstall(self, ctx, cog):
        """Uninstall one of your custom cogs."""
        def check(msg):
            if msg:
                return msg.content.lower().strip() == 'y' or msg.content.lower().strip() == 'n'
            else:
                return False
                
        await self.bot.delete_message(ctx.message)
        response = requests.get("http://appucogs.tk/cogs/{}.json".format(cog))
        if response.status_code == 404:
            await self.bot.send_message(ctx.message.channel, bot_prefix + "That's not a real cog!")
        else:
            found_cog = response.json()
            if os.path.isfile("cogs/" + cog + ".py"):
                embed = discord.Embed(title=found_cog["title"], description=found_cog["description"])
                embed.set_author(name=found_cog["author"])
                await self.bot.send_message(ctx.message.channel, bot_prefix + "Are you sure you want to delete this cog? (y/n)", embed=embed)
                reply = await self.bot.wait_for_message(author=ctx.message.author, check=check)
                if reply.content.lower() == "y":
                    os.remove("cogs/" + cog + ".py")
                    await self.bot.send_message(ctx.message.channel, bot_prefix + "Successfully deleted the `{}` cog.".format(found_cog["title"]))
                else:
                    await self.bot.send_message(ctx.message.channel, bot_prefix + "Didn't delete `{}`: user cancelled.".format(found_cog["title"]))
            else:
                await self.bot.send_message(ctx.message.channel, bot_prefix + "You don't have `{}` installed!".format(found_cog["title"]))
    
    @cog.command(pass_context=True)
    async def list(self, ctx):
        """List all cogs on the server."""
        await self.bot.delete_message(ctx.message)
        site = requests.get('https://github.com/LyricLy/Selfbot-Cogs/tree/master/cogs').text
        soup = BeautifulSoup(site, "lxml")
        data = soup.find_all(attrs={"class": "js-navigation-open"})
        list = []
        for a in data:
            list.append(a.get("title"))
        embed = discord.Embed(title="Cog list", description="")
        for entry in list[2:]:
            entry = entry.rsplit(".")[0]
            if os.path.isfile("cogs/" + entry + ".py"):
                embed.description += "• {} - installed\n".format(entry)
            else:
                embed.description += "• {} - not installed\n".format(entry)
        await self.bot.send_message(ctx.message.channel, "", embed=embed)
        
    @cog.command(pass_context=True)
    async def view(self, ctx, cog):
        """View information about a cog."""
        await self.bot.delete_message(ctx.message)
        response = requests.get("http://appucogs.tk/cogs/{}.json".format(cog))
        if response.status_code == 404:
            await self.bot.send_message(ctx.message.channel, bot_prefix + "That cog couldn't be found on the network. Check your spelling and try again.")
        else:
            cog = response.json()
            embed = discord.Embed(title=cog["title"], description=cog["description"])
            embed.set_author(name=cog["author"])
            await self.bot.send_message(ctx.message.channel, embed=embed)
    
def setup(bot):
    bot.add_cog(Debugger(bot))
