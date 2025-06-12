import os
import sys
import json
from datetime import datetime
import PyPDF2
from io import BytesIO

# 👇 This tells Python to look inside 'src/'
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from oracle_epm_support.crew import build_crew
from flask import Flask, request, render_template_string, make_response
from rag_knowledge_manager import RAGKnowledgeManager

# Configure CrewAI to use Anthropic
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")

app = Flask(__name__)

# RAG Knowledge Base - Oracle EPM Documentation and Common Issues
KNOWLEDGE_BASE = {
    "fccs_issues": [
        {
            "id": "fccs_001",
            "title": "Consolidation Rules Not Executing",
            "content": "Common causes: 1) Missing or incorrect elimination rules 2) Entity hierarchy issues 3) Ownership percentages not defined 4) Period status not set to 'Ready for Consolidation'",
            "keywords": ["consolidation", "rules", "elimination", "not executing", "not working"],
            "module": "FCCS"
        },
        {
            "id": "fccs_002", 
            "title": "Intercompany Elimination Issues",
            "content": "Check: 1) IC partner mapping 2) Account dimension setup 3) IC data quality 4) Matching tolerance settings 5) Currency conversion timing",
            "keywords": ["intercompany", "elimination", "IC", "matching", "partner"],
            "module": "FCCS"
        },
        {
            "id": "fccs_003",
            "title": "Currency Translation Problems",
            "content": "Verify: 1) Exchange rates loaded 2) Translation methods assigned 3) Rate type configuration 4) Historical rate setup for equity accounts",
            "keywords": ["currency", "translation", "exchange rates", "FX", "historical"],
            "module": "FCCS"
        }
    ],
    "epbcs_issues": [
        {
            "id": "epbcs_001",
            "title": "Business Rules Failing",
            "content": "Debug steps: 1) Check syntax in rule editor 2) Verify dimension member references 3) Review calculation order 4) Check security permissions 5) Validate data forms",
            "keywords": ["business rules", "failing", "error", "calculation", "syntax"],
            "module": "EPBCS"
        },
        {
            "id": "epbcs_002",
            "title": "Data Form Performance Issues",
            "content": "Optimize: 1) Reduce form scope 2) Use dynamic members sparingly 3) Implement conditional formatting 4) Review page/POV settings 5) Enable smart push",
            "keywords": ["data form", "performance", "slow", "optimization", "scope"],
            "module": "EPBCS"
        },
        {
            "id": "epbcs_003",
            "title": "Approval Workflow Problems",
            "content": "Troubleshoot: 1) Check planning unit assignments 2) Verify reviewer hierarchy 3) Review approval status 4) Check notification settings 5) Validate security roles",
            "keywords": ["approval", "workflow", "planning unit", "reviewer", "notification"],
            "module": "EPBCS"
        }
    ],
    "essbase_issues": [
        {
            "id": "ess_001",
            "title": "Slow Calculation Performance",
            "content": "Optimize: 1) Review calculation order 2) Use FIXPARALLEL for dense calcs 3) Implement calc scripts vs business rules 4) Check data sparsity 5) Consider ASO vs BSO",
            "keywords": ["calculation", "performance", "slow", "optimization", "parallel"],
            "module": "Essbase"
        },
        {
            "id": "ess_002",
            "title": "Outline Restructure Issues",
            "content": "Best practices: 1) Backup before restructure 2) Check member relationships 3) Review aliases and UDAs 4) Validate data integrity 5) Test calc scripts",
            "keywords": ["outline", "restructure", "member", "hierarchy", "backup"],
            "module": "Essbase"
        }
    ],
    "workforce_issues": [
        {
            "id": "wfp_001",
            "title": "Salary Forecast Calculation Issues",
            "content": "Review: 1) Merit increase assumptions 2) Promotion timing 3) Benefits allocation 4) Headcount driver relationships 5) Salary grade mappings",
            "keywords": ["salary", "forecast", "merit", "promotion", "benefits"],
            "module": "Workforce"
        }
    ],
    "general_issues": [
        {
            "id": "gen_001",
            "title": "Data Integration Problems",
            "content": "Common fixes: 1) Check Data Management connections 2) Verify mapping tables 3) Review error logs 4) Validate source data 5) Check security permissions",
            "keywords": ["data integration", "data management", "mapping", "connection", "error"],
            "module": "General"
        },
        {
            "id": "gen_002",
            "title": "Performance Tuning Best Practices",
            "content": "Optimize: 1) Review application design 2) Implement caching 3) Use parallel processing 4) Monitor system resources 5) Regular maintenance tasks",
            "keywords": ["performance", "tuning", "optimization", "slow", "resources"],
            "module": "General"
        }
    ]
}

