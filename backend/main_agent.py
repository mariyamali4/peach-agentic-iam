from backend.scenario_editor import run_excel_agent
from backend.rag_agent import query_rag
import os
from datetime import datetime, timezone, timedelta
PKT = timezone(timedelta(hours=5))

def process_instruction(instruction, input_file=None, mode="scenario_editor"):
   # timestamp = datetime.now(PKT).isoformat()
    timestamp = datetime.now(PKT).strftime("%Y%m%d-%H%M%S") # e.g. timestamp = 20251105-163919, for output file naming

    if mode == "scenario_editor":
        """Wrapper that calls the backend scenario editing pipeline."""
        output_file = os.path.join("data/outputs", os.path.basename(input_file).replace(".xlsx", f"-updated-{timestamp}.xlsx"))

        result = run_excel_agent(
            instruction=instruction,
            input_file=input_file,
            output_file=output_file
        )

        return {
            "mode": "scenario_editor",
            "output_file": output_file,
            "code": result["code"],
            "logs": result["logs"],
            "timestamp": timestamp
        }

    elif mode == "rag":
        # Directly query the RAG agent
        answer = query_rag(instruction)
        return {
            "mode": "rag",
            "answer": answer,
            "timestamp": timestamp
        }

    else:
        raise ValueError("Invalid mode. Choose 'excel' or 'rag'.")    

