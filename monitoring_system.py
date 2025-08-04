"""
Comprehensive Monitoring System for Large-Scale Deployment
Real-time performance tracking and alerting for 5000+ users
"""
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass
from collections import defaultdict, deque
import threading
import json

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    active_connections: int
    validation_queue_size: int
    processing_rate_per_minute: float
    error_rate_percent: float
    average_response_time: float

class SystemMonitor:
    """
    Real-time system monitoring for production deployment
    Tracks performance, detects issues, provides alerts
    """
    
    def __init__(self):
        self.metrics_history: deque = deque(maxlen=1440)  # 24 hours of minute-by-minute data
        self.validation_stats = defaultdict(int)
        self.response_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.start_time = datetime.now()
        self.monitoring_active = False
        self._lock = threading.Lock()
        
    def start_monitoring(self):
        """Start background monitoring thread"""
        if not self.monitoring_active:
            self.monitoring_active = True
            monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            monitor_thread.start()
            logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        logger.info("System monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                metrics = self._collect_metrics()
                with self._lock:
                    self.metrics_history.append(metrics)
                
                # Check for alerts
                self._check_alerts(metrics)
                
                time.sleep(60)  # Collect metrics every minute
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(60)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current system metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Get database connection count (approximate)
        active_connections = self._get_active_connections()
        
        # Calculate processing rate
        processing_rate = self._calculate_processing_rate()
        
        # Calculate error rate
        error_rate = self._calculate_error_rate()
        
        # Get average response time
        avg_response_time = self._get_average_response_time()
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            active_connections=active_connections,
            validation_queue_size=self.validation_stats.get('queue_size', 0),
            processing_rate_per_minute=processing_rate,
            error_rate_percent=error_rate,
            average_response_time=avg_response_time
        )
    
    def _get_active_connections(self) -> int:
        """Estimate active database connections"""
        try:
            connections = [conn for conn in psutil.net_connections() 
                          if conn.status == 'ESTABLISHED']
            return len(connections)
        except:
            return 0
    
    def _calculate_processing_rate(self) -> float:
        """Calculate validations per minute"""
        if len(self.metrics_history) < 2:
            return 0.0
        
        recent_validations = sum(self.validation_stats.get(f'minute_{i}', 0) 
                               for i in range(5))  # Last 5 minutes
        return recent_validations / 5.0
    
    def _calculate_error_rate(self) -> float:
        """Calculate error percentage"""
        total_requests = sum(self.validation_stats.get(f'total_{i}', 0) 
                           for i in range(5))
        total_errors = sum(self.error_counts.get(f'minute_{i}', 0) 
                         for i in range(5))
        
        if total_requests == 0:
            return 0.0
        return (total_errors / total_requests) * 100
    
    def _get_average_response_time(self) -> float:
        """Get average response time in seconds"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    def _check_alerts(self, metrics: PerformanceMetrics):
        """Check for alert conditions"""
        alerts = []
        
        # High CPU usage
        if metrics.cpu_percent > 80:
            alerts.append(f"HIGH CPU: {metrics.cpu_percent:.1f}%")
        
        # High memory usage  
        if metrics.memory_percent > 85:
            alerts.append(f"HIGH MEMORY: {metrics.memory_percent:.1f}%")
        
        # High error rate
        if metrics.error_rate_percent > 5:
            alerts.append(f"HIGH ERROR RATE: {metrics.error_rate_percent:.1f}%")
        
        # Slow response times
        if metrics.average_response_time > 10:
            alerts.append(f"SLOW RESPONSES: {metrics.average_response_time:.1f}s avg")
        
        # Large queue size
        if metrics.validation_queue_size > 1000:
            alerts.append(f"LARGE QUEUE: {metrics.validation_queue_size} pending")
        
        if alerts:
            alert_msg = f"⚠️ SYSTEM ALERTS: {'; '.join(alerts)}"
            logger.warning(alert_msg)
            # Could send to monitoring service or Telegram admin here
    
    def record_validation(self, validation_type: str, response_time: float, success: bool):
        """Record a validation event"""
        with self._lock:
            minute_key = datetime.now().strftime('%Y%m%d%H%M')
            self.validation_stats[f'total_{minute_key}'] += 1
            self.validation_stats[f'{validation_type}_{minute_key}'] += 1
            
            self.response_times.append(response_time)
            
            if not success:
                self.error_counts[f'minute_{minute_key}'] += 1
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive system dashboard data"""
        with self._lock:
            current_metrics = self.metrics_history[-1] if self.metrics_history else None
            
            uptime = datetime.now() - self.start_time
            
            return {
                'system_status': 'healthy' if current_metrics and current_metrics.cpu_percent < 80 else 'warning',
                'uptime_hours': uptime.total_seconds() / 3600,
                'current_metrics': current_metrics.__dict__ if current_metrics else {},
                'total_validations': sum(self.validation_stats.get(f'total_{k}', 0) 
                                       for k in self.validation_stats.keys() if k.startswith('total_')),
                'avg_response_time': self._get_average_response_time(),
                'error_rate': self._calculate_error_rate(),
                'processing_rate': self._calculate_processing_rate(),
                'metrics_history': [m.__dict__ for m in list(self.metrics_history)[-60:]]  # Last hour
            }

