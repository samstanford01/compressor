from pathlib import Path
from config import Config as BaseConfig

class CompressionConfig(BaseConfig):
    """Configuration for compression settings"""
    
    def __init__(self):
        super().__init__()
        
        # REQUIRED: File format definitions
        self.IMAGE_FORMATS = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.webp', '.bmp'}
        self.VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
        
        # REQUIRED: Compression settings
        self.JPEG_QUALITY = 85
        self.PNG_COMPRESSION_LEVEL = 6
        self.FFMPEG_IMAGE_QUALITY = 2
        self.FFMPEG_VIDEO_PRESET = 'medium'
        self.VIDEO_CRF = 23
        self.VIDEO_AUDIO_BITRATE = '96k'
        self.MAX_FILE_SIZE_FOR_SKIP = 5_000_000  # 5MB
        
        # Compression quality presets
        self.QUALITY_PRESETS = {
            "low": {
                "jpeg_quality": 75,
                "png_compression": 9,
                "ffmpeg_quality": 3,
                "description": "Maximum compression, smaller files"
            },
            "medium": {
                "jpeg_quality": 85,
                "png_compression": 6,
                "ffmpeg_quality": 2,
                "description": "Balanced compression and quality"
            },
            "high": {
                "jpeg_quality": 95,
                "png_compression": 3,
                "ffmpeg_quality": 1,
                "description": "Light compression, preserve quality"
            }
        }
        
        # Temp directories
        self.TEMP_INPUT_DIR = Path("temp_input")
        self.TEMP_OUTPUT_DIR = Path("temp_output")
        
        # Create temp directories
        self.TEMP_INPUT_DIR.mkdir(exist_ok=True)
        self.TEMP_OUTPUT_DIR.mkdir(exist_ok=True)
        
        # File size limits (in bytes)
        self.MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
        self.MIN_COMPRESSION_SAVING = 0.05  # 5% minimum savings to keep compressed version