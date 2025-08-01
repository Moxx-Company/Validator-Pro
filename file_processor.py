"""
File processing service for handling email and phone lists
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
    
    def process_uploaded_file(self, file_path: str, validation_type: str = 'email') -> Tuple[List[str], Dict[str, any]]:
        """Process uploaded file and extract emails or phone numbers"""
        try:
            if validation_type == 'email':
                items = read_emails_from_file(file_path)
            else:
                # Read phone numbers from file
                items = self._read_phones_from_file(file_path)
            
            # Remove duplicates while preserving order
            unique_items = []
            seen = set()
            for item in items:
                item_lower = item.lower() if validation_type == 'email' else item
                if item_lower not in seen:
                    unique_items.append(item)
                    seen.add(item_lower)
            
            # Get file info
            file_info = {
                'original_count': len(items),
                'unique_count': len(unique_items),
                'duplicates_removed': len(items) - len(unique_items),
                'file_size': os.path.getsize(file_path),
                'file_extension': os.path.splitext(file_path)[1].lower()
            }
            
            return unique_items, file_info
            
        except Exception as e:
            raise Exception(f"Failed to process file: {str(e)}")
    
    def _read_phones_from_file(self, file_path: str) -> List[str]:
        """Read phone numbers from various file formats"""
        phones = []
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.csv':
                # Try to read CSV with pandas
                df = pd.read_csv(file_path)
                # Look for phone columns
                phone_columns = [col for col in df.columns if 'phone' in col.lower() or 'mobile' in col.lower() or 'cell' in col.lower()]
                
                if phone_columns:
                    # Use first phone column found
                    phones = df[phone_columns[0]].dropna().astype(str).tolist()
                else:
                    # Try first column
                    phones = df.iloc[:, 0].dropna().astype(str).tolist()
                    
            elif file_ext in ['.xlsx', '.xls']:
                # Read Excel file
                df = pd.read_excel(file_path)
                # Look for phone columns
                phone_columns = [col for col in df.columns if 'phone' in col.lower() or 'mobile' in col.lower() or 'cell' in col.lower()]
                
                if phone_columns:
                    phones = df[phone_columns[0]].dropna().astype(str).tolist()
                else:
                    # Try first column
                    phones = df.iloc[:, 0].dropna().astype(str).tolist()
                    
            else:
                # Read as text file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Split by newlines and filter empty lines
                    lines = [line.strip() for line in content.splitlines() if line.strip()]
                    phones = lines
            
            # Clean phone numbers (basic cleaning)
            cleaned_phones = []
            for phone in phones:
                # Remove common non-phone characters but keep + for international
                phone_str = str(phone).strip()
                # Only filter out completely empty strings - let validator handle length validation
                if phone_str:
                    cleaned_phones.append(phone_str)
            
            return cleaned_phones
            
        except Exception as e:
            raise Exception(f"Error reading phone numbers: {str(e)}")
    
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
            
            # Detect validation type and set appropriate column order
            if 'email' in df.columns:
                # Email validation columns
                column_order = [
                    'email', 'is_valid', 'syntax_valid', 'domain_exists', 
                    'mx_record_exists', 'smtp_connectable', 'domain', 
                    'mx_records', 'error_message', 'validation_time'
                ]
            elif 'number' in df.columns:
                # Phone validation columns
                column_order = [
                    'number', 'is_valid', 'formatted_international', 'formatted_national',
                    'country_code', 'country_name', 'carrier_name', 'number_type',
                    'timezones', 'error_message'
                ]
            else:
                # Fallback - use all available columns
                column_order = list(df.columns)
            
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
            
            # Detect validation type for proper labeling
            validation_type = "Emails" if 'email' in df.columns else "Phone Numbers"
            
            # Create Excel file with multiple sheets
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # All results sheet
                df.to_excel(writer, sheet_name='All Results', index=False)
                
                # Valid results sheet
                valid_df = df[df['is_valid'] == True]
                if not valid_df.empty:
                    valid_df.to_excel(writer, sheet_name=f'Valid {validation_type}', index=False)
                
                # Invalid results sheet
                invalid_df = df[df['is_valid'] == False]
                if not invalid_df.empty:
                    invalid_df.to_excel(writer, sheet_name=f'Invalid {validation_type}', index=False)
                
                # Summary sheet
                summary_data = {
                    'Metric': [
                        f'Total {validation_type}',
                        f'Valid {validation_type}', 
                        f'Invalid {validation_type}',
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
