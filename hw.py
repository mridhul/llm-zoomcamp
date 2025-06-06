import requests 
import minsearch

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
index = minsearch.Index(
    text_fields=["question", "text", "section"],
    keyword_fields=["course"]
)

# Add documents to the index
index.fit(documents)

def search(query, course_filter=None, num_results=5):
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

# Basic search
results = search("Can i enroll for the course if I have no prior experience in data engineering?")

# Search within a specific course
results = search("Can i enroll for the course if I have no prior experience in data engineering?", course_filter="data-engineering-zoomcamp")

print(results)

