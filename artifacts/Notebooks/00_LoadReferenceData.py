# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "__LAKEHOUSE_ID__",
# META       "default_lakehouse_name": "ColdChainLakehouse",
# META       "default_lakehouse_workspace_id": "__WORKSPACE_ID__",
# META       "known_lakehouses": [
# META         {
# META           "id": "__LAKEHOUSE_ID__"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# =============================================================================
# 00_LoadReferenceData
#
# Fabric IQ workshop -- Module 01/02 supporting notebook.
#
# Loads the three cold-chain reference CSVs (Stores, Freezers, Customers)
# from this Lakehouse's Files section into three managed Delta tables of the
# same names. This is the "static/contextual data" half of the RTI +
# ontology pattern this workshop follows: live freezer telemetry streams in
# via FreezerTelemetryEventstream (see artifacts/Eventstream/), while the
# slower-changing "who/where/what" reference data lands here, in the
# Lakehouse, where a Fabric IQ ontology (built live in Module 03) can bind to
# it as entity properties.
#
# This file is checked in using Fabric's own notebook git-source format (the
# "# META"-prefixed blocks above and between cells) rather than a generic
# "# %%"-cell-marker script, so setup/provision_fabric_iq.py can `fab import`
# it directly -- no hand-built-in-a-dev-tenant export round trip needed. The
# __LAKEHOUSE_ID__/__WORKSPACE_ID__ placeholders above are substituted with
# real IDs at import time (see create_notebook_item() in
# setup/provision_fabric_iq.py), which is also what binds this notebook's
# default Lakehouse -- no manual "Add data items" step required either. See
# ../Notebooks/HOW-TO-EXPORT.md for the full story, including why this only
# works because the notebook's *content* needs no tenant-specific values.
#
# PREREQUISITES:
#   The three CSVs must already be uploaded to:
#     Files/SampleData/stores.csv
#     Files/SampleData/freezers.csv
#     Files/SampleData/customers.csv
#   (setup/provision_fabric_iq.py's Lakehouse step does this before this
#   notebook is imported.)
#
# RUNNING THIS NOTEBOOK:
#   Open it in the Fabric portal and select "Run all". On success, three
#   Delta tables appear under this Lakehouse's Tables section: Customers,
#   Stores, Freezers.
# =============================================================================

from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DateType,
)

# Base path for the reference CSVs, relative to the attached default
# Lakehouse's Files section. If you prefer an absolute OneLake path instead
# (e.g. when running this notebook without a default Lakehouse attached),
# replace this with:
#   abfss://<workspace-id>@onelake.dfs.fabric.microsoft.com/<lakehouse-id>/Files/SampleData
SAMPLE_DATA_PATH = "Files/SampleData"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def load_csv(file_name: str, schema: StructType):
    """Read one reference CSV from the Lakehouse Files section with an
    explicit schema (safer than schema inference for a workshop -- it fails
    loudly and immediately if a column is missing or misnamed, rather than
    silently inferring the wrong type)."""
    path = f"{SAMPLE_DATA_PATH}/{file_name}"
    return (
        spark.read.option("header", True)
        .schema(schema)
        .csv(path)
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# --- Stores -------------------------------------------------------------
# StoreId, StoreName, Region, City
stores_schema = StructType(
    [
        StructField("StoreId", StringType(), nullable=False),
        StructField("StoreName", StringType(), nullable=False),
        StructField("Region", StringType(), nullable=False),
        StructField("City", StringType(), nullable=False),
    ]
)

stores_df = load_csv("stores.csv", stores_schema)

(
    stores_df.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("Stores")
)

print(f"Stores loaded: {stores_df.count()} rows")
display(stores_df)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# --- Freezers -------------------------------------------------------------
# FreezerId, StoreId, Model, Capacity, InstallDate
freezers_schema = StructType(
    [
        StructField("FreezerId", StringType(), nullable=False),
        StructField("StoreId", StringType(), nullable=False),
        StructField("Model", StringType(), nullable=False),
        StructField("Capacity", IntegerType(), nullable=False),
        StructField("InstallDate", DateType(), nullable=False),
    ]
)

freezers_df = load_csv("freezers.csv", freezers_schema)

(
    freezers_df.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("Freezers")
)

print(f"Freezers loaded: {freezers_df.count()} rows")
display(freezers_df)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# --- Customers -------------------------------------------------------------
# CustomerId, Name, HomeStoreId, LoyaltyTier
customers_schema = StructType(
    [
        StructField("CustomerId", StringType(), nullable=False),
        StructField("Name", StringType(), nullable=False),
        StructField("HomeStoreId", StringType(), nullable=False),
        StructField("LoyaltyTier", StringType(), nullable=False),
    ]
)

customers_df = load_csv("customers.csv", customers_schema)

(
    customers_df.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("Customers")
)

print(f"Customers loaded: {customers_df.count()} rows")
display(customers_df)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# --- Verification -----------------------------------------------------------
# Quick sanity check: join Freezers -> Stores to confirm referential
# integrity of the reference data before attendees move on to Module 02's
# streaming-enrichment lab (which mirrors this same join, but in KQL, over
# live telemetry -- see artifacts/Eventhouse/ColdChainKQLDB.kql).
verification_df = freezers_df.join(stores_df, on="StoreId", how="left").select(
    "FreezerId", "Model", "Capacity", "StoreId", "StoreName", "Region", "City"
)

print("Freezers joined to Stores (spot-check -- every row should have a StoreName):")
display(verification_df.orderBy("FreezerId"))

unmatched = verification_df.filter(F.col("StoreName").isNull()).count()
if unmatched > 0:
    raise ValueError(
        f"{unmatched} freezer(s) reference a StoreId not present in stores.csv. "
        "Check artifacts/SampleData/freezers.csv and stores.csv for a typo."
    )

print("00_LoadReferenceData completed successfully: Stores, Freezers, Customers tables are ready.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
