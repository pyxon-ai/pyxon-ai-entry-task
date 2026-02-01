"""
Simple test script for the /api/v1/chunk endpoint
"""
import requests
import json

# Configuration
API_URL = "http://127.0.0.1:8000/api/v1/chunk"
TEST_FILE = "test_document.txt"

def test_chunk_endpoint():
    """Test the chunk endpoint with a sample document"""
    
    # Prepare the file
    with open(TEST_FILE, 'rb') as f:
        files = {'file': (TEST_FILE, f, 'text/plain')}
        
        print(f"Testing endpoint: {API_URL}")
        print(f"File: {TEST_FILE}")
        print("-" * 60)
        
        # Make the request
        response = requests.post(API_URL, files=files)
        
        # Check response
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success!")
            print(f"Strategy: {data['strategy']}")
            print(f"Total chunks: {data['total_chunks']}")
            print("-" * 60)
            print("Sample chunks:")
            for idx, chunk in enumerate(data['chunks'][:3]):  # Show first 3 chunks
                print(f"\nChunk {idx}:")
                print(f"Content: {chunk['content'][:100]}...")
                print(f"Metadata: {chunk['metadata']}")
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    try:
        test_chunk_endpoint()
    except requests.exceptions.ConnectionError:
        print("✗ Error: Could not connect to the server.")
        print("Make sure the server is running: uvicorn main:app --reload")
    except FileNotFoundError:
        print(f"✗ Error: Test file '{TEST_FILE}' not found.")
    except Exception as e:
        print(f"✗ Error: {e}")
