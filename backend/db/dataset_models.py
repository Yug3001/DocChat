from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.sql import func
from .database import Base

class DatasetRegistry(Base):
    __tablename__ = "dataset_registry"

    dataset_id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source_type = Column(String(10), nullable=False)  # "CSV" or "MYSQL"
    connection_details = Column(JSON, nullable=True)
    schema_snapshot = Column(JSON, nullable=True)
    row_count = Column(Integer, default=0)
    display_name = Column(String(255), nullable=False)
    version = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())
    status = Column(String(10), default="ACTIVE")  # "ACTIVE", "SYNCING", "ERROR"

class MutationLog(Base):
    __tablename__ = "mutation_log"

    mutation_id = Column(String(36), primary_key=True)
    dataset_id = Column(String(36), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    operation_type = Column(String(30), nullable=False)
    description = Column(String(500), nullable=False)
    forward_sql = Column(Text, nullable=False)
    reverse_sql = Column(Text, nullable=True)
    rows_affected = Column(Integer, default=0)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    reversible_flag = Column(Boolean, default=False)

class QueryCache(Base):
    __tablename__ = "query_cache"

    cache_key = Column(String(64), primary_key=True)
    dataset_id = Column(String(36), nullable=False, index=True)
    natural_language_query = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=False)
    result_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
