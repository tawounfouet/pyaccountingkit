from abc import ABC, abstractmethod
from pathlib import Path
class DocumentConverter(ABC):
    @abstractmethod
    def convert(self, source: Path, target: Path) -> Path: ...
