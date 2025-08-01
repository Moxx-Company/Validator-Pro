"""
File processing service for handling email lists
"""
import os
import tempfile
import pandas as pd
from typing import List, Dict, Tuple, Optional
from config import MAX_FILE_SIZE_MB, ALLOWED_FILE_EXTENSIONS
from utils import read_emails_from_file, create_results_csv, format_file_size
import uuid

class FileProcessor:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.max_file_size = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
    
    def validate_file(self, file_path: str, file_size: int) -> Tuple[bool, str]:
        """Validate uploaded file"""
        # Check file size
        if file_size > self.max_file_size:
            return False, f"File too large. Max size: {format_file_size(self.max_file_size)}"
        
        # Check file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in ALLOWED_FILE_EXTENSIONS:
            return False, f"Unsupported file type. Allowed: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
        
        # Check if file exists and is readable
        if not os.path.exists(file_path):
            return False, "File not found"
        
        try:
            with open(file_path, 'rb') as f:
                # Try to read first few bytes
                f.read(1024)
            return True, "File is valid"
        except Exception as e:
            return False, f"Cannot read file: {str(e)}"
    
    def process_uploaded_file(self, file_path: str) -> Tuple[List[str], Dict[str, any]]:
        """Process uploaded file and extract emails"""
        try:
            emails = read_emails_from_file(file_path)
            
            # Remove duplicates while preserving order
            unique_emails = []
            seen = set()
            for email in emails:
                if email.lower() not in seen:
                    unique_emails.append(email)
                    seen.add(email.lower())
            
            # Get file info
            file_info = {
                'original_count': len(emails),
                'unique_count': len(unique_emails),
                'duplicates_removed': len(emails) - len(unique_emails),
                'file_size': os.path.getsize(file_path),
                'file_extension': os.path.splitext(file_path)[1].lower()
            }
            
            return unique_emails, file_info
            
        except Exception as e:
            raise Exception(f"Failed to process file: {str(e)}")
    
    def create_temp_file(self, file_content: bytes, extension: str) -> str:
        """Create temporary file from content"""
        file_id = str(uuid.uuid4())
        temp_filename = f"upload_{file_id}{extension}"
        temp_path = os.path.join(self.temp_dir, temp_filename)
        
        try:
            with open(temp_path, 'wb') as f:
                f.write(file_content)
            return temp_path
        except Exception as e:
            raise Exception(f"Failed to create temp file: {str(e)}")
    
    def create_results_file(self, results: List[Dict], job_id: str, format_type: str = 'csv') -> str:
        """Create results file from validation results"""
        file_id = str(uuid.uuid4())
        
        if format_type.lower() == 'csv':
            filename = f"results_{job_id}_{file_id}.csv"
            file_path = os.path.join(self.temp_dir, filename)
            
            # Create DataFrame
            df = pd.DataFrame(results)
            
            # Reorder columns for better readability
            column_order = [
                'email', 'is_valid', 'syntax_valid', 'domain_exists', 
                'mx_record_exists', 'smtp_connectable', 'domain', 
                'mx_records', 'error_message', 'validation_time'
            ]
            
            # Only include columns that exist
            available_columns = [col for col in column_order if col in df.columns]
            df = df[available_columns]
            
            # Save to CSV
            df.to_csv(file_path, index=False, encoding='utf-8')
            
        elif format_type.lower() == 'excel':
            filename = f"results_{job_id}_{file_id}.xlsx"
            file_path = os.path.join(self.temp_dir, filename)
            
            # Create DataFrame
            df = pd.DataFrame(results)
            
            # Create Excel file with multiple sheets
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # All results sheet
                df.to_excel(writer, sheet_name='All Results', index=False)
                
                # Valid emails sheet
                valid_df = df[df['is_valid'] == True]
                if not valid_df.empty:
                    valid_df.to_excel(writer, sheet_name='Valid Emails', index=False)
                
                # Invalid emails sheet
                invalid_df = df[df['is_valid'] == False]
                if not invalid_df.empty:
                    invalid_df.to_excel(writer, sheet_name='Invalid Emails', index=False)
                
                # Summary sheet
                summary_data = {
                    'Metric': [
                        'Total Emails',
                        'Valid Emails', 
                        'Invalid Emails',
                        'Success Rate (%)',
                        'Average Validation Time (s)'
                    ],
                    'Value': [
                        len(df),
                        len(valid_df),
                        len(invalid_df),
                        round((len(valid_df) / len(df)) * 100, 2) if len(df) > 0 else 0,
                        round(df['validation_time'].mean(), 3) if 'validation_time' in df.columns else 0
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        return file_path
    
    def get_file_info(self, file_path: str) -> Dict[str, any]:
        """Get information about a file"""
        if not os.path.exists(file_path):
            return {'error': 'File not found'}
        
        try:
            stat = os.stat(file_path)
            return {
                'size': stat.st_size,
                'size_formatted': format_file_size(stat.st_size),
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'extension': os.path.splitext(file_path)[1].lower(),
                'filename': os.path.basename(file_path)
            }
        except Exception as e:
            return {'error': f'Cannot get file info: {str(e)}'}
    
    def cleanup_temp_file(self, file_path: str) -> bool:
        """Remove temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    def parse_email_list(self, text: str) -> List[str]:
        """Parse emails from text input"""
        import re
        
        # Extract email patterns from text
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Remove duplicates while preserving order
        unique_emails = []
        seen = set()
        for email in emails:
            if email.lower() not in seen:
                unique_emails.append(email)
                seen.add(email.lower())
        
        return unique_emails
