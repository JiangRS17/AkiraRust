import os
import subprocess
import tempfile
import shutil

def run_miri_and_parse(edited_code):
    """
    1. 自动创建临时cargo项目，将修复代码写入main.rs。
    2. 执行cargo miri test，收集Miri输出日志。
    3. 返回Miri日志内容（字符串）。
    """
    temp_dir = tempfile.mkdtemp(prefix="miri_proj_")
    try:
        # 初始化cargo项目
        subprocess.run(["cargo", "init", "--bin", temp_dir], check=True)
        src_dir = os.path.join(temp_dir, "src")
        main_rs = os.path.join(src_dir, "main.rs")
        # 将修复代码写入main.rs
        with open(main_rs, "w") as f:
            f.write(edited_code)
        # 执行cargo miri test（或run）
        result = subprocess.run(
            'cargo +nightly-2024-10-01 miri run',
            cwd=temp_dir,
            shell=True,          # 关键：启用 shell 解释器
            capture_output=True,
            text=True
        )
        # 过滤出所有error和Undefined Behavior相关信息（包括多行error block）
        output = result.stdout + "\n" + result.stderr
        lines = output.splitlines()
        miri_log_blocks = []
        current_block = []
        in_error_block = False
        for line in lines:
            if (line.strip().startswith("error")) or ("Undefined Behavior" in line):
                if current_block:
                    miri_log_blocks.append("\n".join(current_block))
                    current_block = []
                in_error_block = True
                current_block.append(line)
            elif in_error_block:
                # 继续收集error block的后续行，直到遇到空行或下一个error
                if line.strip() == "":
                    miri_log_blocks.append("\n".join(current_block))
                    current_block = []
                    in_error_block = False
                else:
                    current_block.append(line)
        if current_block:
            miri_log_blocks.append("\n".join(current_block))
        miri_log = "\n\n".join(miri_log_blocks)
        if miri_log != '':
            print(f"After Miri test, UBs exist!\n\n")
        return miri_log
    except Exception as e:
        return f"[Miri运行异常]: {e}"
    finally:
        shutil.rmtree(temp_dir)
