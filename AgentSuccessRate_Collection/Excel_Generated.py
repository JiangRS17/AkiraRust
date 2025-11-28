import pandas as pd
import re
import os

def parse_defect_file(file_path, file_name):
    with open(file_path, 'r') as file:
        content = file.read()

    data = []
    root_dir = '/home/wyc/Desktop/defect_data_record'
    relative_file_name = os.path.relpath(file_name, root_dir)
    # 去掉文件名中的 '_defect_record.txt' 后缀
    if relative_file_name.endswith('_defect_record.txt'):
        relative_file_name = relative_file_name[:-len('_defect_record.txt')]

    # 提取 Code Features
    code_features_match = re.search(r'Code Features: (.+)', content)
    code_features = code_features_match.group(1).strip() if code_features_match else ''

    solutions = content.split('Solution ')[1:]

    for solution in solutions:
        solution_num_match = re.match(r'(\d+)', solution)
        if not solution_num_match:
            continue
        solution_num = solution_num_match.group(1)

        # 匹配所有 round（如 Round1、Round2）
        round_matches = re.finditer(
            r'Agents Excuted ===(Round\d+)===\s*:\s*([^\n!]+)(?:Supplement:\s*([^\n]+))?(?:\s*Solved!)?',
            solution)
        for round_match in round_matches:
            round_name = round_match.group(1)
            agents = round_match.group(2).strip().split()
            supplement_agents = round_match.group(3).strip().split() if round_match.group(3) else []
            all_agents = agents + supplement_agents

            # 匹配对应 round 的 Miri Errors
            errors_match = re.search(
                rf'Miri Errors ==={round_name}===\s*:\s*([^\n]+)', solution)
            errors_str = errors_match.group(1).strip() if errors_match else ''
            errors_list = errors_str.split() if errors_str else []

            # 去除 Begin、with、Success! 字段
            errors_list = [e for e in errors_list if e not in ('Begain', 'with', 'Success!')]
            errors_changes = ' -> '.join(errors_list)

            success = 'Success!' in errors_str
            # 只在当前 round 后面查找 semantic score
            semantic_score_match = re.search(r'Semantic Score: (\d+\.\d+)', solution)
            semantic_score = semantic_score_match.group(1) if semantic_score_match else None

            data.append({
                'File': relative_file_name,
                'Code Features': code_features,
                'Solution': solution_num,
                'Round': round_name,
                'Agents Used': ', '.join(all_agents),
                'Miri Errors Changes': errors_changes,
                'Success': 'Yes' if success else 'No',
                'Semantic Score': semantic_score if success else None
            })
    return data

def main():
    # 获取指定目录及其子目录下所有txt文件
    root_dir = '/home/wyc/Desktop/defect_data_record'
    files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.txt'):
                files.append(os.path.join(dirpath, filename))

    # Collect data from all files
    all_data = []
    for file_name in files:
        if os.path.exists(file_name):
            file_data = parse_defect_file(file_name, file_name)
            all_data.extend(file_data)
        else:
            print(f"Warning: File {file_name} not found.")

    # Create DataFrame
    df = pd.DataFrame(all_data, columns=[
        'File',
        'Code Features',
        'Solution',
        'Round',
        'Agents Used',
        'Miri Errors Changes',
        'Success',
        'Semantic Score'
    ])

    # Save to Excel
    output_file = 'defect_records.xlsx'
    df.to_excel(output_file, index=False, sheet_name='Defect Records')
    print(f"Excel file '{output_file}' generated successfully.")

if __name__ == '__main__':
    main()
