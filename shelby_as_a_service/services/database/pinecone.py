import os
import typing
from typing import Any, Literal, Optional

import gradio as gr
import pinecone
from pydantic import BaseModel
from services.database.database_base import DatabaseBase


class PineconeDatabase(DatabaseBase):
    class_name = Literal["pinecone_database"]
    CLASS_NAME: str = typing.get_args(class_name)[0]
    CLASS_UI_NAME: str = "Pinecone Database"
    REQUIRED_SECRETS: list[str] = ["pinecone_api_key"]
    DOC_DB_REQUIRES_EMBEDDINGS: bool = True

    class ClassConfigModel(BaseModel):
        index_env: str = "us-central1-gcp"
        index_name: str = "shelby-as-a-service"
        vectorstore_dimension: int = 1536
        upsert_batch_size: int = 20
        vectorstore_metric: str = "cosine"
        vectorstore_pod_type: str = "p1"
        enabled_doc_embedder_name: str = "openai_embedding"
        enabled_doc_embedder_config: dict[str, Any] = {}
        retrieve_n_docs: int = 5
        indexed_metadata: list = [
            "domain_name",
            "source_name",
            "source_type",
            "date_of_creation",
        ]

    config: ClassConfigModel
    existing_entry_count: int
    domain_name: str
    source_name: Optional[str] = None

    def __init__(
        self,
        config_file_dict: dict[str, Any] = {},
        **kwargs,
    ):
        super().__init__(config_file_dict=config_file_dict, **kwargs)

        if (api_key := self.secrets.get("pinecone_api_key")) is None:
            raise ValueError("Pinecone API Key not found.")
        pinecone.init(
            api_key=api_key,
            environment=self.config.index_env,
        )
        self.pinecone = pinecone
        indexes = pinecone.list_indexes()
        if self.config.index_name not in indexes:
            # create new index
            self.create_index()
            indexes = pinecone.list_indexes()
            self.log.info(f"Created index: {indexes}")
        self.pinecone_index = pinecone.Index(self.config.index_name)

    def get_index_domain_or_source_entry_count(
        self, source_name: Optional[str] = None, domain_name: Optional[str] = None
    ) -> int:
        self.log.info(f"Complete index stats: {self.pinecone_index.describe_index_stats()}\n")
        if source_name:
            index_resource_stats = self.pinecone_index.describe_index_stats(
                filter={"source_name": {"$eq": source_name}}
            )
        elif domain_name:
            index_resource_stats = self.pinecone_index.describe_index_stats(
                filter={"domain_name": {"$eq": domain_name}}
            )
        else:
            raise ValueError("Must provide either source_name or domain_name")
        return (
            index_resource_stats.get("namespaces", {}).get(domain_name, {}).get("vector_count", 0)
        )

    def clear_existing_source(self, source_name: str, domain_name: str) -> Any:
        return self.pinecone_index.delete(
            namespace=domain_name,
            delete_all=False,
            filter={"source_name": {"$eq": source_name}},
        )

    def clear_existing_entries_by_id(self, ids: list[str], domain_name: str) -> Any:
        return self.pinecone_index.delete(
            namespace=domain_name,
            delete_all=False,
            ids=ids,
        )

    def prepare_upsert_for_vectorstore(
        self,
        id: str,
        values: Optional[list[float]],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        if not values:
            raise ValueError(f"Must provide values for {self.CLASS_NAME}")
        return {
            "id": id,
            "values": values,
            "metadata": metadata,
        }

    def upsert(
        self,
        entries_to_upsert: list[dict[str, Any]],
        domain_name: str,
    ) -> Any:
        return self.pinecone_index.upsert(
            vectors=entries_to_upsert,
            namespace=domain_name,
            batch_size=self.config.upsert_batch_size,
            show_progress=True,
        )

    def query_by_terms(
        self,
        search_terms,
        domain_name,
    ) -> list[dict]:
        def _query_namespace(search_terms, top_k, namespace, filter=None):
            response = self.pinecone_index.query(
                top_k=self.config.retrieve_n_docs,
                include_values=False,
                namespace=namespace,
                include_metadata=True,
                filter=filter,  # type: ignore
                vector=search_terms,
            )

            returned_documents = []

            for m in response.matches:
                response = {
                    "content": m.metadata["content"],
                    "title": m.metadata["title"],
                    "url": m.metadata["url"],
                    "doc_type": m.metadata["doc_type"],
                    "score": m.score,
                    "id": m.id,
                }
                returned_documents.append(response)

            return returned_documents

        filter = None  # Need to implement

        if domain_name:
            namespace = domain_name
            returned_documents = _query_namespace(search_terms, top_k, namespace, filter)
        # If we don't have a namespace, just search all available namespaces
        else:
            pass
            # returned_documents = []
            # for data_domain in self.index.index_data_domains:
            #     if namespace := getattr(data_domain, "domain_name", None):
            #         returned_documents.extend(
            #             _query_namespace(search_terms, top_k, namespace, filter)
            #         )

        return returned_documents

        #     soft_filter = {
        #         "doc_type": {"$eq": "soft"},
        #         "domain_name": {"$in": domain_names},
        #     }

        #     hard_filter = {
        #         "doc_type": {"$eq": "hard"},
        #         "domain_name": {"$in": domain_names},
        #     }

        # else:
        #     soft_filter = {
        #         "doc_type": {"$eq": "soft"},
        #         "domain_name": {"$eq": domain_name},
        #     }
        #     hard_filter = {
        #         "doc_type": {"$eq": "hard"},
        #         "domain_name": {"$eq": domain_name},
        #     }
        # hard_query_response = self.pinecone_index.query(
        #     top_k=retrieve_n_docs,
        #     include_values=False,
        #     namespace=AppBase.config.app_name,
        #     include_metadata=True,
        #     filter=hard_filter,
        #     vector=dense_embedding

        # )

        # Destructures the QueryResponse object the pinecone library generates.
        # for m in hard_query_response.matches:
        #     response = {
        #         "content": m.metadata["content"],
        #         "title": m.metadata["title"],
        #         "url": m.metadata["url"],
        #         "doc_type": m.metadata["doc_type"],
        #         "score": m.score,
        #         "id": m.id,
        #     }
        #     returned_documents.append(response)

    def fetch_by_ids(
        self,
        ids: list[int],
    ):
        namespace = kwargs.get("namespace", None)
        fetch_response = self.pinecone_index.fetch(
            namespace=namespace,
            ids=ids,
        )
        return fetch_response

    def delete_index(self):
        print(f"Deleting index {self.index_name}")
        stats = self.pinecone_index.describe_index_stats()
        print(stats)
        pinecone.delete_index(self.index_name)
        print(self.pinecone_index.describe_index_stats())

    def clear_index(self):
        print("Deleting all vectors in index.")
        stats = self.pinecone_index.describe_index_stats()
        print(stats)
        for key in stats["namespaces"]:
            self.pinecone_index.delete(deleteAll="true", namespace=key)
        print(self.pinecone_index.describe_index_stats())

    def clear_namespace(self):
        print(f"Clearing namespace aka deployment: {self.app_name}")
        self.pinecone_index.delete(deleteAll="true", namespace=self.app_name)
        print(self.pinecone_index.describe_index_stats())

    def create_index(self):
        metadata_config = {"indexed": self.config.index_indexed_metadata}
        # Prepare log message
        log_message = (
            f"Creating new index with the following configuration:\n"
            f" - Index Name: {self.index_name}\n"
            f" - Dimension: {self.config.index_vectorstore_dimension}\n"
            f" - Metric: {self.config.index_vectorstore_metric}\n"
            f" - Pod Type: {self.config.index_vectorstore_pod_type}\n"
            f" - Metadata Config: {metadata_config}"
        )
        # Log the message
        print(log_message)

        pinecone.create_index(
            name=self.index_name,
            dimension=self.config.index_vectorstore_dimension,
            metric=self.config.index_vectorstore_metric,
            pod_type=self.config.index_vectorstore_pod_type,
            metadata_config=metadata_config,
        )

    def create_provider_management_settings_ui(self):
        ui_components = {}

        ui_components["index_env"] = gr.Textbox(
            value=self.config.index_env, label="index_env", interactive=True, min_width=0
        )
        ui_components["vectorstore_dimension"] = gr.Number(
            value=self.config.vectorstore_dimension,
            label="vectorstore_dimension",
            interactive=True,
            min_width=0,
        )
        ui_components["vectorstore_metric"] = gr.Textbox(
            value=self.config.vectorstore_metric,
            label="vectorstore_metric",
            interactive=True,
            min_width=0,
        )
        ui_components["vectorstore_pod_type"] = gr.Textbox(
            value=self.config.vectorstore_pod_type,
            label="vectorstore_pod_type",
            interactive=True,
            min_width=0,
        )
        ui_components["indexed_metadata"] = gr.Dropdown(
            value=self.config.indexed_metadata[0],
            choices=self.config.indexed_metadata,
            label="indexed_metadata",
            interactive=True,
            min_width=0,
            multiselect=True,
            allow_custom_value=True,
        )
        ui_components["upsert_batch_size"] = gr.Number(
            value=self.config.upsert_batch_size,
            label="upsert_batch_size",
            interactive=True,
            min_width=0,
        )

        return ui_components

    @classmethod
    def create_provider_ui_components(cls, config_model: ClassConfigModel, visibility: bool = True):
        ui_components = {}

        return ui_components
