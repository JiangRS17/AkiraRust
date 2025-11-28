import sys
import os
from Miri_Record.analyzer.miri_runner import run_miri_and_parse
from Miri_Record.analyzer.ub_analyzer import analyze_ub
from Miri_Record.analyzer.semantic_diff import compute_semantic_diff
from Miri_Record.analyzer.diff_complexity import compute_diff_complexity

def analyze_rust_fix(original_code, edited_code):
    """
    综合分析Rust修复代码的未定义行为、语义偏离度和修复复杂度。
    返回结构化结果。
    """
    # 1. 用Miri检测修复代码
    miri_log = run_miri_and_parse(edited_code)
    # 2. 统计未定义行为（传入miri_log和修复后代码）
    ub_report = analyze_ub(miri_log, edited_code)
    # 3. 语义偏离度分析
    semantic_result = compute_semantic_diff(original_code, edited_code, miri_log)
    # 4. 修复diff复杂度评估
    diff_result = compute_diff_complexity(original_code, edited_code)
    return {
        "ub_report": ub_report,
        "semantic_diff": semantic_result,
        "diff_complexity": diff_result,
        "miri_log": miri_log
    }

def batch_analyze():
    src_dir = "/home/wyc/rust_thetis_test/rust_one_trial/"
    fix_dir = "/home/wyc/save_improvement_file/edited_code_saving/"
    src_files = [f for f in os.listdir(src_dir) if f.endswith('.rs')]
    for src_file in src_files:
        path_name = src_file[:-3]  # 去掉 .rs
        original_code_path = os.path.join(src_dir, src_file)
        edited_code_path = os.path.join(fix_dir, f"{path_name}_edited.rs")
        if not os.path.exists(edited_code_path):
            print(f"[跳过] 未找到修复文件: {edited_code_path}")
            continue
        print(f"\n==== 分析: {path_name} ====")
        with open(original_code_path, 'r') as f:
            original_code = f.read()
        with open(edited_code_path, 'r') as f:
            edited_code = f.read()
        result = analyze_rust_fix(original_code, edited_code)
        print("[未定义行为统计]", result["ub_report"])
        print("[语义偏离度]", result["semantic_diff"])
        print("[修复复杂度]", result["diff_complexity"])
        # 如需查看Miri原始日志可取消注释
        # print("[Miri日志]\n", result["miri_log"])
        # 设置权重：所有语法错误的权重都设置为0.5，语义偏离度都设置为0.1，修复复杂度设置为0.01
        ub = result['ub_report']['ub_counts']
        Unchecked_t = ub['unchecked operations'] * 0.5
        Global_t = ub['global objects'] * 0.5
        Interoperability_t = ub['interoperability'] * 0.5
        Low_t = ub['low-level control'] * 0.5
        Concurrent_t = ub['concurrent objects'] * 0.5
        Other_t = ub['other UBs'] * 0.5
        Semantic_t = result['semantic_diff']['hallucination_index'] * 0.1
        Diff_t = result['diff_complexity']['diff_ratio'] * 0.01
        Evaluation_t = Unchecked_t + Global_t + Interoperability_t + Low_t + Concurrent_t + Other_t + Semantic_t + Diff_t
        print("[综合评估分数]:",Evaluation_t)
if __name__ == "__main__":
    batch_analyze()

