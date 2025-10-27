# create_index.py
from services.knowledge_service import KnowledgeService

if __name__ == "__main__":
    ks = KnowledgeService()
    ks.create_knowledge_base()
    print("\nИндексация завершена! Теперь можно запускать main.py.")