def search_knowledge_base(query, max_results=3):
    """Search the knowledge base for relevant documents based on query keywords"""
    query_lower = query.lower()
    results = []
    
    # Search through all categories
    for category, documents in KNOWLEDGE_BASE.items():
        for doc in documents:
            score = 0
            # Check title match
            if any(word in doc['title'].lower() for word in query_lower.split()):
                score += 3
            
            # Check keyword match
            for keyword in doc['keywords']:
                if keyword in query_lower:
                    score += 2
            
            # Check content match
            if any(word in doc['content'].lower() for word in query_lower.split() if len(word) > 3):
                score += 1
            
            if score > 0:
                results.append({
                    'doc': doc,
                    'score': score,
                    'category': category
                })
    
    # Sort by relevance score and return top results
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:max_results]

def extract_text_from_pdf(pdf_file):
    """Extract text content from uploaded PDF file with detailed validation"""
    try:
        # Read PDF content
        pdf_content = pdf_file.read()
        if len(pdf_content) == 0:
            raise ValueError("PDF file is empty")
        
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
        
        # Check if PDF is encrypted
        if pdf_reader.is_encrypted:
            raise ValueError("PDF is password protected and cannot be read")
        
        # Check number of pages
        num_pages = len(pdf_reader.pages)
        if num_pages == 0:
            raise ValueError("PDF contains no pages")
        
        text_content = ""
        pages_with_text = 0
        
        for page_num in range(num_pages):
            try:
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text.strip():
                    text_content += f"[Page {page_num + 1}]\n{page_text}\n\n"
                    pages_with_text += 1
            except Exception as page_error:
                print(f"Warning: Could not extract text from page {page_num + 1}: {page_error}")
                continue
        
        if pages_with_text == 0:
            raise ValueError(f"No readable text found in any of the {num_pages} pages. PDF may contain only images or scanned content.")
        
        return text_content.strip()
        
    except Exception as e:
        raise Exception(f"PDF processing failed: {str(e)}")

def format_rag_context(search_results):
    """Format search results into context for the AI agents"""
    if not search_results:
        return ""
    
    context = "\n=== RELEVANT KNOWLEDGE BASE ARTICLES ===\n"
    for i, result in enumerate(search_results, 1):
        doc = result['doc']
        context += f"\n{i}. [{doc['module']}] {doc['title']}\n"
        context += f"   ID: {doc['id']}\n"
        context += f"   Content: {doc['content']}\n"
        context += f"   Relevance Score: {result['score']}\n"
    
    context += "\n=== END KNOWLEDGE BASE ===\n"
    context += "Please reference these articles when relevant to the user's question.\n\n"
    return context

# Initialize PostgreSQL RAG manager
try:
    db_rag_manager = RAGKnowledgeManager()
    
    # Import existing knowledge base if database is empty
    existing_articles = db_rag_manager.get_all_articles()
    if not existing_articles:
        print("📚 Importing existing knowledge base to PostgreSQL...")
        db_rag_manager.import_from_knowledge_base(KNOWLEDGE_BASE)
    
    print(f"✅ PostgreSQL RAG system initialized with {len(db_rag_manager.get_all_articles())} articles")
except Exception as e:
    print(f"❌ Failed to initialize PostgreSQL RAG: {e}")
    db_rag_manager = None

# Initialize crew with error handling
try:
    crew = build_crew()
    print("✅ Crew initialized successfully")
    print("📚 RAG Knowledge Base loaded with", sum(len(docs) for docs in KNOWLEDGE_BASE.values()), "articles")
except Exception as e:
    print(f"❌ Failed to initialize crew: {e}")
    crew = None

HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oracle EPM Support Assistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .content {
            padding: 40px;
        }

        .section {
            margin-bottom: 40px;
            padding: 30px;
            border-radius: 15px;
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            border: none;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
        }

        .section h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.8em;
            font-weight: 500;
            display: flex;
            align-items: center;
        }

        .section h2::before {
            content: "🏢";
            margin-right: 10px;
            font-size: 1.2em;
        }

        .form-group {
            margin-bottom: 20px;
        }

        textarea {
            width: 100%;
            min-height: 120px;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            padding: 15px;
            font-size: 16px;
            resize: vertical;
            transition: all 0.3s ease;
            font-family: inherit;
        }

        textarea:focus {
            border-color: #667eea;
            outline: none;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        input[type="submit"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
        }

        input[type="submit"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
        }

        input[type="submit"]:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .progress-container {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 10px;
            border-left: 5px solid #007bff;
        }

        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            width: 0%;
            transition: width 0.3s ease;
            animation: progress-animation 2s infinite;
        }

        @keyframes progress-animation {
            0% { width: 0%; }
            50% { width: 60%; }
            100% { width: 100%; }
        }

        .progress-text {
            text-align: center;
            color: #333;
            font-weight: 500;
            margin-bottom: 10px;
        }

        .progress-steps {
            font-size: 0.9em;
            color: #666;
            margin-top: 10px;
        }

        .result-container {
            background: rgba(255, 255, 255, 0.9);
            padding: 25px;
            margin-top: 25px;
            border-radius: 15px;
            border-left: 5px solid #007bff;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .result-container h3 {
            color: #0056b3;
            margin-bottom: 15px;
            font-size: 1.4em;
        }

        .result-container pre {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.5;
            font-family: 'Monaco', 'Menlo', monospace;
            border: 1px solid #dee2e6;
        }

        .agents-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }

        .agent-card {
            background: rgba(255, 255, 255, 0.7);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            font-size: 0.9em;
            border: 1px solid rgba(255, 255, 255, 0.5);
        }

        .agent-card strong {
            display: block;
            margin-bottom: 5px;
            color: #333;
        }

        .upload-zone {
            border: 2px dashed #667eea;
            border-radius: 15px;
            padding: 40px 20px;
            text-align: center;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
            min-height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .upload-zone:hover {
            border-color: #764ba2;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.2);
        }

        .upload-zone.dragover {
            border-color: #28a745;
            background: linear-gradient(135deg, rgba(40, 167, 69, 0.1) 0%, rgba(40, 167, 69, 0.05) 100%);
            border-style: solid;
        }

        .upload-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 15px;
        }

        .upload-icon {
            font-size: 3em;
            opacity: 0.7;
        }

        .upload-text {
            color: #333;
            font-size: 1.1em;
            line-height: 1.4;
        }

        .upload-text strong {
            color: #667eea;
            font-weight: 600;
        }

        .file-info {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(40, 167, 69, 0.1);
            padding: 15px 20px;
            border-radius: 10px;
            border: 2px solid #28a745;
            margin-top: 10px;
            font-weight: 500;
            color: #155724;
        }

        .remove-btn {
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 50%;
            width: 25px;
            height: 25px;
            font-size: 16px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            transition: all 0.3s ease;
        }

        .remove-btn:hover {
            background: #c82333;
            transform: scale(1.1);
        }

        .upload-button {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            padding: 20px 25px;
            border-radius: 15px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
            min-width: 180px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 5px 15px rgba(40, 167, 69, 0.2);
        }

        .upload-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(40, 167, 69, 0.3);
            background: linear-gradient(135deg, #218838 0%, #1ea97c 100%);
        }

        .upload-button[id="instant-upload-btn"]:hover {
            background: linear-gradient(135deg, #e55353 0%, #d63031 100%) !important;
            box-shadow: 0 8px 25px rgba(255, 107, 107, 0.4) !important;
        }

        .upload-button:active {
            transform: translateY(0);
        }

        @media (max-width: 768px) {
            .container {
                margin: 10px;
                border-radius: 15px;
            }

            .header {
                padding: 30px 20px;
            }

            .header h1 {
                font-size: 2em;
            }

            .content {
                padding: 20px;
            }

            .section {
                padding: 20px;
                margin-bottom: 20px;
            }

            .upload-zone {
                padding: 30px 15px;
                min-height: 100px;
            }

            .upload-icon {
                font-size: 2.5em;
            }

            .upload-text {
                font-size: 1em;
            }

            /* Stack upload elements vertically on mobile */
            div[style*="display: flex"] {
                flex-direction: column !important;
                gap: 10px !important;
            }

            .upload-button {
                min-width: auto;
                width: 100%;
                padding: 15px 20px;
                font-size: 14px;
            }
        }
    </style>
    <script>
        function showProgress() {
            const form = document.getElementById('epm-form');
            const submitBtn = document.getElementById('submit-btn');
            const progressContainer = document.getElementById('progress-container');
            const progressText = document.getElementById('progress-text');
            const progressSteps = document.getElementById('progress-steps');
            
            // Disable submit button
            submitBtn.disabled = true;
            submitBtn.value = 'Processing...';
            
            // Show progress bar
            progressContainer.style.display = 'block';
            
            // Progress messages
            const steps = [
                'Initializing AI agents...',
                'Analyzing your EPM problem...',
                'Consulting specialized experts...',
                'FCCS agent reviewing consolidation issues...',
                'EPBCS architect analyzing planning models...',
                'Workforce specialist examining HR data...',
                'Essbase guru optimizing performance...',
                'Free Form analyst designing solutions...',
                'Compiling comprehensive response...',
                'Finalizing recommendations...'
            ];
            
            let currentStep = 0;
            const stepInterval = setInterval(() => {
                if (currentStep < steps.length) {
                    progressText.textContent = steps[currentStep];
                    progressSteps.textContent = `Step ${currentStep + 1} of ${steps.length}`;
                    currentStep++;
                } else {
                    clearInterval(stepInterval);
                    progressText.textContent = 'Almost done...';
                    progressSteps.textContent = 'Preparing final response';
                }
            }, 1000);
            
            return true;
        }

        // Enhanced PDF upload functionality
        document.addEventListener('DOMContentLoaded', function() {
            const dropZone = document.getElementById('drop-zone');
            const fileInput = document.getElementById('pdf-upload');
            const fileInfo = document.getElementById('file-info');
            const fileName = document.getElementById('file-name');
            const removeBtn = document.getElementById('remove-file');
            const uploadContent = document.querySelector('.upload-content');

            // Click to browse files
            dropZone.addEventListener('click', () => {
                if (!fileInput.files.length) {
                    fileInput.click();
                }
            });

            

            // Instant upload button click handler
            const instantUploadBtn = document.getElementById('instant-upload-btn');
            instantUploadBtn.addEventListener('click', () => {
                const hiddenInput = document.createElement('input');
                hiddenInput.type = 'file';
                hiddenInput.accept = '.pdf';
                hiddenInput.style.display = 'none';
                
                hiddenInput.addEventListener('change', (e) => {
                    if (e.target.files.length > 0) {
                        const file = e.target.files[0];
                        if (file.type === 'application/pdf') {
                            // Create form data and upload immediately
                            const formData = new FormData();
                            formData.append('pdf_file', file);
                            formData.append('problem', document.querySelector('textarea[name="problem"]').value || 'PDF analysis only');
                            
                            // Show upload progress
                            showUploadProgress(file.name);
                            
                            // Submit the form automatically with enhanced status tracking
                            fetch('/', {
                                method: 'POST',
                                body: formData
                            })
                            .then(response => {
                                if (!response.ok) {
                                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                                }
                                updateUploadStatus('📊 Processing complete! Loading results...', 'success');
                                return response.text();
                            })
                            .then(html => {
                                // Brief delay to show completion status
                                setTimeout(() => {
                                    // Reload page with results
                                    document.open();
                                    document.write(html);
                                    document.close();
                                }, 500);
                            })
                            .catch(error => {
                                console.error('Upload error:', error);
                                updateUploadStatus(`❌ Upload failed: ${error.message}`, 'error');
                                
                                // Auto-hide error after 5 seconds
                                setTimeout(() => {
                                    hideUploadProgress();
                                }, 5000);
                            });
                        } else {
                            alert('Please select a PDF file only.');
                        }
                    }
                });
                
                hiddenInput.click();
            });

            function showUploadProgress(filename) {
                const statusDiv = document.getElementById('upload-status');
                const statusMessage = document.getElementById('status-message');
                
                // Clear any existing status
                statusDiv.innerHTML = `<span id="status-message">🔄 Uploading ${filename}...</span>`;
                statusDiv.style.display = 'block';
                statusDiv.style.background = '#e3f2fd';
                statusDiv.style.border = '2px solid #2196f3';
                statusDiv.style.color = '#1565c0';
                statusDiv.style.padding = '15px';
                statusDiv.style.borderRadius = '10px';
                statusDiv.style.marginTop = '15px';
                statusDiv.style.transition = 'all 0.3s ease';
                
                // Add animated progress indicator
                let dots = 0;
                const progressInterval = setInterval(() => {
                    dots = (dots + 1) % 4;
                    const newMessage = document.getElementById('status-message');
                    if (newMessage) {
                        newMessage.textContent = `🔄 Processing ${filename}${'.'.repeat(dots)}`;
                    } else {
                        clearInterval(progressInterval);
                    }
                }, 500);
                
                // Store interval for cleanup
                statusDiv.dataset.progressInterval = progressInterval;
            }

            function updateUploadStatus(message, type = 'info') {
                const statusDiv = document.getElementById('upload-status');
                const statusMessage = document.getElementById('status-message');
                
                // Clear any progress intervals
                if (statusDiv.dataset.progressInterval) {
                    clearInterval(parseInt(statusDiv.dataset.progressInterval));
                    delete statusDiv.dataset.progressInterval;
                }
                
                if (statusMessage) {
                    statusMessage.textContent = message;
                }
                
                // Update styling based on status type
                switch(type) {
                    case 'success':
                        statusDiv.style.background = '#d4edda';
                        statusDiv.style.border = '2px solid #28a745';
                        statusDiv.style.color = '#155724';
                        break;
                    case 'error':
                        statusDiv.style.background = '#f8d7da';
                        statusDiv.style.border = '2px solid #dc3545';
                        statusDiv.style.color = '#721c24';
                        break;
                    case 'warning':
                        statusDiv.style.background = '#fff3cd';
                        statusDiv.style.border = '2px solid #ffc107';
                        statusDiv.style.color = '#856404';
                        break;
                    default:
                        statusDiv.style.background = '#e3f2fd';
                        statusDiv.style.border = '2px solid #2196f3';
                        statusDiv.style.color = '#1565c0';
                }
                
                statusDiv.style.display = 'block';
            }

            function hideUploadProgress() {
                const statusDiv = document.getElementById('upload-status');
                
                // Clear any progress intervals
                if (statusDiv.dataset.progressInterval) {
                    clearInterval(parseInt(statusDiv.dataset.progressInterval));
                    delete statusDiv.dataset.progressInterval;
                }
                
                statusDiv.style.display = 'none';
                statusDiv.innerHTML = '<span id="status-message"></span>';
            }

            // Drag and drop events
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            });

            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('dragover');
            });

            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    const file = files[0];
                    if (file.type === 'application/pdf') {
                        fileInput.files = files;
                        showFileInfo(file);
                    } else {
                        updateUploadStatus(`❌ Invalid file type: ${file.type}. Please upload PDF files only.`, 'error');
                        setTimeout(() => {
                            hideUploadProgress();
                        }, 3000);
                    }
                } else {
                    updateUploadStatus('❌ No files detected. Please try again.', 'error');
                    setTimeout(() => {
                        hideUploadProgress();
                    }, 3000);
                }
            });

            // File input change with enhanced validation
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    const file = e.target.files[0];
                    if (file.type === 'application/pdf') {
                        showFileInfo(file);
                    } else {
                        updateUploadStatus(`❌ Invalid file: "${file.name}". Only PDF files are supported.`, 'error');
                        fileInput.value = ''; // Clear invalid selection
                        setTimeout(() => {
                            hideUploadProgress();
                        }, 3000);
                    }
                } else {
                    hideUploadProgress();
                }
            });

            // Remove file
            removeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                fileInput.value = '';
                hideFileInfo();
            });

            function showFileInfo(file) {
                fileName.textContent = `📄 ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB) - Processing...`;
                fileName.style.color = '#ffc107';
                uploadContent.style.display = 'none';
                fileInfo.style.display = 'flex';
                dropZone.style.cursor = 'default';
                
                // Show initial processing status
                updateUploadStatus(`📄 Validating ${file.name}...`, 'info');
                
                // Simulate file validation steps with real-time updates
                setTimeout(() => {
                    updateUploadStatus(`✅ File validated: ${file.name}`, 'info');
                    fileName.textContent = `📄 ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB) - Validated ✅`;
                    fileName.style.color = '#28a745';
                }, 300);
                
                setTimeout(() => {
                    updateUploadStatus(`🚀 Ready to upload ${file.name}`, 'success');
                }, 800);
                
                // Auto-hide status after showing ready state
                setTimeout(() => {
                    hideUploadProgress();
                }, 2500);
            }

            function hideFileInfo() {
                uploadContent.style.display = 'flex';
                fileInfo.style.display = 'none';
                dropZone.style.cursor = 'pointer';
            }
        });
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Oracle EPM Support Assistant</h1>
            <p>AI-powered support for FCCS, EPBCS, Essbase, Workforce Planning & Free Form Planning</p>
        </div>

        <div class="content">
            <div class="section">
                <h2>Oracle EPM Problem Solver</h2>
                <form id="epm-form" method="post" action="/" enctype="multipart/form-data" onsubmit="return showProgress()">
                    <div class="form-group">
                        <textarea name="problem" 
                                  placeholder="Describe your Oracle EPM issue in detail. Include module (FCCS, EPBCS, Essbase, etc.), error messages, and what you were trying to accomplish..."
                                  required>{{ request.form.problem or '' }}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="pdf-upload" style="display: block; margin-bottom: 15px; font-weight: 500; color: #333;">
                            📄 Upload PDF Document (Optional)
                        </label>
                        <div style="display: flex; gap: 15px; align-items: stretch;">
                            <div id="drop-zone" class="upload-zone" style="flex: 1;">
                                <div class="upload-content">
                                    <div class="upload-icon">📄</div>
                                    <div class="upload-text">
                                        <strong>Drag & Drop PDF here</strong>
                                        <br>or click to browse files
                                    </div>
                                    <input type="file" 
                                           id="pdf-upload" 
                                           name="pdf_file" 
                                           accept=".pdf"
                                           style="display: none;">
                                </div>
                                <div id="file-info" class="file-info" style="display: none;">
                                    <span id="file-name"></span>
                                    <button type="button" id="remove-file" class="remove-btn">×</button>
                                </div>
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 10px;">
                                <button type="button" id="instant-upload-btn" class="upload-button" style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); box-shadow: 0 5px 15px rgba(255, 107, 107, 0.2);">
                                    ⚡ Upload & Analyze Now
                                </button>
                            </div>
                        </div>
                        <small style="color: #666; margin-top: 10px; display: block;">
                            Upload Oracle EPM documentation, error logs, or related PDF files for analysis
                        </small>
                        <div id="upload-status" style="display: none; margin-top: 10px; padding: 10px; border-radius: 5px; font-size: 0.9em;">
                            <span id="status-message"></span>
                        </div>
                    </div>
                    <input type="submit" id="submit-btn" value="Get AI-Powered Help">
                </form>

                <div id="progress-container" class="progress-container">
                    <div id="progress-text" class="progress-text">Initializing AI agents...</div>
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                    <div id="progress-steps" class="progress-steps">Step 1 of 10</div>
                </div>

                <div class="agents-info">
                    <div class="agent-card">
                        <strong>💼 FCCS Expert</strong>
                        Consolidation & Close
                    </div>
                    <div class="agent-card">
                        <strong>📊 EPBCS Architect</strong>
                        Planning & Budgeting
                    </div>
                    <div class="agent-card">
                        <strong>👥 Workforce Specialist</strong>
                        HR Planning
                    </div>
                    <div class="agent-card">
                        <strong>⚡ Essbase Guru</strong>
                        Performance Optimization
                    </div>
                    <div class="agent-card">
                        <strong>🎨 Free Form Analyst</strong>
                        Custom Modeling
                    </div>
                </div>

                {% if pdf_content %}
                    <div class="result-container" style="
                        {% if pdf_status == 'success' %}background: rgba(220, 255, 220, 0.9); border-left: 5px solid #28a745;
                        {% elif pdf_status == 'warning' %}background: rgba(255, 248, 220, 0.9); border-left: 5px solid #ffc107;
                        {% elif pdf_status == 'error' %}background: rgba(255, 220, 220, 0.9); border-left: 5px solid #dc3545;
                        {% else %}background: rgba(240, 248, 255, 0.9); border-left: 5px solid #007bff;
                        {% endif %}
                    ">
                        <h3>
                            {% if pdf_status == 'success' %}✅ PDF Successfully Processed
                            {% elif pdf_status == 'warning' %}⚠️ PDF Processed with Warnings
                            {% elif pdf_status == 'error' %}❌ PDF Processing Failed
                            {% else %}📄 PDF Processing Status
                            {% endif %}
                        </h3>
                        <pre style="font-size: 0.9em; max-height: 200px; overflow-y: auto; white-space: pre-wrap;">{{ pdf_content }}</pre>
                    </div>
                {% endif %}

                {% if rag_results %}
                    <div class="result-container" style="background: rgba(255, 248, 220, 0.9); border-left: 5px solid #ffa500;">
                        <h3>📚 Knowledge Base Search Results:</h3>
                        <div style="margin-bottom: 15px;">
                            {% for result in rag_results %}
                                <div style="margin-bottom: 10px; padding: 10px; background: rgba(255, 255, 255, 0.7); border-radius: 5px;">
                                    <strong>[{{ result.doc.module }}] {{ result.doc.title }}</strong>
                                    <br><small>Relevance Score: {{ result.score }}</small>
                                    <br>{{ result.doc.content }}
                                </div>
                            {% endfor %}
                        </div>
                    </div>
                {% endif %}

                {% if result %}
                    <div class="result-container">
                        <h3>🤖 AI Agent Response:</h3>
                        <div style="margin-bottom: 15px;">
                            <strong>💾 Download Results:</strong>
                            <a href="/download/txt" style="margin: 0 5px; padding: 5px 10px; background: #28a745; color: white; text-decoration: none; border-radius: 3px; font-size: 0.9em;">📄 TXT</a>
                            <a href="/download/json" style="margin: 0 5px; padding: 5px 10px; background: #007bff; color: white; text-decoration: none; border-radius: 3px; font-size: 0.9em;">📋 JSON</a>
                            <a href="/download/html" style="margin: 0 5px; padding: 5px 10px; background: #fd7e14; color: white; text-decoration: none; border-radius: 3px; font-size: 0.9em;">🌐 HTML</a>
                        </div>
                        <pre>{{ result }}</pre>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/download/<format>')
