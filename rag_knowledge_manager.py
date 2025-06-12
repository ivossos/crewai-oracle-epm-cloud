
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json

class RAGKnowledgeManager:
    """PostgreSQL-based RAG knowledge management system"""
    
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not found. Please set up PostgreSQL database in Replit.")
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_articles (
                        id SERIAL PRIMARY KEY,
                        article_id VARCHAR(100) UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        module VARCHAR(50) NOT NULL,
                        category VARCHAR(50) DEFAULT 'general',
                        keywords TEXT[] NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create index for faster searching
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_keywords 
                    ON knowledge_articles USING GIN(keywords)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_module 
                    ON knowledge_articles(module)
                """)
                
                conn.commit()
                print("✅ Database tables initialized successfully")
    
    def add_article(self, title, content, module, keywords, category="general"):
        """Add new article to knowledge base"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                article_id = f"{module.lower()}_{int(datetime.now().timestamp())}"
                
                cur.execute("""
                    INSERT INTO knowledge_articles 
                    (article_id, title, content, module, category, keywords, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING article_id
                """, (
                    article_id, title, content, module, category, keywords,
                    datetime.now(), datetime.now()
                ))
                
                result = cur.fetchone()
                conn.commit()
                print(f"✅ Article added: {article_id}")
                return result[0]
    
    def search_articles(self, query, max_results=5):
        """Search articles by query with PostgreSQL full-text search"""
        query_lower = query.lower()
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Search using multiple criteria
                cur.execute("""
                    SELECT *, 
                           CASE 
                               WHEN LOWER(title) LIKE %s THEN 3
                               ELSE 0
                           END +
                           CASE 
                               WHEN keywords && %s THEN 2
                               ELSE 0
                           END +
                           CASE 
                               WHEN LOWER(content) LIKE %s THEN 1
                               ELSE 0
                           END as relevance_score
                    FROM knowledge_articles
                    WHERE LOWER(title) LIKE %s 
                       OR keywords && %s
                       OR LOWER(content) LIKE %s
                    ORDER BY relevance_score DESC, created_at DESC
                    LIMIT %s
                """, (
                    f'%{query_lower}%',  # title search
                    query_lower.split(),  # keywords array search
                    f'%{query_lower}%',  # content search
                    f'%{query_lower}%',  # title filter
                    query_lower.split(),  # keywords filter
                    f'%{query_lower}%',  # content filter
                    max_results
                ))
                
                results = []
                for row in cur.fetchall():
                    if row['relevance_score'] > 0:
                        results.append({
                            'article': dict(row),
                            'score': row['relevance_score']
                        })
                
                return results
    
    def get_article_by_id(self, article_id):
        """Get specific article by ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM knowledge_articles 
                    WHERE article_id = %s
                """, (article_id,))
                
                result = cur.fetchone()
                return dict(result) if result else None
    
    def update_article(self, article_id, **updates):
        """Update existing article"""
        if not updates:
            return False
            
        set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
        values = list(updates.values())
        values.extend([datetime.now(), article_id])
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE knowledge_articles 
                    SET {set_clause}, updated_at = %s
                    WHERE article_id = %s
                """, values)
                
                updated = cur.rowcount > 0
                conn.commit()
                return updated
    
    def delete_article(self, article_id):
        """Delete article by ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM knowledge_articles 
                    WHERE article_id = %s
                """, (article_id,))
                
                deleted = cur.rowcount > 0
                conn.commit()
                return deleted
    
    def get_all_articles(self, module=None):
        """Get all articles, optionally filtered by module"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if module:
                    cur.execute("""
                        SELECT * FROM knowledge_articles 
                        WHERE module = %s
                        ORDER BY created_at DESC
                    """, (module,))
                else:
                    cur.execute("""
                        SELECT * FROM knowledge_articles 
                        ORDER BY created_at DESC
                    """)
                
                return [dict(row) for row in cur.fetchall()]
    
    def import_from_knowledge_base(self, knowledge_base_dict):
        """Import articles from the existing KNOWLEDGE_BASE dictionary"""
        imported_count = 0
        
        for category, documents in knowledge_base_dict.items():
            for doc in documents:
                try:
                    self.add_article(
                        title=doc['title'],
                        content=doc['content'],
                        module=doc['module'],
                        keywords=doc['keywords'],
                        category=category
                    )
                    imported_count += 1
                except Exception as e:
                    print(f"❌ Error importing article {doc.get('id', 'unknown')}: {e}")
        
        print(f"✅ Imported {imported_count} articles to PostgreSQL database")
        return imported_count

# Initialize and populate database if needed
if __name__ == "__main__":
    try:
        rag_manager = RAGKnowledgeManager()
        
        # Check if database is empty
        articles = rag_manager.get_all_articles()
        if not articles:
            print("📚 Database is empty. Would you like to import the existing knowledge base?")
            # You can import from your KNOWLEDGE_BASE here if needed
        
        print(f"📊 Database contains {len(articles)} articles")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        print("Make sure PostgreSQL database is set up in Replit")
