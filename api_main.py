from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
import logging
from pathlib import Path
import asyncio
from datetime import datetime
import sys

from config import Config
from s3_handler import S3Handler

# Ensure the current directory is in the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from services.compression_service import CompressionService
from compressors.Image_compressor import ImageCompressor

#logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MammalWeb Image Compression API",
    description="API for processing images from S3 buckets",
    version="1.0.0"
)

# Load configuration
config = Config()

# Initialize compression service
compression_service = CompressionService(output_dir="temp_compressed")
image_compressor = ImageCompressor(output_dir="temp_compressed")

# Initialize S3 handler (this will be created when first endpoint is called)
s3_handler = None

def get_s3_handler():
    """Get or create S3 handler instance"""
    global s3_handler
    if s3_handler is None:
        try:
            s3_handler = S3Handler()
            logger.info("S3 Handler initialized")
        except Exception as e:
            logger.error(f"Failed to initialize S3 Handler: {e}")
            raise HTTPException(status_code=500, detail=f"S3 connection failed: {str(e)}")
    return s3_handler

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "MammalWeb Image Processing API", 
        "status": "running",
        "version": "1.0.0",
        "source_bucket": config.SOURCE_BUCKET,
        "dest_bucket": config.DEST_BUCKET,
        "endpoints": {
            "health": "/health",
            "list_images": "/images/list",
            "process_image": "/images/process/{image_key}",
            "batch_process": "/images/batch-process",
            "compression_stats": "/compression/stats"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test S3 connection
        s3 = get_s3_handler()
        
        # Try to list one file to verify connection
        files = s3.list_images_in_bucket(config.SOURCE_BUCKET, max_files=1)
        
        return {
            "status": "healthy",
            "s3_connection": "ok",
            "source_bucket": config.SOURCE_BUCKET,
            "dest_bucket": config.DEST_BUCKET,
            "compression_available": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"S3 connection error: {str(e)}")

@app.get("/images/list")
async def list_images(
    max_files: int = Query(50, description="Maximum number of files to return", ge=1, le=1000),
    file_type: Optional[str] = Query(None, description="Filter by file extension (e.g., jpg, png)")
):
    """
    Ai descriptions
    List all image files in the source S3 bucket
    
    Args:
        max_files: Maximum number of files to return (1-1000)
        file_type: Optional filter by file extension
    
    Returns:
        List of image files with metadata
    """
    try:
        logger.info(f"Listing images (max: {max_files}, type: {file_type})")
        
        s3 = get_s3_handler()
        files = s3.list_images_in_bucket(config.SOURCE_BUCKET, max_files=max_files)
        
        # Filter by file type if specified
        if file_type:
            file_extension = f".{file_type.lower().lstrip('.')}"
            files = [f for f in files if f['extension'] == file_extension]
        
        return {
            "success": True,
            "bucket": config.SOURCE_BUCKET,
            "total_files": len(files),
            "max_requested": max_files,
            "file_type_filter": file_type,
            "files": files
        }
        
    except Exception as e:
        logger.error(f"Error listing images: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list images: {str(e)}")

@app.post("/images/process/{image_key:path}")
async def process_single_image(
    image_key: str,
    background_tasks: BackgroundTasks,
    compress: bool = Query(True, description="Whether to compress the image"),
    quality: str = Query("medium", description="Compression quality: low, medium, high")
):
    """
    Process a single image: download from source bucket, optionally compress, upload to destination bucket
    
    Args:
        image_key: S3 key (path) of the image to process
        compress: Whether to apply compression
        quality: Compression quality level
    
    Returns:
        Processing result
    """
    try:
        logger.info(f"Processing image: {image_key}")
        
        s3 = get_s3_handler()
        
        # Validate quality parameter
        if quality not in ["low", "medium", "high"]:
            raise HTTPException(status_code=400, detail="Quality must be 'low', 'medium', or 'high'")
        
        # Check if file exists in source bucket
        if not s3.file_exists_in_s3(config.SOURCE_BUCKET, image_key):
            raise HTTPException(status_code=404, detail=f"Image not found: {image_key}")
        
        # Check if already processed
        dest_key = f"compressed/{image_key}" if compress else f"copied/{image_key}"
        if s3.file_exists_in_s3(config.DEST_BUCKET, dest_key):
            return {
                "success": True,
                "message": "Image already processed",
                "source_key": image_key,
                "dest_key": dest_key,
                "action": "skipped",
                "compressed": compress
            }
        
        # Add background task for processing
        background_tasks.add_task(
            process_image_background,
            image_key, compress, quality
        )
        
        return {
            "success": True,
            "message": "Image processing started",
            "source_key": image_key,
            "dest_key": dest_key,
            "action": "processing",
            "compressed": compress,
            "quality": quality
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image {image_key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")

@app.post("/images/batch-process")
async def batch_process_images(
    background_tasks: BackgroundTasks,
    max_files: int = Query(10, description="Maximum number of files to process", ge=1, le=100),
    file_type: Optional[str] = Query(None, description="Filter by file extension"),
    compress: bool = Query(True, description="Whether to compress images"),
    quality: str = Query("medium", description="Compression quality")
):
    """
    Process multiple images in batch
    
    Args:
        max_files: Maximum number of files to process in this batch
        file_type: Optional filter by file extension
        compress: Whether to apply compression
        quality: Compression quality level
    
    Returns:
        Batch processing status
    """
    try:
        logger.info(f"Starting batch processing (max: {max_files}, type: {file_type})")
        
        # Validate quality parameter
        if quality not in ["low", "medium", "high"]:
            raise HTTPException(status_code=400, detail="Quality must be 'low', 'medium', or 'high'")
        
        s3 = get_s3_handler()
        
        # list of files to process
        files = s3.list_images_in_bucket(config.SOURCE_BUCKET, max_files=max_files)
        
        # Filter by file type if specified
        if file_type:
            file_extension = f".{file_type.lower().lstrip('.')}"
            files = [f for f in files if f['extension'] == file_extension]
        
        if not files:
            return {
                "success": True,
                "message": "No files found to process",
                "files_found": 0,
                "files_queued": 0
            }
        
        # Filter out already processed files
        files_to_process = []
        for file in files:
            dest_key = f"compressed/{file['key']}" if compress else f"copied/{file['key']}"
            if not s3.file_exists_in_s3(config.DEST_BUCKET, dest_key):
                files_to_process.append(file['key'])
        
        # Add background tasks for each file
        for image_key in files_to_process:
            background_tasks.add_task(
                process_image_background,
                image_key, compress, quality
            )
        
        return {
            "success": True,
            "message": f"Batch processing started for {len(files_to_process)} files",
            "files_found": len(files),
            "files_queued": len(files_to_process),
            "files_already_processed": len(files) - len(files_to_process),
            "compress": compress,
            "quality": quality
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

@app.get("/images/status/{image_key:path}")
async def get_image_status(image_key: str):
    """
    Check the processing status of an image
    
    Args:
        image_key: S3 key of the image
    
    Returns:
        Status information
    """
    try:
        s3 = get_s3_handler()
        
        # Check source
        source_exists = s3.file_exists_in_s3(config.SOURCE_BUCKET, image_key)
        if not source_exists:
            raise HTTPException(status_code=404, detail="Image not found in source bucket")
        
        # Check destination (both compressed and copied versions)
        compressed_key = f"compressed/{image_key}"
        copied_key = f"copied/{image_key}"
        
        compressed_exists = s3.file_exists_in_s3(config.DEST_BUCKET, compressed_key)
        copied_exists = s3.file_exists_in_s3(config.DEST_BUCKET, copied_key)
        
        # Get file sizes
        source_size = s3.get_file_size(config.SOURCE_BUCKET, image_key)
        
        result = {
            "image_key": image_key,
            "source_exists": source_exists,
            "source_size": source_size,
            "processed": compressed_exists or copied_exists,
            "compressed_version_exists": compressed_exists,
            "copied_version_exists": copied_exists
        }
        
        if compressed_exists:
            result["compressed_size"] = s3.get_file_size(config.DEST_BUCKET, compressed_key)
            if source_size and result["compressed_size"]:
                result["compression_ratio"] = round(
                    (1 - result["compressed_size"] / source_size) * 100, 2
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking status for {image_key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check status: {str(e)}")

@app.get("/compression/stats")
async def get_compression_stats():
    """
    Get compression statistics and supported formats
    
    Returns:
        Information about compression capabilities
    """
    try:
        return {
            "success": True,
            "compression_service": {
                "supported_image_formats": list(image_compressor.config.IMAGE_FORMATS),
                "compression_methods": ["FFmpeg", "PIL"],
                "quality_levels": ["low", "medium", "high"],
                "features": {
                    "jpeg_optimization": True,
                    "png_compression": True,
                    "lossless_webp": True,
                    "progressive_jpeg": True
                }
            },
            "current_settings": {
                "jpeg_quality": image_compressor.config.JPEG_QUALITY,
                "png_compression_level": image_compressor.config.PNG_COMPRESSION_LEVEL,
                "ffmpeg_quality": image_compressor.config.FFMPEG_IMAGE_QUALITY
            }
        }
    except Exception as e:
        logger.error(f"Error getting compression stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

async def process_image_background(image_key: str, compress: bool, quality: str):
    """
    Background task to process an image with compression
    Runs asynchronously and doesn't block the API response
    """
    try:
        logger.info(f"Background processing: {image_key}")
        
        s3 = get_s3_handler()
        
        # Download from source bucket
        logger.info(f"Downloading {image_key}...")
        temp_file = s3.download_file_from_s3(config.SOURCE_BUCKET, image_key)
        
        if not temp_file:
            logger.error(f"Failed to download {image_key}")
            return
        
        processed_file = temp_file
        original_size = temp_file.stat().st_size
        
        # Apply compression if requested
        if compress:
            logger.info(f"Compressing {image_key} with {quality} quality...")
            
            try:
                # Use your existing compression logic
                compressed_file = await apply_compression(temp_file, quality)
                
                if compressed_file and compressed_file.exists():
                    processed_file = compressed_file
                    compressed_size = compressed_file.stat().st_size
                    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
                    
                    logger.info(f"Compression successful:")
                    logger.info(f"  Original: {original_size:,} bytes")
                    logger.info(f"  Compressed: {compressed_size:,} bytes")
                    logger.info(f"  Reduction: {compression_ratio:.1f}%")
                else:
                    logger.warning(f"Compression failed, using original file")
                    processed_file = temp_file
                    
            except Exception as e:
                logger.error(f"Compression error for {image_key}: {e}")
                logger.info("Using original file instead")
                processed_file = temp_file
        
        # Upload to destination bucket
        dest_key = f"compressed/{image_key}" if compress else f"copied/{image_key}"
        logger.info(f"Uploading to {dest_key}...")
        
        upload_success = s3.upload_file_to_s3(processed_file, config.DEST_BUCKET, dest_key)
        
        if upload_success:
            logger.info(f"Successfully processed {image_key}")
            
            #final statistics
            final_size = processed_file.stat().st_size
            if compress and final_size != original_size:
                ratio = (1 - final_size / original_size) * 100
                logger.info(f"Final compression ratio: {ratio:.1f}%")
        else:
            logger.error(f"Failed to upload {image_key}")
        
        #  Cleanup temporary files
        s3.cleanup_temp_file(temp_file)
        if processed_file != temp_file:
            s3.cleanup_temp_file(processed_file)
            
    except Exception as e:
        logger.error(f"Background processing failed for {image_key}: {e}")

async def apply_compression(input_file: Path, quality: str) -> Optional[Path]:
    """
    Apply compression to an image file using your existing compression logic
    
    Args:
        input_file: Path to the input image file
        quality: Compression quality level (low, medium, high)
    
    Returns:
        Path to compressed file or None if compression failed
    """
    try:
        # Adjust compression settings based on quality level
        if quality == "low":
            # More aggressive compression
            image_compressor.config.JPEG_QUALITY = 75
            image_compressor.config.PNG_COMPRESSION_LEVEL = 9
            image_compressor.config.FFMPEG_IMAGE_QUALITY = 3
        elif quality == "medium":
            # Balanced compression
            image_compressor.config.JPEG_QUALITY = 85
            image_compressor.config.PNG_COMPRESSION_LEVEL = 6
            image_compressor.config.FFMPEG_IMAGE_QUALITY = 2
        elif quality == "high":
            # Light compression, preserve quality
            image_compressor.config.JPEG_QUALITY = 95
            image_compressor.config.PNG_COMPRESSION_LEVEL = 3
            image_compressor.config.FFMPEG_IMAGE_QUALITY = 1
        else:
            # Default to medium
            quality = "medium"
        
        logger.info(f"Applying {quality} quality compression")
        
        # Use your existing compression service
        compressed_path = image_compressor.compress(input_file)
        
        if compressed_path and compressed_path.exists():
            logger.info(f"Compression completed: {compressed_path}")
            return compressed_path
        else:
            logger.warning("Compression returned no result")
            return None
            
    except Exception as e:
        logger.error(f"Error in compression: {e}")
        return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)