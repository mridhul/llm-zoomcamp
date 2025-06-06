import os
import requests 
import minsearch

# Initialize the FAQ index
def initialize_index():
    print("Loading FAQ data...")
    docs_url = 'https://github.com/DataTalksClub/llm-zoomcamp/blob/main/01-intro/documents.json?raw=1'
    docs_response = requests.get(docs_url)
    documents_raw = docs_response.json()

    documents = []
    for course in documents_raw:
        course_name = course['course']
        for doc in course['documents']:
            doc['course'] = course_name
            documents.append(doc)

    # Create search index
    print("Indexing documents...")
    index = minsearch.Index(
        text_fields=["question", "text", "section"],
        keyword_fields=["course"]
    )
    index.fit(documents)
    print(f"Indexed {len(documents)} documents")
    return index

# Initialize the index when the module loads
index = initialize_index()

def search_faq(query, course_filter=None, num_results=3):
    """
    Search the FAQ index
    
    Args:
        query: Search query string
        course_filter: Optional course name to filter by
        num_results: Number of results to return
        
    Returns:
        List of matching documents
    """
    filter_dict = {'course': course_filter} if course_filter else None
    return index.search(
        query,
        filter_dict=filter_dict,
        boost_dict={'question': 3.0, 'section': 0.5},
        num_results=num_results
    )

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

