import pandas as pd

# Ruta a tu archivo Excel
excel_path = r"data\raw\Centini Joaquín.xlsx"  # Cambiá por el nombre real

# Ver todas las hojas disponibles
xl_file = pd.ExcelFile(excel_path)
print("Hojas disponibles:")
print(xl_file.sheet_names)
print("\n" + "="*50 + "\n")

# Explorar la primera hoja
primera_hoja = xl_file.sheet_names[0]
df = pd.read_excel(excel_path, sheet_name=primera_hoja)

print(f"Explorando hoja: {primera_hoja}")
print("\nPrimeras filas:")
print(df.head())
print("\nInfo del DataFrame:")
print(df.info())
print("\nColumnas:")
print(df.columns.tolist())