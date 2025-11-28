import numpy as np
import psycopg2
from pathlib import Path
import matplotlib.pyplot as plt
import time
from psycopg2.extensions import register_adapter, AsIs
psycopg2.extensions.register_adapter(np.float32, psycopg2._psycopg.AsIs)

from Test_Slow_Thinking import read_code_from_file, run_cargo_miri, error_calculate, refine, get_embeddings, agent_function_call
from Test_Code_Evaluate import agent_code_analyze, agent_fault_localize, score_code
from Miri_Record.Miri_Record import analyze_rust_fix

# ============ 全局评估波形记录 ============
Evaluation_list = []


def evaluation_collect(original_rust_code, rust_code):
    """对修复后的Rust代码进行综合评估"""
    result = analyze_rust_fix(original_rust_code, rust_code)
    if original_rust_code == rust_code:
        result['semantic_diff']['hallucination_index'] = 0.0

    print("[未定义行为统计]", result["ub_report"])
    print("[语义偏离度]", result["semantic_diff"])
    print("[修复复杂度]", result["diff_complexity"])

    ub = result['ub_report']['ub_counts']
    Unchecked_t = ub['unchecked operations'] * 0.5
    Global_t = ub['global objects'] * 0.5
    Interoperability_t = ub['interoperability'] * 0.5
    Low_t = ub['low-level control'] * 0.5
    Concurrent_t = ub['concurrent objects'] * 0.5
    Other_t = ub['other UBs'] * 0.5
    Semantic_t = result['semantic_diff']['hallucination_index'] * 0.1
    Diff_t = result['diff_complexity']['diff_ratio'] * 0.01

    Evaluation_t = (
        Unchecked_t + Global_t + Interoperability_t + Low_t +
        Concurrent_t + Other_t + Semantic_t + Diff_t
    )

    print("[综合评估分数]:", Evaluation_t)
    return Evaluation_t


