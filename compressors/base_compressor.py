#Abstract base class for all compressors

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
import os

class BaseCompressor(ABC):
    #Abstract base class for file compressors
    
    def __init__(self, output_dir: str = "compressed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    #Compress a file and return the path to the compressed file
    @abstractmethod
    def compress(self, input_path: Path) -> Optional[Path]:
        pass
    #check format
    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        pass
    
    #compression results
    def get_file_size(self, filepath: Path) -> int:
        
        return os.path.getsize(filepath)
    def calculate_compression_ratio(self, original_size: int, compressed_size: int) -> float:
    
        if original_size == 0:
            return 0
        return (1 - compressed_size / original_size) * 100
    

    def get_output_path(self, input_path: Path, prefix: str = "compressed_") -> Path:
        return self.output_dir / f"{prefix}{input_path.name}"
    
    #Print compression statistics
    def print_compression_stats(self, input_path: Path, output_path: Path, method: str = ""):
        
        original_size = self.get_file_size(input_path)
        compressed_size = self.get_file_size(output_path)
        ratio = self.calculate_compression_ratio(original_size, compressed_size)
        
        method_str = f" ({method})" if method else ""
        print(f" File compressed{method_str}: {input_path.name}")
        print(f"  Original: {original_size:,} bytes")
        print(f"  Compressed: {compressed_size:,} bytes")
        print(f"  Reduction: {ratio:.1f}%")