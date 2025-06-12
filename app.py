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
    """Extract text content from uploaded PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        text_content = ""
        
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text_content += page.extract_text() + "\n"
        
        return text_content.strip()
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

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
                        <label for="pdf-upload" style="display: block; margin-bottom: 10px; font-weight: 500; color: #333;">
                            📄 Upload PDF Document (Optional)
                        </label>
                        <input type="file" 
                               id="pdf-upload" 
                               name="pdf_file" 
                               accept=".pdf"
                               style="width: 100%; padding: 10px; border: 2px dashed #667eea; border-radius: 10px; background: rgba(102, 126, 234, 0.05);">
                        <small style="color: #666; margin-top: 5px; display: block;">
                            Upload Oracle EPM documentation, error logs, or related PDF files for analysis
                        </small>
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
                    <div class="result-container" style="background: rgba(240, 248, 255, 0.9); border-left: 5px solid #007bff;">
                        <h3>📄 PDF Content Processed:</h3>
                        <pre style="font-size: 0.9em; max-height: 200px; overflow-y: auto;">{{ pdf_content }}</pre>
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
    
    if request.method == 'POST' and request.form.get('problem') and crew is not None:
        try:
            problem = request.form['problem']
            print(f"🔄 Processing request: {problem[:100]}...")
            
            # Handle PDF upload if provided
            pdf_text = ""
            if 'pdf_file' in request.files:
                pdf_file = request.files['pdf_file']
                if pdf_file and pdf_file.filename.endswith('.pdf'):
                    try:
                        pdf_text = extract_text_from_pdf(pdf_file)
                        pdf_content = f"Uploaded PDF content (first 500 chars): {pdf_text[:500]}..."
                        print(f"📄 PDF uploaded: {pdf_file.filename} - {len(pdf_text)} characters extracted")
                    except Exception as pdf_error:
                        print(f"❌ PDF processing error: {pdf_error}")
                        pdf_content = "Error processing PDF file"
            
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
    
    return render_template_string(HTML, result=result, rag_results=rag_results, pdf_content=pdf_content, request=request)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=3000)