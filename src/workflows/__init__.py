"""LlamaIndex Workflows integration."""

# Avoid importing heavy/optional dependencies at package import time.
# Consumers should import the required symbols directly from document_workflow.

__all__ = [
    "DocumentProcessingWorkflow",
    "process_document_with_workflow",
]
