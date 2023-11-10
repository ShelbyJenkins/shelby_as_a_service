from typing import Literal, Type

from services.text_processing.ingest_processing.ingest_ceq import IngestCEQ
from services.text_processing.ingest_processing.ingest_open_api import OpenAPIMinifier

AVAILABLE_PROVIDERS_NAMES = Literal[
    IngestCEQ.class_name,
    OpenAPIMinifier.class_name,
]
AVAILABLE_PROVIDERS: list[Type] = [
    IngestCEQ,
    OpenAPIMinifier,
]
AVAILABLE_PROVIDERS_UI_NAMES = [
    IngestCEQ.CLASS_UI_NAME,
    OpenAPIMinifier.CLASS_UI_NAME,
]