import pandas as pd
import re
import os
import google.generativeai as genai
from backend.config.rag_config import load_rag_resources
from backend.rag_core.retriever import retrieve_chunks

genai.configure(api_key=os.environ["GEMINI_API_KEY1"])
llm_model = genai.GenerativeModel("gemini-2.5-flash")

embedding_model, index, metadata = load_rag_resources()

def run_excel_agent(instruction, uploaded, input_file, output_file, max_retries=3):
    """
    Reads Excel, gets transformation code from model, executes it safely, saves new file.
    Returns structured output for front-end.
    Inputs:
    - instruction (str): User's instruction for Excel manipulation
    - uploaded (bool): Whether file was uploaded in input
    - input_file (str): Path to input Excel file
    - output_file (str): Path to save updated Excel file
    - max_retries (int): Number of retries for code execution on failure

    Outputs:
    - dict with keys: success (bool), code (str), logs (str)
    """
    
    logs = []

    df_input, target_sheet_name = None, None
    if uploaded == False:
        retriever_query = f"which sheet has information about this query: {instruction}"
        results = retrieve_chunks(retriever_query, embedding_model, index, metadata, k=1, for_rag=True)
        target_sheet_name = results['body'][0].split('\n')[0]
        target_sheet_name = target_sheet_name.replace('Sheet: ', '')
        logs.append(f"🔍 Identified target sheet: '{target_sheet_name}'")

        xls = pd.ExcelFile(input_file)
        for sheet_name in xls.sheet_names:
            if sheet_name == target_sheet_name:
                df_input = xls.parse(sheet_name)
                break

    else:
        df_input = pd.read_excel(input_file)

    if df_input is None:
        raise ValueError(f"❌ No sheet named '{target_sheet_name}' found in {input_file}.")

    logs.append("📄 Loaded Excel file successfully.")
    logs.append(f"Columns: {list(df_input.columns)}")

    # Prepare prompt
    prompt = f"""
        You are a data engineer for climate scenarios.
        Given this schema:
        Columns: {list(df_input.columns)}

        Example Rows:
        {df_input.head().values.tolist()}

        Instruction: {instruction}

        Write Python (pandas) code to apply this transformation.
        The DataFrame is named `df`.
        Return only the code, without any explanation or markdown formatting.
        Make sure to save the updated columns back to `df`.
        Ensure the code is safe and does not use any file operations or unsafe libraries.
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
