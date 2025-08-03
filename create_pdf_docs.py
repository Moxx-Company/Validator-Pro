#!/usr/bin/env python3
"""
PDF Documentation Generator
Converts Markdown handover documents to PDF format
"""

import markdown
from weasyprint import HTML, CSS
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def markdown_to_pdf(markdown_file, output_pdf, title="Documentation"):
    """Convert a Markdown file to PDF with professional styling"""
    
    try:
        # Read the markdown file
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Convert Markdown to HTML
        md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc'])
        html_content = md.convert(markdown_content)
        
        # Create a complete HTML document with styling
        html_document = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                @page {{
                    size: A4;
                    margin: 2cm;
                    @bottom-center {{
                        content: "Page " counter(page) " of " counter(pages);
                        font-size: 10pt;
                        color: #666;
                    }}
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: none;
                    margin: 0;
                    font-size: 11pt;
                }}
                
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                    margin-top: 30px;
                    font-size: 24pt;
                    page-break-before: auto;
                }}
                
                h2 {{
                    color: #34495e;
                    border-bottom: 2px solid #ecf0f1;
                    padding-bottom: 8px;
                    margin-top: 25px;
                    font-size: 18pt;
                }}
                
                h3 {{
                    color: #2c3e50;
                    margin-top: 20px;
                    font-size: 14pt;
                }}
                
                h4 {{
                    color: #7f8c8d;
                    margin-top: 15px;
                    font-size: 12pt;
                }}
                
                code {{
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 3px;
                    padding: 2px 4px;
                    font-family: 'Monaco', 'Consolas', monospace;
                    font-size: 10pt;
                    color: #d63384;
                }}
                
                pre {{
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 6px;
                    padding: 15px;
                    overflow-x: auto;
                    margin: 15px 0;
                    font-family: 'Monaco', 'Consolas', monospace;
                    font-size: 9pt;
                    line-height: 1.4;
                }}
                
                pre code {{
                    background: none;
                    border: none;
                    padding: 0;
                    color: #333;
                }}
                
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 15px 0;
                    font-size: 10pt;
                }}
                
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                
                ul, ol {{
                    margin: 10px 0;
                    padding-left: 25px;
                }}
                
                li {{
                    margin: 5px 0;
                }}
                
                blockquote {{
                    border-left: 4px solid #3498db;
                    margin: 15px 0;
                    padding: 10px 20px;
                    background-color: #f8f9fa;
                    font-style: italic;
                }}
                
                .status-badge {{
                    background-color: #28a745;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 10pt;
                    font-weight: bold;
                }}
                
                .warning {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    padding: 10px;
                    margin: 10px 0;
                }}
                
                .info {{
                    background-color: #d1ecf1;
                    border: 1px solid #bee5eb;
                    border-radius: 4px;
                    padding: 10px;
                    margin: 10px 0;
                }}
                
                a {{
                    color: #3498db;
                    text-decoration: none;
                }}
                
                a:hover {{
                    text-decoration: underline;
                }}
                
                .page-break {{
                    page-break-before: always;
                }}
                
                .no-break {{
                    page-break-inside: avoid;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Generate PDF
        logger.info(f"Converting {markdown_file} to PDF...")
        HTML(string=html_document).write_pdf(output_pdf)
        logger.info(f"PDF created successfully: {output_pdf}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error converting {markdown_file} to PDF: {str(e)}")
        return False

def main():
    """Generate PDF versions of all documentation files"""
    
    docs_to_convert = [
        {
            'markdown': 'HANDOVER_DOCUMENT.md',
            'pdf': 'HANDOVER_DOCUMENT.pdf',
            'title': 'Validator Pro Bot - Developer Handover Document'
        },
        {
            'markdown': 'PRODUCTION_ENVIRONMENT.md', 
            'pdf': 'PRODUCTION_ENVIRONMENT.pdf',
            'title': 'Validator Pro Bot - Production Environment Configuration'
        },
        {
            'markdown': 'DEPLOYMENT_GUIDE.md',
            'pdf': 'DEPLOYMENT_GUIDE.pdf', 
            'title': 'Validator Pro Bot - Deployment Guide'
        }
    ]
    
    successful_conversions = 0
    total_conversions = 0
    
    for doc in docs_to_convert:
        markdown_path = Path(doc['markdown'])
        
        # Check if markdown file exists
        if not markdown_path.exists():
            logger.warning(f"Markdown file not found: {markdown_path}")
            continue
            
        total_conversions += 1
        
        # Convert to PDF
        if markdown_to_pdf(doc['markdown'], doc['pdf'], doc['title']):
            successful_conversions += 1
            print(f"✅ Created: {doc['pdf']}")
        else:
            print(f"❌ Failed: {doc['pdf']}")
    
    print(f"\n📊 Conversion Summary:")
    print(f"   Total documents: {total_conversions}")
    print(f"   Successful: {successful_conversions}")
    print(f"   Failed: {total_conversions - successful_conversions}")
    
    if successful_conversions > 0:
        print(f"\n🎉 PDF documentation created successfully!")
        print(f"   Files are ready for download and distribution.")

if __name__ == "__main__":
    main()