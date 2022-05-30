import pandas as pd
import seaborn as sns


def get_shacl_statistics():
    sns.set_theme(style="whitegrid", palette="Paired")
    df = pd.read_csv("data/shacl.csv")
    df_cleaned = df.loc[df["Fehleranzahl"] != 0]
    shacl_bar_plot = sns.barplot(
        x="Monat", y="Fehleranzahl", hue="Fehlertyp", data=df_cleaned
    )
    handles, labels = shacl_bar_plot.get_legend_handles_labels()
    lgd = shacl_bar_plot.legend(
        handles, labels, loc="center right", bbox_to_anchor=(0.5, -0.6)
    )
    fig = shacl_bar_plot.get_figure()
    text = shacl_bar_plot.text(
        -0.2, 1.05, "Shacl Checker Validation", transform=shacl_bar_plot.transAxes
    )
    shacl_bar_plot.set_title("Error Type Statistic")
    shacl_bar_plot.grid("on")
    fig.savefig("plots/shacl.png", bbox_extra_artists=(lgd, text), bbox_inches="tight")


get_shacl_statistics()
