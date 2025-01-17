import re
import typing
from typing import Annotated, Any, Generator, Literal, Optional, Type, Union, get_args

import gradio as gr
import services.llm as llm
from agents.agent_base import AgentBase
from context_index.doc_index.docs.context_docs import RetrievalDoc
from context_index.doc_index.docs.doc_retrieval import DocRetrieval
from pydantic import BaseModel, Field
from services.gradio_interface.gradio_base import GradioBase
from services.llm.llm_service import LLMService


class ClassConfigModel(BaseModel):
    """
    The configuration settings for the CEQ agent module.

    Attributes:
        enabled_domains (list[str]): A list of enabled data domains.
        context_to_response_ratio (float): The ratio of context tokens to response tokens to use for generating the response.
    """

    llm_provider_name: str = "openai_llm"
    enabled_domains: list[str] = ["all"]
    context_to_response_ratio: Annotated[float, Field(ge=0, le=1.0)] = 0.5

    class Config:
        extra = "ignore"


class CEQAgent(AgentBase):
    """
    CEQ (Context enhanced querying) is a subset of RAG (Retrieval Augmented Generation).
    CEQAgent generates responses to user queries using by
    1) Calculating the amount of tokens available for context documents for a given query and llm model
    2) Retrieving context documents using the DocRetrieval
    3) Appending the documents to a users query (Prompt Stuffing) for additional context

    Methods:
        run_chat(self, chat_in, llm_provider=None, llm_model=None, token_utilization=None,
                 context_to_response_ratio=None, stream=None, sprite_name="webui_sprite"): Generates a response to user input.
    """

    class_name = Literal["ceq_agent"]
    CLASS_NAME: str = get_args(class_name)[0]
    CLASS_UI_NAME: str = "CEQ"
    DEFAULT_CEQ_PROMPT_TEMPLATE_PATH: str = "agents/ceq/ceq_prompt_templates.yaml"
    DEFAULT_VANILLA_PROMPT_TEMPLATE_PATH: str = "agents/ceq/vanillallm_prompt_templates.yaml"
    DATA_DOMAIN_NONE_FOUND_MESSAGE: str = (
        "Query not related to any supported data domains (aka topics). Supported data domains are:"
    )
    REQUIRED_CLASSES: list[Type] = [DocRetrieval, LLMService]

    class_config_model = ClassConfigModel
    config: ClassConfigModel
    llm_service: LLMService
    doc_retrieval: DocRetrieval

    def __init__(self, config_file_dict: dict[str, Any] = {}, **kwargs):
        super().__init__(
            config_file_dict=config_file_dict,
            **kwargs,
        )

    def create_vanilla_chat(
        self,
        chat_in: str,
        token_utilization: Optional[float] = None,
        stream: Optional[bool] = None,
    ):
        prompt = self.create_prompt(
            user_input=chat_in,
            llm_provider_name=self.llm_service.llm_provider.CLASS_NAME,  # type: ignore
            prompt_template_path=self.DEFAULT_VANILLA_PROMPT_TEMPLATE_PATH,
        )

        for response in self.llm_service.create_chat(
            prompt=prompt,
            token_utilization=token_utilization,
            stream=stream,
        ):
            yield response["response_content_string"]

    def create_ceq_chat(
        self,
        chat_in,
        token_utilization: Optional[float] = None,
        context_to_response_ratio: Optional[float] = None,
        enabled_domains: Optional[list[str] | str] = None,
        stream: Optional[bool] = None,
        sprite_name: Optional[str] = "webui_sprite",
    ) -> Union[Generator[str, None, None], dict[str, str]]:
        """
        Generates a response to user input.
        The default values are for the webui, but can be overridden for other interfaces.

        Args:
            chat_in (str): The user input to generate a response for.
            llm_provider (Optional[str]): The LLM provider to use for generating the response.
            llm_model_name (Optional[str]): The LLM model to use for generating the response.
            token_utilization (Optional[float]): The percentage of available tokens to use for generating the response.
            context_to_response_ratio (Optional[float]): The ratio of context tokens to response tokens to use for generating the response.
            stream (Optional[bool]): Whether to stream the response or not.
            sprite_name (Optional[str]): The name of the sprite to use for displaying the response.

        Yields:
            str: The generated response to the user input.
        """
        if context_to_response_ratio is None:
            context_to_response_ratio = self.config.context_to_response_ratio
        if enabled_domains is None:
            enabled_domains = self.config.enabled_domains
        if token_utilization is None:
            token_utilization = self.llm_service.config.token_utilization
        prompt = self.create_prompt(
            user_input=chat_in,
            llm_provider_name=self.llm_service.llm_provider.CLASS_NAME,  # type: ignore
            prompt_template_path=self.DEFAULT_CEQ_PROMPT_TEMPLATE_PATH,
        )

        # Uses context_to_response_ratio to generate the available tokens for context docs
        _, available_request_tokens = self.llm_service.get_available_request_tokens(
            prompt=prompt,
            token_utilization=token_utilization,
            context_to_response_ratio=context_to_response_ratio,
            llm_provider=self.llm_service.llm_provider,
        )

        context_docs = self.doc_retrieval.get_documents(
            query=chat_in,
            max_total_tokens=available_request_tokens,
            enabled_domains=self.config.enabled_domains,
        )

        prompt = self.create_prompt(
            user_input=chat_in,
            llm_provider_name=self.llm_service.llm_provider.CLASS_NAME,  # type: ignore
            prompt_template_path=self.DEFAULT_CEQ_PROMPT_TEMPLATE_PATH,
            context_docs=context_docs,
        )

        previous_response: Optional[dict] = None
        final_response: Optional[dict] = None

        for current_response in self.llm_service.create_chat(
            prompt=prompt,
            token_utilization=token_utilization,
            stream=stream,
        ):
            if previous_response is not None:
                yield previous_response["response_content_string"]
            if current_response is not None:
                previous_response = current_response

        final_response = previous_response

        llm_model_name = final_response.get("model_name", None) or self.llm_service.llm_provider.llm_model_instance.MODEL_NAME  # type: ignore
        response_content_string = final_response.get("response_content_string", None)  # type: ignore

        full_response = self._ceq_append_meta(response_content_string, context_docs, llm_model_name)

        if sprite_name == "webui_sprite":
            yield self._parse_local_markdown(full_response)
        else:
            return full_response

    def _ceq_append_meta(
        self, response_content_string: str, context_docs: list[RetrievalDoc], llm_model_name
    ) -> dict[str, str]:
        # Covering LLM doc notations cases
        # The modified pattern now includes optional opening parentheses or brackets before "Document"
        # and optional closing parentheses or brackets after the number
        pattern = r"[\[\(]?Document\s*\[?(\d+)\]?\)?[\]\)]?"
        formatted_text = re.sub(pattern, r"[\1]", response_content_string, flags=re.IGNORECASE)

        # This finds all instances of [n] in the LLM response
        pattern_num = r"\[\d\]"
        matches = re.findall(pattern_num, formatted_text)

        if not matches:
            # self.log.info("No supporting docs.")
            answer_obj = {
                "response_content_string": response_content_string,
                "llm": llm_model_name,
                "documents": [],
            }
            return answer_obj

        # Formatted text has all mutations of documents n replaced with [n]

        answer_obj = {
            "response_content_string": formatted_text,
            "llm": llm_model_name,
            "documents": [],
        }

        if matches:
            # Creates a list of each unique mention of [n] in LLM response
            unique_doc_nums = set([int(match[1:-1]) for match in matches])
            for doc_num in unique_doc_nums:
                # doc_num given to llm has an index starting a 1
                # Subtract 1 to get the correct index in the list
                doc_index = doc_num - 1
                # Access the document from the list using the index
                if 0 <= doc_index < len(context_docs):
                    if not (retrieval_rank := context_docs[doc_index].retrieval_rank):
                        retrieval_rank = doc_num
                    if uri := context_docs[doc_index].uri:
                        uri = uri.replace(" ", "-")
                    else:
                        uri = "URI not found"
                    if not (title := context_docs[doc_index].title):
                        title = "Title not found"
                    document = {
                        "doc_num": retrieval_rank,
                        "uri": uri,
                        "title": title,
                    }
                    answer_obj["documents"].append(document)
                else:
                    pass
                    self.log.warning(f"Document{doc_num} not found in the list.")

        # self.log.info(f"response with metadata: {answer_obj}")

        return answer_obj

    def _parse_local_markdown(self, full_response) -> str:
        # Should move this to text processing module
        markdown_string = ""
        # Start with the answer text
        if response_content_string := full_response.get("response_content_string", None):
            markdown_string += f"{response_content_string}\n\n"
        # Add the sources header if there are any documents
        if documents := full_response.get("documents", None):
            markdown_string += "**Sources:**\n"
            # For each document, add a numbered list item with the title and URL
            for doc in documents:
                markdown_string += f"[{doc['doc_num']}] **{doc['title']}**: <{doc['uri']}>\n"
        else:
            markdown_string += "No related documents found.\n"

        return markdown_string

    def create_main_chat_ui(self):
        components = {}

        components["enabled_domains"] = gr.Dropdown(
            choices=["all"] + self.doc_index.domain_names,
            value="all",
            label="Topics to Search",
            multiselect=True,
            min_width=0,
        )
        components["context_to_response_ratio"] = gr.Slider(
            value=self.config.context_to_response_ratio,
            label="Context to Response Ratio",
            minimum=0.0,
            maximum=1.0,
            step=0.05,
            min_width=0,
            info="Percent of the model's context size to use for context docs.",
        )
        self.doc_retrieval.create_settings_ui()

        GradioBase.create_settings_event_listener(self.config, components)
