import boto3
from botocore.exceptions import ClientError
from typing import Optional
import io
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    """S3-compatible storage service"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize S3 client if credentials are available"""
        if settings.s3_access_key and settings.s3_secret_key:
            try:
                self.client = boto3.client(
                    's3',
                    endpoint_url=settings.s3_endpoint_url,
                    aws_access_key_id=settings.s3_access_key,
                    aws_secret_access_key=settings.s3_secret_key
                )
                logger.info("S3 client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}")
    
    def store_document(self, content: bytes, filename: str) -> Optional[str]:
        """
        Store document in S3 storage.
        Returns: storage_path or None if failed
        """
        if not self.client:
            logger.warning("S3 client not available, skipping storage")
            return None
        
        try:
            key = f"documents/{filename}"
            
            self.client.put_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Body=content,
                ContentType='application/pdf'
            )
            
            storage_path = f"s3://{settings.s3_bucket}/{key}"
            logger.info(f"Document stored at: {storage_path}")
            return storage_path
            
        except ClientError as e:
            logger.error(f"Error storing document: {e}")
            return None
    
    def get_document_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """Generate presigned URL for document access"""
        if not self.client or not storage_path.startswith('s3://'):
            return None
        
        try:
            # Extract bucket and key from storage_path
            path_parts = storage_path.replace('s3://', '').split('/', 1)
            if len(path_parts) != 2:
                return None
            
            bucket, key = path_parts
            
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None

# Global storage service instance
storage_service = StorageService()