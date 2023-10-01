from decimal import Decimal
from dataclasses import dataclass
from typing import List, Any
import openai
from services.service_base import ServiceBase
import modules.utils.config_manager as ConfigManager


class OpenAILLM(ServiceBase):
    @dataclass
    class OpenAILLMModel:
        model_name: str
        tokens_max: int
        cost_per_k: float

    provider_name: str = "openai_llm"
    ui_model_names: List[str] = [
        "gpt-4",
        "gpt-4-32k",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ]

    type_model: str = "openai_llm_model"
    available_models: List[OpenAILLMModel] = [
        OpenAILLMModel("gpt-4", 8192, 0.06),
        OpenAILLMModel("gpt-4-32k", 32768, 0.06),
        OpenAILLMModel("gpt-3.5-turbo", 4096, 0.03),
        OpenAILLMModel("gpt-3.5-turbo-16k", 16384, 0.03),
    ]
    required_secrets: List[str] = ["openai_api_key"]

    default_model: str = "gpt-3.5-turbo"
    openai_timeout_seconds: float = 180.0
    max_response_tokens: int = 300

    def __init__(self, parent_service):
        super().__init__(parent_service=parent_service)
        ConfigManager.setup_service_config(self)

    def _check_response(self, response, model):
        # Check if keys exist in dictionary
        parsed_response = (
            response.get("choices", [{}])[0].get("message", {}).get("content")
        )

        total_prompt_tokens = int(response.get("usage").get("prompt_tokens", 0))
        total_completion_tokens = int(response.get("usage").get("completion_tokens", 0))

        if not parsed_response:
            raise ValueError(f"Error in response: {response}")

        self._calculate_cost(
            token_count=(total_prompt_tokens + total_completion_tokens), model=model
        )

        return parsed_response

    def _calculate_cost(self, token_count, model):
        # Convert numbers to Decimal
        cost_per_k_decimal = Decimal(model.cost_per_k)
        token_count_decimal = Decimal(token_count)

        # Perform the calculation using Decimal objects
        request_cost = cost_per_k_decimal * (token_count_decimal / 1000)

        # If you still wish to round (even though Decimal is precise), you can do so
        request_cost = round(request_cost, 10)
        print(f"Request cost: ${format(request_cost, 'f')}")

        # Ensure total_cost_ is a Decimal as well; if it's not already, convert it
        if not isinstance(self.total_cost_, Decimal):
            self.total_cost_ = Decimal(self.total_cost_)
        self.total_cost_ += request_cost
        print(f"Total cost: ${format(self.total_cost_, 'f')}")

    def _create_chat(self, prompt, model_name=None):
        model = self.get_model(self.type_model, model_name=model_name)

        response = openai.ChatCompletion.create(
            api_key=self.app.secrets["openai_api_key"],
            model=model.model_name,
            messages=prompt,
            max_tokens=self.max_response_tokens,
        )
        prompt_response = self._check_response(response, model)
        if not prompt_response:
            return None

        return prompt_response

    def _create_streaming_chat(self, prompt, model_name=None):
        model = self.get_model(self.type_model, model_name=model_name)

        stream = openai.ChatCompletion.create(
            api_key=self.app.secrets["openai_api_key"],
            model=model.model_name,
            messages=prompt,
            max_tokens=self.max_response_tokens,
            stream=True,
        )

        # partial_message[-1][1] = ""
        partial_message = ""
        for chunk in stream:
            delta_content = (
                chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
            )
            if len(delta_content) != 0:
                partial_message += delta_content
                yield partial_message


class LLMService(ServiceBase):
    service_name: str = "llm_service"
    provider_type: str = "llm_provider"
    available_providers: List[str] = ["openai_llm"]
    ui_provider_names: List[Any] = [OpenAILLM.provider_name]

    default_provider: str = "openai_llm"
    max_response_tokens: int = 300

    def __init__(self, parent_agent):
        super().__init__(parent_agent=parent_agent)
        ConfigManager.setup_service_config(self)

        self.openai_llm = OpenAILLM(self)

    def create_chat(self, prompt, provider_name=None, model_name=None):
        provider = self.set_provider(self.provider_type, provider_name=provider_name)

        return provider._create_chat(prompt, model_name)

    def create_streaming_chat(self, prompt, provider_name=None, model_name=None):
        provider = self.set_provider(self.provider_type, provider_name=provider_name)

        yield from provider._create_streaming_chat(prompt, model_name)
