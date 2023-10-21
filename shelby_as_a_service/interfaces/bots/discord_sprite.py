# region
import asyncio
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Generator, List, Optional, Type, Union

import discord
from discord.ext import commands
from sprites.sprite_base import SpriteBase

from shelby_as_a_service.agents.ceq.ceq_agent import CEQAgent

# endregion


class DiscordSprite(SpriteBase):
    CLASS_NAME: str = "discord_sprite"
    available_agents: List[Type] = [CEQAgent]
    REQUIRED_SECRETS: List[str] = ["discord_bot_token"]

    discord_enabled_servers: List[int] = [1132125546340421733]
    discord_specific_channel_ids: List[int] = [1133913077268627526]
    discord_all_channels_excluded_channels: List[int]

    discord_specific_channels_enabled: bool = False
    discord_all_channels_enabled: bool = False
    discord_manual_requests_enabled: bool = True
    # Not enabled
    discord_auto_response_enabled: bool = False
    discord_auto_response_cooldown: int = 10
    discord_auto_respond_in_threads: bool = False
    discord_user_daily_token_limit: int = 30000

    discord_welcome_message: str = "ima tell you about the {}."
    discord_short_message: str = (
        "<@{}>, brevity is the soul of wit, but not of good queries. Please provide more details in your request."
    )
    discord_message_start: str = "Running request... relax, chill, and vibe a minute."
    discord_message_end: str = "Generated by: gpt-4. Memory not enabled. Has no knowledge of past or current queries. For code see https://github.com/shelby-as-a-service/shelby-as-a-service."

    def __init__(self, config_file_dict={}, **kwargs):
        """ """
        super().__init__()

        self.log.info("Starting DiscordSprite.")
        self.ceq_agent = CEQAgent(self)

        self.intents = discord.Intents.default()
        self.intents.guilds = True
        self.bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=self.intents)

        @self.bot.event
        async def on_guild_join(guild: discord.Guild):
            # Checks the guild server ID in the list of monikers, and returns none if it can't find it
            if await self.check_if_server_enabled(guild):
                channel = self.get_channel_for_welcome_message(guild)
                if channel:
                    await channel.send(  # type: ignore
                        self.format_message(
                            self.discord_welcome_message,
                            self.get_random_animal(),
                        )
                    )
                self.log.info(f"Bot has successfully join the server: {guild.name})")

        @self.bot.event
        async def on_ready():
            # App start up actions
            for guild in self.bot.guilds:
                if await self.check_if_server_enabled(guild):
                    channel = self.get_channel_for_welcome_message(guild)
                    if channel:
                        await channel.send(  # type: ignore
                            self.format_message(
                                self.discord_welcome_message,
                                self.get_random_animal(),
                            )
                        )

            self.log.info(f"Bot has logged in as {self.bot.user.name} (ID: {self.bot.user.id})")  # type: ignore
            self.log.info("------")

        @self.bot.event
        async def on_message(message: discord.Message):
            # The bot has four configurations for messages:
            # 1st, to only receive messages when it's tagged with @sprite-name
            # Or 2nd to auto-respond to all messages that it thinks it can answer
            # 3rd, the bot can be in restricted to specific channels
            # 4th, the bot can be allowed to respond in all channels (channels can be excluded)

            if message.author.id == self.bot.user.id:  # type: ignore
                # Don't respond to ourselves
                return

            self.log.info(f"Message received: {message.content}\nServer: {message.guild.name}\nChannel: {message.channel.name}\nFrom: {message.author.name}")  # type: ignore

            # 1st case: bot must be tagged with @sprite-name
            if self.discord_manual_requests_enabled:
                if not self.bot.user.mentioned_in(message):  # type: ignore
                    # Tagging required, but bot was not tagged in message
                    return
            # 2nd case: is  bot auto-responds to all messages that it thinks it can answer
            elif self.discord_auto_response_enabled:
                # if self.discord_auto_response_cooldown:
                #     return
                # To implement
                pass
            # 3rd case: bot restricted to responses in specific channels
            if self.discord_specific_channels_enabled:
                channel_id = self.message_specific_channels(message)
                if not channel_id:
                    # Message not in specified channels
                    return
            # 4th case: bot allowed in all channels, excluding some
            elif self.discord_all_channels_enabled:
                channel_id = self.message_excluded_channels(message)
                if not channel_id:
                    # Message in excluded channel
                    return
            # Implement auto responses in threads self.discord_auto_respond_in_threads

            request = message.content.replace(f"<@{self.bot.user.id}>", "").strip()  # type: ignore

            # If question is too short
            if len(request.split()) < 4:
                await message.channel.send(self.format_message(self.discord_short_message, message.author.id))
                return

            # Create thread
            thread = await message.create_thread(
                name=f"{self.get_random_animal()} {message.author.name}'s request",
                auto_archive_duration=60,
            )

            await thread.send(self.discord_message_start)

            request_response = await self.run_request(request)

            if isinstance(request_response, dict) and "answer_text" in request_response:
                # Parse for discord and then respond
                parsed_reponse = self.parse_discord_markdown(request_response)
                self.log.info(f"Parsed output: {json.dumps(parsed_reponse, indent=4)}")
                await thread.send(parsed_reponse)
                await thread.send(self.discord_message_end)
            else:
                # If not dict, then consider it an error
                await thread.send(f"Error: {request_response}")
                self.log.info(f"Error: {request_response})")

    def parse_discord_markdown(self, request_response) -> str:
        # Start with the answer text
        markdown_string = f"{request_response['answer_text']}\n\n"

        # Add the sources header if there are any documents
        if request_response["documents"]:
            markdown_string += "**Sources:**\n"

            # For each document, add a numbered list item with the title and URL
            for doc in request_response["documents"]:
                markdown_string += f"[{doc['doc_num']}] **{doc['title']}**: <{doc['url']}>\n"
        else:
            markdown_string += "No related documents found.\n"

        return markdown_string

    def get_random_animal(self) -> str:
        # Very important
        animals_txt_path = os.path.join(self.prompt_template_dir, "animals.txt")
        with open(animals_txt_path, "r") as file:
            animals = file.readlines()

        return random.choice(animals).strip().lower()

    def format_message(self, template, var=None) -> str:
        # Formats messages from premade templates
        if var:
            return template.format(var)

        return template.format()

    def message_specific_channels(self, message: discord.Message) -> Optional[int]:
        for config_channel_id in self.discord_specific_channel_ids:
            if message.channel.id == int(config_channel_id):
                return message.channel.id
        return None

    def message_excluded_channels(self, message: discord.Message) -> Optional[int]:
        for config_channel_id in self.discord_all_channels_excluded_channels:
            if message.channel.id == int(config_channel_id):
                return None
        return message.channel.id

    async def check_if_server_enabled(self, guild: discord.Guild) -> bool:
        if guild.id in self.discord_enabled_servers:
            return True
        self.log.info(f"Bot left {guild.id} because it was not in the list of approved servers.)")
        await guild.leave()
        return False

    def get_channel_for_welcome_message(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """On server join or on bot ready return a channel to greet in
        If specific channels enabled, find one that is named 'general' or just pick one at random
        """
        matching_channel = None
        if self.discord_specific_channels_enabled and self.discord_specific_channel_ids is not None:
            for channel in guild.channels:
                for config_channel_id in self.discord_specific_channel_ids:
                    if channel.id == int(config_channel_id):
                        if isinstance(channel, discord.TextChannel) and channel.name == "general":
                            return channel
                        matching_channel = channel
            if matching_channel:
                return matching_channel  # type: ignore

        # Otherwise try to return 'general', and return None if we can't.
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel) and channel.name == "general":
                return channel
        # In the future we can say hi in the last channel we spoke in
        return None

    async def run_request(self, request) -> Optional[Dict[str, str]]:
        # Required to run multiple requests at a time in async
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(executor, self.ceq_agent.create_chat, request)
            return response

    def run_sprite(self):
        try:
            self.bot.run(self.secrets["discord_bot_token"])
        except Warning as w:
            self.log.warning(w)
