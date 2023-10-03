from dataclasses import dataclass
from decimal import Decimal
from typing import Any, List

import modules.text_processing.text as text
import modules.utils.config_manager as ConfigManager
from langchain.embeddings import OpenAIEmbeddings
from services.service_base import ServiceBase


class OpenAIEmbedding(ServiceBase):
    @dataclass
    class OpenAIEmbeddingModel:
        model_name: str
        tokens_max: int
        cost_per_k: float

    provider_name: str = "openai_embedding"
    type_model: str = "openai_embedding_model"
    available_models: List[OpenAIEmbeddingModel] = [
        OpenAIEmbeddingModel("text-embedding-ada-002", 8192, 0.0001)
    ]
    required_secrets: List[str] = ["openai_api_key"]

    default_model: str = "text-embedding-ada-002"
    openai_timeout_seconds: float = 180.0

    def __init__(self, parent_service):
        super().__init__(parent_service=parent_service)

    def _get_query_embedding(self, query, model_name=None):
        model = self.get_model(self.type_model, model_name=model_name)

        embedding_retriever = OpenAIEmbeddings(
            # Note that this is openai_api_key and not api_key
            openai_api_key=self.app.secrets["openai_api_key"],
            model=model.model_name,
            request_timeout=self.openai_timeout_seconds,
        )
        query_embedding = embedding_retriever.embed_query(query)
        self._calculate_cost(query, model)
        self.log.print_and_log("Embeddings retrieved")
        return query_embedding

    def _calculate_cost(self, query, model):
        token_count = text.tiktoken_len(query, model.model_name)

        # Convert numbers to Decimal
        cost_per_k_decimal = Decimal(model.cost_per_k)
        token_count_decimal = Decimal(token_count)

        # Perform the calculation using Decimal objects
        request_cost = cost_per_k_decimal * (token_count_decimal / 1000)

        # If you still wish to round (even though Decimal is precise), you can do so
        request_cost = round(request_cost, 10)
        print(f"Request cost: ${format(request_cost, 'f')}")
        # Ensure total_cost_ is a Decimal as well; if it's not already, convert it
        if not isinstance(self.app.total_cost, Decimal):
            self.app.total_cost = Decimal(self.app.total_cost)

        self.app.total_cost += request_cost
        print(f"Total cost: ${format(self.app.total_cost, 'f')}")


class EmbeddingService(ServiceBase):
    service_name: str = "embedding_service"
    provider_type: str = "embedding_provider"
    available_providers: List[Any] = [OpenAIEmbedding]
    default_provider: Any = OpenAIEmbedding

    def __init__(self, parent_agent=None):
        super().__init__(parent_agent=parent_agent)

        self.openai_embedding = OpenAIEmbedding(self)

    def get_query_embedding(self, query, provider_name=None, model_name=None):
        provider = self.get_provider(new_provider_name=provider_name)
        if provider:
            return provider._get_query_embedding(query, model_name=model_name)
        return None