def download_results(format):
    """Download the last result in specified format"""
    global last_result_data
    
    if not hasattr(download_results, 'last_result') or not download_results.last_result:
        return "No results available for download", 404
    
    result_data = download_results.last_result
    
    if format == 'txt':
        response = make_response(result_data['content'])
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = f'attachment; filename="oracle_epm_analysis_{result_data["timestamp"]}.txt"'
        
    elif format == 'json':
        import json
        json_data = {
            "timestamp": result_data['timestamp'],
            "problem": result_data['problem'],
            "ai_response": result_data['content'],
            "rag_results": result_data.get('rag_results', []),
            "pdf_content": result_data.get('pdf_content', '')
        }
        response = make_response(json.dumps(json_data, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename="oracle_epm_analysis_{result_data["timestamp"]}.json"'
        
    elif format == 'html':
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Oracle EPM Analysis Results</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
                .content {{ margin-top: 20px; white-space: pre-wrap; }}
                .timestamp {{ color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Oracle EPM Support Analysis</h1>
                <p class="timestamp">Generated: {result_data['timestamp']}</p>
                <h3>Problem:</h3>
                <p>{result_data['problem']}</p>
            </div>
            <div class="content">
                <h3>AI Analysis:</h3>
                <pre>{result_data['content']}</pre>
            </div>
        </body>
        </html>
        """
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = f'attachment; filename="oracle_epm_analysis_{result_data["timestamp"]}.html"'
    
    else:
        return "Invalid format. Use: txt, json, or html", 400
    
    return response

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    rag_results = None
    pdf_content = None
    pdf_status = None
    
    if request.method == 'POST' and request.form.get('problem') and crew is not None:
        try:
            problem = request.form['problem']
            print(f"🔄 Processing request: {problem[:100]}...")
            
            # Handle PDF upload if provided
            pdf_text = ""
            pdf_status = None
            if 'pdf_file' in request.files:
                pdf_file = request.files['pdf_file']
                if pdf_file and pdf_file.filename:
                    if not pdf_file.filename.endswith('.pdf'):
                        pdf_content = f"❌ Error: '{pdf_file.filename}' is not a PDF file. Please upload a .pdf file."
                        pdf_status = "error"
                    else:
                        try:
                            pdf_text = extract_text_from_pdf(pdf_file)
                            if len(pdf_text.strip()) < 10:
                                pdf_content = f"⚠️ Warning: PDF '{pdf_file.filename}' appears to be empty or contains mostly images/unreadable text. Only {len(pdf_text)} characters extracted."
                                pdf_status = "warning"
                            else:
                                pdf_content = f"✅ Successfully processed PDF '{pdf_file.filename}'\n📊 Extracted {len(pdf_text)} characters\n📄 Preview: {pdf_text[:300]}..."
                                pdf_status = "success"
                            print(f"📄 PDF uploaded: {pdf_file.filename} - {len(pdf_text)} characters extracted")
                        except Exception as pdf_error:
                            print(f"❌ PDF processing error: {pdf_error}")
                            pdf_content = f"❌ Error processing PDF '{pdf_file.filename}': {str(pdf_error)}"
                            pdf_status = "error"
            
            # Search knowledge base for relevant information
            search_query = f"{problem} {pdf_text[:200]}" if pdf_text else problem
            
            # Use PostgreSQL RAG if available, fallback to in-memory search
            if db_rag_manager:
                db_results = db_rag_manager.search_articles(search_query)
                rag_results = [{'doc': r['article'], 'score': r['score'], 'category': r['article']['category']} for r in db_results]
            else:
                rag_results = search_knowledge_base(search_query)
            
            rag_context = format_rag_context(rag_results)
            
            print(f"🔍 RAG Search found {len(rag_results)} relevant articles")
            
            # Combine user problem with RAG context and PDF content
            enhanced_problem = f"{rag_context}\nUSER PROBLEM: {problem}"
            if pdf_text:
                enhanced_problem += f"\n\nUPLOADED PDF CONTENT:\n{pdf_text}\n"
            
            print("🤖 Starting AI agent processing...")
            
            # Process with AI agents with timeout handling
            try:
                import threading
                import time
                
                result_container = [None]
                error_container = [None]
                
                def ai_worker():
                    try:
                        result_container[0] = crew.kickoff(inputs={"problem": enhanced_problem})
                    except Exception as e:
                        error_container[0] = e
                
                # Start AI processing in separate thread
                ai_thread = threading.Thread(target=ai_worker)
                ai_thread.daemon = True
                ai_thread.start()
                
                # Wait for completion with 5-minute timeout
                ai_thread.join(timeout=300)
                
                if ai_thread.is_alive():
                    result = "⏰ Request timeout: The AI agents took too long to process your request. Please try again with a more specific question or contact support."
                    print("⏰ AI processing timeout occurred")
                elif error_container[0]:
                    raise error_container[0]
                else:
                    result = result_container[0]
                    print("✅ AI processing completed successfully")
                
            except Exception as ai_error:
                result = f"🤖 AI Processing Error: {str(ai_error)}\n\nPlease try again or contact support if the issue persists."
                print(f"❌ AI processing error: {ai_error}")
            
            # Store result for download
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            download_results.last_result = {
                'content': str(result),
                'problem': problem,
                'timestamp': timestamp,
                'rag_results': [{'doc': r['doc'], 'score': r['score']} for r in rag_results] if rag_results else [],
                'pdf_content': pdf_content or ''
            }
            
        except Exception as e:
            result = f"❌ System Error: {str(e)}\n\nPlease check your input and try again."
            print(f"❌ System error: {e}")
    elif request.method == 'POST' and request.form.get('problem') and crew is None:
        result = "Service temporarily unavailable. Please check configuration."
    
    return render_template_string(HTML, result=result, rag_results=rag_results, pdf_content=pdf_content, pdf_status=pdf_status, request=request)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=3000)