from typing import Dict, Optional, List, Any
from pydantic import BaseModel


class ServiceBase:
    config: Dict[str, str] = {}

    provider_type: Optional[str] = None
    default_provider: Optional[str] = None
    available_providers: Optional[List[Any]] = None
    current_provider: Optional[Any] = None

    def __init__(self, parent_agent=None, parent_service=None):
        if parent_agent:
            self.app = parent_agent.app
            self.parent_sprite = parent_agent.parent_sprite
            self.parent_agent = parent_agent
        if parent_service:
            self.parent_sprite = parent_service.parent_agent.parent_sprite
            self.parent_agent = parent_service.parent_agent
            self.app = self.parent_agent.app
            self.parent_service = parent_service
        self.index = self.app.index
        self.log = self.app.log

    def set_provider(self, new_provider_name=None):
        """Returns an instance of a provider
        First tries the requested provider,
        Then tries the parent_agent's,
        Then uses default"""

        def _find_provider(provider_name):
            if not self.available_providers:
                return None

            for provider in self.available_providers:
                if provider.provider_name == provider_name:
                    # Reuse current provider if name matches.
                    if provider.provider_name == getattr(
                        self.current_provider, "provider_name", None
                    ):
                        return self.current_provider
                    else:
                        self.current_provider = provider(self)
                        return self.current_provider

        provider_names_to_check = [
            new_provider_name,  # Tries the requested provider
            getattr(self.parent_agent, self.provider_type, None)
            if self.provider_type
            else None,  # Then the parent's agent
            getattr(self.default_provider, "provider_name", None)
            if self.default_provider
            else None,  # Then the default
        ]

        for provider_name in provider_names_to_check:
            if provider_name:
                provider_instance = _find_provider(provider_name)
                if provider_instance:
                    return provider_instance

        return None

    def get_model(self, type_model, model_name=None):
        """Returns an instance of a model
        First tries the requested model,
        Then tries the parent_agent's,
        Then uses default"""
        # Tries the requested model
        available_models = getattr(self, "available_models", [])
        if model_name:
            model_instance = next(
                (model for model in available_models if model.model_name == model_name),
                None,
            )
            if model_instance:
                return model_instance
        # Then the parent's agent
        if model := getattr(self.parent_agent, type_model, None):
            if model_instance := getattr(self, model, None):
                return model_instance
        # Then the default

        return next(
            (
                model
                for model in available_models
                if model.model_name == self.default_model
            ),
            None,
        )
