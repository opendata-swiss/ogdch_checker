# Visualize Link and Shacl Checker Statistics 

This part has been written in order to get statistics for a presentation.
Statistics Visualization is not part of the main command yet.

## Get the data (Manually)

The data must currently be retrieved manually from the server:
Each checker run writes a run directory: in there a csv directory that includes also files for statistical data.
From there the data for each month was added manually:

- a Month column has been added
- the Column names have been adjusted
- the numbers column reflects the original data and are stored in the column 'Fehleranzahl'
- the orginal message column has been transformed to beeter describe the "Fehlertyp" or "DCAT-Property"

Sample input data is available at [data/links.csv](data/links.csv) and [data/shacl.csv](data/shacl.csv)

## Plot ths data (automatic)

Once the data has been imported, run

```
source p3venv/bin/activate
pip install -r requirements_stat.txt
python statistics_shacl.py
python statistics_links.py
```

Sample plot for the provided sample data can be found at [plots/links.png](plots/links.png) and [plots/shacl.png](plots/shacl.png)
