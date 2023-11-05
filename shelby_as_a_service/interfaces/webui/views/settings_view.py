import typing
from typing import Any, Dict, Optional, Type

import gradio as gr
import interfaces.webui.gradio_helpers as GradioHelpers
from app.module_base import ModuleBase
from pydantic import BaseModel


class SettingsView(ModuleBase):
    CLASS_NAME: str = "settings_view"
    CLASS_UI_NAME: str = "⚙️"
    SETTINGS_UI_COL = 4
    PRIMARY_UI_COL = 6

    class ClassConfigModel(BaseModel):
        current_ui_view_name: str = "Settings View"

        class Config:
            extra = "ignore"

    config: ClassConfigModel

    def __init__(self, config_file_dict: dict[str, typing.Any] = {}, **kwargs):
        super().__init__(config_file_dict=config_file_dict, **kwargs)

    def create_primary_ui(self):
        components = {}

        with gr.Column(elem_classes="primary_ui_col"):
            components["chat_tab_out_text"] = gr.Textbox(
                show_label=False,
                interactive=False,
                placeholder=f"Welcome to {SettingsView.CLASS_UI_NAME}",
                elem_id="chat_tab_out_text",
                elem_classes="chat_tab_out_text_class",
                scale=7,
            )

    def create_settings_ui(self):
        with gr.Column():
            gr.Textbox(value="To Implement")
