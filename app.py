import os
import sys

# 👇 This tells Python to look inside 'src/'
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from oracle_epm_support.crew import build_crew
from flask import Flask, request, render_template_string

# Configure CrewAI to use Anthropic
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")
os.environ["OPENAI_MODEL_NAME"] = "claude-3-sonnet-20240229"
os.environ["OPENAI_API_BASE"] = "https://api.anthropic.com"

app = Flask(__name__)
crew = build_crew()

HTML = """
<!doctype html>
<title>Oracle EPM Support Assistant</title>
<h2>Enter your Oracle EPM Problem:</h2>
<form method=post>
  <textarea name=problem rows=6 cols=60>{{ request.form.problem or '' }}</textarea><br>
  <input type=submit value="Get Help">
</form>
{% if result %}
  <h3>Agent Response:</h3>
  <pre>{{ result }}</pre>
{% endif %}
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        problem = request.form['problem']
        result = crew.kickoff(inputs={"problem": problem})
    return render_template_string(HTML, result=result)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=3000)