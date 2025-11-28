from Miri_Record.analyzer.Code_Evaluate import agent_code_analyze,agent_fault_localize,score_code
from Miri_Record.analyzer.miri_runner import run_miri_and_parse
def compute_semantic_diff(original_code, edited_code, miri_log):
    """
    Use LLM to compare the original and fixed Rust code, analyze semantic deviation, and return a score between 0~1 (higher means more deviation).
    """
    error_message = miri_log
    analysis = agent_code_analyze(original_code,error_message,edited_code)
    fault_localization = agent_fault_localize(original_code,error_message,edited_code,analysis)
    score = score_code(fault_localization)
    return {"hallucination_index": 1-score}