# ============ 状态机核心实现 ============
class StateMachine:
    def __init__(self):
        self.state = "INIT"
        self.repair_count = 0
        self.max_repair = 7
        self.max_beyond_limits = 2
        self.case_name_count = {}
        self.best_rust_code = None
        self.best_evaluation_t = None

    def run(self, rust_code):
        """运行状态机"""
        self.state = "INIT"
        print(f"进入状态: {self.state}")
        original_rust_code = rust_code
        self.beyond_limits = 0

        while self.state != "END":
            if self.state == "INIT":
                self.repair_count = 0
                rust_code = original_rust_code
                self.used_agents = set()

                Evaluation_t = evaluation_collect(original_rust_code, rust_code)
                global Original_Evaluation_t
                Original_Evaluation_t = Evaluation_t
                global Evaluation_list
                Evaluation_list = [Evaluation_t]

                # 初始化最优状态
                self.best_rust_code = rust_code
                self.best_evaluation_t = Evaluation_t

                error_message, error_exist = self.miri_check(rust_code)
                original_error_message = error_message

                if error_exist:
                    self.state = "SELECT_AGENT"
                else:
                    pass_code_file = f'/home/wyc/save_improvement_file/pass/{PATH_NAME}_passed.rs'
                    with open(pass_code_file, 'w') as file:
                        file.write(original_rust_code)
                    self.state = "END"

            elif self.state == "SELECT_AGENT":
                agent_number = self.select_agent(rust_code, error_message)
                self.state = "AGENT_REPAIR"
                self.current_agent = agent_number

            elif self.state == "AGENT_REPAIR":
                rust_code = self.current_agent_repair(rust_code, self.current_agent, error_message)
                print(f"中间代码:\n{rust_code}\n")

                Evaluation_t = evaluation_collect(original_rust_code, rust_code)
                Evaluation_list.append(Evaluation_t)

                # (1) 若比当前最优更好，更新best
                if self.best_evaluation_t is None or Evaluation_t < self.best_evaluation_t:
                    self.best_evaluation_t = Evaluation_t
                    self.best_rust_code = rust_code

                # (2) 若恶化（≥Original_Evaluation_t+1.0），回滚
                if Evaluation_t >= Original_Evaluation_t + 1.0:
                    print(f"[回滚触发] 原始Evaluation_t为{Original_Evaluation_t}\n当前 Evaluation_t = {Evaluation_t} ≥ {Original_Evaluation_t + 1.0}，回滚至最优中间代码")
                    rust_code = self.best_rust_code
                    Evaluation_list.append(self.best_evaluation_t)
                # 再检测 UB
                error_message, error_exist = self.miri_check(rust_code)

                # (3) 原逻辑保持
                if error_exist:
                    if self.repair_count >= self.max_repair:
                        self.beyond_limits += 1
                        if self.beyond_limits >= self.max_beyond_limits:
                            print("修复次数超过上限，直接到 END")
                            print(f"{PATH_NAME}.rs 存在的未定义行为难以解决，请人工核查!")
                            fail_code_file = f'/home/wyc/save_improvement_file/failure/{PATH_NAME}_failed.rs'
                            with open(fail_code_file, 'w') as file:
                                file.write(original_rust_code)
                            self.state = "END"
                        else:
                            print(f"第 {self.beyond_limits} 轮修复失败，回到 INIT")
                            self.state = "INIT"
                    else:
                        self.state = "SELECT_AGENT"
                else:
                    self.state = "SEMANTIC_EVAL"

            elif self.state == "SEMANTIC_EVAL":
                if self.semantic_eval(rust_code, original_error_message, original_rust_code):
                    edited_code_file = f'/home/wyc/save_improvement_file/edited_code_saving/{PATH_NAME}_edited.rs'
                    with open(edited_code_file, 'w') as file:
                        file.write(rust_code)
                    self.state = "END"
                else:
                    print("语义评估未通过，回到 INIT")
                    self.state = "INIT"

            print(f"当前状态 -> {self.state}")

        print("状态机结束")
        print(f"最优 Evaluation_t: {self.best_evaluation_t}")
        return self.best_rust_code

    # ====== 功能函数 ======
    def miri_check(self, code):
        error_message, returncode = run_cargo_miri(code)
        error_count = error_calculate(error_message)
        return error_message, error_count != 0

    def select_agent(self, code, error_message):
        # 生成当前处理代码的特征标签以及向量
        code_tag = refine(code,error_message)
        print("Successfully generate keywords!") 
        start = code_tag.find('[')
        end = code_tag.find(']')
        formatted_output = code_tag[start+1:end]
        code_embedding = get_embeddings(formatted_output)  #将代码的特征标签转化为向量
        result = find_similar_errors(code_embedding)
        # 过滤出所有agent的成功率并转成浮点数
        agent_rates = { 
            key: float(value) for key, value in result.items() if key.startswith("agent")
        }
        # case_name计数
        print(f"database item is : {result['case_name']}")
        case_name = result.get('case_name', None)
        if case_name is not None:
            count = self.case_name_count.get(case_name, 0)
            self.case_name_count[case_name] = count + 1
        else:
            count = 0
        # 按成功率从高到低排序
        sorted_agents = sorted(agent_rates.items(), key=lambda x: x[1], reverse=True)
        # 跳过所有已用过的 agent，优先选未用过的 success_rate 高的 agent
        selected_agent = None
        for agent, _ in sorted_agents:
            if agent not in self.used_agents:
                selected_agent = agent
                break
        # 如果都用过了，则选 success_rate 最高的 agent，并清空used_agents
        if selected_agent is None:
            selected_agent = sorted_agents[0][0]
            self.used_agents = set() # 清空used_agents
        # 记录已用过的 agent
        self.used_agents.add(selected_agent)
        # 提取 agent 后面的数字
        selected_agent_number = selected_agent.replace("agent", "").replace("_success_rate", "")
        return selected_agent_number

    def current_agent_repair(self, code, agent_number, error_message):
        if agent_number != '4':
            # 只执行执行修复操作agent
            print(f"Agent{agent_number} 正在修复代码...")
            self.repair_count += 1
            return agent_function_call(agent_number, code, error_message)
        if agent_number == '4':
            return code

    def semantic_eval(self, code, original_error_message, original_rust_code):
        analysis = agent_code_analyze(original_rust_code, original_error_message, code)
        fault_localization = agent_fault_localize(original_rust_code, original_error_message, code, analysis)
        score = score_code(fault_localization)
        print(f"Evaluation:\n{fault_localization}")
        print(f"Score: {score}")
        if score == 1:
            record_file_path = f'/home/wyc/save_improvement_file/score_recording/{PATH_NAME}_record.txt'
            with open(record_file_path, 'w', encoding='utf-8') as file:
                file.write(f"Analysis:\n{analysis}\n\nFault localization:\n{fault_localization}\nScore:{score}")
            return True
        else:
            return False


