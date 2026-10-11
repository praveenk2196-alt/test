from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

# CSV-based version of Praveen's Tennis Ranking Explorer.
# No MySQL server, SQLAlchemy, or database credentials are required.

APP_DIR = Path(__file__).resolve().parent
DATA_DIRS = [APP_DIR / "Data", APP_DIR]


st.set_page_config(page_title="Tennis Analytics", page_icon="🎾", layout="wide")


@st.cache_data(show_spinner=False)
def read_csv_file(path_string):
    """Read a CSV safely and cache it until the file changes/app restarts."""
    path = Path(path_string)
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", low_memory=False)


def load_csv(filename):
    """Look in the Data folder first, then beside this Python file."""
    for folder in DATA_DIRS:
        path = folder / filename
        if path.is_file():
            return read_csv_file(str(path))
    return pd.DataFrame()


def find_col(df, *possible_names):
    """Find a column without being sensitive to case, spaces, or underscores."""
    if df.empty:
        return None
    lookup = {
        str(column).strip().lower().replace(" ", "_"): column
        for column in df.columns
    }
    for name in possible_names:
        key = name.strip().lower().replace(" ", "_")
        if key in lookup:
            return lookup[key]
    return None


def rename_to(df, target, *possible_names):
    """Rename the first matching column to a standard internal name."""
    result = df.copy()
    source = find_col(result, target, *possible_names)
    if source is not None and source != target:
        result = result.rename(columns={source: target})
    return result


