"""
Intent Detection Module
Routes user queries between 'scenario-editor' and 'rag-agent'
based on intent classification — using a rule-based method
with an optional LLM fallback.
"""
import os
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY1"])
model = genai.GenerativeModel("gemini-2.5-flash")

"""
Initialize the router.
use_llm: If True, enables LLM fallback for ambiguous cases.
edit_keywords, excel_terms: Keywords indicating editing intent.
question_words: Words indicating question/retrieval intent.
"""
use_llm = True

edit_keywords = [
    "make", "update", "change", "modify", "edit", "replace", "rename", "filter", "delete", "drop", "add", "remove", "save", "create",
    "format", "convert", "read", "write", "output", "double", "halve", "increase", "decrease", "multiply", "divide"
]
excel_terms = ["excel", "sheet", "df", "dataframe", "pd", "column", "row"]
question_words = ["what", "which", "who", "where", "when", "why", "how", "is", "are", "does", "do"]


def rule_based_route(user_input):
    """
    Fast rule-based classification between agents.
    """
    if user_input:
        text = user_input.lower().strip()

        # Case 1: explicit edit / manipulation
        if any(k in text for k in edit_keywords) or any(k in text for k in excel_terms):
            if any(text.startswith(q + " ") for q in question_words):
                return {
                    "selected_agent": "rag",
                    "reason": "Question phrasing detected, likely information retrieval."
                }
            else:
                return {
                    "selected_agent": "scenario_editor",
                    "reason": "Contains edit or Excel manipulation keywords."
                }

        # Case 2: pure question or retrieval
        if any(text.startswith(q + " ") for q in question_words):
            return {
                "selected_agent": "rag",
                "reason": "Question form indicates retrieval or explanation query."
            }

    # Fallback: assume rag
    return {
        "selected_agent": "rag",
        "reason": "Defaulting to RAG agent (no edit indicators found)."
    }


def llm_route(user_input: str):
    """
    LLM-based classification (fallback or enhanced reasoning).
    """
    few_shot_prompt = r"""
        You are an Agent Router in a multi-agent system:
        1. scenario_editor — edits Excel data according to user instructions.
        2. rag-agent — retrieves or explains information from a knowledge base.

        
        Examples:
        User: formulas and variables related to fix_cost, inv_cost, var_cost
        Output: {"selected_agent": "rag", "reason": "User is asking for information, not editing data."}

        User: make the inv_cost half
        Output: {"selected_agent": "scenario_editor", "reason": "User is modifying Excel data values."}

        User: "rename the column 'investment_cost' to 'inv_cost' and save the file"
        Output: {"selected_agent": "scenario_editor", "reason": " Explicit data transformation, so use the scenario-editor agent."}

        User: "read the inv_cost sheet, format the data into a pd dataframe, and double the solar value. give the output in form of an excel file, with the relevant changes saved"
        Output: {"selected_agent": "scenario_editor", "reason": "This requires reading, editing, and writing Excel data, so use the scenario-editor agent."}

        Decide which agent should handle the given input: {user_input}. 
        Output format strictly as JSON:
        {"selected_agent": "rag" or "scenario_editor", 
         "reason": "<short explanation>"}
    """

    try:
        llm = genai.GenerativeModel(model)
        resp = llm.generate_content(few_shot_prompt)
        return resp
    except Exception as e:
        print(f"[Router Warning] LLM routing failed: {e}")
        return None


def get_intent(user_input: str):
    """
    Route a user input to the appropriate sub-agent.
    Automatically uses LLM fallback if enabled and available.
    """
    rule_result = rule_based_route(user_input)

    # If LLM mode is active, only invoke for uncertain or generic retrieval cases
    if use_llm and rule_result["selected_agent"] == "rag":
        llm_result = llm_route(user_input)
        if llm_result:
            return llm_result

    return rule_result


# r = get_intent("past 10 years convex investment costs trends")
# print(r['selected_agent'])
