from dataclasses import dataclass, field
from typing import List, Optional

class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class DeploymentModel(metaclass=SingletonMeta):
    deployment_name: str = None
    # Variables here are for populating workflow
    
    DEPLOYMENT_REQUIREMENTS_ = [
        "docker_registry",
        "docker_username",
        "docker_repo"
    ]
    
    SECRETS_ = [
        "docker_token",
        "stackpath_stack_slug",
        "stackpath_client_id",
        "stackpath_api_client_secret"
    ]
    
@dataclass
class MonikerModel:
    moniker_name: str = field(default=None)
    moniker_enabled: bool = field(default=None)
    moniker_enabled_sprite_names: list = field(default_factory=list)
    moniker_enabled_data_domains: dict = field(default_factory=dict)
    
@dataclass
class ShelbyModel:
    
    index_name: str = None
    index_env: str = None
    action_llm_model: str = "gpt-4"
    # QueryAgent
    ceq_data_domain_constraints_enabled: bool = False
    ceq_data_domain_constraints_llm_model: str = "gpt-4"
    ceq_data_domain_none_found_message: str = "Query not related to any supported data domains (aka topics). Supported data domains are:"
    ceq_keyword_generator_enabled: bool = False
    ceq_keyword_generator_llm_model: str = "gpt-4"
    ceq_doc_relevancy_check_enabled: bool = False
    ceq_doc_relevancy_check_llm_model: str = "gpt-4"
    ceq_embedding_model: str = "text-embedding-ada-002"
    ceq_tiktoken_encoding_model: str = "text-embedding-ada-002"
    ceq_docs_to_retrieve: int = 5
    ceq_docs_max_token_length: int = 1200
    ceq_docs_max_total_tokens: int = 3500
    ceq_docs_max_used: int = 5
    ceq_main_prompt_llm_model: str = "gpt-4"
    ceq_max_response_tokens: int = 300
    openai_timeout_seconds: float = 180.0
    # APIAgent
    api_agent_select_operationID_llm_model: str = "gpt-4"
    api_agent_create_function_llm_model: str = "gpt-4"
    api_agent_populate_function_llm_model: str = "gpt-4"
    
    # Adds as 'required' to deployment.env and workflow


@dataclass
class DiscordModel:
    sprite_name = 'discord'
    enabled: bool = None
    required_services = [ShelbyModel]
    discord_enabled_servers = [] 
    discord_specific_channels_enabled: bool = False 
    discord_specific_channel_ids = [] 
    discord_all_channels_enabled: bool = False
    discord_all_channels_excluded_channels = []
    discord_manual_requests_enabled: bool = True
    discord_auto_response_enabled: bool = False
    discord_auto_response_cooldown: int = 10
    discord_auto_respond_in_threads: bool = False
    discord_user_daily_token_limit: int = 30000
    discord_welcome_message: str = 'ima tell you about the {}.'
    discord_short_message: str = '<@{}>, brevity is the soul of wit, but not of good queries. Please provide more details in your request.'
    discord_message_start: str = 'Running request... relax, chill, and vibe a minute.'
    discord_message_end: str = 'Generated by: gpt-4. Memory not enabled. Has no knowledge of past or current queries. For code see https://github.com/ShelbyJenkins/shelby-as-a-service.'
    
    # Adds as 'required' to deployment.env and workflow
    SECRETS_ = [
        "discord_bot_token",
        "openai_api_key",
        "pinecone_api_key"
    ]

    # def check_model(self, sprite_config):
    #     # Special rules for discord Model
        
    #     if sprite_config.discord_manual_requests_enabled is False and sprite_config.discord_auto_response_enabled is False:
    #         raise ValueError(
    #             "Error: manual_requests_enabled and auto_response_enabled cannot both be False."
    #         )
    #     if (sprite_config.discord_all_channels_enabled or sprite_config.discord_specific_channels_enabled is not None) and \
    #         sprite_config.discord_all_channels_enabled == sprite_config.discord_specific_channels_enabled:
    #         raise ValueError(
    #             "Error: all_channels_enabled and specific_channels_enabled cannot have the same boolean state."
    #         )
            
    #     required_vars = []
    #     for var in vars(self):
    #         if not var.startswith("_") and not var.endswith("_") and not callable(getattr(self, var)):
    #             if (var == "discord_all_channels_excluded_channels" and sprite_config.discord_all_channels_enabled == False):
    #                 continue
    #             if (var == "discord_specific_channel_ids" and sprite_config.discord_specific_channels_enabled == False):
    #                 continue
    #             required_vars.append(var)

@dataclass
class SlackModel:
    sprite_name = 'slack'
    enabled: bool = None
    required_services = [ShelbyModel]
    slack_enabled_teams = []
    slack_welcome_message: str = 'ima tell you about the {}.'
    slack_short_message: str = '<@{}>, brevity is the soul of wit, but not of good queries. Please provide more details in your request.'
    slack_message_start: str = 'Relax and vibe while your query is embedded, documents are fetched, and the LLM is prompted.'
    slack_message_end: str = 'Generated by: gpt-4. Memory not enabled. Has no knowledge of past or current queries. For code see https://github.com/ShelbyJenkins/shelby-as-a-service.'
    # Adds as 'required' to deployment.env and workflow
    SECRETS_ = [
        "slack_app_token",
        "slack_bot_token",
        "openai_api_key",
        "pinecone_api_key"
    ]


    # def check_parse_model(self):
    #     # Special rules for discord Model
        
    #     if sprite_config.discord_manual_requests_enabled is False and self.discord_auto_response_enabled is False:
    #         raise ValueError(
    #             "Error: manual_requests_enabled and auto_response_enabled cannot both be False."
    #         )
    #     if (self.discord_all_channels_enabled or self.discord_specific_channels_enabled is not None) and \
    #         self.discord_all_channels_enabled == self.discord_specific_channels_enabled:
    #         raise ValueError(
    #             "Error: all_channels_enabled and specific_channels_enabled cannot have the same boolean state."
    #         )
            
    #     required_vars = []
    #     for var in vars(self):
    #         if not var.startswith("_") and not var.endswith("_") and not callable(getattr(self, var)):
    #             if (var == "discord_all_channels_excluded_channels" and self.discord_all_channels_enabled == False):
    #                 continue
    #             if (var == "discord_specific_channel_ids" and self.discord_specific_channels_enabled == False):
    #                 continue
    #             required_vars.append(var)
            
    #     ModelSharedTools.check_required_vars_list(self, required_vars)

class IndexModel:
    index_env: str = None
    index_name: str = None
    index_embedding_model: str = "text-embedding-ada-002"
    index_tiktoken_encoding_model: str = "text-embedding-ada-002"
    index_embedding_max_chunk_size: int = 8191
    index_embedding_batch_size: int = 100
    index_vectorstore_dimension: int = 1536
    index_vectorstore_upsert_batch_size: int = 20
    index_vectorstore_metric: str = "dotproduct"
    index_vectorstore_pod_type: str = "p1"
    index_preprocessor_min_length: int = 150
    index_text_splitter_goal_length: int = 1500
    index_text_splitter_max_length: int = 2000
    index_text_splitter_chunk_overlap: int = 300
    index_openai_timeout_seconds: float = 180.0
    index_indexed_metadata: List[str] = field(default_factory=lambda: ["data_domain_name", "data_source_name", "doc_type", "target_type"]) 

    SECRETS_ = [
        "openai_api_key",
        "pinecone_api_key"
    ]
