# token_usage_manager.py
"""
Token Usage Tracking and Management System
Tracks and displays token usage for project generation and code assistant
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class TokenUsage:
    """Token usage information"""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    timestamp: float
    operation_type: str  # "project_generation", "code_assistant", "file_analysis"
    project_id: Optional[str] = None
    model: str = "claude-sonnet-4-5-20250929"
    cost_estimate: float = 0.0
    
    def __post_init__(self):
        if self.cost_estimate == 0.0:
            # Approximate cost calculation (adjust based on actual pricing)
            # These are example rates - update with actual Claude pricing
            input_rate = 0.003 / 1000  # $0.003 per 1K input tokens
            output_rate = 0.015 / 1000  # $0.015 per 1K output tokens
            
            self.cost_estimate = (
                (self.input_tokens * input_rate) + 
                (self.output_tokens * output_rate)
            )

class TokenUsageManager:
    """Manages token usage tracking and storage"""
    
    def __init__(self, storage_dir: str = "token_usage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.usage_file = self.storage_dir / "token_usage.json"
        self.project_usage_file = self.storage_dir / "project_usage.json"
        
        # In-memory caches
        self._daily_usage = {}
        self._project_usage = {}
        
        self._load_usage_data()
    
    def _load_usage_data(self):
        """Load existing usage data"""
        try:
            if self.usage_file.exists():
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                    self._daily_usage = data.get('daily_usage', {})
            
            if self.project_usage_file.exists():
                with open(self.project_usage_file, 'r') as f:
                    self._project_usage = json.load(f)
        except Exception as e:
            print(f"[DEBUG] Error loading token usage data: {e}")
    
    def _save_usage_data(self):
        """Save usage data to files"""
        try:
            # Save daily usage
            with open(self.usage_file, 'w') as f:
                json.dump({
                    'daily_usage': self._daily_usage,
                    'last_updated': time.time()
                }, f, indent=2)
            
            # Save project usage
            with open(self.project_usage_file, 'w') as f:
                json.dump(self._project_usage, f, indent=2)
        except Exception as e:
            print(f"[DEBUG] Error saving token usage data: {e}")
    
    def record_usage(self, input_tokens: int, output_tokens: int, 
                    operation_type: str, project_id: Optional[str] = None,
                    model: str = "claude-sonnet-4-5-20250929") -> TokenUsage:
        """Record token usage"""
        
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            timestamp=time.time(),
            operation_type=operation_type,
            project_id=project_id,
            model=model
        )
        
        # Record daily usage
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self._daily_usage:
            self._daily_usage[today] = {
                'total_tokens': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'operations': {},
                'cost_estimate': 0.0
            }
        
        day_data = self._daily_usage[today]
        day_data['total_tokens'] += usage.total_tokens
        day_data['input_tokens'] += usage.input_tokens
        day_data['output_tokens'] += usage.output_tokens
        day_data['cost_estimate'] += usage.cost_estimate
        
        if operation_type not in day_data['operations']:
            day_data['operations'][operation_type] = {
                'count': 0,
                'total_tokens': 0,
                'cost': 0.0
            }
        
        day_data['operations'][operation_type]['count'] += 1
        day_data['operations'][operation_type]['total_tokens'] += usage.total_tokens
        day_data['operations'][operation_type]['cost'] += usage.cost_estimate
        
        # Record project-specific usage
        if project_id:
            if project_id not in self._project_usage:
                self._project_usage[project_id] = {
                    'total_tokens': 0,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'cost_estimate': 0.0,
                    'operations': [],
                    'created_at': usage.timestamp
                }
            
            project_data = self._project_usage[project_id]
            project_data['total_tokens'] += usage.total_tokens
            project_data['input_tokens'] += usage.input_tokens
            project_data['output_tokens'] += usage.output_tokens
            project_data['cost_estimate'] += usage.cost_estimate
            
            # Store detailed operation record
            project_data['operations'].append(asdict(usage))
            
            # Keep only last 50 operations per project
            if len(project_data['operations']) > 50:
                project_data['operations'] = project_data['operations'][-50:]
        
        self._save_usage_data()
        return usage
    
    def get_project_usage(self, project_id: str) -> Dict[str, Any]:
        """Get usage statistics for a specific project"""
        if project_id not in self._project_usage:
            return {
                'project_id': project_id,
                'total_tokens': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'cost_estimate': 0.0,
                'operations_count': 0,
                'operations': []
            }
        
        data = self._project_usage[project_id].copy()
        data['project_id'] = project_id
        data['operations_count'] = len(data['operations'])
        
        # Calculate operations breakdown
        ops_breakdown = {}
        for op in data['operations']:
            op_type = op['operation_type']
            if op_type not in ops_breakdown:
                ops_breakdown[op_type] = {
                    'count': 0,
                    'tokens': 0,
                    'cost': 0.0
                }
            ops_breakdown[op_type]['count'] += 1
            ops_breakdown[op_type]['tokens'] += op['total_tokens']
            ops_breakdown[op_type]['cost'] += op['cost_estimate']
        
        data['operations_breakdown'] = ops_breakdown
        return data
    
    def get_daily_usage(self, days: int = 7) -> Dict[str, Any]:
        """Get daily usage statistics"""
        result = {}
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            if date in self._daily_usage:
                result[date] = self._daily_usage[date]
            else:
                result[date] = {
                    'total_tokens': 0,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'operations': {},
                    'cost_estimate': 0.0
                }
        
        return result
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get overall usage summary"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Today's usage
        today_usage = self._daily_usage.get(today, {
            'total_tokens': 0,
            'cost_estimate': 0.0
        })
        
        # Total usage (all projects)
        total_tokens = 0
        total_cost = 0.0
        total_projects = len(self._project_usage)
        
        for project_data in self._project_usage.values():
            total_tokens += project_data['total_tokens']
            total_cost += project_data['cost_estimate']
        
        # Last 7 days
        weekly_tokens = 0
        weekly_cost = 0.0
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            if date in self._daily_usage:
                day_data = self._daily_usage[date]
                weekly_tokens += day_data['total_tokens']
                weekly_cost += day_data['cost_estimate']
        
        return {
            'today': {
                'tokens': today_usage['total_tokens'],
                'cost': today_usage['cost_estimate']
            },
            'last_7_days': {
                'tokens': weekly_tokens,
                'cost': weekly_cost
            },
            'total': {
                'tokens': total_tokens,
                'cost': total_cost,
                'projects': total_projects
            }
        }
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old usage data"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        # Remove old daily usage
        dates_to_remove = []
        for date_str in self._daily_usage.keys():
            if date_str < cutoff_str:
                dates_to_remove.append(date_str)
        
        for date_str in dates_to_remove:
            del self._daily_usage[date_str]
        
        # Clean up old project operations
        cutoff_timestamp = cutoff_date.timestamp()
        for project_id, project_data in self._project_usage.items():
            project_data['operations'] = [
                op for op in project_data['operations']
                if op['timestamp'] > cutoff_timestamp
            ]
        
        self._save_usage_data()
        print(f"[DEBUG] Cleaned up token usage data older than {days_to_keep} days")

# Global token usage manager instance
global_token_manager = TokenUsageManager()


# Helper function to extract token usage from Anthropic response
def extract_token_usage(response_message) -> tuple[int, int]:
    """Extract token usage from Anthropic API response"""
    try:
        if hasattr(response_message, 'usage'):
            return (
                response_message.usage.input_tokens,
                response_message.usage.output_tokens
            )
    except Exception as e:
        print(f"[DEBUG] Could not extract token usage: {e}")
    
    return (0, 0)  # Fallback if usage not available