import typing
from abc import ABC, abstractmethod
from typing import Any, Final, Iterator, Literal, Optional, Type, Union

from pydantic import BaseModel
from services.service_base import ServiceBase


class ClassConfigModel(BaseModel):
    provider_model_name: str
    available_models: dict[str, Any]

    class Config:
        extra = "ignore"


class ModelConfig(BaseModel):
    MODEL_NAME: str
    TOKENS_MAX: int
    COST_PER_K: float

    class Config:
        extra = "ignore"


class EmbeddingBase(ABC, ServiceBase):
    ModelConfig: Type[BaseModel]
    config: BaseModel
    MODEL_DEFINITIONS: dict[str, Any]
    DOC_INDEX_KEY: str = "enabled_doc_embedder"
    embedding_provider: "EmbeddingBase"
    embedding_model_instance: "ModelConfig"

    def get_embedding_of_text_with_provider(self, text: str) -> list[float]:
        raise NotImplementedError

    def get_embeddings_from_list_of_texts_with_provider(
        self, texts: list[str]
    ) -> list[list[float]]:
        raise NotImplementedError