def show_df(df):
    if df.empty:
        st.info("No records to display. Check the corresponding CSV file.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def numeric_series(df, column):
    return pd.to_numeric(df[column], errors="coerce")


# Expected CSV exports from Praveen's MySQL tables.
competitors_raw = load_csv("competitors.csv")
rankings_raw = load_csv("competitor_rankings.csv")
competitions_raw = load_csv("competitions.csv")
categories_raw = load_csv("categories.csv")
venues_raw = load_csv("venues.csv")
complexes_raw = load_csv("complexes.csv")

# Standardise common column-name variations.
competitors = competitors_raw.copy()
for target, alternatives in {
    "competitor_id": ("id",),
    "name": ("competitor_name", "competitor"),
    "country": ("country_name",),
}.items():
    competitors = rename_to(competitors, target, *alternatives)

rankings = rankings_raw.copy()
for target, alternatives in {
    "competitor_id": ("id",),
    "rank": ("ranking", "position"),
    "points": ("ranking_points",),
    "movement": ("rank_movement",),
    "competitions_played": ("competitions played",),
}.items():
    rankings = rename_to(rankings, target, *alternatives)

competitions = competitions_raw.copy()
for target, alternatives in {
    "competition_id": ("id",),
    "competition_name": ("name",),
    "type": ("competition_type",),
}.items():
    competitions = rename_to(competitions, target, *alternatives)

categories = categories_raw.copy()
for target, alternatives in {
    "category_id": ("id",),
    "category_name": ("name",),
}.items():
    categories = rename_to(categories, target, *alternatives)

venues = venues_raw.copy()
for target, alternatives in {
    "venue_id": ("id",),
    "venue_name": ("name",),
    "country_name": ("country",),
}.items():
    venues = rename_to(venues, target, *alternatives)

complexes = complexes_raw.copy()
for target, alternatives in {
    "complex_id": ("id",),
    "complex_name": ("name",),
}.items():
    complexes = rename_to(complexes, target, *alternatives)

# Recreate Praveen's first SQL JOIN using the CSV files.
ranking_df = pd.DataFrame()
if not rankings.empty:
    ranking_df = rankings.copy()
    if not competitors.empty and "competitor_id" in rankings.columns and "competitor_id" in competitors.columns:
        keep = [
            c for c in [
                "competitor_id", "name", "country", "country_code", "abbreviation"
            ] if c in competitors.columns
        ]
        competitor_lookup = competitors[keep].copy()
        competitor_lookup["competitor_id"] = competitor_lookup["competitor_id"].astype(str).str.strip()
        competitor_lookup = competitor_lookup.drop_duplicates("competitor_id")
        ranking_df["competitor_id"] = ranking_df["competitor_id"].astype(str).str.strip()
        # Avoid duplicate columns if the rankings CSV already contains competitor details.
        add_columns = [c for c in keep if c != "competitor_id" and c not in ranking_df.columns]
        ranking_df = ranking_df.merge(
            competitor_lookup[["competitor_id"] + add_columns],
            on="competitor_id",
            how="left",
        )

# Recreate Praveen's competition/category JOIN.
competition_df = competitions.copy()
if not competition_df.empty and "category_name" not in competition_df.columns:
    if (
        not categories.empty
        and "category_id" in competition_df.columns
        and "category_id" in categories.columns
        and "category_name" in categories.columns
    ):
        category_lookup = categories[["category_id", "category_name"]].drop_duplicates("category_id").copy()
        competition_df["category_id"] = competition_df["category_id"].astype(str).str.strip()
        category_lookup["category_id"] = category_lookup["category_id"].astype(str).str.strip()
        competition_df = competition_df.merge(category_lookup, on="category_id", how="left")

# Recreate Praveen's venues/complexes JOIN.
venue_df = venues.copy()
if not venue_df.empty and "complex_name" not in venue_df.columns:
    if (
        not complexes.empty
        and "complex_id" in venue_df.columns
        and "complex_id" in complexes.columns
        and "complex_name" in complexes.columns
    ):
        complex_lookup = complexes[["complex_id", "complex_name"]].drop_duplicates("complex_id").copy()
        venue_df["complex_id"] = venue_df["complex_id"].astype(str).str.strip()
        complex_lookup["complex_id"] = complex_lookup["complex_id"].astype(str).str.strip()
        venue_df = venue_df.merge(complex_lookup, on="complex_id", how="left")


st.title("🎾 Tennis Ranking Explorer")
st.sidebar.header("Filters")

# Dashboard metrics
col1, col2, col3, col4 = st.columns(4)

competitor_id_col = find_col(ranking_df, "competitor_id")
country_col = find_col(ranking_df, "country")
points_col = find_col(ranking_df, "points")
rank_col = find_col(ranking_df, "rank")

total_competitors = (
    ranking_df[competitor_id_col].nunique()
    if not ranking_df.empty and competitor_id_col
    else (competitors["competitor_id"].nunique() if "competitor_id" in competitors.columns else 0)
)
competition_id_col = find_col(competition_df, "competition_id")
total_competitions = (
    competition_df[competition_id_col].nunique()
    if not competition_df.empty and competition_id_col
    else len(competition_df)
)
total_countries = ranking_df[country_col].nunique() if not ranking_df.empty and country_col else 0
maximum_points = numeric_series(ranking_df, points_col).max() if not ranking_df.empty and points_col else None

col1.metric("Total Competitors", f"{total_competitors:,}")
col2.metric("Total Competitions", f"{total_competitions:,}")
col3.metric("Total Countries", f"{total_countries:,}")
col4.metric("Highest Points", f"{maximum_points:,.0f}" if pd.notna(maximum_points) else "N/A")

missing_files = [
    filename for filename, frame in [
        ("competitors.csv", competitors_raw),
        ("competitor_rankings.csv", rankings_raw),
        ("competitions.csv", competitions_raw),
        ("categories.csv", categories_raw),
        ("venues.csv", venues_raw),
        ("complexes.csv", complexes_raw),
    ] if frame.empty
]
if missing_files:
    st.warning(
        "Some CSV files are missing or empty: "
        + ", ".join(missing_files)
        + ". Put the files in the Data folder beside this Python file."
    )

# Top 10 competitors
st.subheader("Top 10 Competitors")
if ranking_df.empty:
    st.info("Ranking data has not loaded. Check competitor_rankings.csv.")
elif rank_col:
    top_10 = ranking_df.copy()
    top_10["_numeric_rank"] = numeric_series(top_10, rank_col)
    top_10 = top_10.sort_values("_numeric_rank", na_position="last").head(10)
    show_df(top_10.drop(columns="_numeric_rank"))
else:
    st.warning("Could not find a rank column in competitor_rankings.csv.")
    show_df(ranking_df.head(10))

# Country filter
st.header("Filtered Data by Country")
if ranking_df.empty or not country_col:
    st.info("Country filtering needs a country column in the rankings/competitors CSV data.")
else:
    country_options = sorted(ranking_df[country_col].dropna().astype(str).unique().tolist())
    selected_country = st.sidebar.selectbox("Country", ["All"] + country_options)
    filtered_country = ranking_df.copy()
    if selected_country != "All":
        filtered_country = filtered_country[
            filtered_country[country_col].astype(str) == selected_country
        ]
    show_df(filtered_country)

# Country analysis
st.header("🌍 Country Analysis")
if not ranking_df.empty and country_col and points_col:
    country_analysis = ranking_df.copy()
    country_analysis["_numeric_points"] = numeric_series(country_analysis, points_col)
    if competitor_id_col:
        country_stats = country_analysis.groupby(country_col, dropna=False).agg(
            competitors=(competitor_id_col, "nunique"),
            total_points=("_numeric_points", "sum"),
            average_points=("_numeric_points", "mean"),
        ).reset_index()
    else:
        country_stats = country_analysis.groupby(country_col, dropna=False).agg(
            total_points=("_numeric_points", "sum"),
            average_points=("_numeric_points", "mean"),
        ).reset_index()
    country_stats = country_stats.sort_values("total_points", ascending=False)
    show_df(country_stats)
    chart_data = country_stats.head(10).copy()
    chart_data[country_col] = chart_data[country_col].fillna("Unknown").astype(str)
    fig = px.bar(
        chart_data,
        x=country_col,
        y="total_points",
        title="Top 10 Countries by Total Ranking Points",
        labels={country_col: "Country", "total_points": "Total Points"},
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Country analysis needs country and points columns in the loaded ranking data.")

# Rank filter
st.header("Filtered Data by Rank")
if ranking_df.empty or not rank_col:
    st.info("Rank filtering needs a rank column in competitor_rankings.csv.")
else:
    numeric_ranks = numeric_series(ranking_df, rank_col).dropna()
    max_rank = max(500, int(numeric_ranks.max())) if not numeric_ranks.empty else 500
    selected_rank = st.sidebar.number_input("Rank", min_value=1, max_value=max_rank, value=1, step=1)
    filtered_rank = ranking_df[numeric_series(ranking_df, rank_col) == selected_rank]
    show_df(filtered_rank)

# Points distribution
st.header("📈 Points Distribution")
if not ranking_df.empty and points_col:
    points_data = ranking_df.copy()
    points_data["_numeric_points"] = numeric_series(points_data, points_col)
    points_data = points_data.dropna(subset=["_numeric_points"])
    if not points_data.empty:
        fig = px.histogram(
            points_data,
            x="_numeric_points",
            nbins=20,
            title="Distribution of Competitor Points",
            labels={"_numeric_points": "Ranking Points"},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("The points column has no numeric values.")
else:
    st.info("Points distribution needs a points column in competitor_rankings.csv.")

# Gender filter for competitions
st.header("Filtered Data by Gender")
gender_col = find_col(competition_df, "gender")
if competition_df.empty or not gender_col:
    st.info("Gender filtering needs competition data with a gender column.")
else:
    gender_options = sorted(competition_df[gender_col].dropna().astype(str).unique().tolist())
    selected_gender = st.selectbox("Gender", ["All"] + gender_options)
    filtered_gender = competition_df.copy()
    if selected_gender != "All":
        filtered_gender = filtered_gender[filtered_gender[gender_col].astype(str) == selected_gender]
    show_df(filtered_gender)

# Venue and complex table
st.header("Complexes and Venues")
show_df(venue_df)

# Search competitor
st.header("🔍 Search Competitor")
name_col = find_col(ranking_df, "name", "competitor_name")
search_name = st.text_input("Enter competitor name")
if search_name:
    if name_col:
        search_result = ranking_df[
            ranking_df[name_col].astype(str).str.contains(search_name, case=False, na=False)
        ]
        if search_result.empty:
            st.warning("No competitor found.")
        else:
            preferred = [
                "name", "country", "country_code", "rank", "points",
                "movement", "competitions_played"
            ]
            display_cols = [c for c in preferred if c in search_result.columns]
            show_df(search_result[display_cols] if display_cols else search_result)
    else:
        st.info("Competitor names could not be found. Check competitors.csv and competitor_rankings.csv.")
