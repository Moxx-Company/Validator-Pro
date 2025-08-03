"""
Progress tracking system for validation jobs
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Track progress of validation jobs with real-time updates"""
    
    def __init__(self):
        self.jobs: Dict[int, Dict[str, Any]] = {}
        self.cleanup_interval = 3600  # Clean up completed jobs after 1 hour
        
    def start_job(self, job_id: int, total_items: int, validation_type: str = 'email'):
        """Start tracking a validation job"""
        self.jobs[job_id] = {
            'job_id': job_id,
            'validation_type': validation_type,
            'total_items': total_items,
            'processed_items': 0,
            'valid_items': 0,
            'invalid_items': 0,
            'status': 'processing',
            'started_at': datetime.utcnow(),
            'last_update': datetime.utcnow(),
            'speed': 0.0,  # items per second
            'eta_seconds': 0,
            'error_message': None
        }
        logger.info(f"Started tracking job {job_id}: {validation_type} validation of {total_items} items")
    
    def update_progress(self, job_id: int, processed_items: int, valid_items: int = None, invalid_items: int = None):
        """Update job progress"""
        if job_id not in self.jobs:
            logger.warning(f"Job {job_id} not found in progress tracker")
            return
        
        job = self.jobs[job_id]
        now = datetime.utcnow()
        
        # Calculate speed
        time_elapsed = (now - job['started_at']).total_seconds()
        if time_elapsed > 0:
            job['speed'] = processed_items / time_elapsed
        
        # Calculate ETA
        remaining_items = job['total_items'] - processed_items
        if job['speed'] > 0:
            job['eta_seconds'] = remaining_items / job['speed']
        else:
            job['eta_seconds'] = 0
        
        # Update values
        job['processed_items'] = processed_items
        if valid_items is not None:
            job['valid_items'] = valid_items
        if invalid_items is not None:
            job['invalid_items'] = invalid_items
        job['last_update'] = now
        
        logger.debug(f"Job {job_id} progress: {processed_items}/{job['total_items']} ({job['speed']:.1f} items/sec)")
    
    def complete_job(self, job_id: int, success: bool = True, error_message: str = None):
        """Mark job as completed"""
        if job_id not in self.jobs:
            logger.warning(f"Job {job_id} not found in progress tracker")
            return
        
        job = self.jobs[job_id]
        job['status'] = 'completed' if success else 'failed'
        job['completed_at'] = datetime.utcnow()
        if error_message:
            job['error_message'] = error_message
        
        logger.info(f"Job {job_id} {'completed' if success else 'failed'}")
        
        # Schedule cleanup
        asyncio.create_task(self._cleanup_job_later(job_id))
    
    def get_progress(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get current progress for a job"""
        return self.jobs.get(job_id)
    
    def get_progress_percentage(self, job_id: int) -> float:
        """Get progress as percentage"""
        job = self.jobs.get(job_id)
        if not job or job['total_items'] == 0:
            return 0.0
        return (job['processed_items'] / job['total_items']) * 100
    
    def get_formatted_progress(self, job_id: int) -> str:
        """Get formatted progress string"""
        job = self.jobs.get(job_id)
        if not job:
            return "Progress not found"
        
        percentage = self.get_progress_percentage(job_id)
        progress_bar = self._create_progress_bar(percentage)
        
        # Format ETA
        eta_str = self._format_duration(int(job['eta_seconds'])) if job['eta_seconds'] > 0 else "Calculating..."
        
        return f"""🔄 {job['validation_type'].title()} Validation Progress

📊 Progress: {job['processed_items']}/{job['total_items']} ({percentage:.1f}%)
{progress_bar}

⚡ Speed: {job['speed']:.1f} items/second
⏱️ ETA: {eta_str}
✅ Valid: {job['valid_items']}
❌ Invalid: {job['invalid_items']}"""
    
    def _create_progress_bar(self, percentage: float, length: int = 10) -> str:
        """Create a visual progress bar"""
        filled = int(length * percentage / 100)
        empty = length - filled
        return "█" * filled + "░" * empty
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    async def _cleanup_job_later(self, job_id: int):
        """Clean up job after delay"""
        await asyncio.sleep(self.cleanup_interval)
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.debug(f"Cleaned up job {job_id} from progress tracker")
    
    def cleanup_old_jobs(self):
        """Clean up jobs older than cleanup interval"""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.cleanup_interval)
        
        jobs_to_remove = []
        for job_id, job in self.jobs.items():
            if job.get('completed_at') and job['completed_at'] < cutoff:
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.jobs[job_id]
            logger.debug(f"Cleaned up old job {job_id}")

# Global progress tracker instance
progress_tracker = ProgressTracker()