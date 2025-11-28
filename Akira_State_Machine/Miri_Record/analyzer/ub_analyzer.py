import re
from Miri_Record.analyzer.agent import chat_with_agent
import json

def parse_json_block(text: str) -> dict:
    """
    从任意字符串中提取 ```json ... ``` 里的 JSON 并解析成 dict。
    如果找不到 code block，则直接尝试全文解析。
    """
    # 1. 优先匹配 ```json 包裹的内容
    m = re.search(r'```json\s*(\{.*?\})\s*```', text, flags=re.S)
    if m:
        return json.loads(m.group(1))
    # 2. 退化为全文解析
    return json.loads(text)

def analyze_ub(miri_log, edited_code, max_retry=3):
    """
    利用大模型分析Miri日志和修复后Rust代码，统计常见未定义行为（UB）类型及数量。
    返回：字典，key为UB类型，value为数量。
    如果无法解析JSON，则让大模型重新生成回复，最多重试max_retry次。
    """
    messages_template = [
        {"role": "system", "content": "You are an expert in Rust undefined behavior detection."},
        {"role": "user", "content": (
            "Given the following unsafe Rust code and its Miri log, check the code and its Miri log.\n"
            f"Rust code:\n{edited_code}\nMiri log:\n{miri_log}\n"
            "First of all, remember the Rust Code surely exsits UBs!\n"
            "Analyze step by step:\n"
            "(1).Check the Miri log of the Rust code, especially error messages.\n"
            "(2).Examine the unsafe Rust code carefully, especially focus on its Undefined Behaviors.\n"
            "(3).Identify all types of undefined behavior (UB) present in the code.\n"
            "UB Types: (a).unchecked operations(such as raw pointer, mut-static-var, union), (b).global objects(such as mutable static variable), (c).interoperability(such as unsafe fn (extern 'C'), (d).low-level control(union, raw pointer, unsafe fn), (e).concurrent objects(Send/Sync trait).\n"
            "If the detected UB does not belong to the above categories, it should be classified as 'other UBs'.\n"
            "(4).Based on types of UBs, count the number of UBs of each type."
            "Do NOT output thinking process!!! Only return a JSON object where keys are UB types and values are their counts finally."
            "Do NOT output thinking process!!! Only output in the JSON format as below finally:(IMPORTANT: MUST IN FORMAT BELOW)"
            '```json{"ub_counts": {"unchecked operations": {num1}, "global objects": {num2}, "interoperability": {num3}, "low-level control": {num4}, "concurrent objects": {num5}, "other UBs": {num6}}}```'
        )}
    ]
    if miri_log != '':
        retry = 0
        while retry < max_retry:
            reply = chat_with_agent(messages_template)
            # 打印大模型回复内容
            print(reply)
            try:
                # 尝试直接解析模型返回的JSON
                result = json.loads(reply)
                if isinstance(result, dict):
                    return result
            except Exception:
                pass
            try:
                # 若无法解析，尝试解析 code block
                UB_dict = parse_json_block(reply)
                if isinstance(UB_dict, dict):
                    return UB_dict
            except Exception:
                pass
            retry += 1
        # 多次重试后仍失败，返回默认值或抛出异常
        return {'error': 'Failed to get valid JSON from model after retries'}
    if miri_log == '':
        return {'ub_counts': {'unchecked operations': 0, 'global objects': 0, 'interoperability': 0, 'low-level control': 0, 'concurrent objects': 0, 'other UBs': 0}}

