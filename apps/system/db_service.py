"""
AquaFlow — Database Configuration Service
Powered by Quantum Axis

Handles:
- Test database connection
- Detect empty/wrong databases
- Save to .env file
- Rollback on failure
"""

import psycopg2
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger('apps')


class DatabaseService:

    @staticmethod
    def test_connection(host, port, db_name, username, password, ssl_mode='prefer'):
        """
        Test database connection. Returns dict with detailed info.
        """
        result = {
            'success':      False,
            'error':        '',
            'server_version': '',
            'database_exists': False,
            'has_aquaflow_tables': False,
            'table_count': 0,
            'user_count':  0,
            'is_empty':    True,
            'warnings':    [],
        }

        try:
            conn = psycopg2.connect(
                host=host,
                port=int(port),
                dbname=db_name,
                user=username,
                password=password,
                sslmode=ssl_mode,
                connect_timeout=10,
            )
            result['success'] = True
            result['database_exists'] = True

            cursor = conn.cursor()

            # Get PostgreSQL version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            result['server_version'] = version.split(',')[0]

            # Count tables in public schema
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
            """)
            table_count = cursor.fetchone()[0]
            result['table_count'] = table_count
            result['is_empty'] = table_count == 0

            # Check for AquaFlow-specific tables
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                    'businesses', 'customers', 'vehicles',
                    'orders', 'invoices', 'services'
                  )
            """)
            aq_tables = cursor.fetchone()[0]
            result['has_aquaflow_tables'] = aq_tables >= 3

            # Count users (if table exists)
            try:
                cursor.execute("SELECT COUNT(*) FROM auth_user")
                result['user_count'] = cursor.fetchone()[0]
            except Exception:
                pass

            # Warnings
            if result['is_empty']:
                result['warnings'].append(
                    'This database is empty. If you switch, the app will appear empty.'
                )
            elif not result['has_aquaflow_tables']:
                result['warnings'].append(
                    'This database does NOT contain AquaFlow tables. '
                    'It may belong to a different application!'
                )

            cursor.close()
            conn.close()

        except psycopg2.OperationalError as e:
            error_msg = str(e).strip()
            result['error'] = error_msg

            if 'authentication failed' in error_msg.lower():
                result['error'] = 'Authentication failed. Check username and password.'
            elif 'does not exist' in error_msg.lower():
                result['error'] = f'Database "{db_name}" does not exist on server.'
            elif 'could not connect' in error_msg.lower() or 'timeout' in error_msg.lower():
                result['error'] = f'Cannot reach server at {host}:{port}. Check host/port/firewall.'
            elif 'ssl' in error_msg.lower():
                result['error'] = f'SSL error: {error_msg}'

        except Exception as e:
            result['error'] = f'Unexpected error: {str(e)}'

        return result

    @staticmethod
    def update_env_file(config_dict):
        """
        Update .env file with new database config.
        Preserves other settings.
        """
        env_path = Path(settings.BASE_DIR) / '.env'

        if not env_path.exists():
            raise Exception('.env file not found.')

        # Read existing lines
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Update or add each key
        updated_keys = set()
        new_lines = []

        for line in lines:
            stripped = line.strip()

            # Preserve comments and blank lines
            if not stripped or stripped.startswith('#'):
                new_lines.append(line)
                continue

            # Check if this line matches any of our keys
            if '=' in stripped:
                key = stripped.split('=', 1)[0].strip()
                if key in config_dict:
                    new_lines.append(f'{key}={config_dict[key]}\n')
                    updated_keys.add(key)
                    continue

            new_lines.append(line)

        # Add any keys that weren't already in the file
        for key, value in config_dict.items():
            if key not in updated_keys:
                new_lines.append(f'{key}={value}\n')

        # Write back
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        return True