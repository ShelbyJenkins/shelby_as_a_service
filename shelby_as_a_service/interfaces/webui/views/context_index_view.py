from typing import Any, Dict, List, Optional, Type

import gradio as gr
import interfaces.webui.gradio_helpers as GradioHelper
from app_config.app_base import AppBase


class ContextIndexView(AppBase):
    MODULE_NAME: str = "context_index_view"
    MODULE_UI_NAME: str = "Context Index"
    SETTINGS_UI_COL = 4
    PRIMARY_UI_COL = 6

    components: Dict[str, Any]

    def __init__(self, webui_sprite):
        self.webui_sprite = webui_sprite
        self.ingest_agent = self.webui_sprite.ingest_agent
        self.the_context_index = AppBase.the_context_index
        self.components = {}

    def create_primary_ui(self):
        with gr.Column(elem_classes="primary_ui_col"):
            self.components["chat_tab_out_text"] = gr.Textbox(
                show_label=False,
                interactive=False,
                placeholder=f"Welcome to {ContextIndexView.MODULE_UI_NAME}",
                elem_id="chat_tab_out_text",
                elem_classes="chat_tab_out_text_class",
                scale=7,
            )

        self.create_event_handlers()

    def create_settings_ui(self):
        with gr.Column():
            self.quick_add()
            self.add_source()
            with gr.Tab(label="Add Topic"):
                pass
            with gr.Tab(label="Index Management"):
                pass

    def quick_add(self):
        with gr.Tab("Quick Add"):
            self.components["ingest_button"] = gr.Button(
                value="Ingest",
                variant="primary",
                elem_classes="chat_tab_button",
                min_width=0,
            )
            self.components["url_textbox"] = gr.Textbox(
                placeholder="Paste URL Link",
                lines=1,
                show_label=False,
            )
            self.components["file_path_textbox"] = gr.Textbox(
                placeholder="Paste Filepath (or drag and drop)",
                lines=1,
                visible=False,
                show_label=False,
            )

            with gr.Row():
                with gr.Column(min_width=0):
                    self.components["url_or_file_radio"] = gr.Radio(
                        value="From Website",
                        choices=["From Website", "From Local File"],
                        interactive=True,
                        show_label=False,
                        min_width=0,
                    )
                with gr.Column(min_width=0, scale=3):
                    with gr.Row():
                        self.components["default_web_data_source_drp"] = gr.Dropdown(
                            visible=True,
                            allow_custom_value=True,
                            value=self.the_context_index.index_data_domains[0]
                            .data_domain_sources[0]
                            .data_source_name,
                            choices=[
                                cls.data_source_name
                                for cls in self.the_context_index.index_data_domains[
                                    0
                                ].data_domain_sources
                            ],
                            show_label=False,
                            interactive=True,
                        )
                        self.components["default_local_data_source_drp"] = gr.Dropdown(
                            visible=False,
                            allow_custom_value=True,
                            value=self.the_context_index.index_data_domains[0]
                            .data_domain_sources[0]
                            .data_source_name,
                            choices=[
                                cls.data_source_name
                                for cls in self.the_context_index.index_data_domains[
                                    0
                                ].data_domain_sources
                            ],
                            show_label=False,
                            interactive=True,
                        )
                    with gr.Row():
                        self.components["custom_web_data_source_drp"] = gr.Dropdown(
                            visible=False,
                            allow_custom_value=True,
                            value=self.the_context_index.index_data_domains[0]
                            .data_domain_sources[0]
                            .data_source_name,
                            choices=[
                                cls.data_source_name
                                for cls in self.the_context_index.index_data_domains[
                                    0
                                ].data_domain_sources
                            ],
                            show_label=False,
                            interactive=True,
                        )
                        self.components["custom_local_data_source_drp"] = gr.Dropdown(
                            visible=False,
                            allow_custom_value=True,
                            value=self.the_context_index.index_data_domains[0]
                            .data_domain_sources[0]
                            .data_source_name,
                            choices=[
                                cls.data_source_name
                                for cls in self.the_context_index.index_data_domains[
                                    0
                                ].data_domain_sources
                            ],
                            show_label=False,
                            interactive=True,
                        )
                    self.components["default_custom_checkbox"] = gr.Checkbox(label="Use custom")

            self.components["files_drop_box"] = gr.File(
                visible=False,
                label="Drag and drop file",
            )

            def toggle_web_or_local(value):
                if value == "From Website":
                    return [
                        gr.Textbox(visible=True),
                        gr.File(visible=False),
                        gr.Textbox(visible=False),
                    ]
                return [
                    gr.Textbox(visible=False),
                    gr.File(visible=True),
                    gr.Textbox(visible=True),
                ]

            def toggle_default_custom(url_or_file_radio, default_custom_checkbox):
                if url_or_file_radio == "From Website":
                    if default_custom_checkbox == False:
                        return [
                            gr.Dropdown(visible=True),
                            gr.Dropdown(visible=False),
                            gr.Dropdown(visible=False),
                            gr.Dropdown(visible=False),
                        ]
                    return [
                        gr.Dropdown(visible=False),
                        gr.Dropdown(visible=False),
                        gr.Dropdown(visible=True),
                        gr.Dropdown(visible=False),
                    ]
                else:
                    if default_custom_checkbox == False:
                        return [
                            gr.Dropdown(visible=False),
                            gr.Dropdown(visible=True),
                            gr.Dropdown(visible=False),
                            gr.Dropdown(visible=False),
                        ]
                    return [
                        gr.Dropdown(visible=False),
                        gr.Dropdown(visible=False),
                        gr.Dropdown(visible=False),
                        gr.Dropdown(visible=True),
                    ]

            self.components["default_custom_checkbox"].change(
                fn=toggle_default_custom,
                inputs=[
                    self.components["url_or_file_radio"],
                    self.components["default_custom_checkbox"],
                ],
                outputs=[
                    self.components["default_web_data_source_drp"],
                    self.components["default_local_data_source_drp"],
                    self.components["custom_web_data_source_drp"],
                    self.components["custom_local_data_source_drp"],
                ],
            )

            self.components["url_or_file_radio"].change(
                fn=toggle_default_custom,
                inputs=[
                    self.components["url_or_file_radio"],
                    self.components["default_custom_checkbox"],
                ],
                outputs=[
                    self.components["default_web_data_source_drp"],
                    self.components["default_local_data_source_drp"],
                    self.components["custom_web_data_source_drp"],
                    self.components["custom_local_data_source_drp"],
                ],
            ).then(
                fn=toggle_web_or_local,
                inputs=self.components["url_or_file_radio"],
                outputs=[
                    self.components["url_textbox"],
                    self.components["file_path_textbox"],
                    self.components["files_drop_box"],
                ],
            )

    def add_source(self):
        with gr.Tab(label="Add Source"):
            with gr.Row():
                self.components["url_or_file_radio"] = gr.Radio(
                    value="From Website",
                    choices=["From Website", "From Local File"],
                    interactive=True,
                    show_label=False,
                    min_width=0,
                )
                self.components["source_preset"] = gr.Dropdown(
                    value="Github",
                    choices=["Github", "Save to Topic Domain", "Don't Save"],
                    info="Applies presets that improves performance.",
                    interactive=True,
                    show_label=False,
                    min_width=0,
                )
                self.components["ingest_button"] = gr.Button(
                    value="Ingest",
                    variant="primary",
                    elem_classes="chat_tab_button",
                    min_width=0,
                )

            self.components["url_textbox"] = gr.Textbox(
                placeholder="Paste URL Link",
                lines=1,
                show_label=False,
            )
            self.components["files_drop_box"] = gr.File(
                visible=False,
                label="Drag and drop file",
            )
            self.components["file_path_textbox"] = gr.Textbox(
                placeholder="or Paste Filepath",
                lines=1,
                visible=False,
                show_label=False,
            )
            with gr.Tab("Save Document"):
                gr.Checkbox(label="test")
            with gr.Tab(open=False, label="Custom Loader"):
                with gr.Row():
                    self.components["custom_loader"] = gr.Dropdown(
                        value="Github",
                        choices=["Github", "Save to Topic Domain", "Don't Save"],
                        label="Source",
                        interactive=True,
                    )
                    self.components["test_loader_button"] = gr.Button(
                        value="Test Loader",
                        variant="primary",
                        elem_classes="chat_tab_button",
                        min_width=0,
                    )

                # Settings go here
                gr.Checkbox(label="test")
            with gr.Tab(open=False, label="Custom Text Processor"):
                with gr.Row():
                    self.components["custom_text_proc"] = gr.Dropdown(
                        value="Github",
                        choices=["Github", "Save to Topic Domain", "Don't Save"],
                        label="Source",
                        interactive=True,
                    )
                    self.components["test_proc"] = gr.Button(
                        value="Test Loader",
                        variant="primary",
                        elem_classes="chat_tab_button",
                        min_width=0,
                    )

                # Settings go here
                gr.Checkbox(label="test")
            with gr.Tab(open=False, label="Contextual Compressors and Minifiers"):
                with gr.Row():
                    self.components["custom_special"] = gr.Dropdown(
                        value="Github",
                        choices=["Github", "Save to Topic Domain", "Don't Save"],
                        label="Source",
                        interactive=True,
                    )
                    self.components["test_special"] = gr.Button(
                        value="Test Loader",
                        variant="primary",
                        elem_classes="chat_tab_button",
                        min_width=0,
                    )

                # Settings go here
                gr.Checkbox(label="test")

            with gr.Tab(open=False, label="Save files and configs"):
                self.components["data_domain_drp"] = gr.Dropdown(
                    allow_custom_value=True,
                    value=self.the_context_index.index_data_domains[0].data_domain_name,
                    choices=[
                        cls.data_domain_name for cls in self.the_context_index.index_data_domains
                    ],
                    show_label=False,
                    interactive=True,
                )
                self.components["data_source_drp"] = gr.Dropdown(
                    allow_custom_value=True,
                    value=self.the_context_index.index_data_domains[0]
                    .data_domain_sources[0]
                    .data_source_name,
                    choices=[
                        cls.data_source_name
                        for cls in self.the_context_index.index_data_domains[0].data_domain_sources
                    ],
                    show_label=False,
                    interactive=True,
                )
            # self.url_or_files_radio_toggle()

    def create_event_handlers(self):
        gr.on(
            triggers=[
                self.components["ingest_button"].click,
                self.components["url_textbox"].submit,
                self.components["file_path_textbox"].submit,
            ],
            inputs=list(self.components.values()),
            fn=lambda val: self.ingest_agent.ingest_from_ui(self.components, val),
        )
