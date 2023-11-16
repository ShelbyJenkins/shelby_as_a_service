import logging
from typing import Any, Optional, Type

import context_index.doc_index as doc_index_models
from context_index.doc_index.doc_index_templates import DocIndexTemplates
from context_index.index_base import IndexBase
from services.database.database_service import DatabaseService
from services.document_loading.document_loading_service import DocLoadingService
from services.embedding.embedding_service import EmbeddingService
from services.service_base import ServiceBase
from services.text_processing.ingest_processing.ingest_processing_service import (
    IngestProcessingService,
)
from services.text_processing.text_utils import check_and_handle_name_collision
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class DocIndex(IndexBase, ServiceBase):
    doc_index_model_instance: doc_index_models.DocIndexModel
    session: Session
    log: logging.Logger
    context_template: doc_index_models.DocIndexTemplateModel

    def __init__(self) -> None:
        self.log = logging.getLogger(__name__)

        DocIndex.setup_index()
        self.setup_doc_index()

    def setup_doc_index(self):
        try:
            DocIndex.session = self.open_session()
            if doc_index_model_instance := DocIndex.session.query(
                doc_index_models.DocIndexModel
            ).first():
                DocIndex.doc_index_model_instance = doc_index_model_instance
                self.populate_service_providers(
                    target_instance=DocIndex.doc_index_model_instance,
                    doc_index_model_name=doc_index_models.DocDBModel.CLASS_NAME,  # type: ignore
                )
                self.add_default_doc_index_templates_to_index()
            else:
                DocIndex.doc_index_model_instance = doc_index_models.DocIndexModel()
                DocIndex.session.add(DocIndex.doc_index_model_instance)
                DocIndex.session.flush()

                self.populate_service_providers(
                    target_instance=DocIndex.doc_index_model_instance,
                    doc_index_model_name=doc_index_models.DocDBModel.CLASS_NAME,  # type: ignore
                )
                self.add_default_doc_index_templates_to_index()

                self.create_domain_or_source()

        except SQLAlchemyError:
            DocIndex.session.rollback()
            raise

    @property
    def close_doc_index_session(self):
        self.close_session(DocIndex.session)

    @property
    def open_doc_index_session(self):
        DocIndex.session = self.open_session()
        # DocIndex.session.refresh(DocIndex.doc_index_model_instance)

    def open_doc_index_write_session(self, objects: Any | list[Any]) -> Session:
        self.close_doc_index_session
        return self.open_write_session(objects)

    @property
    def close_doc_index_write_session(self):
        self.close_write_session()
        self.open_doc_index_session

    @property
    def commit_session(self):
        try:
            DocIndex.session.commit()
        except:
            DocIndex.session.rollback()  # Rollback in case of error
            raise

    @property
    def domain_names(self) -> list:  # Can't type this due to Gradio issue
        return [domain.name for domain in DocIndex.doc_index_model_instance.domains]

    @property
    def source_names_in_doc_index(self) -> list:
        return [name[0] for name in DocIndex.session.query(doc_index_models.SourceModel.name).all()]

    @property
    def index(self) -> doc_index_models.DocIndexModel:
        return DocIndex.doc_index_model_instance

    @property
    def domain(self) -> doc_index_models.DomainModel:
        if getattr(self.index, "current_domain", None) is None:
            raise Exception(f"{self.index} has no domain.")
        return self.index.current_domain

    @property
    def source(self) -> doc_index_models.SourceModel:
        if getattr(self.domain, "current_source", None) is None:
            raise Exception(f"{self.domain} has no source.")
        return self.domain.current_source

    @classmethod
    def create_doc_index_model_instance(
        cls,
        doc_index_model_name: doc_index_models.DOC_INDEX_MODEL_NAMES,
        provider_name: Optional[str] = None,
        config: dict[str, Any] = {},
    ) -> (
        doc_index_models.DocDBModel
        | doc_index_models.DocLoaderModel
        | doc_index_models.DocIngestProcessorModel
        | doc_index_models.DocEmbeddingModel
    ):
        match doc_index_model_name:
            case doc_index_models.DocDBModel.CLASS_NAME:
                available_classes = DatabaseService.REQUIRED_CLASSES
                doc_index_model = doc_index_models.DocDBModel
                if not provider_name:
                    provider_name = doc_index_models.DocDBModel.DEFAULT_PROVIDER_NAME
            case doc_index_models.DocLoaderModel.CLASS_NAME:
                available_classes = DocLoadingService.REQUIRED_CLASSES
                doc_index_model = doc_index_models.DocLoaderModel
                if not provider_name:
                    provider_name = doc_index_models.DocLoaderModel.DEFAULT_PROVIDER_NAME
            case doc_index_models.DocIngestProcessorModel.CLASS_NAME:
                available_classes = IngestProcessingService.REQUIRED_CLASSES
                doc_index_model = doc_index_models.DocIngestProcessorModel
                if not provider_name:
                    provider_name = doc_index_models.DocIngestProcessorModel.DEFAULT_PROVIDER_NAME
            case doc_index_models.DocEmbeddingModel.CLASS_NAME:
                available_classes = EmbeddingService.REQUIRED_CLASSES
                doc_index_model = doc_index_models.DocEmbeddingModel
                if not provider_name:
                    provider_name = doc_index_models.DocEmbeddingModel.DEFAULT_PROVIDER_NAME
            case _:
                raise Exception(
                    f"Unexpected error: doc_index_model_name should be of type doc_index_models.DOC_INDEX_MODEL_NAMES but is {doc_index_model_name}."
                )
        provider_class = cls.get_requested_class(
            requested_class=provider_name,
            available_classes=available_classes,
        )

        config = provider_class.ClassConfigModel(**config).model_dump()
        return doc_index_model(name=provider_name, config=config)

    def get_provider_instance_model_from_service_name(
        self,
        service_name: str,
        provider_name: str,
        parent_domain_or_source: Optional[
            doc_index_models.DomainModel | doc_index_models.SourceModel
        ] = None,
    ) -> Any:
        # Used for UI components generated by services
        if not parent_domain_or_source:
            if service_name == DatabaseService.CLASS_NAME:
                provider_model = self.get_index_model_instance(
                    list_of_instances=self.index.doc_dbs, name=provider_name
                )
            else:
                raise ValueError(f"service_name must be {DatabaseService.CLASS_NAME}")
        else:
            if service_name == DocLoadingService.CLASS_NAME:
                provider_model = self.get_index_model_instance(
                    list_of_instances=parent_domain_or_source.doc_loaders, name=provider_name
                )

            elif service_name == IngestProcessingService.CLASS_NAME:
                provider_model = self.get_index_model_instance(
                    list_of_instances=parent_domain_or_source.doc_ingest_processors,
                    name=provider_name,
                )
            else:
                raise ValueError(
                    f"service_name must be {DocLoadingService.CLASS_NAME}, {IngestProcessingService.CLASS_NAME}"
                )
        if provider_model is None:
            raise ValueError(f"provider_model {provider_model} not found")
        return provider_model

    def set_current_domain_or_source_provider_instance(
        self,
        domain_or_source: Type[doc_index_models.DomainModel] | Type[doc_index_models.SourceModel],
        doc_index_model_name: doc_index_models.DOC_INDEX_MODEL_NAMES,
        set_id: Optional[int] = None,
        set_name: Optional[str] = None,
    ):
        if domain_or_source is doc_index_models.DomainModel:
            parent_instance = self.domain
        elif domain_or_source is doc_index_models.SourceModel:
            parent_instance = self.source
        else:
            raise Exception(f"Unexpected error: {domain_or_source.__name__} not found.")
        match doc_index_model_name:
            case doc_index_models.DocDBModel.CLASS_NAME:
                parent_instance.enabled_doc_db = self.get_index_model_instance(
                    list_of_instances=self.index.doc_dbs, id=set_id, name=set_name
                )
            case doc_index_models.DocLoaderModel.CLASS_NAME:
                parent_instance.enabled_doc_loader = self.get_index_model_instance(
                    list_of_instances=parent_instance.doc_loaders, id=set_id, name=set_name
                )
            case doc_index_models.DocIngestProcessorModel.CLASS_NAME:
                parent_instance.enabled_doc_ingest_processor = self.get_index_model_instance(
                    list_of_instances=parent_instance.doc_ingest_processors,
                    id=set_id,
                    name=set_name,
                )
            case _:
                raise Exception(
                    f"Unexpected error: doc_index_model_name should be of type doc_index_models.DOC_INDEX_MODEL_NAMES but is {doc_index_model_name}."
                )

        DocIndex.session.flush()

    def create_domain_or_source(
        self,
        new_name: Optional[str] = None,
        new_description: Optional[str] = None,
        requested_template_name: Optional[str] = None,
        clone_name: Optional[str] = None,
        clone_id: Optional[int] = None,
        parent_domain: Optional[doc_index_models.DomainModel] = None,
    ) -> doc_index_models.DomainModel | doc_index_models.SourceModel:
        if parent_domain:
            domain_or_source = doc_index_models.SourceModel
            current_domain_or_source = parent_domain.current_source
            existing_names = self.source_names_in_doc_index
            list_of_domains_or_sources = self.domain.sources
        else:
            domain_or_source = doc_index_models.DomainModel
            current_domain_or_source = self.index.current_domain
            existing_names = self.domain_names
            list_of_domains_or_sources = self.index.domains

        if not new_name:
            if clone_name:
                new_name = clone_name
            else:
                new_name = domain_or_source.DEFAULT_NAME
        new_name = check_and_handle_name_collision(existing_names=existing_names, new_name=new_name)
        if not new_description:
            new_description = domain_or_source.DEFAULT_DESCRIPTION
        new_instance = domain_or_source(name=new_name, description=new_description)

        if isinstance(new_instance, doc_index_models.DomainModel):
            self.index.domains.append(new_instance)
        if isinstance(new_instance, doc_index_models.SourceModel):
            if parent_domain:  # For type checker
                parent_domain.sources.append(new_instance)
        DocIndex.session.flush()

        if not current_domain_or_source:
            if isinstance(new_instance, doc_index_models.DomainModel):
                self.index.current_domain = new_instance
            if isinstance(new_instance, doc_index_models.SourceModel):
                if parent_domain:  # For type checker
                    parent_domain.current_source = new_instance
            DocIndex.session.flush()

        if not clone_name and not clone_id:  # In this case we're using a template
            if not requested_template_name:
                requested_template_name = new_instance.DEFAULT_TEMPLATE_NAME
            context_template = self.get_index_model_instance(
                list_of_instances=self.index.doc_index_templates,
                name=requested_template_name,
            )
            self.initialize_domain_or_source_config(
                target_instance=new_instance,
                batch_update_enabled=context_template.batch_update_enabled,
                enabled_doc_ingest_processor_name=context_template.enabled_doc_ingest_processor_name,
                enabled_doc_loader_name=context_template.enabled_doc_loader_name,
                enabled_doc_db_name=context_template.enabled_doc_db.name,
                enabled_doc_ingest_processor_config=context_template.enabled_doc_ingest_processor_config,
                enabled_doc_loader_config=context_template.enabled_doc_loader_config,
            )
            if isinstance(new_instance, doc_index_models.DomainModel):
                self.create_domain_or_source(parent_domain=new_instance)

        else:  # In this case, we are cloning an existing domain or source
            object_to_clone = self.get_index_model_instance(
                list_of_instances=list_of_domains_or_sources,
                id=clone_id,
                name=clone_name,
            )
            if isinstance(new_instance, doc_index_models.DomainModel):
                for source_model_to_clone in object_to_clone.sources:
                    self.create_domain_or_source(
                        parent_domain=new_instance,
                        clone_name=source_model_to_clone.name,
                        clone_id=source_model_to_clone.id,
                    )

            self.initialize_domain_or_source_config(
                target_instance=new_instance,
                batch_update_enabled=object_to_clone.batch_update_enabled,
                enabled_doc_ingest_processor_name=object_to_clone.enabled_doc_ingest_processor.name,
                enabled_doc_loader_name=object_to_clone.enabled_doc_loader.name,
                enabled_doc_db_name=object_to_clone.enabled_doc_db.name,
                enabled_doc_ingest_processor_config=object_to_clone.enabled_doc_ingest_processor.config,
                enabled_doc_loader_config=object_to_clone.enabled_doc_loader.config,
            )
        self.commit_session
        return new_instance

    def initialize_domain_or_source_config(
        self,
        target_instance: doc_index_models.DomainModel | doc_index_models.SourceModel,
        batch_update_enabled: bool,
        enabled_doc_ingest_processor_name: str,
        enabled_doc_loader_name: str,
        enabled_doc_db_name: str,
        enabled_doc_ingest_processor_config: dict = {},
        enabled_doc_loader_config: dict = {},
    ):
        target_instance.batch_update_enabled = batch_update_enabled

        enabled_doc_loader = self.create_doc_index_model_instance(
            doc_index_model_name=doc_index_models.DocLoaderModel.CLASS_NAME,  # type: ignore
            provider_name=enabled_doc_loader_name,
            config=enabled_doc_loader_config,
        )
        if not isinstance(enabled_doc_loader, doc_index_models.DocLoaderModel):
            raise Exception(
                "Unexpected error: enabled_doc_loader should be of type doc_index_models.DocLoaderModel."
            )
        target_instance.doc_loaders.append(enabled_doc_loader)
        DocIndex.session.flush()
        target_instance.enabled_doc_loader = enabled_doc_loader
        self.populate_service_providers(
            target_instance=target_instance,
            doc_index_model_name=doc_index_models.DocLoaderModel.CLASS_NAME,  # type: ignore
        )

        enabled_doc_ingest_processor = self.create_doc_index_model_instance(
            doc_index_model_name=doc_index_models.DocIngestProcessorModel.CLASS_NAME,  # type: ignore
            provider_name=enabled_doc_ingest_processor_name,
            config=enabled_doc_ingest_processor_config,
        )
        if not isinstance(enabled_doc_ingest_processor, doc_index_models.DocIngestProcessorModel):
            raise Exception(
                "Unexpected error: enabled_doc_ingest_processor should be of type doc_index_models.DocIngestProcessorModel."
            )
        target_instance.doc_ingest_processors.append(enabled_doc_ingest_processor)
        DocIndex.session.flush()
        target_instance.enabled_doc_ingest_processor = enabled_doc_ingest_processor
        self.populate_service_providers(
            target_instance=target_instance,
            doc_index_model_name=doc_index_models.DocIngestProcessorModel.CLASS_NAME,  # type: ignore
        )

        target_instance.enabled_doc_db = self.get_index_model_instance(
            list_of_instances=DocIndex.doc_index_model_instance.doc_dbs, name=enabled_doc_db_name
        )

        DocIndex.session.flush()

    def populate_service_providers(
        self,
        target_instance: doc_index_models.DomainModel
        | doc_index_models.SourceModel
        | doc_index_models.DocIndexModel
        | doc_index_models.DocDBModel,
        doc_index_model_name: doc_index_models.DOC_INDEX_MODEL_NAMES,
    ):
        if isinstance(target_instance, doc_index_models.DocIndexModel):
            if doc_index_model_name == doc_index_models.DocDBModel.CLASS_NAME:
                list_of_current_providers = target_instance.doc_dbs
                available_providers = DatabaseService.REQUIRED_CLASSES
                model_type = doc_index_models.DocDBModel
            else:
                raise Exception(
                    "doc_index_models.DocDBModel's can only be added to doc_index_models.DocIndexModel's."
                )
        elif isinstance(target_instance, doc_index_models.DocDBModel):
            if doc_index_model_name == doc_index_models.DocEmbeddingModel.CLASS_NAME:
                list_of_current_providers = target_instance.doc_embedders
                available_providers = EmbeddingService.REQUIRED_CLASSES
                model_type = doc_index_models.DocEmbeddingModel
            else:
                raise Exception(
                    "doc_index_models.DocEmbeddingModel's can only be added to doc_index_models.DocDBModel's."
                )
        else:
            if doc_index_model_name == doc_index_models.DocLoaderModel.CLASS_NAME:
                list_of_current_providers = target_instance.doc_loaders
                available_providers = DocLoadingService.REQUIRED_CLASSES
                model_type = doc_index_models.DocLoaderModel
            elif doc_index_model_name == doc_index_models.DocIngestProcessorModel.CLASS_NAME:
                list_of_current_providers = target_instance.doc_ingest_processors
                available_providers = IngestProcessingService.REQUIRED_CLASSES
                model_type = doc_index_models.DocIngestProcessorModel
            else:
                raise Exception(f"Unexpected error: {doc_index_model_name} not found.")

        for available_provider_class in available_providers:
            if available_provider_class.CLASS_NAME in [
                current_provider.name for current_provider in list_of_current_providers
            ]:
                continue

            model_instance = self.create_doc_index_model_instance(
                doc_index_model_name=doc_index_model_name,
                provider_name=available_provider_class.CLASS_NAME,
            )
            if not isinstance(model_instance, model_type):
                raise Exception(
                    f"Unexpected error: model_instance should be of type {doc_index_model_name}."
                )
            list_of_current_providers.append(model_instance)  # type: ignore

            if isinstance(model_instance, doc_index_models.DocDBModel):
                self.populate_service_providers(
                    target_instance=model_instance,
                    doc_index_model_name=doc_index_models.DocEmbeddingModel.CLASS_NAME,  # type: ignore
                )
                model_instance.enabled_doc_embedder = self.get_index_model_instance(
                    list_of_instances=model_instance.doc_embedders,
                    name=doc_index_models.DocEmbeddingModel.DEFAULT_PROVIDER_NAME,
                )

        DocIndex.session.flush()

    def add_default_doc_index_templates_to_index(self):
        for available_template in DocIndexTemplates.AVAILABLE_TEMPLATES:
            existing_config = next(
                (
                    index_context_template
                    for index_context_template in DocIndex.doc_index_model_instance.doc_index_templates
                    if index_context_template.name == available_template.TEMPLATE_NAME
                ),
                None,
            )
            if not existing_config:
                enabled_doc_db = self.get_index_model_instance(
                    list_of_instances=DocIndex.doc_index_model_instance.doc_dbs,
                    name=available_template.doc_db_provider_name,
                )
                if not isinstance(enabled_doc_db, doc_index_models.DocDBModel):
                    raise Exception(
                        "Unexpected error: enabled_doc_db should not be of type doc_index_models.DocDBModel."
                    )
                new_template = self.create_template(
                    new_template_name=available_template.TEMPLATE_NAME,
                    enabled_doc_ingest_processor_name=available_template.doc_ingest_processor_provider_name,
                    enabled_doc_ingest_processor_config=available_template.doc_ingest_processor_config.model_dump(),
                    enabled_doc_loader_name=available_template.doc_loader_provider_name,
                    enabled_doc_loader_config=available_template.doc_loader_config.model_dump(),
                    enabled_doc_db=enabled_doc_db,
                    batch_update_enabled=available_template.batch_update_enabled,
                )

                DocIndex.doc_index_model_instance.doc_index_templates.append(new_template)
                DocIndex.session.flush()

    def save_config_as_template(
        self,
        parent_object: doc_index_models.DomainModel | doc_index_models.SourceModel,
        new_template_name: Optional[str] = None,
    ):
        if not new_template_name:
            new_template_name = parent_object.name

        new_context_template_name = check_and_handle_name_collision(
            existing_names=DocIndex.doc_index_model_instance.list_of_doc_index_template_names,
            new_name=new_template_name,
        )
        new_template = self.create_template(
            new_template_name=new_context_template_name,
            enabled_doc_ingest_processor_name=parent_object.enabled_doc_ingest_processor.name,
            enabled_doc_ingest_processor_config=parent_object.enabled_doc_ingest_processor.config,
            enabled_doc_loader_name=parent_object.enabled_doc_loader.name,
            enabled_doc_loader_config=parent_object.enabled_doc_loader.config,
            enabled_doc_db=parent_object.enabled_doc_db,
            batch_update_enabled=parent_object.batch_update_enabled,
        )

        # Append it to the index's list of context_configs
        DocIndex.doc_index_model_instance.doc_index_templates.append(new_template)
        DocIndex.session.flush()

    def create_template(
        self,
        new_template_name: str,
        enabled_doc_ingest_processor_name: str,
        enabled_doc_ingest_processor_config: dict,
        enabled_doc_loader_name: str,
        enabled_doc_loader_config: dict,
        enabled_doc_db: doc_index_models.DocDBModel,
        batch_update_enabled: bool,
    ):
        return doc_index_models.DocIndexTemplateModel(
            name=new_template_name,
            enabled_doc_ingest_processor_name=enabled_doc_ingest_processor_name,
            enabled_doc_ingest_processor_config=enabled_doc_ingest_processor_config,
            enabled_doc_loader_name=enabled_doc_loader_name,
            enabled_doc_loader_config=enabled_doc_loader_config,
            enabled_doc_db=enabled_doc_db,
            batch_update_enabled=batch_update_enabled,
        )

    def delete_source(self):
        pass

    def delete_domain(self):
        pass

    def delete_document(self, document: doc_index_models.DocumentModel) -> bool:
        undeleted_chunks = []

        def delete_entries(doc_db_ids_requiring_deletion, chunk_doc_db_name):
            try:
                DatabaseService().clear_existing_entries_by_id(
                    domain_name=document.domain_model.name,
                    doc_db_provider_name=chunk_doc_db_name,  # type: ignore
                    doc_db_ids_requiring_deletion=doc_db_ids_requiring_deletion,
                )
            except Exception as error:
                self.log.info(f"An error occurred: {error}")
                persisted_chunks = DatabaseService().fetch_by_ids(
                    domain_name=document.domain_model.name,
                    doc_db_provider_name=chunk_doc_db_name,  # type: ignore
                    ids=doc_db_ids_requiring_deletion,
                )
                if not persisted_chunks:
                    self.log.info(
                        f"It seems like the chunks were deleted succesffuly despite the error."
                    )
                else:
                    self.log.info(
                        f"Failed to delete the following chunks: '{persisted_chunks.keys()}'"
                    )
                    undeleted_chunks.extend(list(persisted_chunks.keys()))

        session = self.open_doc_index_write_session(document)
        chunk_doc_db_name = None
        doc_db_ids_requiring_deletion = []

        for chunk in document.context_chunks:
            if chunk_doc_db_name is None:
                chunk_doc_db_name = chunk.chunk_doc_db_name
            if chunk_doc_db_name != chunk.chunk_doc_db_name:
                delete_entries(doc_db_ids_requiring_deletion, chunk_doc_db_name)
                chunk_doc_db_name = chunk.chunk_doc_db_name
                doc_db_ids_requiring_deletion = []
            doc_db_ids_requiring_deletion.append(chunk.chunk_doc_db_id)
        delete_entries(doc_db_ids_requiring_deletion, chunk_doc_db_name)

        if undeleted_chunks:
            self.log.info(
                f"Failed to delete the following chunks for document: '{document.title}'. Persisting document."
            )
            self.close_doc_index_write_session
            return False
        try:
            session.delete(document)
            session.flush()
            session.refresh(document.source_model.domain_model)
            self.log.info(f"Successfully deleted document '{document.title}'")
        except Exception as error:
            self.log.info(f"An error occurred: {error}")
            session.rollback()
            return False
        finally:
            self.close_doc_index_write_session

        return True

    def clear_source(self, source: doc_index_models.SourceModel) -> bool:
        self.open_doc_index_write_session(source)
        persisted_doc_index_docs = []
        deleted_doc_index_docs = []
        for document in source.documents:
            if not self.delete_document(document=document):
                persisted_doc_index_docs.append(document)
            else:
                deleted_doc_index_docs.append(document)

        self.close_doc_index_write_session
        if not persisted_doc_index_docs:
            self.log.info(f"Successfully deleted all documents for {source.name}")
            return True
        else:
            undeleted_titles = [document.title for document in persisted_doc_index_docs]
            deleted_titles = [document.title for document in deleted_doc_index_docs]
            self.log.info(
                f"Successfully deleted {deleted_titles}.\n"
                f"Failed to delete the following documents: {undeleted_titles}"
            )
            return False

    def clear_domain(self, domain: doc_index_models.DomainModel):
        self.open_doc_index_write_session(domain)
        domain_name = domain.name
        cleared_doc_index_sources = []
        uncleared_doc_index_sources = []
        for source in domain.sources:
            if self.clear_source(source=source):
                cleared_doc_index_sources.append(source)
            else:
                uncleared_doc_index_sources.append(source)
        if not uncleared_doc_index_sources:
            self.log.info(f"Successfully cleared all documents for {domain_name}")
        else:
            uncleared_sources = [source.name for source in uncleared_doc_index_sources]
            cleared_sources = [source.name for source in cleared_doc_index_sources]
            self.log.info(
                f"Successfully cleared {cleared_sources}.\n"
                f"Failed to delete all documents for the following cleared: {uncleared_sources}"
            )
        self.close_doc_index_write_session
