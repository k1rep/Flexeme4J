import argparse
import json
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multiprocessing import Process
import jsonpickle
import networkx as nx
from deltaPDG.Util.generate_pdg import PDG_Generator
from deltaPDG.Util.git_util import Git_Util
from deltaPDG.deltaPDG import deltaPDG, quote_label
from tangle_concerns.tangle_by_file import tangle_by_file

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s][%(name)s] %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    handlers=[logging.StreamHandler()])


def mark_originating_commit(dpdg, marked_diff, filename):
    dpdg = dpdg.copy()
    for node, data in dpdg.nodes(data=True):
        if 'color' in data.keys() and data['color'] != 'orange':
            start, end = [int(l) for l in data['span'].split('-')] if '-' in data['span'] else [-1, -1]

            if start == end == -1:
                continue

            change_type = '+' if data['color'] == 'green' else '-'
            masked_diff = [p for p in marked_diff if p[0] == change_type and p[1] == filename]

            label = data['label'].replace('\'\'', '"')
            if 'Entry' in label:
                label = label[len('Entry '):].split('(')[0].split('.')[-1]
            elif 'Exit' in label:
                label = label[len('Exit '):].split('(')[0].split('.')[-1]
            if 'lambda' in label:
                label = '=>'
            if '\\r' in label:
                label = label.split('\\r')[0]
            elif '\\n' in label:
                label = label.split('\\n')[0]

            community = max([cm
                             for _, _, after_coord, before_coord, line, cm in masked_diff
                             if label in line and (start <= after_coord <= end or start <= before_coord <= end)],
                            default=0)

            dpdg.node[node]['community'] = community

    return dpdg


def mark_origin(tangled_diff, atomic_diffs):
    output = list()
    for change_type, file, after_coord, before_coord, line in tangled_diff:
        if change_type != ' ':
            relevant = {i: [(ct, f, ac, bc, ln) for ct, f, ac, bc, ln in diff
                            if file == f and line.strip() == ln.strip()]
                        for i, diff in atomic_diffs.items()}
            relevant = [i for i, diff in relevant.items() if len(diff) > 0]
            label = max(relevant, default=0)
            output.append((change_type, file, after_coord, before_coord, line, label))
    return output


def worker(work, subject_location, id_, temp_loc, extractor_location):
    repository_name = os.path.basename(subject_location)
    method_fuzziness = 100
    node_fuzziness = 100

    git_handler = Git_Util(temp_dir=temp_loc)

    with git_handler as gh:
        v1 = gh.move_git_repo_to_tmp(subject_location)
        v2 = gh.move_git_repo_to_tmp(subject_location)

        os.makedirs('./temp/%d' % id_, exist_ok=True)
        v1_pdg_generator = PDG_Generator(
            repository_location=v1,
            target_filename='before_pdg.dot',
            target_location='./temp/%d' % id_,
            extractor_location=extractor_location)
        v2_pdg_generator = PDG_Generator(
            repository_location=v2,
            target_filename='after_pdg.dot',
            target_location='./temp/%d' % id_,
            extractor_location=extractor_location)
        for chain in work:
            print('Working on chain: %s' % str(chain))
            from_ = chain[0]

            from git import Repo
            repo = Repo(v1)
            commit = repo.commit(from_)

            if len(commit.parents) == 0:
                # logger.warning(f'Ignoring {from_} because the commit has no parents')
                continue

            # 将v1仓库回溯到from_提交的父提交
            # 在对比from_提交与其他提交的差异前，需要有from_提交之前的代码状态，这个状态用作差异比较的起点
            gh.set_git_to_rev(from_ + '^', v1)
            # 将v2仓库回溯到from_提交
            gh.set_git_to_rev(from_, v2)

            labeli_changes = dict()
            # 获取from_提交与from_提交的父提交之间的在v2仓库的差异
            labeli_changes[0] = gh.process_diff_between_commits(from_ + '^', from_, v2)
            previous_sha = from_
            i = 1
            for to_ in chain[1:]:
                gh.cherry_pick_on_top(to_, v2)

                changes = gh.process_diff_between_commits(from_ + '^', to_, v2)

                labeli_changes[i] = gh.process_diff_between_commits(previous_sha, to_, v2)
                i += 1
                previous_sha = to_
                files_touched = {filename for _, filename, _, _, _ in changes if
                                 os.path.basename(filename).split('.')[-1] == 'java'}

                for filename in files_touched:
                    local_filename = os.path.normpath(filename.lstrip('/'))
                    logging.info(f"Generating PDGs for {filename}")
                    try:
                        output_path = './data/corpora_raw/%s/%s_%s/%d/%s.dot' % (
                            repository_name, from_, to_, i, os.path.basename(filename))
                        try:
                            with open(output_path) as f:
                                print('Skipping %s as it exits' % output_path)
                                f.read()
                        except FileNotFoundError:
                            v1_pdg_generator(filename)
                            v2_pdg_generator(filename)
                            delta_gen = deltaPDG('./temp/%d/before_pdg.dot' % id_, m_fuzziness=method_fuzziness,
                                                 n_fuzziness=node_fuzziness)
                            delta_pdg = delta_gen('./temp/%d/after_pdg.dot' % id_,
                                                  [ch for ch in changes if ch[1] == filename])
                            delta_pdg = mark_originating_commit(delta_pdg, mark_origin(changes, labeli_changes),
                                                                filename)
                            os.makedirs(os.path.dirname(output_path), exist_ok=True)
                            nx.set_node_attributes(delta_pdg, local_filename, "filepath")
                            nx.drawing.nx_pydot.write_dot(quote_label(delta_pdg), output_path)
                    except Exception:
                        pass
                # if len(files_touched) != 0:
                #     merged_path = merge_files_pdg(out_dir)
                #     clean_path = clean_graph(merged_path, repository_name)
                #     validate([clean_path], 1, 1, repository_name)  # Flexeme's paper uses 1-hop clustering


if __name__ == '__main__':
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(description="示例脚本说明")

    # 添加参数
    parser.add_argument("json_location", help="JSON文件位置")
    parser.add_argument("git_location", help="Git位置")
    parser.add_argument("temp_location", help="临时文件位置")
    parser.add_argument("extractor_location", help="提取器位置")
    parser.add_argument("thread_id_start", type=int, help="线程ID起始值")
    parser.add_argument("number_of_threads", type=int, help="线程数量")

    # 解析命令行参数
    args = parser.parse_args()

    json_location = args.json_location
    subject_location = args.git_location
    temp_loc = args.temp_location
    extractor_location = args.extractor_location
    n_workers = args.number_of_threads

    try:
        with open(json_location) as f:
            list_to_tangle = jsonpickle.decode(f.read())
    except FileNotFoundError:
        list_to_tangle = tangle_by_file(subject_location, temp_loc)
        with open(json_location, 'w') as f:
            f.write(json.dumps(list_to_tangle))

    chunck_size = int(len(list_to_tangle) / n_workers)
    list_to_tangle = [list_to_tangle[i:i + chunck_size] for i in range(0, len(list_to_tangle), chunck_size)]

    processes = []
    id_ = int(sys.argv[5])
    for work in list_to_tangle:
        process = Process(target=worker, args=(work, subject_location, id_, temp_loc, extractor_location))
        id_ += 1
        processes.append(process)
        process.start()

    for p in processes:
        p.join()
