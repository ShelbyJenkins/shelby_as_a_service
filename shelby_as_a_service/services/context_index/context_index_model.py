from datetime import datetime

from services.database.index_base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship


class DocIngestProcessorModel(Base):
    __tablename__ = "doc_ingest_processors"
    id: Mapped[int] = mapped_column(primary_key=True)

    domain_id: Mapped[int] = mapped_column(Integer, ForeignKey("domains.id"), nullable=True)
    domain_model = relationship("DomainModel", foreign_keys=[domain_id])
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=True)
    source_model = relationship("SourceModel", foreign_keys=[source_id])

    DEFAULT_DOC_INGEST_PROCESSOR_NAME: str = "process_ingest_documents"
    name: Mapped[str] = mapped_column(String)
    config: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))  # type: ignore


class DocLoaderModel(Base):
    __tablename__ = "doc_loaders"
    id: Mapped[int] = mapped_column(primary_key=True)

    domain_id: Mapped[int] = mapped_column(Integer, ForeignKey("domains.id"), nullable=True)
    domain_model = relationship("DomainModel", foreign_keys=[domain_id])
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=True)
    source_model = relationship("SourceModel", foreign_keys=[source_id])

    DEFAULT_DOC_LOADER_NAME: str = "generic_recursive_web_scraper"
    name: Mapped[str] = mapped_column(String)
    config: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))  # type: ignore


class DocDBModel(Base):
    __tablename__ = "doc_dbs"
    id: Mapped[int] = mapped_column(primary_key=True)
    context_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("context_index_model.id"), nullable=True
    )
    context_index_model = relationship(
        "ContextIndexModel", back_populates="doc_dbs", foreign_keys=[context_id]
    )
    DEFAULT_DOC_DB_NAME: str = "pinecone_database"
    name: Mapped[str] = mapped_column(String, unique=True)
    config: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))  # type: ignore


class ContextTemplateModel(Base):
    __tablename__ = "index_context_templates"
    id: Mapped[int] = mapped_column(primary_key=True)

    context_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("context_index_model.id"), nullable=True
    )
    context_index_model = relationship("ContextIndexModel", foreign_keys=[context_id])

    enabled_doc_loader_name: Mapped[str] = mapped_column(String)
    enabled_doc_loader_config: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))  # type: ignore

    enabled_doc_ingest_processor_name: Mapped[str] = mapped_column(String)
    enabled_doc_ingest_processor_config: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))  # type: ignore

    doc_db_id: Mapped[int] = mapped_column(Integer, ForeignKey("doc_dbs.id"), nullable=True)
    enabled_doc_db = relationship("DocDBModel")

    batch_update_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    name: Mapped[str] = mapped_column(String)


class ChunkModel(Base):
    __tablename__ = "chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), nullable=True)
    document_model: Mapped["DocumentModel"] = relationship(
        "DocumentModel", foreign_keys=[document_id]
    )

    processed_content: Mapped[str] = mapped_column(String, nullable=True)


class DocumentModel(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=True)
    source_model: Mapped["SourceModel"] = relationship("SourceModel", foreign_keys=[source_id])
    domain_model: Mapped["DomainModel"] = relationship(
        "DomainModel",
        secondary="sources",
        primaryjoin="DocumentModel.source_id==SourceModel.id",
        secondaryjoin="SourceModel.domain_id==DomainModel.id",
        viewonly=True,
        uselist=False,  # Since each document is related to one domain through its source
    )
    chunked_content: Mapped[list[ChunkModel]] = relationship(
        "ChunkModel",
        back_populates="document_model",
        cascade="all, delete-orphan",
        foreign_keys=[ChunkModel.document_id],
    )
    original_content: Mapped[str] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    uri: Mapped[str] = mapped_column(String, nullable=True)
    batch_update_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    input_file_type: Mapped[str] = mapped_column(String, nullable=True)
    date_published: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    date_of_creation: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    date_of_last_update: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class SourceModel(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)

    domain_id: Mapped[int] = mapped_column(Integer, ForeignKey("domains.id"), nullable=True)
    domain_model: Mapped["DomainModel"] = relationship("DomainModel", foreign_keys=[domain_id])

    doc_loader_id: Mapped[int] = mapped_column(Integer, ForeignKey("doc_loaders.id"), nullable=True)
    enabled_doc_loader = relationship("DocLoaderModel", foreign_keys=[doc_loader_id])
    doc_loaders: Mapped[list[DocLoaderModel]] = relationship(
        "DocLoaderModel",
        back_populates="source_model",
        cascade="all, delete-orphan",
        foreign_keys=[DocLoaderModel.source_id],
    )

    @property
    def list_of_doc_loader_names(self) -> list:
        return [doc_loader.name for doc_loader in self.doc_loaders]

    doc_ingest_processor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("doc_ingest_processors.id"), nullable=True
    )
    enabled_doc_ingest_processor = relationship(
        "DocIngestProcessorModel", foreign_keys=[doc_ingest_processor_id]
    )
    doc_ingest_processors: Mapped[list[DocIngestProcessorModel]] = relationship(
        "DocIngestProcessorModel",
        back_populates="source_model",
        cascade="all, delete-orphan",
        foreign_keys=[DocIngestProcessorModel.source_id],
    )

    @property
    def list_of_doc_ingest_processor_names(self) -> list:
        return [doc_processor.name for doc_processor in self.doc_ingest_processors]

    doc_db_id: Mapped[int] = mapped_column(Integer, ForeignKey("doc_dbs.id"), nullable=True)
    enabled_doc_db = relationship("DocDBModel")

    DEFAULT_NAME: str = "default_source_name"
    DEFAULT_TEMPLATE_NAME: str = "default_template_name"
    DEFAULT_DESCRIPTION: str = "A default source description"
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default=DEFAULT_DESCRIPTION)
    batch_update_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    source_uri: Mapped[str] = mapped_column(String, nullable=True)

    documents: Mapped[list[DocumentModel]] = relationship(
        "DocumentModel",
        back_populates="source_model",
        cascade="all, delete-orphan",
        foreign_keys=[DocumentModel.source_id],
    )


