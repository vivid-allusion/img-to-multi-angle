"""
Batch monitoring for OpenRouter API batch operations.
Tracks batch status and handles completion detection.
"""

import time
from typing import Dict, Any, List
from loguru import logger
from openrouter import OpenRouter
from .batch_formatter import BatchStatusFormatter


class BatchMonitor:
    """Monitors batch processing status and completion."""
    
    def __init__(self, client: OpenRouter, config: Dict[str, Any]):
        """
        Initialize batch monitor.
        
        Args:
            client: OpenRouter API client
            config: Configuration dictionary with batch settings
        """
        self.client = client
        if "batch_config" not in config:
            raise ValueError("Missing 'batch_config' in configuration")
        self.batch_config = config["batch_config"]
        
    def check_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Check the status of a batch.
        
        Args:
            batch_id: The batch ID to check
            
        Returns:
            Dictionary with batch status information
        """
        try:
            batch = self.client.chat.completions.batch.retrieve(batch_id)
            
            request_count = 0
            completed_count = 0
            failed_count = 0
            
            if hasattr(batch, 'request_counts') and batch.request_counts:
                counts = batch.request_counts
                completed_count = getattr(counts, 'completed', 0) or 0
                failed_count = getattr(counts, 'failed', 0) or 0
                request_count = completed_count + failed_count
            
            status_info = {
                "id": batch.id,
                "processing_status": batch.status,
                "created_at": batch.created_at,
                "request_count": request_count,
                "completed_count": completed_count,
                "failed_count": failed_count,
                "is_complete": batch.status in ["completed", "failed", "expired"]
            }
            
            if hasattr(batch, 'completed_at') and batch.completed_at:
                status_info["ended_at"] = batch.completed_at
                
            return status_info
            
        except Exception as e:
            logger.error(f"Error checking batch status: {e}")
            raise
            
    def wait_for_completion(self, batch_id: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Wait for a batch to complete processing.
        
        Args:
            batch_id: The batch ID to monitor
            verbose: Whether to print progress updates
            
        Returns:
            Final batch status information
        """
        check_interval = self.batch_config["check_interval_minutes"] * 60
        max_wait_hours = self.batch_config["max_wait_hours"]
        max_wait_seconds = max_wait_hours * 3600
        
        start_time = time.time()
        last_status = None
        
        logger.info(f"🔄 Monitoring batch {batch_id}")
        logger.info(f"Check interval: {check_interval/60:.1f} minutes")
        logger.info(f"Max wait time: {max_wait_hours} hours")
        
        while True:
            try:
                status = self.check_batch_status(batch_id)
                
                if status["processing_status"] != last_status:
                    BatchStatusFormatter.log_status_change(status, verbose)
                    last_status = status["processing_status"]
                    
                if status["is_complete"]:
                    logger.success(f"✅ Batch {batch_id} completed!")
                    BatchStatusFormatter.log_completion_stats(status, start_time)
                    return status
                    
                elapsed = time.time() - start_time
                if elapsed > max_wait_seconds:
                    logger.warning(f"⏱️ Batch monitoring timed out after {max_wait_hours} hours")
                    logger.info("Batch may still be processing. Check status later.")
                    return status
                    
                if verbose:
                    remaining = max_wait_seconds - elapsed
                    msg = BatchStatusFormatter.format_progress_message(check_interval, remaining)
                    logger.info(msg)
                               
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring interrupted by user")
                return self.check_batch_status(batch_id)
            except Exception as e:
                logger.error(f"Error during monitoring: {e}")
                time.sleep(check_interval)
                
    def list_batches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List recent batches.
        
        Args:
            limit: Maximum number of batches to return
            
        Returns:
            List of batch information dictionaries
        """
        try:
            batches = []
            
            for batch in self.client.chat.completions.batch.list(limit=limit):
                batch_info = {
                    "id": batch.id,
                    "processing_status": batch.status,
                    "created_at": batch.created_at,
                    "request_count": getattr(batch.request_counts, 'total', None) if hasattr(batch, 'request_counts') else None
                }
                batches.append(batch_info)
                
            return batches
            
        except Exception as e:
            logger.error(f"Error listing batches: {e}")
            return []
            
    def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel an in-progress batch.
        
        Args:
            batch_id: The batch ID to cancel
            
        Returns:
            True if cancellation was successful
        """
        try:
            logger.info(f"Canceling batch {batch_id}...")
            batch = self.client.chat.completions.batch.cancel(batch_id)
            
            if batch.status in ["cancelling", "cancelled"]:
                logger.success(f"✅ Batch {batch_id} cancellation initiated")
                return True
            else:
                logger.warning(f"Batch status after cancel: {batch.status}")
                return False
                
        except Exception as e:
            logger.error(f"Error canceling batch: {e}")
            return False
            
    def delete_batch(self, batch_id: str) -> bool:
        """
        Delete a completed batch.
        
        Args:
            batch_id: The batch ID to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            logger.info(f"Deleting batch {batch_id}...")
            deleted = self.client.chat.completions.batch.delete(batch_id)
            
            if hasattr(deleted, 'id'):
                logger.success(f"✅ Batch {batch_id} deleted")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error deleting batch: {e}")
            return False
