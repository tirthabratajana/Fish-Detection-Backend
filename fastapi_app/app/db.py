import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from app.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "fish_app")

SQLSERVER_HOST = os.getenv("SQLSERVER_HOST", "aquasense.database.windows.net").strip()
SQLSERVER_PORT = os.getenv("SQLSERVER_PORT", "1433").strip()
SQLSERVER_DB = os.getenv("SQLSERVER_DB", "fish_db").strip()
SQLSERVER_USER = os.getenv("SQLSERVER_USER", "db_admin").strip()
SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD", "Password@123").strip()
SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server").strip()


def resolve_database_url() -> str:
    if DATABASE_URL:
        return DATABASE_URL

    if SQLSERVER_HOST and SQLSERVER_USER:
        return (
            "mssql+pyodbc://"
            f"{quote_plus(SQLSERVER_USER)}:{quote_plus(SQLSERVER_PASSWORD)}@"
            f"{SQLSERVER_HOST}:{SQLSERVER_PORT}/{SQLSERVER_DB}"
            f"?driver={quote_plus(SQLSERVER_DRIVER)}&Encrypt=yes&TrustServerCertificate=no"
        )

    return (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    )

ROOT_DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/"
RESOLVED_DATABASE_URL = resolve_database_url()
IS_MYSQL = RESOLVED_DATABASE_URL.startswith("mysql")
DB_READY = False

if IS_MYSQL:
    # Create database if it does not exist
    try:
        root_engine = create_engine(ROOT_DATABASE_URL, future=True)
        with root_engine.connect() as connection:
            connection = connection.execution_options(isolation_level="AUTOCOMMIT")
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
        root_engine.dispose()
    except SQLAlchemyError as err:
        raise RuntimeError(f"Unable to create or access MySQL database: {err}")

engine = create_engine(RESOLVED_DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def bootstrap_database() -> None:
    global DB_READY
    try:
        Base.metadata.create_all(bind=engine)

        if IS_MYSQL:
            with engine.connect() as connection:
                has_users_column = connection.execute(text(
                    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'users' AND COLUMN_NAME = 'phone_number'"
                ), {"db": MYSQL_DB}).scalar_one()
                if has_users_column == 0:
                    connection.execute(text(
                        "ALTER TABLE users ADD COLUMN phone_number VARCHAR(50) UNIQUE"
                    ))

                has_ponds_table = connection.execute(text(
                    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'ponds'"
                ), {"db": MYSQL_DB}).scalar_one()
                if has_ponds_table:
                    has_verified_column = connection.execute(text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'ponds' AND COLUMN_NAME = 'verified'"
                    ), {"db": MYSQL_DB}).scalar_one()
                    if has_verified_column == 0:
                        connection.execute(text(
                            "ALTER TABLE ponds ADD COLUMN verified BOOLEAN DEFAULT FALSE"
                        ))

                    # Backward compatibility: older schemas may still have ph/temperature as NOT NULL
                    # with no default, which would fail inserts now that API no longer sends them.
                    has_ph_column = connection.execute(text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'ponds' AND COLUMN_NAME = 'ph'"
                    ), {"db": MYSQL_DB}).scalar_one()
                    if has_ph_column:
                        connection.execute(text(
                            "ALTER TABLE ponds MODIFY COLUMN ph FLOAT NOT NULL DEFAULT 0"
                        ))

                    has_temperature_column = connection.execute(text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'ponds' AND COLUMN_NAME = 'temperature'"
                    ), {"db": MYSQL_DB}).scalar_one()
                    if has_temperature_column:
                        connection.execute(text(
                            "ALTER TABLE ponds MODIFY COLUMN temperature FLOAT NOT NULL DEFAULT 0"
                        ))

                    has_latitude_column = connection.execute(text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'ponds' AND COLUMN_NAME = 'latitude'"
                    ), {"db": MYSQL_DB}).scalar_one()
                    if has_latitude_column == 0:
                        connection.execute(text(
                            "ALTER TABLE ponds ADD COLUMN latitude FLOAT"
                        ))

                    has_longitude_column = connection.execute(text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'ponds' AND COLUMN_NAME = 'longitude'"
                    ), {"db": MYSQL_DB}).scalar_one()
                    if has_longitude_column == 0:
                        connection.execute(text(
                            "ALTER TABLE ponds ADD COLUMN longitude FLOAT"
                        ))

                    has_estimated_area_column = connection.execute(text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'ponds' AND COLUMN_NAME = 'estimated_area'"
                    ), {"db": MYSQL_DB}).scalar_one()
                    if has_estimated_area_column == 0:
                        connection.execute(text(
                            "ALTER TABLE ponds ADD COLUMN estimated_area FLOAT"
                        ))

                    has_fish_species_column = connection.execute(text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'ponds' AND COLUMN_NAME = 'fish_species'"
                    ), {"db": MYSQL_DB}).scalar_one()
                    if has_fish_species_column == 0:
                        connection.execute(text(
                            "ALTER TABLE ponds ADD COLUMN fish_species TEXT"
                        ))

                    has_geo_image_type_column = connection.execute(text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'ponds' AND COLUMN_NAME = 'geo_image_content_type'"
                    ), {"db": MYSQL_DB}).scalar_one()
                    if has_geo_image_type_column == 0:
                        connection.execute(text(
                            "ALTER TABLE ponds ADD COLUMN geo_image_content_type VARCHAR(64)"
                        ))

                    has_geo_image_data_column = connection.execute(text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'ponds' AND COLUMN_NAME = 'geo_image_data'"
                    ), {"db": MYSQL_DB}).scalar_one()
                    if has_geo_image_data_column == 0:
                        connection.execute(text(
                            "ALTER TABLE ponds ADD COLUMN geo_image_data LONGBLOB"
                        ))

                    has_reports_table = connection.execute(text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'reports'"
                    ), {"db": MYSQL_DB}).scalar_one()
                    if has_reports_table:
                        has_report_verified = connection.execute(text(
                            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                            "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'reports' AND COLUMN_NAME = 'verified'"
                        ), {"db": MYSQL_DB}).scalar_one()
                        if has_report_verified == 0:
                            connection.execute(text(
                                "ALTER TABLE reports ADD COLUMN verified BOOLEAN DEFAULT FALSE"
                            ))

        DB_READY = True
    except SQLAlchemyError as err:
        DB_READY = False
        print(f"Database bootstrap skipped or failed: {err}")


bootstrap_database()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
