from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    if not version:
        return

    # Remove the unique constraint
    cr.execute("""
        SELECT conname
        FROM pg_constraint
        WHERE conname = 'import_fees_harmonized_code_name_uniq'
    """)
    if cr.fetchone():
        cr.execute("""
            ALTER TABLE import_fees_harmonized_code
            DROP CONSTRAINT import_fees_harmonized_code_name_uniq
        """)

    # If you also want to remove the SQL index (if it exists)
    cr.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE indexname = 'import_fees_harmonized_code_name_index'
    """)
    if cr.fetchone():
        cr.execute("""
            DROP INDEX import_fees_harmonized_code_name_index
        """)

    # Log the change
    cr.execute("""
        INSERT INTO ir_logging(create_date, create_uid, type, dbname, name, level, message, path, line, func)
        VALUES (now() at time zone 'UTC', %s, 'server', current_database(), 'import_fees', 'info', 'Removed unique constraint on import_fees_harmonized_code table', 'migrations', 0, 'migrate')
    """, (SUPERUSER_ID,))