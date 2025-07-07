import boto3
import os
from pathlib import Path
import tempfile
import logging
from typing import Optional, List, Dict
from botocore.exceptions import ClientError, NoCredentialsError
from config import Config

# Set up logging so we can see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class S3Handler:
    """
    Handles all S3 operations for MammalWeb image processing
    This class can download files from one bucket and upload to another
    """
    
    def __init__(self):
        """Initialize the S3 client with AWS credentials"""
        self.config = Config()
        
        try:
            # Create S3 client using credentials from .env file
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY,
                region_name=self.config.AWS_REGION
            )
            
            # Test the connection by listing buckets
            self.s3_client.list_buckets()
            logger.info("S3 connection successful!")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found! Check your .env file")
            raise
        except Exception as e:
            logger.error(f"S3 connection failed: {e}")
            raise
    
    def list_images_in_bucket(self, bucket_name: str, max_files: int = 100) -> List[Dict]:
        """
        List image files in a specific S3 bucket
        
        Args:
            bucket_name: Name of the S3 bucket
            max_files: Maximum number of files to return
            
        Returns:
            List of dictionaries with file information
        """
        try:
            logger.info(f"Listing images in bucket: {bucket_name}")
            
            # Use S3 client to list objects
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                MaxKeys=max_files
            )
            
            # Check if bucket has any files
            if 'Contents' not in response:
                logger.warning(f"No files found in bucket: {bucket_name}")
                return []
            
            # Filter for image files only
            image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp', '.bmp'}
            image_files = []
            
            for obj in response['Contents']:
                file_key = obj['Key']
                file_extension = Path(file_key).suffix.lower()
                
                # Only include image files
                if file_extension in image_extensions:
                    image_files.append({
                        'key': file_key,
                        'filename': Path(file_key).name,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'extension': file_extension
                    })
            
            logger.info(f"Found {len(image_files)} image files")
            return image_files
            
        except ClientError as e:
            logger.error(f"Error listing files in bucket {bucket_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []
    
    def download_file_from_s3(self, bucket_name: str, s3_key: str) -> Optional[Path]:
        """
        Download a file from S3 to local temporary storage
        
        Args:
            bucket_name: S3 bucket name
            s3_key: S3 object key (file path in bucket)
            
        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            # Create a temporary file with the same extension
            file_extension = Path(s3_key).suffix
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=file_extension,
                prefix="mammalweb_"
            )
            temp_path = Path(temp_file.name)
            temp_file.close()
            
            logger.info(f"Downloading s3://{bucket_name}/{s3_key}")
            logger.info(f"Saving to: {temp_path}")
            
            # Download the file
            self.s3_client.download_file(bucket_name, s3_key, str(temp_path))
            
            # Check if file was downloaded successfully
            if temp_path.exists() and temp_path.stat().st_size > 0:
                logger.info(f"Downloaded successfully: {temp_path.stat().st_size} bytes")
                return temp_path
            else:
                logger.error("Downloaded file is empty or doesn't exist")
                return None
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.error(f"File not found: s3://{bucket_name}/{s3_key}")
            elif error_code == 'NoSuchBucket':
                logger.error(f"Bucket not found: {bucket_name}")
            else:
                logger.error(f"AWS error downloading file: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
    
    def upload_file_to_s3(self, local_file_path: Path, bucket_name: str, s3_key: str) -> bool:
        """
        Upload a local file to S3
        
        Args:
            local_file_path: Path to local file
            bucket_name: Destination S3 bucket
            s3_key: S3 key (path) for the uploaded file
            
        Returns:
            True if successful, error otherwise
        """
        try:
            if not local_file_path.exists():
                logger.error(f"Local file not found: {local_file_path}")
                return False
            
            logger.info(f"⬆️ Uploading {local_file_path} to s3://{bucket_name}/{s3_key}")
            
            # Determine content type based on file extension
            content_type = self._get_content_type(local_file_path.suffix)
            
            # Prepare upload arguments
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            # Upload the file
            self.s3_client.upload_file(
                str(local_file_path),
                bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Upload successful: s3://{bucket_name}/{s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"AWS error uploading file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False
    
    def file_exists_in_s3(self, bucket_name: str, s3_key: str) -> bool:
        """
        Check if a file exists in S3
        
        Args:
            bucket_name: S3 bucket name
            s3_key: S3 object key
            
        Returns:
            True if file exists, error otherwise
        """
        try:
            self.s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"Error checking if file exists: {e}")
                return False
    
    def get_file_size(self, bucket_name: str, s3_key: str) -> Optional[int]:
        """
        Get the size of a file in S3
        
        Args:
            bucket_name: S3 bucket name
            s3_key: S3 object key
            
        Returns:
            File size in bytes, or None if error
        """
        try:
            response = self.s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            return response['ContentLength']
        except ClientError as e:
            logger.error(f"Error getting file size: {e}")
            return None
    
    def _get_content_type(self, file_extension: str) -> Optional[str]:
        """
        Get MIME content type based on file extension
        
        Args:
            file_extension: File extension (e.g., '.jpg')
            
        Returns:
            MIME type string
        """
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.bmp': 'image/bmp'
        }
        
        return content_types.get(file_extension.lower())
    
    def cleanup_temp_file(self, file_path: Path):
        """
        Delete a temporary file
        
        Args:
            file_path: Path to file to delete
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not delete temp file {file_path}: {e}")