import os
import sys

# 👇 This tells Python to look inside 'src/'
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from oracle_epm_support.crew import build_crew
from flask import Flask, request, render_template_string

# Configure CrewAI to use Anthropic
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")

app = Flask(__name__)

# Initialize crew with error handling
try:
    crew = build_crew()
    print("✅ Crew initialized successfully")
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
            background: #f8f9fa;
            border: none;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
        }

        .calculator {
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        }

        .epm-support {
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
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
            content: "🧮";
            margin-right: 10px;
            font-size: 1.2em;
        }

        .epm-support h2::before {
            content: "🏢";
        }

        .form-group {
            margin-bottom: 20px;
        }

        .calc-input-group {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }

        input[type="text"], textarea {
            border: 2px solid #e9ecef;
            border-radius: 10px;
            padding: 15px;
            font-size: 16px;
            transition: all 0.3s ease;
            font-family: inherit;
        }

        input[type="text"] {
            flex: 1;
            min-width: 300px;
        }

        textarea {
            width: 100%;
            min-height: 120px;
            resize: vertical;
        }

        input[type="text"]:focus, textarea:focus {
            border-color: #667eea;
            outline: none;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        button, input[type="submit"] {
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

        button:hover, input[type="submit"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
        }

        .calc-result {
            background: rgba(255, 255, 255, 0.9);
            padding: 20px;
            margin-top: 20px;
            border-radius: 10px;
            border-left: 5px solid #28a745;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }

        .calc-result strong {
            color: #155724;
            font-size: 1.1em;
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

            .calc-input-group {
                flex-direction: column;
            }

            input[type="text"] {
                min-width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Oracle EPM Support Assistant</h1>
            <p>AI-powered support for FCCS, EPBCS, Essbase, Workforce Planning & Free Form Planning</p>
        </div>

        <div class="content">
            <div class="section calculator">
                <h2>Quick Calculator</h2>
                <form method="post" action="/calculate">
                    <div class="form-group">
                        <div class="calc-input-group">
                            <input type="text" name="expression" 
                                   placeholder="Enter calculation (e.g., 10e7, 5+3*2, sqrt(16))" 
                                   value="{{ request.form.expression or '' }}">
                            <input type="submit" value="Calculate">
                        </div>
                    </div>
                </form>
                {% if calc_result %}
                    <div class="calc-result">
                        <strong>Result:</strong> {{ calc_result }}
                    </div>
                {% endif %}
            </div>

            <div class="section epm-support">
                <h2>Oracle EPM Problem Solver</h2>
                <form method="post" action="/">
                    <div class="form-group">
                        <textarea name="problem" 
                                  placeholder="Describe your Oracle EPM issue in detail. Include module (FCCS, EPBCS, Essbase, etc.), error messages, and what you were trying to accomplish..."
                                  >{{ request.form.problem or '' }}</textarea>
                    </div>
                    <input type="submit" value="Get AI-Powered Help">
                </form>

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

                {% if result %}
                    <div class="result-container">
                        <h3>🤖 AI Agent Response:</h3>
                        <pre>{{ result }}</pre>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    calc_result = None
    if request.method == 'POST' and request.form.get('problem') and crew is not None:
        try:
            problem = request.form['problem']
            result = crew.kickoff(inputs={"problem": problem})
        except Exception as e:
            result = f"Error processing request: {str(e)}"
    elif request.method == 'POST' and request.form.get('problem') and crew is None:
        result = "Service temporarily unavailable. Please check configuration."
    return render_template_string(HTML, result=result, calc_result=calc_result, request=request)


@app.route('/calculate', methods=['POST'])
def calculate():
    result = None
    problem = None
    calc_result = None
    if request.method == 'POST':
        try:
            expression = request.form['expression']
            # Safely evaluate the expression (basic arithmetic operations only)
            calc_result = eval(expression, {"__builtins__": None}, {
                'sqrt': __import__('math').sqrt,
                'pow': __import__('math').pow,
            })  # Removed potentially dangerous functions
        except Exception as e:
            calc_result = f"Calculation error: {str(e)}"
    return render_template_string(HTML, result=result, calc_result=calc_result, request=request)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=3000)