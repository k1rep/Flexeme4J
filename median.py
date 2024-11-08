import os
import pandas as pd


def process_project_data(project, method):
    file_path = f'./out/{project}/{method}'
    if os.path.exists(file_path):
        data = pd.read_csv(file_path)
        print("Project:", project)
        num = data['Concepts'].value_counts()
        print("Concerns:", num)

        median = data.groupby('Concepts')['Accuracy'].median().round(2)
        print("Median of Concerns:", median)

        overall = data.loc[data['Concepts'].isin([2, 3]), 'Accuracy'].median().round(2)
        print("Overall of Concerns:", overall)
        return data
    return pd.DataFrame()  # 返回空DataFrame以便合并


def main(method):
    projects = ['Commandline', 'CommonMark', 'Hangfire', 'Humanizer',
                'Lean', 'Nancy', 'Newtonsoft.Json', 'Ninject', 'RestSharp']

    # 处理单个项目
    combined_data = pd.DataFrame()
    for project in projects:
        data = process_project_data(project, method)
        combined_data = pd.concat([combined_data, data], ignore_index=True)

    # 处理所有项目的总体数据
    if not combined_data.empty:
        overall = combined_data.loc[combined_data['Concepts'].isin([2, 3])].groupby('Concepts')[
            'Accuracy'].median().round(2)
        overall_by_concerns = combined_data.loc[combined_data['Concepts'].isin([2, 3]), 'Accuracy'].median().round(2)
        print("Overall of all projects")
        print(overall)
        print("Overall of all projects by concerns")
        print(overall_by_concerns)


if __name__ == '__main__':
    main('wl_all_1_results_raw.csv')
