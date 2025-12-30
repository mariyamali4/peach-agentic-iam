import pandas as pd
import re
import os
import google.generativeai as genai
from backend.config.rag_config import load_rag_resources
from backend.rag_core.retriever import retrieve_chunks

genai.configure(api_key=os.environ["GEMINI_API_KEY1"])
llm_model = genai.GenerativeModel("gemini-2.5-flash")

embedding_model, index, metadata = load_rag_resources()

def run_excel_agent(instruction, input_file, output_file, max_retries=3):
    """
    Reads Excel, gets transformation code from model, executes it safely, saves new file.
    Returns structured output for front-end.
    Inputs:
    - instruction (str): User's instruction for Excel manipulation
  #  - uploaded (bool): Whether file was uploaded in input
    - input_file (str): Path to input Excel file
    - output_file (str): Path to save updated Excel file
    - max_retries (int): Number of retries for code execution on failure

    Outputs:
    - dict with keys: success (bool), code (str), logs (str)
    """
    
    logs = []

    df_input, target_sheet_name = None, None
    if input_file is not None:
        df_input = pd.read_excel(input_file)
    else:
        retriever_query = f"which CurPol-v2 sheet has information about this query: {instruction}"
        results = retrieve_chunks(retriever_query, embedding_model, index, metadata, k=1, for_rag=True)
     #   print(results['body'][0])
        target_sheet_name = results['body'][0].split('\n')[0]
        target_sheet_name = target_sheet_name.replace('Sheet: ', '')
        logs.append(f"🔍 Identified target sheet: '{target_sheet_name}'")

        xls = pd.ExcelFile(input_file)
        for sheet_name in xls.sheet_names:
            if sheet_name == target_sheet_name:
                df_input = xls.parse(sheet_name)
                break

    if df_input is None:
        raise ValueError(f"❌ No sheet named '{target_sheet_name}' found in {input_file}.")

    logs.append("📄 Loaded Excel file successfully.")
    logs.append(f"Columns: {list(df_input.columns)}")

    # Prepare prompt
    prompt = f"""
        You are a data engineer working with climate scenario data.
        You are given a pandas DataFrame named `df`.

        Schema:
        {list(df_input.columns)}

        Example rows:
        {df_input.head().to_dict(orient="records")}

        Instruction:
        {instruction}

        TASK:
        Write Python (pandas) code that applies the instruction by modifying `df` in-place.

        RULES:
        - The DataFrame is named `df`
        - Modify `df` directly (do not create a new DataFrame)
        - Use `.loc[...]` for assignments
        - Filter rows using `.str.contains(...)`, not exact matches
        - Preserve all rows and columns unless the instruction explicitly says otherwise
        - If time series behavior is implied, sort by the appropriate year column
        - Use only pandas and numpy

        FORBIDDEN:
        - File operations (read/write)
        - Defining functions or classes
        - Using os, sys, pathlib, subprocess, eval, exec

        OUTPUT:
        - Return ONLY valid Python code
        - No explanations
        - No markdown
    """



    def generate_code(extra_context=None):
        context = prompt
        if extra_context:
            context += f"\nFix the issue described here: {extra_context}"
        response = llm_model.generate_content(context)
        return re.sub(r"^```(?:python)?|```$", "", response.text.strip(), flags=re.MULTILINE).strip()

    # First attempt
    code = generate_code()
    logs.append("🧠 Model-generated code:")
    logs.append(code)

    # Safety checks
    forbidden_patterns = [
        r"os\.", r"sys\.", r"open\s*\(", r"subprocess",
        r"eval\s*\(", r"exec\s*\(", r"__", r"shutil", r"pathlib"
    ]
    if any(re.search(p, code, re.IGNORECASE) for p in forbidden_patterns):
        print(code)
        raise ValueError("⚠️ Unsafe code detected! Execution blocked.")
    
    # Whiteliseted imports
    #allowed_imports = ["import numpy", "import numpy as np", "import pandas", "import pandas as pd"]

    import_lines = re.findall(r"^\s*import\s+[^\n]+", code, flags=re.MULTILINE)
    for line in import_lines:
        if not any(pkg in line for pkg in ["numpy", "pandas"]):
            raise ValueError(f"⚠️ Unsafe import detected: '{line.strip()}' — only numpy and pandas are allowed.")

    # --- Auto-inject safe imports if missing ---
    if "import pandas" not in code:
        logs.append("ℹ️ Auto-added: import pandas as pd")
        code = "import pandas as pd\n" + code
    if "import numpy" not in code:
        logs.append("ℹ️ Auto-added: import numpy as np")
        code = "import numpy as np\n" + code

    # Try executing
    for attempt in range(max_retries + 1):
        try:
            local_env = {"df": df_input.copy(), "pd": pd}
            exec(code, {}, local_env)
            df_new = local_env.get("df")

            if not isinstance(df_new, pd.DataFrame):
                raise ValueError("No valid DataFrame 'df' produced.")

            df_new.to_excel(output_file, index=False)
            logs.append(f"✅ Saved updated file to {output_file}")
            return {"success": True, "code": code, "logs": "\n".join(logs)}

        except Exception as e:
            logs.append(f"❌ Error executing code: {e}")
            if attempt < max_retries:
                logs.append("🔁 Retrying with fix...")
                code = generate_code(extra_context=str(e))
            else:
                return {"success": False, "code": code, "logs": "\n".join(logs)}
