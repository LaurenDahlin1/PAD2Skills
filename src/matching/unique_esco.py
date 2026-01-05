"""Create unique ESCO matches from selection results."""

import ast
from pathlib import Path

import pandas as pd


def format_skills(skills_str: str) -> str:
    """Format skills string by removing brackets and adding quotes.

    Args:
        skills_str: String representation of skills list

    Returns:
        Formatted skills string with quoted items
    """
    if pd.isna(skills_str):
        return ""
    try:
        # Parse the string as a list
        skills_list = ast.literal_eval(skills_str)
        # Add quotes around each skill and join with comma
        return ", ".join([f'"{skill}"' for skill in skills_list])
    except Exception:
        # If parsing fails, return as is
        return skills_str


def create_unique_esco_matches(
    project_id: str,
    selections_csv_path: Path,
    esco_occupations_path: Path,
    output_path: Path,
    overwrite: bool = False,
) -> pd.DataFrame:
    """Create unique ESCO matches file from selections.

    This function:
    1. Loads the ESCO selections CSV
    2. Filters out records that need manual review
    3. Formats quotes with section names
    4. Groups by ESCO ID and aggregates PAD data
    5. Merges with ESCO occupations data
    6. Saves the result as a CSV

    Args:
        project_id: Project identifier (e.g., P075941)
        selections_csv_path: Path to the _esco_selections.csv file
        esco_occupations_path: Path to the ESCO occupations CSV
        output_path: Path where the unique matches CSV will be saved
        overwrite: If False, skip processing if output file exists

    Returns:
        DataFrame with unique ESCO matches and aggregated PAD data
    """
    # Check if output already exists and skip if not overwriting
    if output_path.exists() and not overwrite:
        print(f"○ Skipped (already exists): {output_path.name}")
        return pd.read_csv(output_path)
    
    # Read the esco_selections CSV
    df_selections = pd.read_csv(selections_csv_path)

    print(f"✓ Loaded selections data: {len(df_selections)} rows")
    print(f"  Columns: {list(df_selections.columns)}")

    # Drop records where needs_manual_review = True
    df_filtered = df_selections[df_selections["needs_manual_review"] != True].copy()  # noqa: E712
    dropped_count = len(df_selections) - len(df_filtered)

    print("\n✓ Filtered out records with needs_manual_review=True")
    print(f"  Dropped: {dropped_count} rows")
    print(f"  Remaining: {len(df_filtered)} rows")

    # Add pad_section_name to the front of each pad_quote
    # Convert pad_section_name to string and handle NaN values
    df_filtered["pad_section_name"] = df_filtered["pad_section_name"].fillna("").astype(str)
    df_filtered["pad_quote"] = df_filtered["pad_quote"].fillna("").astype(str)
    
    df_filtered["pad_quote"] = (
        df_filtered["pad_section_name"] + ': "' + df_filtered["pad_quote"] + '"'
    )

    print("\n✓ Formatted pad_quote with section names")

    # Group by esco_id and aggregate
    grouped = (
        df_filtered.groupby(["project_id", "esco_id", "esco_label"])
        .agg(
            {
                "pad_occupation": lambda x: ", ".join(
                    [
                        f'"{occupation}"'
                        for occupation in x.dropna().astype(str).unique()
                    ]
                ),
                "pad_activity": lambda x: ", ".join(
                    [f'"{activity}"' for activity in x.dropna().astype(str).unique()]
                ),
                "pad_skills": lambda x: ", ".join(
                    [format_skills(skill) for skill in x.dropna().astype(str).unique()]
                ),
                "pad_quote": lambda x: ", ".join(x.dropna().astype(str).unique()),
            }
        )
        .reset_index()
    )

    # Rename columns
    grouped = grouped.rename(
        columns={
            "pad_occupation": "pad_occupations",
            "pad_activity": "pad_activities",
            "pad_quote": "pad_quotes",
        }
    )

    print("\n✓ Flattened data by esco_id")
    print(f"  Unique ESCO IDs: {len(grouped)}")

    # Create esco_uri from esco_id
    grouped["esco_uri"] = "http://data.europa.eu/esco/occupation/" + grouped["esco_id"]

    print("✓ Created esco_uri field")

    # Load ESCO occupations data
    esco_df = pd.read_csv(esco_occupations_path)

    print(f"\n✓ Loaded ESCO occupations data: {len(esco_df)} rows")

    # Select relevant columns from ESCO data
    esco_subset = esco_df[["conceptUri", "description"]].copy()
    esco_subset = esco_subset.rename(
        columns={"conceptUri": "esco_uri", "description": "esco_description"}
    )

    # Merge with grouped data
    df_unique = grouped.merge(esco_subset, on="esco_uri", how="left")

    # Reorder columns
    column_order = [
        "project_id",
        "esco_id",
        "esco_label",
        "esco_description",
        "pad_occupations",
        "pad_activities",
        "pad_skills",
        "pad_quotes",
        "esco_uri",
    ]
    df_unique = df_unique[column_order]

    print("\n✓ Merged with ESCO data")
    print(f"  Final rows: {len(df_unique)}")
    print(f"  Columns: {list(df_unique.columns)}")
    print(
        f"  Non-null esco_description count: {df_unique['esco_description'].notna().sum()}"
    )

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to CSV
    df_unique.to_csv(output_path, index=False)

    print(f"\n✓ Saved unique ESCO matches to: {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024:.2f} KB")
    print(f"  Rows: {len(df_unique):,}")
    print(f"  Columns: {len(df_unique.columns)}")
    print("\nCSV contains:")
    print("  - Unique ESCO occupations with aggregated PAD data")
    print("  - ESCO descriptions")
    print("  - Collapsed occupations, activities, skills, and quotes")

    return df_unique
