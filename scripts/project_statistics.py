import json
import os
import subprocess
import argparse
from collections import defaultdict


def get_commit_count(repo_dir):
    try:
        os.chdir(repo_dir)
        # 运行 git 命令，获取 commit 数量
        result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'],
                                capture_output=True, text=True, check=True)
        # 打印 commit 数量
        commit_count = int(result.stdout.strip())
        os.chdir('..')
        return commit_count
    except subprocess.CalledProcessError as e:
        os.chdir('..')
        print(f"Error occurred: {e}")
        return 0


def is_comment_line(line, in_block_comment):
    stripped_line = line.strip()
    if in_block_comment:
        if stripped_line.endswith('*/'):
            in_block_comment = False
        return True, in_block_comment
    if stripped_line.startswith('//'):
        return True, in_block_comment
    if stripped_line.startswith('/*'):
        in_block_comment = True
        return True, in_block_comment
    if stripped_line.startswith('/**'):
        in_block_comment = True
        return True, in_block_comment
    return False, in_block_comment


def count_code_lines_in_git(repo_path, language):
    try:
        # Change to the repository directory
        os.chdir(repo_path)

        if language == 'java':
            # Run the git command to list Java files
            result = subprocess.run(['git', 'ls-files', '*.java'], stdout=subprocess.PIPE, text=True, check=True)
        elif language == 'python':
            # Run the git command to list Python files
            result = subprocess.run(['git', 'ls-files', '*.py'], stdout=subprocess.PIPE, text=True, check=True)
        else:
            result = subprocess.run(['git', 'ls-files', '*.cs'], stdout=subprocess.PIPE, text=True, check=True)
        files = result.stdout.splitlines()
        total_lines = 0

        # Count lines in each Java file
        for file in files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    in_block_comment = False
                    for line in lines:
                        if line.strip() == '':
                            continue
                        is_comment, in_block_comment = is_comment_line(line, in_block_comment)
                        if not is_comment:
                            total_lines += 1
            except FileNotFoundError:
                continue
        os.chdir('..')
        return total_lines
    except subprocess.CalledProcessError as e:
        os.chdir('..')
        print(f"Error executing git command in {repo_path}: {e}")
        return 0
    except Exception as e:
        os.chdir('..')
        print(f"Error processing {repo_path}: {e}")
        return 0


def get_last_commit_hash(repo_path):
    try:
        # Change to the repository directory
        os.chdir(repo_path)

        # Get the latest commit hash
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE, text=True, check=True)
        last_commit_hash = result.stdout.strip()
        os.chdir('..')
        return last_commit_hash
    except subprocess.CalledProcessError as e:
        os.chdir('..')
        print(f"Error executing git command in {repo_path}: {e}")
        return None
    except Exception as e:
        os.chdir('..')
        print(f"Error processing {repo_path}: {e}")
        return None


def count_subarrays(data):
    if isinstance(data, list):
        total_subarrays = 0
        sub_elements_count = defaultdict(int)

        for subarray in data:
            if isinstance(subarray, list):
                total_subarrays += 1
                sub_elements_count[len(subarray)] += 1

        return total_subarrays, sub_elements_count
    else:
        raise ValueError("Input data must be a list of lists")


def main(repo_paths, language):
    sum = 0
    sum_of_concerns = defaultdict(int)
    sum_of_composite_commits = 0
    sum_of_commits = 0
    for repo_path in repo_paths:
        repo_dir = os.path.join('../subjects', repo_path)
        if os.path.isdir(repo_dir):
            total_commits = get_commit_count(repo_dir)
            total_lines = count_code_lines_in_git(repo_dir, 'python')
            sum += total_lines
            sum_of_commits += total_commits
            print('-' * 30)
            print(f'Total lines of {language} code in {repo_dir}: {total_lines}')
            print(f'Total commits in {repo_dir}: {total_commits}')
            last_commit_hash = get_last_commit_hash(repo_dir)
            if last_commit_hash:
                print(f'Last revision hash in {repo_dir}: {last_commit_hash[:7]}')
            json_file_path = os.path.join(f'../out/{repo_path}', f'{repo_path}_history_filtered_flat.json')
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                total_count, sub_elements_count = count_subarrays(data)
                sum_of_composite_commits += total_count
                for k, v in sub_elements_count.items():
                    sum_of_concerns[k] += v
                print(f'Total composite commits: {total_count}, concerns count: {sub_elements_count}')
        else:
            print(f'Invalid repository path: {repo_path}')
    print('-' * 30)
    print(f'sum of Total lines: {sum}')
    print(f'sum of Total commits: {sum_of_commits}')
    print(f'sum of Total composite commits: {sum_of_composite_commits}')
    print(f'sum of Total concerns: {sum_of_concerns}')
    print('-' * 30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Count lines of Java code in multiple Git repositories.')
    parser.add_argument('repo_paths', nargs='+', help='Paths to Git repositories')
    parser.add_argument('--language', default='python', help='Programming language of the code')
    args = parser.parse_args()
    main(args.repo_paths, args.language)
