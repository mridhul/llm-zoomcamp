import minsearch
import json
import os

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

query = "Can i enroll for the course if I have no prior experience in data engineering?"

results = index.search(
    query, 
    filter_dict={'course': 'data-engineering-zoomcamp'}, 
    boost_dict={'question': 3.0, 'section': 0.5}, 
    num_results=5
)

#print(results)
if not results:
    print("No results found for the query.")
    exit()

context = ""
context = context + "section: " + results[0]['section'] + "\n" + "question: " + results[0]['question'] + "\n" + "answer: " + results[0]['text'] + "\n"
print("Context for the query: ", context)

prompt_template = """
You are a helpful teaching assistant. Anser the QUESTION based on the CONTEXT in the FAQ database.
use the CONTEXT to answer the question. Anything not in the CONTEXT, do not answer and just return NONE.
QUESTION: {query}
CONTEXT: {context}
""".strip()
prompt = prompt_template.format(query=query, context=context).strip()

#Make a call to Groq
from groq import Groq
key=os.getenv('GROQ_API_KEY')

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

for chunk in completion:
    print(chunk.choices[0].delta.content or "", end="")
