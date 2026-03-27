"""Carga de datos: detecta Excel en data/raw/, corre ETL si es más nuevo que la DB"""

import glob
import os
import sys
import logging
import tempfile

import duckdb
import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

# Agregar rutas del proyecto para importar ETL
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ETL_BRONZE_DIR = os.path.join(PROJECT_ROOT, "etl", "bronze")
ETL_SILVER_DIR = os.path.join(PROJECT_ROOT, "etl", "silver")
for path in (ETL_BRONZE_DIR, ETL_SILVER_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

LOCAL_DB_PATH = os.path.join(PROJECT_ROOT, "data", "gym.duckdb")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
ALUMNO = "CentiniJoaquín"


def _find_latest_excel() -> str | None:
    """Busca el Excel más reciente en data/raw/ con patrón YYYYMMDD<Alumno>.xlsx"""
    pattern = os.path.join(RAW_DIR, f"*{ALUMNO}.xlsx")
    files = glob.glob(pattern)
    if not files:
        return None
    # El nombre con fecha YYYYMMDD ordena naturalmente
    files.sort()
    return files[-1]


def _excel_is_newer_than_db() -> str | None:
    """Retorna la ruta del Excel si es más nuevo que la DB, o si la DB no existe."""
    excel_path = _find_latest_excel()
    if excel_path is None:
        return None
    if not os.path.exists(LOCAL_DB_PATH):
        return excel_path
    if os.path.getmtime(excel_path) > os.path.getmtime(LOCAL_DB_PATH):
        return excel_path
    return None


def _run_etl(excel_path: str):
    """Ejecuta el ETL Bronze + Silver sobre la DB local"""
    from etl_bronze_v2 import GymETLBronze
    from etl_silver import GymETLSilver

    logger.info("Corriendo ETL desde: %s", excel_path)

    os.makedirs(os.path.dirname(LOCAL_DB_PATH), exist_ok=True)

    # Borrar DB vieja para evitar datos duplicados de hojas renombradas
    if os.path.exists(LOCAL_DB_PATH):
        os.remove(LOCAL_DB_PATH)

    xl = pd.ExcelFile(excel_path)
    meso_sheets = [s for s in xl.sheet_names if "Meso" in s]
    xl.close()
    logger.info("Excel: %d hojas de mesociclo", len(meso_sheets))

    with GymETLBronze(excel_path, LOCAL_DB_PATH) as bronze:
        for sheet in meso_sheets:
            try:
                bronze.extract_sheet(sheet)
            except Exception as e:
                logger.warning("Error procesando %s: %s", sheet, e)

    with GymETLSilver(LOCAL_DB_PATH) as silver:
        silver.transform_bronze_to_silver()

    logger.info("ETL completado — DB local actualizada")


def has_local_db() -> bool:
    """Verifica si existe la base de datos local"""
    return os.path.exists(LOCAL_DB_PATH)


@st.cache_resource
def _open_db(_db_mtime: float) -> duckdb.DuckDBPyConnection:
    """Abre conexión a la DB. El parámetro _db_mtime invalida el cache
    cuando la DB cambia."""
    logger.info("Abriendo conexión a DB local: %s", LOCAL_DB_PATH)
    return duckdb.connect(LOCAL_DB_PATH, read_only=False)


def load_from_excel(_file_bytes: bytes, file_name: str) -> duckdb.DuckDBPyConnection:
    """Ejecuta el ETL desde un Excel subido por el usuario"""
    tmp_dir = tempfile.mkdtemp()
    tmp_excel_path = os.path.join(tmp_dir, file_name)
    with open(tmp_excel_path, "wb") as f:
        f.write(_file_bytes)

    _open_db.clear()
    _run_etl(tmp_excel_path)

    try:
        os.unlink(tmp_excel_path)
    except OSError:
        pass

    return _open_db(os.path.getmtime(LOCAL_DB_PATH))


def clear_excel_cache():
    """Limpia el cache de la DB para forzar reprocesamiento"""
    _open_db.clear()


def get_connection(uploaded_file=None) -> duckdb.DuckDBPyConnection | None:
    """Obtiene la conexión a DuckDB. Prioridad:
    1. Upload del usuario (sidebar)
    2. Excel nuevo en data/raw/ → corre ETL automáticamente
    3. DB local existente
    """
    if uploaded_file is not None:
        return load_from_excel(uploaded_file.getvalue(), uploaded_file.name)

    # Detectar si hay un Excel más nuevo que la DB
    new_excel = _excel_is_newer_than_db()
    if new_excel is not None:
        _open_db.clear()
        _run_etl(new_excel)

    if has_local_db():
        return _open_db(os.path.getmtime(LOCAL_DB_PATH))

    return None
