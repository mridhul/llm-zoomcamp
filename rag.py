import minsearch
import json
import os

query = "Can i enroll for the course if I have no prior experience in data engineering?"

def search():
    with open('documents.json', 'rt') as f_in:
        docs_raw = json.load(f_in)

    documents = []

    for course_dict in docs_raw:
        for doc in course_dict['documents']:
            doc['course'] = course_dict['course']
            documents.append(doc)

    index = minsearch.Index(
    text_fields=["question", "text", "section"],
    keyword_fields=["course"]
)

    index.fit(documents)


    results = index.search(
    query, 
    filter_dict={'course': 'data-engineering-zoomcamp'}, 
    boost_dict={'question': 3.0, 'section': 0.5}, 
    num_results=5
)
    
    return results

results = search()

#print(results)
if not results:
    print("No results found for the query.")
    exit()

def build_prompt(query,results):
    context = ""
    context = context + "section: " + results[0]['section'] + "\n" + "question: " + results[0]['question'] + "\n" + "answer: " + results[0]['text'] + "\n"
    print("Context for the query: ", context)

    prompt_template = """
    You are a helpful teaching assistant. Anser the QUESTION based on the CONTEXT in the FAQ database.
    use the CONTEXT to answer the question.
    QUESTION: {query}
    CONTEXT: {context}
    """.strip()
    prompt = prompt_template.format(query=query, context=context).strip()
    return prompt

prompt = build_prompt(query,results)

#Make a call to Groq
def llm_call(prompt):
    """
    Make a call to Groq with the given prompt.
    """
    print("Calling Groq with the prompt...")
    #print(prompt)
    # Import Groq client    
    import os
    from groq import Groq


    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
        {
            "role": "user",
            "content": prompt
        }
        ],
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=True,
        stop=None,
    )

    response_text = ""
    for chunk in completion:
        content = chunk.choices[0].delta.content or ""
        print(content, end="")  # Still show it on console
        response_text += content

    return response_text

def rag(query):
    """
    Run the RAG pipeline.
    """
    search_results = search()
    if not search_results:
        print("No results found for the query.")
        return None
    prompt = build_prompt(query, search_results)
    response = llm_call(prompt)
    return response

if __name__ == "__main__":
    response = rag(query)
    if response:
        print("\nResponse from the LLM:")
        print(response)
    else:
        print("No response from the LLM.")