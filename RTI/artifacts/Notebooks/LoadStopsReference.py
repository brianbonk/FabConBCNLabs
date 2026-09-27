# LoadStopsReference
#
# Lab 06 (RTI half). Loads every CSV found in the default Lakehouse's
# Files/reference/ folder into the managed Delta table `Stops`.
#
# Designed to be run by an Activator rule that fires on the OneLake
# `Microsoft.Fabric.OneLake.FileCreated` event for that folder, so it:
#   - exits cleanly (no error) when the folder is empty, so the one manual
#     validation run in Lab 06 Part A succeeds before any file exists;
#   - overwrites the table on every run (idempotent; re-uploading a file is a
#     "replace" that raises FileCreated again).
#
# Requires TransitLakehouse attached as the notebook's default lakehouse.

from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, DoubleType, BooleanType, IntegerType,
)

REFERENCE_PATH = "Files/reference"
TARGET_TABLE = "Stops"

stops_schema = StructType([
    StructField("StopCode", LongType(), nullable=False),
    StructField("StopName", StringType(), nullable=False),
    StructField("Address", StringType(), nullable=True),
    StructField("Zone", StringType(), nullable=False),
    StructField("Lat", DoubleType(), nullable=False),
    StructField("Lon", DoubleType(), nullable=False),
    StructField("Lines", StringType(), nullable=True),
    StructField("IsPrimary", BooleanType(), nullable=True),
    StructField("PollIntervalSeconds", IntegerType(), nullable=True),
])

# List the folder; if it doesn't exist or is empty, stop quietly.
try:
    entries = notebookutils.fs.ls(REFERENCE_PATH)  # type: ignore[name-defined]
except Exception as exc:  # folder missing, or no default lakehouse attached
    print(f"Could not list {REFERENCE_PATH}: {exc}")
    print("Attach TransitLakehouse as the default lakehouse and make sure Files/reference exists.")
    raise

csv_files = [e.path for e in entries if e.name.lower().endswith(".csv")]

if not csv_files:
    print(f"No files in {REFERENCE_PATH} yet; nothing to load.")
else:
    print(f"Found {len(csv_files)} CSV file(s):")
    for p in csv_files:
        print("  ", p)

    df = (
        spark.read.option("header", True)  # type: ignore[name-defined]
        .schema(stops_schema)
        .csv(csv_files)
    )

    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(TARGET_TABLE)
    )

    count = spark.table(TARGET_TABLE).count()  # type: ignore[name-defined]
    print(f"Loaded {count} rows into {TARGET_TABLE}.")
    display(spark.table(TARGET_TABLE).orderBy("Zone", "StopName"))  # type: ignore[name-defined]
