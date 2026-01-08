# **AkiraRust** 🦀🤖

&gt; **An LLM-driven Rust repair framework with adaptive dual-mode reasoning and FSM-based runtime feedback**

---

## 📖 Overview

AkiraRust introduces a **dual-mode reasoning strategy** that coordinates **fast and slow thinking** across multiple agents, achieving **~92% semantic correctness** with **2.2× average speedup** over state-of-the-art methods.

---

## 📁 Project Structure

---

## 🔍 `AgentSuccessRate_Collection/` — **Indispensable: Agent Effectiveness Evaluation**

This folder provides **quantitative foundations** for FSM state design. It evaluates RustBrain architecture performance across defect types, generating data that **directly configures state transition priorities**.

### Core Components:

| File | Purpose | Why Essential |
|------|---------|---------------|
| **`Defect_Fast_Thinking.py`** | Implements RustBrain fast-thinking mode | Generates baseline data for FSM's **lightweight repair states**; achieves 92% success on simple defects |
| **`Defect_Slow_Thinking.py`** | Implements RustBrain slow-thinking mode | Provides deep analysis capability for **complex semantic states** (ownership, lifetime violations) |
| **`Defect_Code_Evaluate.py`** | Evaluates generated code & records metrics | **Single source of truth** for `q_assert`, `q_modify`, `q_replace` effectiveness scores; without it, FSM cannot rank agent priorities |
| **Table Generation** | Compiles agent success rate tables | Transforms evaluation results into **FSM transition function δ parameters**; required for adaptive agent selection |

**Output**: Agent effectiveness matrix, UB count variations, and FSM configuration files.

---

## ⚙️ `Akira_State_Machine/` — **Indispensable: FSM Runtime Engine**

This folder implements the **adaptive decision core**. It converts agent evaluation data into runtime FSM logic, enabling waveform-driven rollbacks and dynamic scheduling as described in the paper.

### Core Components:

| File/Folder | Purpose | Why Essential |
|-------------|---------|---------------|
| **`SQL_create.py`** | Builds vector knowledge base | Enables **KnowledgeAgent** semantic retrieval; required for cross-module defect handling |
| **`State_Machine.py`** | Implements FSM backbone `(Σ, S, s₀, F, δ, λ)` | **System core**: Defines state set `S` and transition function `δ`; without it, dual-mode agents cannot coordinate and degrade to random invocation |
| **`Miri_Record/`** | Calculates Incorrectness Score | **Runtime feedback source**: Provides `α_t` signal vector (UB count, semantic drift, complexity) that **directly drives rollback decisions** |
| **`Miri_Record/analyzer/`** | Multi-dimensional evaluation | Contains UB counter, semantic drift analyzer, complexity evaluator; **exactly computes** the Incorrectness Score needed by FSM |

**Waveform Logic**:
```python
E(t) = Σ w_i · g_i(f_i(t))  # Code incorrectness curve
if E(t) > threshold:         # Rollback point detection
    rollback_to_min_state()
elif variance(E(t)) < ε:     # Convergence detection
    trigger_semantic_check()
```
