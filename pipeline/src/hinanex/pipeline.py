from src.hinanex.adapters.base import SourceAdapter
from src.hinanex.models.common import NormalizedDataset


def run_adapter(adapter: SourceAdapter) -> NormalizedDataset:
    """Minimal pipeline: fetch -> raw preservation -> normalize."""
    raw = adapter.fetch()
    adapter.save_raw(raw)
    return adapter.normalize(raw)
