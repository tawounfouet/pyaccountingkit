from abc import ABC, abstractmethod
from pathlib import Path
class AccountExtractor(ABC):
    @abstractmethod
    def extract(self, source: Path, document_id: str): ...
