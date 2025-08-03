"""
File serving module for validation results
"""
import os
import csv
import json
import logging
from datetime import datetime
from io import StringIO
from typing import List, Dict, Any
from flask import Flask, Response, request, jsonify, send_file
from database import SessionLocal
from models import ValidationJob, ValidationResult, User
from config import ADMIN_CHAT_ID

logger = logging.getLogger(__name__)

# Create Flask app for file serving
file_server = Flask(__name__)

def create_results_csv(results: List[ValidationResult], validation_type: str = 'email') -> str:
    """Create CSV content from validation results"""
    output = StringIO()
    
    if validation_type == 'email':
        fieldnames = [
            'email', 'is_valid', 'syntax_valid', 'domain_exists', 
            'mx_record_exists', 'smtp_connectable', 'error_message', 'mx_records'
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                'email': result.email or '',
                'is_valid': 'Yes' if result.is_valid else 'No',
                'syntax_valid': 'Yes' if result.syntax_valid else 'No',
                'domain_exists': 'Yes' if result.domain_exists else 'No',
                'mx_record_exists': 'Yes' if result.mx_record_exists else 'No',
                'smtp_connectable': 'Yes' if result.smtp_connectable else 'No',
                'error_message': result.error_message or '',
                'mx_records': result.mx_records or ''
            })
    else:  # phone
        fieldnames = [
            'phone_number', 'is_valid', 'formatted_international', 'formatted_national',
            'country_code', 'country_name', 'carrier', 'number_type', 'timezone', 'error_message'
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                'phone_number': result.phone_number or '',
                'is_valid': 'Yes' if result.is_valid else 'No',
                'formatted_international': result.formatted_international or '',
                'formatted_national': result.formatted_national or '',
                'country_code': result.country_code or '',
                'country_name': result.country_name or '',
                'carrier': result.carrier or '',
                'number_type': result.number_type or '',
                'timezone': result.timezone or '',
                'error_message': result.error_message or ''
            })
    
    return output.getvalue()

@file_server.route('/download/<int:job_id>')
def download_validation_results(job_id: int):
    """Download validation results as CSV"""
    try:
        # Get user_id from request parameter
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id parameter'}), 400
        
        with SessionLocal() as db:
            # Verify job belongs to user or user is admin
            job = db.query(ValidationJob).filter(
                ValidationJob.id == job_id,
                ValidationJob.user_id == int(user_id)
            ).first()
            
            if not job:
                return jsonify({'error': 'Job not found or access denied'}), 404
            
            # Get results
            results = db.query(ValidationResult).filter(
                ValidationResult.job_id == job_id
            ).all()
            
            if not results:
                return jsonify({'error': 'No results found'}), 404
            
            # Determine validation type
            validation_type = job.validation_type or 'email'
            
            # Create CSV content
            csv_content = create_results_csv(results, validation_type)
            
            # Create filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{validation_type}_validation_results_{timestamp}.csv"
            
            # Return CSV file
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment;filename={filename}'}
            )
            
    except Exception as e:
        logger.error(f"Error downloading results for job {job_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_server.route('/job/<int:job_id>/summary')
def get_job_summary(job_id: int):
    """Get job summary as JSON"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id parameter'}), 400
        
        with SessionLocal() as db:
            job = db.query(ValidationJob).filter(
                ValidationJob.id == job_id,
                ValidationJob.user_id == int(user_id)
            ).first()
            
            if not job:
                return jsonify({'error': 'Job not found or access denied'}), 404
            
            # Get results summary
            results = db.query(ValidationResult).filter(
                ValidationResult.job_id == job_id
            ).all()
            
            valid_count = sum(1 for r in results if r.is_valid)
            invalid_count = len(results) - valid_count
            
            return jsonify({
                'job_id': job.id,
                'filename': job.filename,
                'validation_type': job.validation_type or 'email',
                'status': job.status,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'total_items': len(results),
                'valid_items': valid_count,
                'invalid_items': invalid_count,
                'success_rate': (valid_count / len(results) * 100) if results else 0
            })
            
    except Exception as e:
        logger.error(f"Error getting job summary for {job_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_server.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

def run_file_server():
    """Run the file server"""
    try:
        file_server.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Error starting file server: {e}")

if __name__ == '__main__':
    run_file_server()