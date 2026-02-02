import time
import os
from dotenv import load_dotenv
from database_manager import DatabaseManager

load_dotenv() 

def run_benchmark():
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in .env file.")
        return

    db_mgr = DatabaseManager()
    
    # Examples
    test_queries = [
        "ما هو اسم الصياد؟",
        "ما هي انواع الاقتصاد",
    ]
    
    print(" Starting the Benchmarking Suite...\n")
    print(f"{'Question':<40} | {'Time (s)':<10} | {'Similarity Score'}")
    print("-" * 75)
    
    for query in test_queries:
        start_time = time.time()
        results = db_mgr.query_documents(query, k=1)
        end_time = time.time()
        
        latency = round(end_time - start_time, 4)
        
        if results and len(results) > 0:
            score = round(results[0][1], 4)
            print(f"{query:<40} | {latency:<10} | {score}")
        else:
            print(f"{query:<40} | {latency:<10} | No results found")

if __name__ == "__main__":
    run_benchmark()