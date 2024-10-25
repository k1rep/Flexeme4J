import os
import pandas as pd


def main(method):
    project = ['Commandline', 'CommonMark', 'Hangfire', 'Humanizer',
               'Lean', 'Nancy', 'Newtonsoft.Json', 'Ninject', 'RestSharp']

    for p in project:
        if os.path.exists(f'./out/{p}/{method}'):
            data = pd.read_csv(f'./out/{p}/{method}')
            print("Project", p)
            # 'Concepts' == 2 and 'Concepts' == 3 number
            num = data['Concepts'].value_counts()
            print("Concerns", num)

            # group by the 'Concepts' column and get the median of the 'Accuracy' column
            median = data.groupby('Concepts')['Accuracy'].median().round(2)
            print("Median of Concerns", median)
            print(median)
            # select the row where 'Concepts' == 2 and 'Concepts' == 3
            overall = data.loc[data['Concepts'].isin([2, 3])]['Accuracy'].median().round(2)
            print("Overall of Concerns")
            print(overall)

    # total
    data = pd.DataFrame()
    for p in project:
        if os.path.exists(f'./out/{p}/{method}'):
            temp = pd.read_csv(f'./out/{p}/{method}')
            data = pd.concat([data, temp], ignore_index=True)

    overall = data.loc[data['Concepts'].isin([2, 3])].groupby('Concepts')['Accuracy'].median().round(2)
    overall_by_concerns = data.loc[data['Concepts'].isin([2, 3])]['Accuracy'].median().round(2)
    print("Overall of all projects")
    print(overall)
    print("Overall of all projects by concerns")
    print(overall_by_concerns)


if __name__ == '__main__':
    main('wl_all_1_results_raw.csv')
