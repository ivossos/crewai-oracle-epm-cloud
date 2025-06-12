
import json
from datetime import datetime

class RAGKnowledgeManager:
    """Utility class for managing RAG knowledge base"""
    
    def __init__(self, knowledge_file="knowledge_base.json"):
        self.knowledge_file = knowledge_file
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Load knowledge base from file"""
        try:
            with open(self.knowledge_file, 'r') as f:
                self.knowledge_base = json.load(f)
        except FileNotFoundError:
            self.knowledge_base = {"articles": []}
    
    def save_knowledge_base(self):
        """Save knowledge base to file"""
        with open(self.knowledge_file, 'w') as f:
            json.dump(self.knowledge_base, f, indent=2)
    
    def add_article(self, title, content, module, keywords, category="general"):
        """Add new article to knowledge base"""
        article = {
            "id": f"{module.lower()}_{len(self.knowledge_base['articles'])}",
            "title": title,
            "content": content,
            "keywords": keywords,
            "module": module,
            "category": category,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.knowledge_base["articles"].append(article)
        self.save_knowledge_base()
        return article["id"]
    
    def search_articles(self, query, max_results=5):
        """Search articles by query"""
        query_lower = query.lower()
        results = []
        
        for article in self.knowledge_base["articles"]:
            score = 0
            
            # Title match
            if any(word in article['title'].lower() for word in query_lower.split()):
                score += 3
            
            # Keyword match
            for keyword in article['keywords']:
                if keyword in query_lower:
                    score += 2
            
            # Content match
            if any(word in article['content'].lower() for word in query_lower.split() if len(word) > 3):
                score += 1
            
            if score > 0:
                results.append({
                    'article': article,
                    'score': score
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:max_results]
    
    def get_article_by_id(self, article_id):
        """Get specific article by ID"""
        for article in self.knowledge_base["articles"]:
            if article["id"] == article_id:
                return article
        return None
    
    def update_article(self, article_id, **updates):
        """Update existing article"""
        for article in self.knowledge_base["articles"]:
            if article["id"] == article_id:
                article.update(updates)
                article["updated_at"] = datetime.now().isoformat()
                self.save_knowledge_base()
                return True
        return False
    
    def delete_article(self, article_id):
        """Delete article by ID"""
        self.knowledge_base["articles"] = [
            article for article in self.knowledge_base["articles"] 
            if article["id"] != article_id
        ]
        self.save_knowledge_base()

# Example usage and initial setup
if __name__ == "__main__":
    rag_manager = RAGKnowledgeManager()
    
    # Add sample articles if knowledge base is empty
    if not rag_manager.knowledge_base["articles"]:
        print("Initializing knowledge base with sample articles...")
        
        sample_articles = [
            {
                "title": "FCCS Consolidation Rules Troubleshooting",
                "content": "When consolidation rules fail to execute, check: 1) Entity hierarchy setup 2) Ownership percentages 3) Elimination rules syntax 4) Period lock status 5) Security permissions for consolidation process",
                "module": "FCCS",
                "keywords": ["consolidation", "rules", "troubleshooting", "elimination", "hierarchy"],
                "category": "troubleshooting"
            },
            {
                "title": "EPBCS Business Rule Optimization",
                "content": "To optimize EPBCS business rules: 1) Use efficient calculation order 2) Implement parallel processing 3) Minimize cross-dimensional calculations 4) Use FIX statements effectively 5) Regular performance monitoring",
                "module": "EPBCS", 
                "keywords": ["business rules", "optimization", "performance", "calculation", "parallel"],
                "category": "optimization"
            },
            {
                "title": "Essbase Calculation Performance Tuning",
                "content": "Improve Essbase calculation performance: 1) Use FIXPARALLEL for dense calculations 2) Optimize calculation order 3) Consider calc scripts vs business rules 4) Monitor block density 5) Use appropriate aggregation",
                "module": "Essbase",
                "keywords": ["calculation", "performance", "tuning", "parallel", "optimization"],
                "category": "performance"
            }
        ]
        
        for article in sample_articles:
            rag_manager.add_article(**article)
        
        print(f"Added {len(sample_articles)} sample articles to knowledge base")
