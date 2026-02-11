# orchestrator_agent.py
import os
from datetime import datetime, timezone, timedelta

from backend.intent_detection import get_intent
from backend.scenario_editor import run_scenario_agent

from backend.rag_engine import query_rag
from backend.conv_history import init_db, new_conversation, log_turn

PKT = timezone(timedelta(hours=5))

# Ensure DB is ready once
init_db()
base_scenario_path = r"D:\lums-python-programming\thesis\wit-messageix-docs\MESSAGEix-Pakistan-CurPol.xlsx"

def orchestrate(instruction, input_file=None):
    print("ORCHESTRATE CALLED WITH:", repr(instruction))

    """
    Central orchestration layer:
    - intent detection
    - agent routing
    - DB logging
    """
    uploaded = input_file is not None
    timestamp = datetime.now(PKT).strftime("%Y%m%d-%H%M%S")

    # ---- conversation lifecycle ----
    conv_id = new_conversation()

    routing = get_intent(instruction)
    mode = routing["selected_agent"]
    routing_reason = routing.get("reason", "")

    # ---------- SCENARIO EDITOR ----------
    if mode == "scenario_editor":
        if input_file is None:
            input_file = base_scenario_path

        output_file = os.path.join(
                "data/history/outputs",
                os.path.basename(input_file).replace(".xlsx", f"-updated-{timestamp}.xlsx")
            )

        result = run_scenario_agent(
            instruction=instruction,
            input_file=input_file,
            uploaded=uploaded,
            output_file=output_file
        )

        reply = f"✅ Scenario updated: `{os.path.basename(output_file)}`"

        stored_reply = (
            f"{reply}\n\n"
            f"Generated code:\n{result.get('code')}"
        )

        # ---- DB LOGGING ----
        log_turn(
            conv_id=conv_id,
            mode=mode,
            routing_reason=routing_reason,
            timestamp=timestamp,
            query=instruction,
            response=stored_reply,
            output_file_name=os.path.basename(output_file)
        )

        return {
            "mode": mode,
            "reply": reply,
            "output_file": output_file,
            "code": result.get("code"),
            "logs": result.get("logs"),
            "timestamp": timestamp
        }

    # ---------- RAG ----------
    elif mode == "rag":
        reply = query_rag(instruction)

        log_turn(
            conv_id=conv_id,
            mode=mode,
            routing_reason=routing_reason,
            timestamp=timestamp,
            query=instruction,
            response=reply,
            output_file_name=None
        )

        return {
            "mode": mode,
            "reply": reply,
            "timestamp": timestamp
        }

    else:
        raise ValueError(f"Unknown agent mode: {mode}")
