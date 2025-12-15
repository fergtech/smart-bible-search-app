"""
Centralized Structured Logging Module
Provides JSON-based logging for analytics and adaptive intelligence.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import time
import uuid

# Setup logging directory
# Use path that matches docker-compose volume mount: ./logs:/app/logs
LOG_DIR = Path("/app/logs")
LOG_DIR.mkdir(exist_ok=True, parents=True)

APP_LOG_FILE = LOG_DIR / "app.log"
ERROR_LOG_FILE = LOG_DIR / "errors.log"

# Configure standard Python logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StructuredLogger:
    """
    Structured JSON logger for all application events.
    Thread-safe, async-compatible, with error isolation.
    """
    
    def __init__(self, log_file: Path = APP_LOG_FILE):
        self.log_file = log_file
        self.session_id = str(uuid.uuid4())[:8]  # Unique session identifier
        
    def log_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Log a structured event to JSON lines file.
        
        Args:
            event_type: Type of event (e.g., 'search', 'commentary', 'error')
            data: Event-specific data dictionary
            session_id: Optional session identifier
            user_id: Optional user identifier
        """
        try:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'session_id': session_id or self.session_id,
                **data
            }
            
            if user_id:
                log_entry['user_id'] = user_id
            
            # Write to JSON lines file (atomic append)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
                f.flush()  # Ensure write
                
        except Exception as e:
            # Logging failure should never break the app
            import sys
            print(f"LOGGING ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            logger.error(f"Structured logging failed: {e}")
    
    def log_search(
        self,
        query: str,
        query_type: str,
        module: str,
        verses_retrieved: List[Dict],
        response_time: float,
        status: str = 'success',
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ):
        """Log a search request"""
        data = {
            'query': query,
            'query_normalized': query.lower().strip(),
            'query_type': query_type,  # 'keyword', 'semantic', 'chapter'
            'module': module,
            'verses_count': len(verses_retrieved),
            'verses': [
                {
                    'reference': v.get('reference'),
                    'book': v.get('book'),
                    'chapter': v.get('chapter'),
                    'verse': v.get('verse'),
                    'relevance_score': v.get('relevance_score')
                }
                for v in verses_retrieved[:10]  # Limit to top 10 for log size
            ],
            'response_time_ms': round(response_time * 1000, 2),
            'status': status,
            'tags': tags or []
        }
        
        self.log_event('search', data, session_id=session_id)
    
    def log_commentary(
        self,
        query: str,
        verses_used: List[Dict],
        commentary: str,
        commentary_mode: str,
        response_time: float,
        model_info: Optional[Dict] = None,
        status: str = 'success',
        session_id: Optional[str] = None
    ):
        """Log a commentary generation request"""
        data = {
            'query': query,
            'query_normalized': query.lower().strip(),
            'query_type': 'commentary',
            'module': 'commentary_summarizer',
            'commentary': commentary,
            'commentary_mode': commentary_mode,  # 'full', 'fallback', 'missing'
            'verses_count': len(verses_used),
            'verses': [
                {
                    'reference': v.get('reference'),
                    'book': v.get('book'),
                    'chapter': v.get('chapter'),
                    'verse': v.get('verse')
                }
                for v in verses_used[:10]
            ],
            'response_time_ms': round(response_time * 1000, 2),
            'status': status,
            'model_info': model_info or {}
        }
        
        self.log_event('commentary', data, session_id=session_id)
    
    def log_explain(
        self,
        verse_reference: str,
        explanation: str,
        response_time: float,
        status: str = 'success',
        session_id: Optional[str] = None
    ):
        """Log an explain request"""
        data = {
            'verse_reference': verse_reference,
            'query_type': 'explain',
            'module': 'explain',
            'explanation': explanation,
            'response_time_ms': round(response_time * 1000, 2),
            'status': status
        }
        
        self.log_event('explain', data, session_id=session_id)
    
    def log_chapter(
        self,
        book: str,
        chapter: int,
        verses_count: int,
        response_time: float,
        status: str = 'success',
        session_id: Optional[str] = None
    ):
        """Log a chapter view request"""
        data = {
            'book': book,
            'chapter': chapter,
            'query_type': 'chapter',
            'module': 'chapter_view',
            'verses_count': verses_count,
            'response_time_ms': round(response_time * 1000, 2),
            'status': status
        }
        
        self.log_event('chapter', data, session_id=session_id)
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None,
        session_id: Optional[str] = None
    ):
        """Log an error event"""
        data = {
            'error_type': error_type,
            'error_message': str(error_message),
            'context': context or {}
        }
        
        self.log_event('error', data, session_id=session_id)
        
        # Also write to error log file
        try:
            with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'timestamp': datetime.utcnow().isoformat(),
                    'session_id': session_id or self.session_id,
                    **data
                }) + '\n')
        except:
            pass
    
    def log_frontend_action(
        self,
        action: str,
        context: Dict[str, Any],
        session_id: Optional[str] = None
    ):
        """Log a frontend user action"""
        data = {
            'action': action,  # 'search_submitted', 'commentary_displayed', 'chapter_opened', etc.
            'context': context
        }
        
        self.log_event('frontend_action', data, session_id=session_id)


@contextmanager
def log_request_timing(logger_instance: StructuredLogger, operation: str):
    """
    Context manager for timing operations.
    
    Usage:
        with log_request_timing(app_logger, 'search'):
            # perform operation
            pass
    """
    start_time = time.time()
    try:
        yield start_time
    finally:
        elapsed = time.time() - start_time
        logger.debug(f"{operation} completed in {elapsed*1000:.2f}ms")


# Global logger instance
app_logger = StructuredLogger()


def get_logger() -> StructuredLogger:
    """Get the global structured logger instance"""
    return app_logger


# Convenience functions
def log_search(*args, **kwargs):
    """Convenience function for logging searches"""
    app_logger.log_search(*args, **kwargs)


def log_commentary(*args, **kwargs):
    """Convenience function for logging commentary"""
    app_logger.log_commentary(*args, **kwargs)


def log_explain(*args, **kwargs):
    """Convenience function for logging explanations"""
    app_logger.log_explain(*args, **kwargs)


def log_chapter(*args, **kwargs):
    """Convenience function for logging chapter views"""
    app_logger.log_chapter(*args, **kwargs)


def log_error(*args, **kwargs):
    """Convenience function for logging errors"""
    app_logger.log_error(*args, **kwargs)


def log_frontend_action(*args, **kwargs):
    """Convenience function for logging frontend actions"""
    app_logger.log_frontend_action(*args, **kwargs)
