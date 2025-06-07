import os
import requests 
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# Elasticsearch configuration
ELASTICSEARCH_INDEX = "faq_index"
ELASTICSEARCH_HOST = "http://127.0.0.1:9200"

def connect_elasticsearch():
    """Try to connect to Elasticsearch with different configurations"""
    # Try different connection parameters
    connection_params = [
        # Basic connection with basic auth disabled (for local development)
        {
            "hosts": ["http://localhost:9200"],
            "verify_certs": False,
            "ssl_show_warn": False,
            "request_timeout": 30,
            "max_retries": 3,
            "retry_on_timeout": True
        },
        # Connection with basic auth (in case it's enabled)
        {
            "hosts": ["http://localhost:9200"],
            "basic_auth": ("elastic", "changeme"),
            "verify_certs": False,
            "ssl_show_warn": False
        },
        # Direct IP connection
        {
            "hosts": ["http://127.0.0.1:9200"],
            "verify_certs": False,
            "ssl_show_warn": False
        },
        # Connection with basic auth to IP
        {
            "hosts": ["http://127.0.0.1:9200"],
            "basic_auth": ("elastic", "changeme"),
            "verify_certs": False,
            "ssl_show_warn": False
        }
    ]
    
    for params in connection_params:
        try:
            print(f"\nTrying to connect to Elasticsearch at {params['hosts'][0]}")
            print(f"Using parameters: {', '.join([f'{k}=...' for k in params.keys()])}")
            es = Elasticsearch(**params)
            
            # Try to get cluster info directly
            try:
                info = es.info()
                print("✓ Successfully connected to Elasticsearch!")
                print("\nElasticsearch cluster info:")
                print(f"Version: {info['version']['number']}")
                print(f"Cluster Name: {info['cluster_name']}")
                print(f"Node Name: {info.get('name', 'N/A')}")
                return es
            except Exception as info_error:
                print(f"✗ Could not get cluster info: {str(info_error)}")
                
            # If we got here, try a simple ping
            try:
                if es.ping():
                    print("✓ Ping successful but couldn't get cluster info")
                    return es
                else:
                    print("✗ Ping failed")
            except Exception as ping_error:
                print(f"✗ Ping error: {str(ping_error)}")
                
        except Exception as e:
            import traceback
            print(f"✗ Connection error: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
    
    return None

# Initialize Elasticsearch client
try:
    print("\n=== Testing Elasticsearch Connection ===")
    es = connect_elasticsearch()
    if not es:
        print("\n❌ Could not connect to Elasticsearch. Please check if it's running and accessible.")
        print("You can start Elasticsearch using Docker with this command:")
        print("docker run -p 9200:9200 -p 9300:9300 -e \"discovery.type=single-node\" -e \"xpack.security.enabled=false\" docker.elastic.co/elasticsearch/elasticsearch:8.11.0")
        print("\nNote: The command above disables security for easier local development.")
        exit(1)
except Exception as e:
    print(f"Error connecting to Elasticsearch: {str(e)}")
    print("\nTo run Elasticsearch using Docker, use this command:")
    print("docker run -p 9200:9200 -p 9300:9300 -e \"discovery.type=single-node\" docker.elastic.co/elasticsearch/elasticsearch:8.11.0")
    print("\nOr install Elasticsearch locally from: https://www.elastic.co/guide/en/elasticsearch/reference/current/install-elasticsearch.html")
    exit(1)

def initialize_index():
    """Initialize Elasticsearch index with FAQ data"""
    print("Loading FAQ data...")
    try:
        docs_url = 'https://github.com/DataTalksClub/llm-zoomcamp/blob/main/01-intro/documents.json?raw=1'
        docs_response = requests.get(docs_url)
        docs_response.raise_for_status()
        documents_raw = docs_response.json()
    except Exception as e:
        print(f"Error loading FAQ data: {str(e)}")
        return None

    try:
        # Check if index exists, delete if it does
        if es.indices.exists(index=ELASTICSEARCH_INDEX):
            es.indices.delete(index=ELASTICSEARCH_INDEX)
    except Exception as e:
        print(f"Error managing Elasticsearch index: {str(e)}")
        return None
    
    # Create index with mapping
    mapping = {
        "mappings": {
            "properties": {
                "course": {"type": "keyword"},
                "section": {"type": "text"},
                "question": {
                    "type": "text",
                    "fields": {
                        "boosted": {
                            "type": "text",
                            "analyzer": "standard"
                        }
                    }
                },
                "text": {"type": "text"},
                "section_keyword": {"type": "keyword"}
            }
        }
    }
    
    # Create the index with the mapping
    try:
        es.indices.create(
            index=ELASTICSEARCH_INDEX,
            mappings=mapping["mappings"]
        )
    except Exception as e:
        print(f"Error creating index: {str(e)}")
        raise
    
    # Prepare documents for bulk indexing
    actions = []
    doc_id = 1
    
    for course in documents_raw:
        course_name = course['course']
        for doc in course['documents']:
            # Create a document with all necessary fields
            doc_data = {
                "_index": ELASTICSEARCH_INDEX,
                "_id": doc_id,
                "_source": {
                    "course": course_name,
                    "section": doc.get('section', ''),
                    "question": doc.get('question', ''),
                    "text": doc.get('text', ''),
                    "section_keyword": doc.get('section', '')
                }
            }
            actions.append(doc_data)
            doc_id += 1
    
    # Bulk index the documents
    success, _ = bulk(es, actions)
    print(f"Indexed {success} documents")
    
    # Refresh the index to make the documents searchable
    es.indices.refresh(index=ELASTICSEARCH_INDEX)
    return es

# Initialize the index when the module loads
es = initialize_index()
if es is None:
    exit(1)

def search_faq(query, course_filter=None, num_results=3):
    """
    Search the FAQ index using Elasticsearch
    
    Args:
        query: Search query string
        course_filter: Optional course name to filter by
        num_results: Number of results to return
        
    Returns:
        List of matching documents with their _source
    """
    # Build the query with boosting
    search_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "bool": {
                            "should": [
                                {"match": {"question": {"query": query, "boost": 3.0}}},
                                {"match": {"question.boosted": {"query": query, "boost": 2.0}}},
                                {"match": {"text": query}},
                                {"match": {"section": {"query": query, "boost": 0.5}}}
                            ],
                            "minimum_should_match": 1
                        }
                    }
                ]
            }
        },
        "size": num_results,
        "min_score": 0.1  # Only return results with a minimum score
    }
    
    # Add course filter if provided
    if course_filter:
        search_body["query"]["bool"]["filter"] = [{"term": {"course": course_filter}}]
    
    try:
        response = es.search(index=ELASTICSEARCH_INDEX, body=search_body)
        return [hit["_source"] for hit in response["hits"]["hits"]]
    except Exception as e:
        print(f"Error searching Elasticsearch: {str(e)}")
        return []

