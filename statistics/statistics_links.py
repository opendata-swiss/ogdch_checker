import pandas as pd
import seaborn as sns


def get_link_statistics():
    sns.set_theme(style="whitegrid", palette="Paired")
    df = pd.read_csv("data/links.csv")
    links_bar_plot = sns.barplot(
        x="Monat", y="Fehleranzahl", hue="DCAT-Property", data=df
    )
    fig = links_bar_plot.get_figure()
    fig.savefig("plots/links.png")


get_link_statistics()
