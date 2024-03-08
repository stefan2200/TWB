"""
This module can be used in order to report actions to a file or remote MySQL server
"""
import logging
import time
import warnings

try:
    import pymysql

    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False


class RemoteReporter:
    """
    Base class for a reporter object
    """
    def report(self, connection, village_id, action, data):
        """
        Sets report data
        """
        return

    def add_data(self, connection, village_id, data_type, data):
        """
        Sets type-specific data
        """
        return

    def get_config(self, connection, village_id, action, data):
        """
        Gets the configuration from reporter
        """
        return

    def setup(self, connection):
        """
        Set-up the reporter
        """
        return


class FileReporter:
    """
    Reporter that writes data to a text file
    """
    def report(self, connection, village_id, action, data):
        """
        Writes an entry to a report file
        """
        with open(connection, 'a', encoding="utf-8") as f:
            f.write("%d - %s - %s - %s\n" % (time.time(), village_id, action, data))
        return

    def add_data(self, connection, village_id, data_type, data):
        """
        Unused for this type
        """
        return

    def get_config(self, connection, village_id, action, data):
        """
        Unused for this type
        """
        return

    def setup(self, connection):
        """
        Make sure the logfile exists
        """
        with open(connection, 'w', encoding="utf-8") as f:
            f.write("Starting bot at %d\n" % time.time())


class MySQLReporter(RemoteReporter):
    """
    Uses a (remote) MySQL server for logging
    """
    @staticmethod
    def connection_from_object(cobj):
        """
        Fetches variables from a connection config
        """
        return pymysql.connect(
            host=cobj['host'],
            port=cobj['port'],
            user=cobj['user'],
            password=cobj['password'],
            database=cobj['database'])

    def report(self, connection, village_id, action, data):
        """
        Add a report entry
        """
        con = MySQLReporter.connection_from_object(connection)
        cur = con.cursor()
        cur.execute("INSERT INTO twb_logs (village, action, data, ts) VALUES (%s, %s, %s, NOW())",
                    (village_id, action, data))
        con.commit()
        cur.close()
        con.close()

    def add_data(self, connection, village_id, data_type, data):
        """
        Saves data to a remote MySQL server
        """
        con = self.connection_from_object(connection)
        cur = con.cursor()
        cur.execute(
            "SELECT * FROM twb_data WHERE village_id = %s AND data_type = %s",
            (village_id, data_type)
        )
        if cur.rowcount > 0:
            cur.execute(
                "UPDATE twb_data SET data = %s, last_update = NOW() WHERE village_id = %s AND data_type = %s",
                (data, village_id, data_type)
            )
        else:
            cur.execute(
                "INSERT INTO twb_data (village_id, data_type, data, last_update) VALUES (%s, %s, %s, NOW())",
                (village_id, data_type, data)
            )
        con.commit()
        cur.close()
        con.close()

    def setup(self, connection):
        """
        Creates the initial database tables
        """
        try:
            con = self.connection_from_object(connection)
            query_data = """CREATE TABLE IF NOT EXISTS `twb_data` (
                    `id`  int NOT NULL AUTO_INCREMENT ,
                    `village_id`  int NULL ,
                    `data_type`  varchar(50) NULL ,
                    `data`  text NULL ,
                    `last_update`  datetime NULL ,
                    PRIMARY KEY (`id`)
                    )"""
            query_logs = """CREATE TABLE IF NOT EXISTS `twb_logs` (
                            `id`  int NOT NULL AUTO_INCREMENT ,
                            `village_id`  int NULL ,
                            `action`  varchar(50) NULL ,
                            `data`  text NULL ,
                            `ts`  datetime NULL ,
                            PRIMARY KEY (`id`)
                            )"""
            cur = con.cursor()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                cur.execute(query_data)
                cur.execute(query_logs)
                con.commit()
            cur.close()
            con.close()
            return True
        except Exception as e:
            print(f"MYSQL ERROR: {e}")
            return False


class ReporterObject:
    """
    Base reporting object for a remote/local logger
    """
    enabled = False
    object = None
    logger = logging.getLogger("RemoteLogger")
    connection = None

    def __init__(self, enabled=False, connection_string=None):
        """
        Detects reporter configuration
        """
        if enabled and connection_string:
            self.enabled = True
            self.setup(connection_string=connection_string)

    def setup(self, connection_string):
        """
        Fetchers the used reporter
        """
        if connection_string.startswith('mysql://'):
            if not HAS_PYMYSQL:
                self.logger.error("pymysql is required for MYSQL logging\nYou can install it using pip install pymysql")
                self.enabled = False
                return

            parameters = connection_string.split('://')[1]
            creds, host_and_db = parameters.split('@')
            username, password = creds.split(':')
            host, database = host_and_db.split('/')
            port = 3306
            if ":" in host:
                host, port = host.split(":")
                port = int(port)
            self.connection = {"host": host, "port": port, "user": username, "password": password, "database": database}
            self.object = MySQLReporter()
            if self.object.setup(self.connection):
                self.logger.info("MySQL set-up complete")
            else:
                self.logger.info("Unable to set-up MySQL logging, disabling!")
                self.enabled = False
        elif connection_string.startswith('file://'):
            outfile = connection_string.split("://")[1]
            outfile = outfile.replace('{ts}', str(int(time.time())))
            self.connection = outfile
            self.object = FileReporter()
            self.object.setup(self.connection)
        else:
            self.object = RemoteReporter()

    def report(self, village_id, action, data):
        """
        Run the report function on the installed reporter
        """
        if self.enabled:
            return self.object.report(self.connection, village_id, action, data)
        return

    def add_data(self, village_id, data_type, data):
        """
        Run the add_data function on the installed reporter
        """
        if self.enabled:
            return self.object.add_data(self.connection, village_id, data_type, data)
        return

    def get_config(self, village_id, action, data):
        """
        Run the get_config function on the installed reporter
        """
        if self.enabled:
            return self.object.get_config(self.connection, village_id, action, data)
        return
