import pandas as pd

df = pd.read_excel(r"data\raw\Centini Joaquín.xlsx", sheet_name="Meso 2", header=None)

# Buscar todos los "DÍA X" en la columna 0
for idx in range(0, 300):
    if idx >= len(df):
        break
    val = df.iloc[idx, 0]
    if pd.notna(val) and 'DÍA' in str(val):
        print(f"  Fila {idx}: {val}")