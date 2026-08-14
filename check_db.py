from pathlib import Path
import pandas as pd

file_path = Path("output/portfolio_stats.csv")

if not file_path.exists():
    print("portfolio_stats.csv NOT FOUND")
else:
    df = pd.read_csv(file_path)

    print("PORTFOLIO STATS COLUMNS:")

    for column in df.columns:
        print(column)

    print("\nROWS:", len(df))

    print("\nDATA:")
    print(df.to_string(index=False))