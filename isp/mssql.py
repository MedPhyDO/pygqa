# -*- coding: utf-8 -*-

"""ispMssql

pip install python-tds

pip install pyodbc

for using pyodbc install microsoft-odbc with unixODBC development headers

Example:

msdb = mssqlClass( "KonfigurationName" )

print( msdb.getDbVersion() ) )

or

print( msdb.execute("select @@version as version") )

use {dbname} in sql querys to replace it with dbname from config


CHANGELOG
=========
0.1.2 / 2024-03-18
------------------
- some code cleanup and documentation

0.1.1 / 2021-09-03
------------------
- add support for pyodbc

0.1.0 / 2021-01-16
------------------
- First Release

"""

__author__ = "R. Bauer"
__copyright__ = "MedPhyDO - Machbarkeitsstudien des Instituts für Medizinische Strahlenphysik und Strahlenschutz am Klinikum Dortmund im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund"
__credits__ = ["R.Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.1.2"
__status__ = "Prototype"


import logging
logger = logging.getLogger( "ISP" )

class ispMssql( ):
    '''Database querys on mssql database

    Attributes
    ----------

    name : str
        database configuration name from config

    connect : class
         An instance of :class:`Connection`

    engine : str
         Databaseengine `pytds` or `pyodbc`

    dbname : object
        Names of dbname in connection

    lastExecuteSql: str
        Holds last executed sql query

    config: Dot
        An instance of ispConfig

    '''

    def __init__( self, name:str=None, config=None):
        '''initialise class

        Parameters
        ----------
        name : str, optional
            used to get database configuration from config
        config : Dot, optional
            An instance of ispConfig
        Returns
        -------
        None.

        '''

        self.connect = None
        self.engine = None
        self.name = None
        self.dbname = None
        self.lastExecuteSql = ""

        if config:
            self.config = config

        if name:
            self.name = name


    def openDatabase( self, name:str=None ):
        '''Open database connection

        holds connection in self.connect

        Parameters
        ----------
        name : str, optional
            used to get database configuration from config

        Returns
        -------
        class
            An instance of :class:`Connection`.

        '''

        self.connect = None
        if not name:
            name = self.name
        if not name:  # pragma: no cover
            logger.warning( "mssqlClass.openDatabase - missing databasename." )
            return

        if self.config.database[ name ]:
            self.engine = self.config.database[name].get("engine", "pytds")
            self.dbname = self.config.database[name].get("dbname", name )

            if self.engine == "pytds":
                import pytds
                try:
                    self.connect = pytds.connect(
                        dsn = self.config.database[name].host,
                        database = self.dbname,
                        user = self.config.database[name].user,
                        password = self.config.database[name].password,
                        as_dict = True,
                        login_timeout = int( self.config.database[name].get("login_timeout", 3 ) ) # timeout for connection and login in seconds, default 15
                    )

                except Exception as err: # pragma: no cover
                    logger.warning( "mssqlClass.openDatabase '{}' failed. {}".format( name, err ) )

            elif self.engine == "pyodbc":
                import pyodbc
                DRIVER = self.config.database[name].driver
                SERVER = self.config.database[name].server_ip
                DATABASE = self.config.database[name].dbname
                USERNAME = self.config.database[name].user
                PASSWORD = self.config.database[name].password
                connectionString = f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'
                try:
                    self.connect = pyodbc.connect( connectionString )
                except Exception as err:
                    logger.warning( "mssqlClass.openDatabase '{}' failed. {}".format( name, err ) )

        return self.connect

    def close(self):
        """close database connection
        """
        self.connect.close()

    def execute( self, sql ):
        """Execute database Query

        If not connected open database

        holds last sqlquery in this.lastExecuteSql

        Parameters
        ----------
        sql : str
            sql query string

        Returns
        -------
        list
            query result from execute fetchall

        """

        def to_dict(row):
            return dict(zip([t[0] for t in row.cursor_description], row))

        result = []
        # try to open database once. if not possible leave function
        if not self.connect:
            if not self.openDatabase( self.name ): # pragma: no cover
                return result

        sql = sql.format( dbname=self.dbname )
        # use with to close cursor automatically
        try:
            with self.connect.cursor() as cur:
                cur.execute( sql )

                if self.engine == "pyodbc":
                    rows = cur.fetchall()
                    result = [to_dict(row) for row in rows ]
                else:
                    result = cur.fetchall()

        except Exception as err: # pragma: no cover
            logger.warning( "mssqlClass.execute: {} ".format(err ) )

        self.lastExecuteSql = sql
        return result

    def getDbVersion(self):
        """Ask database for version

        Returns
        -------
        str
            version result string

        """
        result = self.execute( "select @@version as version" )
        if len( result ) > 0:
            return str(result[0]["version"])
        else:
            return ""