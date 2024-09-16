"""
This script analyses the commit history in a Git repository
and identifies relevant changes(files point 3)
that were committed by the same author within a certain period of time (point 1)
and that do not contain too many keywords in the message, (point 4)
links those changes into chains, and returns all such chains of commits.
"""
import argparse
import datetime
import json
import os
import sys
from collections import defaultdict
from typing import List, Tuple, Any

import numpy as np

from deltaPDG.Util.git_util import GitUtil

# some VERB keywords that are used to identify bug-fixing and feature-implementing commits
KEYWORDS = {'FIX',
            'FIXES',
            'FIXED',
            'IMPLEMENTS',
            'IMPLEMENTED',
            'IMPLEMENT',
            'BUG',
            'FEATURE',
            'BUGS',
            'FEATURES',
            'CHANGE',
            'CHANGES',
            'CHANGED',
            'ADDED',
            'ADDS',
            'ADD',
            'REMOVED',
            'REMOVES',
            'REMOVE',
            'REFACTOR',
            'REFACTORS',
            'REFACTORED',
            'UPDATE',
            'UPDATES',
            'UPDATED',
            'MODIFY',
            'MODIFIES',
            'MODIFIED',
            'CORRECT',
            'CORRECTS',
            'CORRECTED',
            'SOLVE',
            'SOLVES',
            'SOLVED',
            'RESOLVE',
            'RESOLVES',
            'RESOLVED',
            'REPAIR',
            'REPAIRS',
            'REPAIRED',
            'DELETE',
            'DELETES',
            'DELETED',
            'PATCH',
            'PATCHES',
            'PATCHED',
            'CLEAN',
            'CLEANS',
            'CLEANED',
            'RENAME',
            'RENAMES',
            'RENAMED',
            'REFORMAT',
            'REFORMATS',
            'REFORMATTED',
            }


def get_history_by_file(gh: GitUtil, repository_root: str, files_considered: List[str]):
    """
    Get the commit history for each file in files_considered.
    """
    return {filename: gh.get_commits_for_file(filename, repository_root) for filename in files_considered}


def merge_commit_chains(list_of_pairs: List[Tuple[str, str]]) -> List[Tuple[str, ...]]:
    """
    Merge the commit chains to form a list of tuples where each tuple is a chain of commits.
    """
    before_to_after = defaultdict(list)
    after_to_before = {}
    for before, after in list_of_pairs:
        before_to_after[before].append(after)
        after_to_before[after] = before
    merged_chains = list()
    while before_to_after:
        start = next((k for k in before_to_after.keys() if k not in after_to_before), None)
        if start is None:
            start = next(iter(before_to_after))

        chain = []
        current = start

        while current is not None:
            chain.append(current)
            next_commit = before_to_after.pop(current, None)
            if next_commit:
                current = next_commit[0]
            else:
                current = None
        merged_chains.append(tuple(chain))
    return merged_chains


def get_cooccurrence_row_up_to_commit(current_commit: str, file1_index: int, file2_index: int, candidates, occurrence):
    """
    Get the number of times the two files have changed together before a certain commit.
    """
    selected_idx = list()
    for i in range(candidates.index(current_commit)):
        if occurrence[(file1_index, i)] and occurrence[(file2_index, i)]:
            selected_idx.append(i)
    return np.squeeze(np.asarray(occurrence[:, selected_idx].sum(axis=1)))


def filter_pairs_by_predicates(list_of_pairs: List[Tuple[str, str]], predicates: Any) -> List[Tuple[str, str]]:
    """
    Filter submission pairs according to the given predicate function.
    """
    result = list()
    for i in range(len(list_of_pairs)):
        if all(map(lambda pred: pred(*list_of_pairs[i]), predicates)):
            result.append(list_of_pairs[i])
    return result


def commits_within(gh, path, days):
    """
    Predicate function that checks if the time between two commits is within a certain number of days.
    Contain files that are frequently changed together. (point 3)
    """

    def inner_predicate(sha1, sha2):
        return gh.get_time_between_commits(sha1, sha2, path) <= datetime.timedelta(days=days)

    return inner_predicate


def same_author(gh, path):
    """
    Predicate function that checks if the author of the two commits is the same.
    """

    def inner_predicate(sha1, sha2):
        author_old = gh.get_author(sha1, path)
        author_new = gh.get_author(sha2, path)
        return author_old == author_new

    return inner_predicate


def diff_regions_size(gh, path, max_regions):
    """
    Predicate function that checks if the number of diff regions between two commits is less than a certain number.
    """

    def inner_predicate(sha1, sha2):
        return len(gh.merge_diff_into_diff_regions(gh.process_diff_between_commits(sha1, sha2, path))) <= max_regions

    return inner_predicate


def both_are_atomic(gh, path):
    """
    Predicate function that checks if both commits are atomic.
    """

    def inner_predicate(sha1, sha2):
        commit_msg1 = gh.get_commit_msg(sha1, path)
        commit_msg2 = gh.get_commit_msg(sha2, path)
        return len(set(commit_msg1.upper().split()).intersection(KEYWORDS)) <= 1 \
            and len(set(commit_msg2.upper().split()).intersection(KEYWORDS)) <= 1

    return inner_predicate


def tangle_by_file(subject, temp_loc):
    """
    Analyses the commit history in a Git repository, identifies relevant changes that were
    committed by the same author within a certain period of time (point 1)
    and that do not contain too many keywords in the message, (point 4)
    links those changes into chains, and returns all such chains of commits.
    """
    days = 14
    up_to_concerns = 5

    git_handler = GitUtil(temp_dir=temp_loc)

    with git_handler as gh:
        temp = gh.move_git_repo_to_tmp(subject)
        candidates = gh.get_all_commit_hashes_authors_dates_messages(temp)
        # commits in groups of authors
        candidates_by_author = defaultdict(list)
        for sha, author, date, msg, diff in candidates:
            candidates_by_author[author].append((sha, date, msg))
        candidates_by_author = dict(candidates_by_author)

        history_flat = list()
        for candidates in candidates_by_author.values():
            candidates = sorted(candidates, key=lambda x: x[1])
            index = 0
            while index < len(candidates):
                sha, date, msg = candidates[index]
                index += 1
                if len(set(msg.upper().split()).intersection(KEYWORDS)) <= 1:
                    chain = [sha]
                    for offset in range(1, up_to_concerns):
                        try:
                            new_sha, new_date, new_msg = candidates[index + offset]
                            if new_date - date <= datetime.timedelta(days=days) \
                                    and len(set(new_msg.upper().split()).intersection(KEYWORDS)) <= 1:
                                chain.append(new_sha)
                                index += 1
                            else:
                                break
                        except IndexError:
                            break
                    if len(chain) > 1:
                        history_flat.append(chain)

    return history_flat


def process_repository(repository_name):
    history_flat = tangle_by_file('../subjects/%s' % repository_name, '../temp')
    output_dir = '../out/{}'.format(repository_name)
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, '{}_history_filtered_flat.json'.format(repository_name)), 'w') as f:
        f.write(json.dumps(history_flat))


def main():
    parser = argparse.ArgumentParser(description='Process multiple repositories.')
    parser.add_argument('repositories', metavar='N', type=str, nargs='+', help='a list of repository names')
    args = parser.parse_args()

    for repository_name in args.repositories:
        process_repository(repository_name)


if __name__ == '__main__':
    main()
