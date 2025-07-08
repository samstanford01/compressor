from pathlib import Path
from config import Config as BaseConfig

class CompressionConfig(BaseConfig):
    """configuration for compression settings"""
    
    def __init__(self):
        super().__init__()
        
        # Compression quality presets
        self.IMAGE_FORMATS = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.webp', '.bmp'}
        self.VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
        
        # Compression settings
        self.JPEG_QUALITY = 85
        self.PNG_COMPRESSION_LEVEL = 6
        self.FFMPEG_IMAGE_QUALITY = 2
        self.FFMPEG_VIDEO_PRESET = 'medium'
        self.VIDEO_CRF = 23
        self.VIDEO_AUDIO_BITRATE = '96k'
        self.MAX_FILE_SIZE_FOR_SKIP = 5_000_000
        
        # Temp directories
        self.TEMP_INPUT_DIR = Path("temp_input")
        self.TEMP_OUTPUT_DIR = Path("temp_output")
        
        # Create temp directories
        self.TEMP_INPUT_DIR.mkdir(exist_ok=True)
        self.TEMP_OUTPUT_DIR.mkdir(exist_ok=True)
        
        # File size limits (in bytes)
        self.MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
        self.MIN_COMPRESSION_SAVING = 0.05  # 5% minimum savings to keep compressed version