def build_prompt(query, results):
    """Build a prompt for the LLM using the search results"""
    if not results:
        return "I couldn't find any relevant information to answer your question."
    
    context = ""
    for i, result in enumerate(results, 1):
        context += f"\n--- Result {i} ---\n"
        context += f"Course: {result.get('course', 'N/A')}\n"
        if 'section' in result:
            context += f"Section: {result['section']}\n"
        if 'question' in result:
            context += f"Question: {result['question']}\n"
        if 'text' in result:
            context += f"Answer: {result['text']}\n"
    
    prompt = f"""You are a helpful teaching assistant. Answer the QUESTION based on the CONTEXT from the FAQ database.
If the context doesn't contain relevant information, say that you don't know the answer.

QUESTION: {query}

CONTEXT:
{context}

Answer the question based on the context above. If the context doesn't contain relevant information, say that you don't know the answer."""
    
    return prompt

def llm_call(prompt):
    """Make a call to Groq with the given prompt"""
    try:
        from groq import Groq
        
        if not os.environ.get("GROQ_API_KEY"):
            print("Error: GROQ_API_KEY environment variable not set")
            return "Error: GROQ_API_KEY environment variable not set"
            
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
        print("\nGenerating response...\n")
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024,
            stream=True
        )
        
        response = ""
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            print(content, end="", flush=True)
            response += content
            
        return response
        
    except ImportError:
        print("Groq library not found. Please install it with: pip install groq")
        return "Error: Groq library not installed"
    except Exception as e:
        print(f"Error calling Groq API: {str(e)}")
        return f"Error: {str(e)}"

def rag(query, course_filter=None):
    """
    Run the RAG pipeline
    """
    print(f"\nSearching for: {query}")
    if course_filter:
        print(f"Filtering by course: {course_filter}")
    
    # Search the FAQ
    results = search_faq(query, course_filter=course_filter)
    
    if not results:
        print("No relevant results found.")
        return
    
    # Build and display the prompt
    prompt = build_prompt(query, results)
    
    # Get response from LLM
    return llm_call(prompt)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FAQ Search and Answer System")
    parser.add_argument("query", nargs="?", help="Your question")
    parser.add_argument("--course", help="Filter by course name (e.g., data-engineering-zoomcamp)")
    args = parser.parse_args()
    
    if not args.query:
        # Interactive mode
        print("FAQ Search System (type 'exit' to quit)")
        print("Enter your question below:")
        while True:
            try:
                query = input("\n> ")
                if query.lower() in ('exit', 'quit', 'q'):
                    break
                if query.strip():
                    rag(query, course_filter=args.course)
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {str(e)}")
    else:
        # Command-line mode
        rag(args.query, course_filter=args.course)

