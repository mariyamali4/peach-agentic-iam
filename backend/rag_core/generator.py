from google import generativeai as genai
import os
import re

genai.configure(api_key=os.environ.get("GEMINI_API_KEY1"))

def generate_answer(query, context, docTitles, llm_model_name="gemini-2.5-flash"):
    '''
    Generate answer using LLM given the query and context chunks.
     Inputs:
        - query (str): User's question or instruction
        - context (str): Retrieved document chunks as context
        - docTitles (str): Titles of the source documents
        - llm_model_name (str): Name of the LLM model to use
     Outputs:
        - answer (str): Generated answer from the LLM
        - output_file (str or None): Name of output file if mentioned in answer
    '''
  
    prompt = f"""
        You are a helpful assistant specialized in climate scenario modeling.
        Use only the following context to answer the user’s question as precisely as possible.

        Context:
        {context}

        Question:
        {query}

        Source:
        {docTitles}

        If the text contains math notation, format your response in a readable way for user. 
        Mention the source document titles at the end of the answer.
    """
    llm = genai.GenerativeModel(llm_model_name)
    resp = llm.generate_content(prompt)
   # return resp.text

    text = resp.text
    match = re.search(r"saved to ([\w\-.]+\.xlsx)", text, re.IGNORECASE)
    output_file = match.group(1) if match else None

    return {
        "answer": text,
        "output_file": output_file
    }

    # stream = llm.generate_content(prompt, stream=True)
    # print("Gathering the information...\n")
    # final_text = ""
    # for chunk in stream:
    #     if chunk.text:
    #         print(chunk.text, end="", flush=True)   # real-time console stream
    #         final_text += chunk.text
