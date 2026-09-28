from abc import ABC, abstractmethod

from src.hinanex.models.common import NormalizedDataset


class SourceAdapter(ABC):
    """Common interface for source-specific acquisition and normalization."""

    @abstractmethod
    def fetch(self) -> bytes:
        """Fetch the original source without transforming it."""
        raise NotImplementedError

    @abstractmethod
    def save_raw(self, raw: bytes) -> str:
        """Persist the original bytes and return the saved path."""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: bytes) -> NormalizedDataset:
        """Convert source-specific data into the HINANEX common schema."""
        raise NotImplementedError
