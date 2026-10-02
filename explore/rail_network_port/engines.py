"""One interface over the two engines.

DuckDB and SedonaDB both give SQL over files with no server. Explore using either here.

TODO - remove this and pick SedonaDB.
"""

import geopandas as gpd


class DuckDB:
    """DuckDB with spatial extension.
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
    """SedonaDB backend
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
