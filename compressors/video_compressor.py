#Video compression using FFmpeg

import subprocess
import shutil
from pathlib import Path
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from Compressors.base_compressor import BaseCompressor
from config import CompressionConfig



class VideoCompressor(BaseCompressor):
   #video file compressor using FFmpeg
    
    def __init__(self, output_dir: str = "compressed"):
        super().__init__(output_dir)
        self.config = CompressionConfig()
    
    def supports_format(self, file_extension: str) -> bool:
        #Check video format valid
        return file_extension.lower() in self.config.VIDEO_FORMATS
    
    def compress(self, input_path: Path) -> Optional[Path]:
        #video copmression
        if not self.supports_format(input_path.suffix):
            print(f"Unsupported video format: {input_path.suffix}")
            return None
        
        return self._intelligent_compression(input_path)
    
    #Smart compression: stream copy, skip small files or re-encode
    def _intelligent_compression(self, input_path: Path) -> Optional[Path]:
        
        try:
            original_size = self.get_file_size(input_path)
            output_path = self.get_output_path(input_path, "compressed_")
            
            # First try: Stream copy (re-container without re-encoding)
            print(f"Trying stream copy for: {input_path.name}")
            if self._try_stream_copy(input_path, output_path, original_size):
                return output_path
            
            # Check if file is small enough to skip re-encoding
            if original_size < self.config.MAX_FILE_SIZE_FOR_SKIP:
                print(f"File is already small ({original_size:,} bytes), copying without compression")
                output_path_copy = self.get_output_path(input_path, "")
                shutil.copy2(input_path, output_path_copy)
                
                print(f" Video copied (no compression needed): {input_path.name}")
                print(f"Original: {original_size:,} bytes")
                print(f"Output: {original_size:,} bytes")
                print(f"Note: File already efficiently compressed")
                
                return output_path_copy
            
            # Re-encode for larger files
            return self._reencode_video(input_path, output_path)
            
        except Exception as e:
            print(f"Error compressing video {input_path.name}: {str(e)}")
            return None
    
    #stream copy compression
    def _try_stream_copy(self, input_path: Path, output_path: Path, original_size: int) -> bool:
        
        try:
            cmd = [
                'ffmpeg', '-i', str(input_path),
                '-c', 'copy',
                '-avoid_negative_ts', 'make_zero',
                '-y', str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                copy_size = self.get_file_size(output_path)
                if copy_size < original_size:
                    self.print_compression_stats(input_path, output_path, "stream copy")
                    return True
            
            return False
            
        except Exception:
            return False
        



    #Re-encode video for compression
    def _reencode_video(self, input_path: Path, output_path: Path) -> Optional[Path]:
        
        try:
            print(f"Re-encoding video: {input_path.name}")
            
            cmd = [
                'ffmpeg', '-i', str(input_path),
                '-c:v', 'libx264',
                '-preset', self.config.FFMPEG_VIDEO_PRESET,
                '-crf', str(self.config.VIDEO_CRF),
                '-c:a', 'aac',
                '-b:a', self.config.VIDEO_AUDIO_BITRATE,
                '-movflags', '+faststart',
                '-y', str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.print_compression_stats(input_path, output_path, "re-encoded")
                return output_path
            else:
                print(f"FFmpeg error: {result.stderr}")
                return None
                
        except FileNotFoundError:
            print("FFmpeg not found. Please install FFmpeg for video compression.")
            return None
        except Exception as e:
            print(f"Re-encoding failed: {str(e)}")
            return None