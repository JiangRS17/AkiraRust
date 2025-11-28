import os
import re
import pandas as pd

# 根目录和子目录
root_dir = "/home/wyc/Desktop/defect_data_record"
sub_dirs = ["alloc", "both_borrows", "concurrency", "dangling_pointers", "function_pointers"]

# Excel记录列表
records = []

# 所有 agent
agents = ["Agent1", "Agent2", "Agent3", "Agent4", "Agent5"]

for sub_dir in sub_dirs:
    full_path = os.path.join(root_dir, sub_dir)
    for filename in os.listdir(full_path):
        if filename.endswith(".txt"):
            case_name = sub_dir + '/' + filename.replace("_defect_record", "").replace(".txt", "")
            with open(os.path.join(full_path, filename), "r", encoding="utf-8") as f:
                content = f.read()

            # 提取 Code Feature（默认在第一行）
            match = re.search(r'Code Features:\s*(.*)', content)
            code_feature = match.group(1).strip() if match else ""

            # 分割所有 Solution
            solutions = re.split(r'Solution \d+', content)
            solutions = [s.strip() for s in solutions if s.strip()]

            total_rounds = 0
            total_success = 0
            agent_success_counts = {agent: 0 for agent in agents}

            for sol in solutions:
                # 统计轮次
                rounds = re.findall(r'Agents Excuted ===Round\d+===\s*:\s*(.*)', sol)
                total_rounds += len(rounds)

                # 统计每个成功轮次中的 agent
                successful_rounds = re.finditer(r'Agents Excuted ===Round\d+===\s*:\s*(.*?Solved!)', sol)
                for match in successful_rounds:
                    total_success += 1  # 成功轮次数
                    line = match.group(1)
                    used_agents = re.findall(r'Agent\d+', line)
                    for ag in used_agents:
                        if ag in agent_success_counts:
                            agent_success_counts[ag] += 1

            # 计算 agent 成功率
            success_rates = {}
            for ag in agents:
                rate = agent_success_counts[ag] / total_rounds if total_rounds > 0 else 0.0
                success_rates[ag] = round(rate, 3)

            # 构建记录
            row = {
                "Case": case_name,
                "Code Feature": code_feature,
                "Total Rounds": total_rounds,
                "Total Success Rate": round(total_success / total_rounds, 3) if total_rounds > 0 else 0.0,
            }
            for ag in agents:
                row[f"{ag} Success Rate"] = success_rates[ag]

            records.append(row)

# 转换为 DataFrame 并导出为 Excel
df = pd.DataFrame(records)
output_path = "/home/wyc/Desktop/rustlathe_analysis_result.xlsx"
df.to_excel(output_path, index=False)
print(f"Excel 已生成: {output_path}")
