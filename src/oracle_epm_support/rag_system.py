
import os
from pathlib import Path
import yaml
from typing import List, Dict, Any
import json

class SimpleRAGSystem:
    """Simple RAG system for Oracle EPM knowledge retrieval"""
    
    def __init__(self):
        self.knowledge_base = self._load_knowledge_base()
        
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load Oracle EPM knowledge base"""
        return {
            "fccs": {
                "consolidation_rules": [
                    "Check entity hierarchy in Data Management",
                    "Verify intercompany matching rules",
                    "Review elimination entries configuration",
                    "Validate currency translation settings"
                ],
                "close_process": [
                    "Run consolidation with detailed logging",
                    "Check for data validation errors",
                    "Review journal entries posting",
                    "Verify close task dependencies"
                ],
                "common_errors": {
                    "FCCS-00001": "Data validation failed - check dimension mappings",
                    "FCCS-00002": "Consolidation timeout - optimize rules",
                    "FCCS-00003": "Currency translation error - verify rates"
                }
            },
            "epbcs": {
                "business_rules": [
                    "Check calculation dependencies",
                    "Verify member formulas syntax",
                    "Review runtime prompts configuration",
                    "Validate data form associations"
                ],
                "planning_setup": [
                    "Configure scenario and version setup",
                    "Set up approval workflow",
                    "Define security access rights",
                    "Create data validation rules"
                ],
                "performance_tips": [
                    "Use dense calculations where possible",
                    "Optimize allocation rules",
                    "Implement parallel processing",
                    "Configure calculation ordering"
                ]
            },
            "essbase": {
                "performance_tuning": [
                    "Analyze calculation scripts for efficiency",
                    "Review database outline structure",
                    "Optimize block size and density",
                    "Configure cache settings appropriately"
                ],
                "calc_scripts": [
                    "Use CALC ALL sparingly",
                    "Implement conditional calculations",
                    "Leverage parallel calculation blocks",
                    "Optimize member selection criteria"
                ]
            },
            "workforce": {
                "modeling_best_practices": [
                    "Set up proper employee hierarchies",
                    "Configure benefit calculations correctly",
                    "Implement salary escalation rules",
                    "Design headcount planning workflows"
                ]
            },
            "freeform": {
                "custom_modeling": [
                    "Design flexible dimension structures",
                    "Implement custom business logic",
                    "Create dynamic reporting views",
                    "Configure user-defined calculations"
                ]
            }
        }
    
    def retrieve_relevant_context(self, query: str, module: str = None) -> List[str]:
        """Retrieve relevant context based on query and module"""
        relevant_info = []
        query_lower = query.lower()
        
        # Determine module if not specified
        if not module:
            if any(word in query_lower for word in ['fccs', 'consolidation', 'close']):
                module = 'fccs'
            elif any(word in query_lower for word in ['epbcs', 'planning', 'budget']):
                module = 'epbcs'
            elif any(word in query_lower for word in ['essbase', 'cube', 'calculation']):
                module = 'essbase'
            elif any(word in query_lower for word in ['workforce', 'employee', 'headcount']):
                module = 'workforce'
            elif any(word in query_lower for word in ['freeform', 'free form']):
                module = 'freeform'
        
        # Retrieve module-specific context
        if module and module in self.knowledge_base:
            module_kb = self.knowledge_base[module]
            
            # Check for specific keywords and retrieve relevant info
            for category, items in module_kb.items():
                if isinstance(items, list):
                    if any(keyword in query_lower for keyword in category.split('_')):
                        relevant_info.extend([f"{category.upper()}: {item}" for item in items])
                elif isinstance(items, dict):
                    for key, value in items.items():
                        if key in query_lower:
                            relevant_info.append(f"ERROR {key}: {value}")
        
        # Add general troubleshooting steps
        if any(word in query_lower for word in ['error', 'issue', 'problem', 'failed']):
            relevant_info.extend([
                "TROUBLESHOOTING: Check application logs for detailed error messages",
                "TROUBLESHOOTING: Verify user permissions and security settings",
                "TROUBLESHOOTING: Ensure all required services are running",
                "TROUBLESHOOTING: Check network connectivity and firewall settings"
            ])
        
        return relevant_info[:5]  # Limit to top 5 most relevant items
    
    def enhance_prompt_with_context(self, original_prompt: str, context: List[str]) -> str:
        """Enhance the original prompt with retrieved context"""
        if not context:
            return original_prompt
        
        context_str = "\n".join([f"- {item}" for item in context])
        
        enhanced_prompt = f"""{original_prompt}

RELEVANT KNOWLEDGE BASE CONTEXT:
{context_str}

Please use this context information when providing your response to ensure accuracy and completeness."""
        
        return enhanced_prompt
