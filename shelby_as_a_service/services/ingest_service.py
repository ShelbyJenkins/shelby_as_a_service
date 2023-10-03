import json
import os
import traceback
from typing import Any, Iterator, List

import modules.text_processing.text as TextProcess
import modules.utils.config_manager as ConfigManager
import pinecone
import yaml
from bs4 import BeautifulSoup
from langchain.document_loaders import (
    GitbookLoader,
    RecursiveUrlLoader,
    SitemapLoader,
    WebBaseLoader,
)
from langchain.schema import Document
from services.service_base import ServiceBase


class GenericRecursiveWebScraper(ServiceBase):
    provider_name: str = "generic_recursive_web_scraper"

    def __init__(self, parent_service):
        super().__init__(parent_service=parent_service)

    @staticmethod
    def custom_extractor(html_text: str) -> str:
        soup = BeautifulSoup(html_text, "html.parser")
        text_element = soup.find(id="content")
        if text_element:
            return text_element.get_text()
        return ""

    def _load(self, url) -> Iterator[Document]:
        documents = RecursiveUrlLoader(url=url, extractor=self.custom_extractor).load()

        return (
            Document(page_content=doc.page_content, metadata=doc.metadata)
            for doc in documents
        )


class GenericWebScraper(ServiceBase):
    provider_name: str = "generic_web_scraper"

    def __init__(self, parent_service):
        super().__init__(parent_service=parent_service)

    def _load(self, url) -> Iterator[Document]:
        documents = WebBaseLoader(web_path=url).load()
        for document in documents:
            document.page_content = TextProcess.clean_text_content(
                document.page_content
            )

        return (
            Document(page_content=doc.page_content, metadata=doc.metadata)
            for doc in documents
        )


# class OpenAPILoader(ServiceBase):
#     def __init__(self, data_source_config: DataSourceConfig):
#         self.index_agent = data_source_config.index_agent
#         self.config = data_source_config
#         self.data_source_config = data_source_config

#     def load(self):
#         open_api_specs = self.load_spec()

#         return open_api_specs

#     def load_spec(self):
#         """Load YAML or JSON files."""
#         open_api_specs = []
#         file_extension = None
#         for filename in os.listdir(self.data_source_config.target_url):
#             if file_extension is None:
#                 if filename.endswith(".yaml"):
#                     file_extension = ".yaml"
#                 elif filename.endswith(".json"):
#                     file_extension = ".json"
#                 else:
#                     # self.data_source_config.index_agent.log_agent.print_and_log(f"Unsupported file format: {filename}")
#                     continue
#             elif not filename.endswith(file_extension):
#                 # self.data_source_config.index_agent.log_agent.print_and_log(f"Inconsistent file formats in directory: {filename}")
#                 continue
#             file_path = os.path.join(self.data_source_config.target_url, filename)
#             with open(file_path, "r") as file:
#                 if file_extension == ".yaml":
#                     open_api_specs.append(yaml.safe_load(file))
#                 elif file_extension == ".json":
#                     open_api_specs.append(json.load(file))

#         return open_api_specs


# class LoadTextFromFile(ServiceBase):
#     def __init__(self, data_source_config):
#         self.config = data_source_config
#         self.data_source_config = data_source_config

#     def load(self):
#         text_documents = self.load_texts()
#         return text_documents

#     # def load_texts(self):
#     #     """Load text files and structure them in the desired format."""
#     #     text_documents = []
#     #     file_extension = ".txt"
#     #     for filename in os.listdir(self.data_source_config.target_url):
#     #         if not filename.endswith(file_extension):
#     #             # Uncomment the line below if you wish to log unsupported file formats
#     #             # self.data_source_config.index_agent.log_agent.print_and_log(f"Unsupported file format: {filename}")
#     #             continue

#     #         file_path = os.path.join(self.data_source_config.target_url, filename)
#     #         title = os.path.splitext(filename)[0]
#     #         with open(file_path, "r", encoding="utf-8") as file:
#     #             document_metadata = {
#     #                 "loc": file_path,
#     #                 "source": file_path,
#     #                 "title": title
#     #             }
#     #             document = Document(page_content=file.read(), metadata=document_metadata)
#     #             text_documents.append(document)

#     #     return text_documents

#     def load_texts(self):
#         """Load text and JSON files and structure them in the desired format."""
#         text_documents = []
#         allowed_extensions = [".txt", ".json"]

#         for filename in os.listdir(self.data_source_config.target_url):
#             file_extension = os.path.splitext(filename)[1]

#             if file_extension not in allowed_extensions:
#                 # Uncomment the line below if you wish to log unsupported file formats
#                 # self.data_source_config.index_agent.log_agent.print_and_log(f"Unsupported file format: {filename}")
#                 continue

#             file_path = os.path.join(self.data_source_config.target_url, filename)
#             title = os.path.splitext(filename)[0]

#             with open(file_path, "r", encoding="utf-8") as file:
#                 if file_extension == ".txt":
#                     content = file.read()
#                     # You might want to adapt the following based on how you wish to represent JSON content
#                     document_metadata = {
#                         "loc": file_path,
#                         "source": file_path,
#                         "title": title,
#                     }
#                     document = Document(
#                         page_content=content, metadata=document_metadata
#                     )
#                 elif file_extension == ".json":
#                     content = json.load(file)  # Now content is a dictionary

#                     # You might want to adapt the following based on how you wish to represent JSON content
#                     document_metadata = {
#                         "loc": file_path,
#                         "source": file_path,
#                         "title": title,
#                     }
#                     document = Document(
#                         page_content=content["content"], metadata=document_metadata
#                     )
#                 text_documents.append(document)

#         return text_documents


class IngestService(ServiceBase):
    service_name: str = "ingest_service"

    provider_type: str = "ingest_provider"
    default_provider: Any = GenericWebScraper
    available_providers: List[Any] = [
        GenericWebScraper,
        GenericRecursiveWebScraper,
        # OpenAPILoader,
        # LoadTextFromFile,
    ]

    def __init__(self, parent_agent=None):
        super().__init__(parent_agent=parent_agent)

        self.current_provider = self.get_provider()

    def load(self, data_source):
        provider = self.get_provider(data_source.data_source_ingest_provider)
        if provider:
            return provider._load(data_source.data_source_url)
        else:
            print("rnr")