class DomainModel(Base):
    __tablename__ = "domains"
    id: Mapped[int] = mapped_column(primary_key=True)

    context_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("context_index_model.id"), nullable=True
    )
    context_index_model: Mapped["ContextIndexModel"] = relationship(
        "ContextIndexModel", foreign_keys=[context_id]
    )

    current_source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=True)
    current_source = relationship("SourceModel", foreign_keys=[current_source_id])
    sources: Mapped[list[SourceModel]] = relationship(
        "SourceModel",
        back_populates="domain_model",
        cascade="all, delete-orphan",
        foreign_keys=[SourceModel.domain_id],
    )

    @property
    def list_of_source_names(self) -> list:
        return [source.name for source in self.sources]

    doc_ingest_processor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("doc_ingest_processors.id"), nullable=True
    )
    enabled_doc_ingest_processor = relationship(
        "DocIngestProcessorModel", foreign_keys=[doc_ingest_processor_id]
    )
    doc_ingest_processors: Mapped[list[DocIngestProcessorModel]] = relationship(
        "DocIngestProcessorModel",
        back_populates="domain_model",
        cascade="all, delete-orphan",
        foreign_keys=[DocIngestProcessorModel.domain_id],
    )

    @property
    def list_of_doc_ingest_processor_names(self) -> list:
        return [doc_processor.name for doc_processor in self.doc_ingest_processors]

    doc_loader_id: Mapped[int] = mapped_column(Integer, ForeignKey("doc_loaders.id"), nullable=True)
    enabled_doc_loader = relationship("DocLoaderModel", foreign_keys=[doc_loader_id])
    doc_loaders: Mapped[list[DocLoaderModel]] = relationship(
        "DocLoaderModel",
        back_populates="domain_model",
        cascade="all, delete-orphan",
        foreign_keys=[DocLoaderModel.domain_id],
    )

    @property
    def list_of_doc_loader_names(self) -> list:
        return [doc_loader.name for doc_loader in self.doc_loaders]

    doc_db_id: Mapped[int] = mapped_column(Integer, ForeignKey("doc_dbs.id"), nullable=True)
    enabled_doc_db = relationship("DocDBModel")

    DEFAULT_NAME: str = "default_domain_name"
    DEFAULT_TEMPLATE_NAME: str = "default_template_name"
    DEFAULT_DESCRIPTION: str = "A default domain description"
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str] = mapped_column(String, default=DEFAULT_DESCRIPTION)
    batch_update_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    documents: Mapped[list[DocumentModel]] = relationship(
        "DocumentModel",
        secondary="sources",
        primaryjoin="DomainModel.id==SourceModel.domain_id",
        secondaryjoin="SourceModel.id==DocumentModel.source_id",
        viewonly=True,
    )


class ContextIndexModel(Base):
    __tablename__ = "context_index_model"
    id: Mapped[int] = mapped_column(primary_key=True)

    current_domain_id: Mapped[int] = mapped_column(Integer, ForeignKey("domains.id"), nullable=True)
    current_domain = relationship("DomainModel", foreign_keys=[current_domain_id])
    domains: Mapped[list[DomainModel]] = relationship(
        "DomainModel",
        back_populates="context_index_model",
        cascade="all, delete-orphan",
        foreign_keys=[DomainModel.context_id],
    )

    doc_dbs: Mapped[list[DocDBModel]] = relationship(
        "DocDBModel",
        back_populates="context_index_model",
        foreign_keys="DocDBModel.context_id",
    )

    @property
    def list_of_doc_db_names(self) -> list:
        return [doc_db.name for doc_db in self.doc_dbs]

    index_context_templates: Mapped[list[ContextTemplateModel]] = relationship(
        "ContextTemplateModel",
        back_populates="context_index_model",
        foreign_keys=[ContextTemplateModel.context_id],
    )

    @property
    def list_of_context_template_names(self) -> list:
        return [
            index_context_template.name for index_context_template in self.index_context_templates
        ]
