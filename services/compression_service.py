#main compression service

from pathlib import Path
from typing import Dict, List, Optional, Any

from compressors.Image_compressor import ImageCompressor
from compressors.video_compressor import VideoCompressor

class CompressionService:
    #handles compression of files and directories using multiple compressors
    
    def __init__(self, output_dir: str = "compressed"):
        self.output_dir = output_dir
        self.compressors = [
            ImageCompressor(output_dir),
            VideoCompressor(output_dir)
        ]
    
    def compress_file(self, input_path: Path) -> Optional[Path]:
        #compress a single file
        if not input_path.exists():
            print(f"File not found: {input_path}")
            return None
        
        for compressor in self.compressors:
            if compressor.supports_format(input_path.suffix):
                return compressor.compress(input_path)
        
        print(f"Unsupported file format: {input_path.suffix}")
        return None
    
    def compress_directory(self, directory: Path) -> List[Dict[str, Any]]:
        #Compress all files in a directory
        if not directory.exists():
            print(f"Directory not found: {directory}")
            return []
        
        print(f"Processing directory: {directory}")
        results = []
        
        for filepath in directory.iterdir():
            if filepath.is_file():
                original_size = filepath.stat().st_size if filepath.exists() else 0
                
                result_path = self.compress_file(filepath)
                
                if result_path:
                    compressed_size = result_path.stat().st_size
                    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
                    
                    results.append({
                        'input_file': str(filepath),
                        'output_file': str(result_path),
                        'original_size': original_size,
                        'compressed_size': compressed_size,
                        'compression_ratio': compression_ratio,
                        'success': True
                    })
                else:
                    results.append({
                        'input_file': str(filepath),
                        'output_file': None,
                        'success': False
                    })
        
        return results
    
    def compress_multiple_files(self, input_paths: List[Path]) -> List[Dict[str, Any]]:
        #Compress multiple files
        results = []
        
        for input_path in input_paths:
            if input_path.is_file():
                original_size = input_path.stat().st_size if input_path.exists() else 0
                
                result_path = self.compress_file(input_path)
                
                if result_path:
                    compressed_size = result_path.stat().st_size
                    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
                    
                    results.append({
                        'input_file': str(input_path),
                        'output_file': str(result_path),
                        'original_size': original_size,
                        'compressed_size': compressed_size,
                        'compression_ratio': compression_ratio,
                        'success': True
                    })
                else:
                    results.append({
                        'input_file': str(input_path),
                        'output_file': None,
                        'success': False
                    })
            elif input_path.is_dir():
                # Process directory
                dir_results = self.compress_directory(input_path)
                results.extend(dir_results)
        
        return results