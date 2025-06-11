
# Oracle EPM Support Assistant

A Flask-based web application powered by CrewAI that provides specialized support for Oracle Enterprise Performance Management (EPM) applications using AI agents.

## Overview

This application features 5 specialized AI agents that can help troubleshoot and provide guidance for different Oracle EPM modules:

- **FCCS Support Agent** - Financial Consolidation and Close Cloud Service
- **EPBCS Support Agent** - Enterprise Planning and Budgeting Cloud Service  
- **Workforce Planning Agent** - Workforce Planning module
- **Essbase Support Agent** - Essbase database optimization
- **Free Form Planning Agent** - Free Form Planning applications

## Features

- Web-based interface for submitting EPM-related questions
- Multi-agent AI system with specialized knowledge for each EPM module
- Powered by Anthropic's Claude AI model
- Sequential task processing for comprehensive responses
- Error handling and graceful degradation

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- Anthropic API key

### Installation

1. **Clone or fork this Repl**

2. **Set up your API key**
   - Go to the Secrets tool in your Replit workspace
   - Add a new secret with key: `ANTHROPIC_API_KEY`
   - Add your Anthropic API key as the value

3. **Install dependencies**
   Dependencies are automatically installed from `pyproject.toml` when you run the application.

### Running the Application

1. **Start the application**
   ```bash
   python3 app.py
   ```
   Or click the **Run** button in Replit.

2. **Access the application**
   - Open your browser to the provided URL (typically port 3000)
   - The application will be accessible at your Repl's public URL

## How to Use

1. **Access the web interface**
   - Navigate to your application URL
   - You'll see a simple form with a text area

2. **Submit your Oracle EPM question**
   - Enter your specific Oracle EPM problem or question in the text area
   - Click "Get Help" to submit

3. **Receive AI-powered assistance**
   - The system will analyze your question
   - Multiple specialized agents will collaborate to provide comprehensive guidance
   - Results will be displayed on the same page

## Example Use Cases

### FCCS Issues
- Consolidation rule problems
- Elimination entries not working
- Currency translation issues
- Intercompany matching problems

### EPBCS Issues
- Business rule errors
- Form design problems
- Approval workflow issues
- Data validation failures

### Workforce Planning
- Headcount forecasting
- Salary planning
- Benefits calculations
- Organizational structure setup

### Essbase Performance
- Calculation optimization
- Database restructuring
- ASO/BSO performance tuning
- Memory allocation issues

### Free Form Planning
- Model design
- Custom calculations
- Integration setup
- Report configuration

## Application Structure

```
├── app.py                          # Main Flask application
├── src/oracle_epm_support/
│   ├── crew.py                     # CrewAI setup and configuration
│   └── config/
│       ├── agents.yaml             # AI agent definitions
│       └── tasks.yaml              # Task configurations
├── pyproject.toml                  # Python dependencies
└── README.md                       # This file
```

## Configuration

### Agent Configuration (`src/oracle_epm_support/config/agents.yaml`)
- Defines the 5 specialized agents
- Sets roles, goals, and backstories for each agent
- Configures agent behavior and expertise areas

### Task Configuration (`src/oracle_epm_support/config/tasks.yaml`)
- Defines tasks for each agent
- Sets expected outputs and descriptions
- Links tasks to appropriate agents

## Deployment

### Deploy to Replit

1. **Configure deployment settings**
   - The app is pre-configured for Replit deployment
   - Uses port 3000 with proper host binding (0.0.0.0)

2. **Deploy your application**
   - Click the **Deploy** button in Replit
   - Choose **Autoscale** deployment type
   - Ensure your `ANTHROPIC_API_KEY` is set in deployment secrets

3. **Access your deployed app**
   - Your app will be available at the provided deployment URL
   - Automatically scales based on usage

## Troubleshooting

### Common Issues

**Error: "Failed to initialize Claude model"**
- Check that your `ANTHROPIC_API_KEY` is properly set in Secrets
- Verify the API key is valid and has sufficient credits

**Error: "Service temporarily unavailable"**
- This indicates the CrewAI agents failed to initialize
- Check the console for specific error messages
- Verify all configuration files are present and valid

**Slow response times**
- AI processing can take 30-60 seconds for complex questions
- This is normal behavior for multi-agent processing

### Getting Help

- Check the console output for detailed error messages
- Ensure all dependencies are properly installed
- Verify your Anthropic API key has sufficient credits

## Technical Details

- **Framework**: Flask (Python web framework)
- **AI Engine**: CrewAI with Anthropic Claude
- **Model**: Claude-3-Sonnet-20240229
- **Architecture**: Multi-agent sequential processing
- **Deployment**: Replit Cloud Run

## Contributing

To modify or extend the application:

1. **Add new agents**: Edit `src/oracle_epm_support/config/agents.yaml`
2. **Modify tasks**: Edit `src/oracle_epm_support/config/tasks.yaml`
3. **Update UI**: Modify the HTML template in `app.py`
4. **Add features**: Extend the Flask application in `app.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