class ValidationPerformanceTracker:
    """
    Track validation performance specifically
    Optimizes for large-scale phone/email validation
    """
    
    def __init__(self):
        self.phone_validation_times = deque(maxlen=1000)
        self.email_validation_times = deque(maxlen=1000)
        self.country_success_rates = defaultdict(list)
        self.domain_success_rates = defaultdict(list)
        
    def record_phone_validation(self, country_code: str, validation_time: float, success: bool):
        """Record phone validation performance"""
        self.phone_validation_times.append(validation_time)
        self.country_success_rates[country_code].append(success)
        
        # Keep only recent data
        if len(self.country_success_rates[country_code]) > 100:
            self.country_success_rates[country_code] = self.country_success_rates[country_code][-100:]
    
    def record_email_validation(self, domain: str, validation_time: float, success: bool):
        """Record email validation performance"""
        self.email_validation_times.append(validation_time)
        self.domain_success_rates[domain].append(success)
        
        # Keep only recent data
        if len(self.domain_success_rates[domain]) > 100:
            self.domain_success_rates[domain] = self.domain_success_rates[domain][-100:]
    
    def get_phone_performance_stats(self) -> Dict[str, Any]:
        """Get phone validation performance statistics"""
        if not self.phone_validation_times:
            return {'status': 'no_data'}
        
        times = list(self.phone_validation_times)
        country_stats = {}
        
        for country, successes in self.country_success_rates.items():
            if successes:
                success_rate = sum(successes) / len(successes) * 100
                country_stats[country] = {
                    'success_rate': success_rate,
                    'sample_size': len(successes)
                }
        
        return {
            'avg_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'p95_time': sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times),
            'total_validations': len(times),
            'country_performance': country_stats
        }
    
    def get_email_performance_stats(self) -> Dict[str, Any]:
        """Get email validation performance statistics"""
        if not self.email_validation_times:
            return {'status': 'no_data'}
        
        times = list(self.email_validation_times)
        domain_stats = {}
        
        for domain, successes in self.domain_success_rates.items():
            if successes:
                success_rate = sum(successes) / len(successes) * 100
                domain_stats[domain] = {
                    'success_rate': success_rate,
                    'sample_size': len(successes)
                }
        
        return {
            'avg_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'p95_time': sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times),
            'total_validations': len(times),
            'domain_performance': domain_stats
        }

# Global monitoring instances
system_monitor = SystemMonitor()
performance_tracker = ValidationPerformanceTracker()

def start_monitoring():
    """Initialize all monitoring systems"""
    system_monitor.start_monitoring()
    logger.info("All monitoring systems started")

def get_comprehensive_status() -> Dict[str, Any]:
    """Get complete system status for admin dashboard"""
    return {
        'system': system_monitor.get_dashboard_data(),
        'phone_performance': performance_tracker.get_phone_performance_stats(),
        'email_performance': performance_tracker.get_email_performance_stats(),
        'timestamp': datetime.now().isoformat()
    }