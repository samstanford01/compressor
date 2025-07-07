#Image compression using FFmpeg and PIL
import subprocess
from pathlib import Path
from typing import Optional
from PIL import Image, ImageFile
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from compressors.base_compressor import BaseCompressor
from compresssor_config import CompressionConfig


# Allow loading of truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

class ImageCompressor(BaseCompressor):
    #Handles compression of image files
    
    def __init__(self, output_dir: str = "compressed"):
        super().__init__(output_dir)
        self.config = CompressionConfig()
    
    def supports_format(self, file_extension: str) -> bool:
        
        return file_extension.lower() in self.config.IMAGE_FORMATS
    
    def compress(self, input_path: Path) -> Optional[Path]:
        #Compress an image file
        if not self.supports_format(input_path.suffix):
            print(f"Unsupported image format: {input_path.suffix}")
            return None
        
        output_path = self.get_output_path(input_path)
        
        # Try FFmpeg first, fallback to PIL
        if self._compress_with_ffmpeg(input_path, output_path):
            self.print_compression_stats(input_path, output_path, "FFmpeg")
            return output_path
        
        # Fallback to PIL
        print(f"FFmpeg failed, trying PIL for: {input_path.name}")
        result = self._compress_with_pil(input_path, output_path)
        if result:
            self.print_compression_stats(input_path, output_path, "PIL")
        return result
    
    def _compress_with_ffmpeg(self, input_path: Path, output_path: Path) -> bool:
        #Compress using FFmpeg
        try:
            file_ext = input_path.suffix.lower()
            
            if file_ext in ['.jpg', '.jpeg']:
                cmd = [
                    'ffmpeg', '-i', str(input_path),
                    '-c:v', 'mjpeg',
                    '-q:v', str(self.config.FFMPEG_IMAGE_QUALITY),
                    '-huffman', 'optimal',
                    '-y', str(output_path)
                ]
            elif file_ext == '.png':
                cmd = [
                    'ffmpeg', '-i', str(input_path),
                    '-c:v', 'png',
                    '-compression_level', str(self.config.PNG_COMPRESSION_LEVEL),
                    '-pred', 'mixed',
                    '-y', str(output_path)
                ]
            elif file_ext == '.webp':
                cmd = [
                    'ffmpeg', '-i', str(input_path),
                    '-c:v', 'libwebp',
                    '-lossless', '1',
                    '-compression_level', '6',
                    '-y', str(output_path)
                ]
            else:
                return False
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except FileNotFoundError:
            return False
        except Exception:
            return False
    
    def _compress_with_pil(self, input_path: Path, output_path: Path) -> Optional[Path]:
        #Compress using PIL as fallback
        try:
            with Image.open(input_path) as img:
                # Convert RGBA to RGB if saving as JPEG
                if input_path.suffix.lower() in ['.jpg', '.jpeg'] and img.mode == 'RGBA':
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1])
                    img = rgb_img
                
                # Format-specific compression settings
                if input_path.suffix.lower() == '.png':
                    img.save(output_path, 'PNG', optimize=True, 
                            compress_level=self.config.PNG_COMPRESSION_LEVEL)
                elif input_path.suffix.lower() in ['.jpg', '.jpeg']:
                    img.save(output_path, 'JPEG', optimize=True, progressive=True)
                elif input_path.suffix.lower() in ['.tiff', '.tif']:
                    img.save(output_path, 'TIFF', compression='lzw')
                elif input_path.suffix.lower() == '.webp':
                    img.save(output_path, 'WebP', lossless=True, quality=100)
                else:
                    img.save(output_path, optimize=True)
            
            return output_path
            
        except Exception as e:
            print(f"PIL compression failed for {input_path.name}: {str(e)}")
            return None