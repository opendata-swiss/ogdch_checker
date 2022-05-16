import seaborn as sns
import pandas as pd


def get_shacl_statistics():
    sns.set_theme(style="whitegrid", palette="Paired")
    df = pd.read_csv('shacl.csv')
    print(df)
    df_cleaned = df.loc[df['Fehleranzahl'] != 0]
    print(df_cleaned)
    print(df_cleaned['Fehlertyp'].unique())
    shacl_bar_plot = sns.barplot(x="Monat", y="Fehleranzahl", hue='Fehlertyp', data=df_cleaned)
    handles, labels = shacl_bar_plot.get_legend_handles_labels()
    print(labels)
    lgd = shacl_bar_plot.legend(handles, labels, loc='center right', bbox_to_anchor=(0.5, -0.6))
    fig = shacl_bar_plot.get_figure()
    fig.savefig("shacl.png")
    text = shacl_bar_plot.text(-0.2,1.05, "Shacl Checker Validation", transform=shacl_bar_plot.transAxes)
    shacl_bar_plot.set_title("Error Type Statistic")
    shacl_bar_plot.grid('on')
    fig.savefig('shacl.png', bbox_extra_artists=(lgd,text), bbox_inches='tight')


get_shacl_statistics()