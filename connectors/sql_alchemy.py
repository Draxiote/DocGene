from sqlalchemy import create_engine, text , MetaData , select, inspect
from sqlalchemy.types import NullType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable
from helpers.validation import is_safe_query
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv(override=True)

engine_uri = {
    "mysql": "mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    "postgres": "postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    "mssql": "mssql+pymssql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    "oracle": "oracle+cx_oracle://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
}

class SqlAlchemy:
    def __init__(self):
        load_dotenv(override=True)
        
        # Load environment variables with defaults
        self.DB_HOST = os.getenv("DB_HOST", "localhost")
        self.DB_USER = os.getenv("DB_USER", "user")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
        self.DB_NAME = os.getenv("DB_NAME", "database")
        self.DB_PORT = os.getenv("DB_PORT", "5432")
        self.DB_DRIVER = os.getenv("DB_DRIVER", "postgres")

        # Construct the connection string based on the DB_DRIVER
        connection_string_template = engine_uri.get(self.DB_DRIVER)
        if not connection_string_template:
            raise ValueError(f"Unsupported database driver: {self.DB_DRIVER}")

        try:
            self.CONNECTION_STRING = connection_string_template.format(
                DB_USER=self.DB_USER or "user",
                DB_PASSWORD=self.DB_PASSWORD or "password",
                DB_HOST=self.DB_HOST or "localhost",
                DB_PORT=self.DB_PORT or "5432",
                DB_NAME=self.DB_NAME or "database"
            )
        except KeyError as e:
            raise ValueError(f"Missing configuration for {e}")

        # Create the SQLAlchemy engine
        try:
            self.engine = create_engine(self.CONNECTION_STRING)
            self.base = declarative_base()
        except Exception as e:
            raise ConnectionError(f"Failed to create SQLAlchemy engine: {e}")

    def run_query(self, query):
        try:
            # Validate query before creating session
            if not is_safe_query(query):
                return "Query blocked: Potentially unsafe SQL detected."
            
            Session = sessionmaker(bind=self.engine)
            session = Session()  # Only create session if query is safe

            result = session.execute(text(query))  # Execute query

            if query.strip().lower().startswith("select"):
                fetched_data = result.fetchall()
                
                if not fetched_data:
                    return "No data found."

                return pd.DataFrame(fetched_data, columns=result.keys())
            else:
                session.commit()  # Commit for DML queries
                return "Query executed successfully."
        
        except Exception as e:
            if 'session' in locals():  # Ensure session exists before rollback
                session.rollback()  # Rollback in case of error
            return f"An error occurred: {e}"
        
        finally:
            if 'session' in locals():  # Close session only if it was created
                session.close()




    def show_db_schema(self):
        schema_info = ""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names(schema=self.DB_NAME)
            for table_name in tables:
                columns = inspector.get_columns(table_name, schema=self.DB_NAME)
                schema_info += f"Table: {table_name.upper()}\n"
                for column in columns:
                    column_name = column["name"]
                    data_type = column["type"]
                    schema_info += f"  Column: {column_name}, Type: {data_type}\n"
                schema_info += "\n"
        except Exception as e:
            schema_info = f"Error retrieving schema: {e}"
        return schema_info
    
    def get_sample_rows(self, table, sample_row_limit):
        engine = self.engine
        command = select(table).limit(sample_row_limit)
        with engine.connect() as connection:
            rows = connection.execute(command).fetchall()
            rows_str = "\n".join("\t".join(str(col)[:100] for col in row) for row in rows)
        return rows_str
    
    def get_db_schema(self, schema=None, sample_rows_in_table_info=3, indexes_in_table_info=False):
        """Get information about specified tables.

            Follows best practices as specified in: Rajkumar et al, 2022
            (https://arxiv.org/abs/2204.00498)

            If `sample_rows_in_table_info`, the specified number of sample rows will be
            appended to each table description. This can increase performance as
            demonstrated in the paper.
        """
        engine = self.engine
        metadata = MetaData()
        metadata.reflect(bind=engine, schema=schema)
        
        tables = []
        for table in metadata.sorted_tables:
            # Exclude tables with SQLite system prefix
            if table.name.startswith("sqlite_"):
                continue
                
            # Exclude columns with JSON/unsupported datatypes
            for column in table.columns:
                if isinstance(column.type, NullType):
                    table._columns.remove(column)
                    
            # Generate table creation statement
            create_table = str(CreateTable(table).compile(engine))
            table_info = f"{create_table.rstrip()}"
            
            # Add indexes and sample rows
            if indexes_in_table_info:
                indexes = engine.execute(f"PRAGMA index_list({table.name})").fetchall()
                indexes_str = "\n".join([f"Index: {idx[1]}, Unique: {idx[2]}" for idx in indexes])
                table_info += f"\nTable Indexes:\n{indexes_str}"
            
            if sample_rows_in_table_info > 0:
                sample_rows_str = self.get_sample_rows(table, sample_rows_in_table_info)
                table_info += f"\nSample Rows:\n{sample_rows_str}"
            
            tables.append(table_info)
            
        return "\n\n".join(tables)
