import seaborn as sns
import pandas as pd


def get_link_statistics():
    sns.set_theme(style="whitegrid", palette="Paired")
    df = pd.read_csv('link.csv')
    links_bar_plot = sns.barplot(x="Monat", y="Fehleranzahl", hue='DCAT-Poperty', data=df)
    fig = links_bar_plot.get_figure()
    fig.savefig("links.png")


get_link_statistics()
