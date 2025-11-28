import difflib

def compute_diff_complexity(original_lines, edited_lines):
    """
    计算修复diff的规模和复杂度，返回修改行数、修改块数、diff比例等。
    """
    diff = list(difflib.unified_diff(original_lines, edited_lines, lineterm=''))
    # 统计修改行数和块数
    added, removed, blocks = 0, 0, 0
    in_block = False
    for line in diff:
        if line.startswith('@@'):
            blocks += 1
            in_block = True
        elif line.startswith('+') and not line.startswith('+++'):
            added += 1
        elif line.startswith('-') and not line.startswith('---'):
            removed += 1
    total_lines = max(len(original_lines), len(edited_lines))
    diff_ratio = (added + removed) / total_lines if total_lines > 0 else 0
    return {
        'diff_ratio': round(diff_ratio, 4)
    }
