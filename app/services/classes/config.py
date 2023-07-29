
from dataclasses import dataclass
from .base import BaseClass

@dataclass
class DiscordConfig(BaseClass):
    ### These will all be set by file ###
    discord_manual_requests_enabled: bool = True 
    discord_auto_response_enabled: bool = False
    discord_auto_response_cooldown: int = 10
    discord_auto_respond_in_threads: bool = False 
    discord_all_channels_enabled: bool = False
    discord_specific_channels_enabled: bool = True 
    discord_user_daily_token_limit: int = 30000
    discord_welcome_message: str = 'ima tell you about the {}.'
    discord_short_message: str = '<@{}>, brevity is the soul of wit, but not of good queries. Please provide more details in your request.'
    discord_message_start: str = 'Running request... relax, chill, and vibe a minute.'
    discord_message_end: str = 'Generated by: gpt-4. Memory not enabled. Has no knowledge of past or current queries. For code see https://github.com/ShelbyJenkins/shelby-as-a-service.'
   
    # Adds as 'required' to deployment.env and workflow
    DEPLOYMENT_REQUIRED_VARIABLES_ = [
        "discord_bot_token"
    ]
    MONIKER_REQUIRED_VARIABLES_ = [
        "discord_enabled_servers",
        "discord_specific_channel_ids",
        "discord_all_channels_excluded_channels"
    ]
    SPRITE_REQS_ = [
        "ShelbyConfig"
    ]

    def check_parse_config(self):
        # Special rules for discord config
        
        if self.discord_manual_requests_enabled is False and self.discord_auto_response_enabled is False:
            raise ValueError(
                "Error: manual_requests_enabled and auto_response_enabled cannot both be False."
            )
        if (self.discord_all_channels_enabled or self.discord_specific_channels_enabled is not None) and \
            self.discord_all_channels_enabled == self.discord_specific_channels_enabled:
            raise ValueError(
                "Error: all_channels_enabled and specific_channels_enabled cannot have the same boolean state."
            )
            
        required_vars = []
        for var in vars(self):
            if not var.startswith("_") and not var.endswith("_") and not callable(getattr(self, var)):
                if (var == "discord_all_channels_excluded_channels" and self.discord_all_channels_enabled == False):
                    continue
                if (var == "discord_specific_channel_ids" and self.discord_specific_channels_enabled == False):
                    continue
                required_vars.append(var)
            
        BaseClass.check_required_vars_list(self, required_vars)

@dataclass
class ShelbyConfig(BaseClass):
    ### These will all be set by file ###
    action_llm_model: str = "gpt-4"
    # QueryAgent
    pre_query_llm_model: str = "gpt-4"
    max_doc_token_length: int = 1200
    embedding_model: str = "text-embedding-ada-002"
    tiktoken_encoding_model: str = "text-embedding-ada-002"
    # pre_query_llm_model: str = 'gpt-3.5-turbo'
    query_llm_model: str = "gpt-4"
    vectorstore_top_k: int = 5
    max_docs_tokens: int = 3500
    max_docs_used: int = 5
    max_response_tokens: int = 300
    openai_timeout_seconds: float = 180.0
    # APIAgent
    select_operationID_llm_model: str = "gpt-4"
    create_function_llm_model: str = "gpt-4"
    populate_function_llm_model: str = "gpt-4"
    
    # Adds as 'required' to deployment.env and workflow
    DEPLOYMENT_REQUIRED_VARIABLES_ = [
        "index_env",
        "index_name",
        "openai_api_key",
        "pinecone_api_key"
    ]
    MONIKER_REQUIRED_VARIABLES_ = [
    ]
 
    def check_parse_config(self):

        BaseClass.check_class_required_vars(self)

@dataclass
class AllSpritesAndServices(BaseClass):
    all_sprites: list = [
        DiscordConfig
        ]
    all_services: list = [
        ShelbyConfig
        ]