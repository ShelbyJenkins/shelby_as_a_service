from typing import Literal

# from interfaces.bots.discord_sprite import DiscordSprite
# from interfaces.bots.slack_sprite import SlackSprite
from interfaces.webui_sprite import WebUISprite

AVAILABLE_SPRITE_NAMES = Literal[
    # DiscordSprite.class_name,
    # SlackSprite.class_name,
    WebUISprite.class_name,
]
AVAILABLE_SPRITE_UI_NAMES = [
    # DiscordSprite.CLASS_UI_NAME,
    # SlackSprite.CLASS_UI_NAME,
    WebUISprite.CLASS_UI_NAME,
]
AVAILABLE_SPRITES = [
    # DiscordSprite,
    # SlackSprite,
    WebUISprite,
]
