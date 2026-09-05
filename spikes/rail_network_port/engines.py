"""One interface over the two engines the port could run on.

DuckDB and SedonaDB both give SQL over files with no server, and the steps in
``prepare_network.py`` run unchanged on either: the two adapters here differ
only in how a table is loaded and how results come back. Keeping both lets the
same work be timed on each.

This is spike code - see README.md. It is not part of the workflow.
"""

import geopandas as gpd


class DuckDB:
    """DuckDB with its spatial extension.

    Reads GeoPackage directly through GDAL, keeps tables in a database file,
    and writes GeoPackage back with ``COPY ... (FORMAT gdal)``.
    """

    name = "duckdb"

    def __init__(self, database=":memory:"):
        import duckdb

        self.con = duckdb.connect(database)
        self.con.execute("INSTALL spatial; LOAD spatial;")

    def load_layer(self, table, path, layer=None):
        source = f"st_read('{path}'" + (f", layer = '{layer}')" if layer else ")")
        self.con.execute(
            f"""
            create or replace table {table} as
            select * exclude geom, st_setcrs(geom, 'EPSG:4326') as geom
            from {source}
            """
        )

    def load_frame(self, table, frame):
        self.con.register(f"{table}_frame", frame)
        self.con.execute(
            f"create or replace table {table} as select * from {table}_frame"
        )

    def sql(self, statement):
        self.con.execute(statement)

    def rows(self, query):
        return self.con.execute(query).fetchall()

    def value(self, query):
        return self.rows(query)[0][0]


class SedonaDB:
    """SedonaDB, the single-node Rust engine.

    Has no GDAL reader of its own, so layers come in through geopandas and
    pyogrio. Tables live in memory rather than in a database file.
    """

    name = "sedonadb"

    def __init__(self, database=None):
        import sedonadb

        self.sd = sedonadb.connect()

    def load_layer(self, table, path, layer=None):
        frame = gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)
        self.load_frame(table, frame.set_crs("EPSG:4326", allow_override=True))

    def load_frame(self, table, frame):
        if isinstance(frame, gpd.GeoDataFrame):
            frame = frame.rename_geometry("geom")
        self.sd.create_data_frame(frame).to_view(table, overwrite=True)

    def sql(self, statement):
        # A statement at a time: DataFusion takes one per call.
        for part in filter(str.strip, statement.split(";")):
            self.sd.sql(part).to_pandas()

    def rows(self, query):
        return self.sd.sql(query).to_pandas().values.tolist()

    def value(self, query):
        return self.rows(query)[0][0]


ENGINES = {engine.name: engine for engine in (DuckDB, SedonaDB)}
