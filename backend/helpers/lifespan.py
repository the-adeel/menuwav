# helpers/lifespan.py
from contextlib import asynccontextmanager
from tortoise import Tortoise
from tortoise.connection import connections
from helpers.tortoise_config import TORTOISE_ORM
import logging

logger = logging.getLogger(__name__)

async def sync_model_columns():
    """Add missing columns to existing tables based on model definitions"""
    try:
        conn = connections.get("default")
        models = Tortoise.apps.get("models")
        
        for model_name, model_class in models.items():
            if model_name == "aerich.models.Aerich":
                continue
                
            table_name = model_class._meta.db_table
            model_fields = model_class._meta.fields_map
            
            # Get existing columns in the table
            try:
                existing_columns_query = """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = $1
                """
                _, existing_columns_result = await conn.execute_query(
                    existing_columns_query,
                    [table_name]
                )
                # Result is a list of tuples, extract column names
                existing_columns = {row[0] for row in existing_columns_result}
                
                # Check each model field
                for field_name, field in model_fields.items():
                    # Get the actual database column name (may differ from field name)
                    db_column_name = getattr(field, 'source_field', None) or field_name
                    
                    # Skip if column already exists
                    if db_column_name in existing_columns:
                        continue
                    
                    # Skip primary key fields (they should already exist)
                    if getattr(field, 'pk', False):
                        continue
                    
                    # Generate ALTER TABLE statement for missing column
                    field_type = type(field).__name__
                    is_nullable = getattr(field, 'null', False)
                    
                    # Map field types to PostgreSQL SQL types
                    sql_type = None
                    default_clause = ""
                    
                    if field_type == "IntField":
                        sql_type = "INTEGER"
                    elif field_type == "CharField":
                        max_length = getattr(field, 'max_length', 255)
                        sql_type = f"VARCHAR({max_length})"
                    elif field_type == "TextField":
                        sql_type = "TEXT"
                    elif field_type == "BooleanField":
                        sql_type = "BOOLEAN"
                        if hasattr(field, 'default') and field.default is not None:
                            if callable(field.default):
                                default_val = field.default()
                            else:
                                default_val = field.default
                            default_clause = f"DEFAULT {str(default_val).lower()}"
                    elif field_type == "DecimalField":
                        max_digits = getattr(field, 'max_digits', 10)
                        decimal_places = getattr(field, 'decimal_places', 2)
                        sql_type = f"NUMERIC({max_digits},{decimal_places})"
                        if hasattr(field, 'default') and field.default is not None:
                            if callable(field.default):
                                default_val = field.default()
                            else:
                                default_val = field.default
                            default_clause = f"DEFAULT {default_val}"
                    elif field_type == "DatetimeField":
                        sql_type = "TIMESTAMP"
                    elif field_type == "CharEnumField":
                        sql_type = "VARCHAR(50)"  # Enum strings are usually short
                    elif field_type == "ForeignKeyFieldInstance":
                        # Foreign keys are stored as integers
                        sql_type = "INTEGER"
                    elif field_type == "ForeignKeyField":
                        # Alternative name for foreign key fields
                        sql_type = "INTEGER"
                    else:
                        logger.warning(f"Unknown field type {field_type} for {model_name}.{field_name}, skipping")
                        continue
                    
                    # Handle default values for other field types
                    if not default_clause and hasattr(field, 'default') and field.default is not None:
                        try:
                            if callable(field.default):
                                default_val = field.default()
                            else:
                                default_val = field.default
                            
                            if isinstance(default_val, bool):
                                default_clause = f"DEFAULT {str(default_val).lower()}"
                            elif isinstance(default_val, (int, float)):
                                default_clause = f"DEFAULT {default_val}"
                            elif isinstance(default_val, str):
                                default_clause = f"DEFAULT '{default_val}'"
                        except Exception:
                            pass  # Skip if default can't be converted
                    
                    # Determine NULL constraint
                    null_clause = "NULL" if is_nullable else "NOT NULL"
                    
                    # Build ALTER TABLE statement
                    alter_sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{db_column_name}" {sql_type} {null_clause}'
                    if default_clause:
                        alter_sql += f" {default_clause}"
                    
                    try:
                        logger.info(f"Adding missing column {db_column_name} to table {table_name}")
                        await conn.execute_query(alter_sql)
                        logger.info(f"Successfully added column {db_column_name} to {table_name}")
                    except Exception as e:
                        # Column might have been added by another process, or constraint issue
                        error_str = str(e).lower()
                        if "already exists" not in error_str and "duplicate" not in error_str:
                            logger.error(f"Error adding column {db_column_name} to {table_name}: {e}")
                        
            except Exception as e:
                # Table might not exist yet, generate_schemas will create it
                error_str = str(e).lower()
                if "does not exist" not in error_str:
                    logger.debug(f"Table {table_name} might not exist yet or error checking columns: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error in sync_model_columns: {e}")
        # Don't fail startup if schema sync fails

@asynccontextmanager
async def lifespan():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)  # Creates missing tables
    await sync_model_columns()  # Adds missing columns to existing tables
    yield
    await Tortoise.close_connections()