# ====== 数据库检索函数 ======
def find_similar_errors(embedding):
    conn = psycopg2.connect(dbname='agentdb', user='postgres', password='451125', host='localhost', port='5432')
    cur = conn.cursor()
    embedding_str = f"[{', '.join(map(str, embedding.tolist()))}]"
    cur.execute("""
        SELECT case_name, agent1_success_rate, agent2_success_rate, agent3_success_rate,
               agent4_success_rate, agent5_success_rate
        FROM query_database
        ORDER BY embedding <-> %s::vector
        LIMIT 1;
    """, (embedding_str,))
    res = cur.fetchall()
    result = {}
    for i, (case_name, a1, a2, a3, a4, a5) in enumerate(res, 1):
        result = {
            'case_name': case_name,
            'agent1_success_rate': a1,
            'agent2_success_rate': a2,
            'agent3_success_rate': a3,
            'agent4_success_rate': a4,
            'agent5_success_rate': a5
        }
    cur.close()
    conn.close()
    return result


# ====== 绘图函数 ======
def plot_evaluation_wave(evaluations, path_name):
    """绘制每轮修复的 Evaluation_t 波形（纵坐标≥1.5的点标红并标rollback）"""
    plt.figure(figsize=(8, 4))
    x = range(len(evaluations))  # 从 0 开始（0 表示原始代码）
    plt.plot(x, evaluations, marker='o', linewidth=2, color='blue', label='Evaluation')

    # 横坐标为整数
    plt.xticks(range(len(evaluations)))

    plt.title(f"Evaluation Waveform - {path_name}")
    plt.xlabel("Repair Iteration (0 = original)")
    plt.ylabel("Evaluation_t")
    plt.grid(True, linestyle='--', alpha=0.5)

    # 标注最优点（最小 Evaluation_t）
    best_index = np.argmin(evaluations)
    if evaluations[best_index] < 0.15:
        plt.scatter(best_index, evaluations[best_index], color='green', s=80, zorder=5, label='Success')

    # 标注 Evaluation_t ≥ Original_Evaluation_t+1.0 的点（标红 + rollback）
    for i, val in enumerate(evaluations):
        if val >= (Original_Evaluation_t+1.0) and i !=0 :
            plt.scatter(i, val, color='red', s=80, zorder=6)
            plt.text(i + 0.05, val + 0.03, "rollback", color='red', fontsize=8)

    plt.legend()

    # 保存图像
    save_dir = Path('/home/wyc/save_improvement_file/evaluation_wave')
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{path_name}_wave.png"
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[绘图完成] 已保存至 {save_path}")

# ====== 文件批处理入口 ======
def slow_process_files_in_directory(directory_path):
    pathlist = Path(directory_path).rglob('*.rs')
    code_count = 0
    for path in pathlist:
        global PATH_NAME
        PATH_NAME = path.stem
        code_count += 1
        print(f"正在处理第 {code_count} 个Rust代码 {PATH_NAME}.rs ...")
        fsm = StateMachine()
        rust_code = read_code_from_file(str(path))
        result = fsm.run(rust_code)
        print("最终代码:\n", result)
        print(f"Wave is: {Evaluation_list}")

        # 绘制波形
        plot_evaluation_wave(Evaluation_list, PATH_NAME)


# ====== 主入口 ======
if __name__ == "__main__":
    directory_path = '/home/wyc/rust_thetis_test/rust_one_trial'
    start = time.perf_counter() # 进行运行记时
    slow_process_files_in_directory(directory_path)
    end = time.perf_counter()
    elapsed = end - start
    print(f"耗时：{elapsed:.6f} 秒")
