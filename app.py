import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Dashboard Performance Retail",
    page_icon="📊",
    layout="wide"
)

# =========================
# STYLE
# =========================

st.markdown("""
<style>
.main-title {
    font-size: 42px;
    font-weight: 800;
    color: #1f2937;
}
.subtitle {
    font-size: 18px;
    color: #4b5563;
}
.kpi-card {
    background-color: #f8fafc;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #e5e7eb;
}
.section-title {
    font-size: 26px;
    font-weight: 700;
    color: #111827;
    margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)


# =========================
# FUNCTIONS
# =========================

def convert_excel_or_date(x):
    if pd.isna(x):
        return pd.NaT
    if isinstance(x, pd.Timestamp):
        return x
    if hasattr(x, "year") and hasattr(x, "month") and hasattr(x, "day"):
        return pd.Timestamp(x)
    try:
        return pd.to_datetime("1899-12-30") + pd.to_timedelta(float(x), unit="D")
    except Exception:
        return pd.to_datetime(x, errors="coerce")


@st.cache_data
def load_data(file):
    succ = pd.read_excel(file, sheet_name="Succ", header=3)
    franchises = pd.read_excel(file, sheet_name="Franchises", header=3)

    succ = succ.rename(columns={
        "date": "Date",
        "Code mag": "Code_magasin",
        "Magasins": "Nom_magasin",
        "régions": "Region",
        "enseignes": "Enseigne",
        "Somme de CA N": "CA_N",
        "Somme de CA N-1": "CA_N_1",
        "Somme de Budget": "Budget"
    })

    succ["type_magasin"] = "Succursale"
    succ["Date"] = succ["Date"].apply(convert_excel_or_date)

    franchises = franchises.rename(columns={
        "Date telex": "Date",
        "Code Magasin": "Code_magasin",
        "Somme de CA N": "CA_N",
        "Somme de CA N-1": "CA_N_1",
        "Somme de Budget CA": "Budget",
        "Région": "Region",
        "Enseigne": "Enseigne"
    })

    franchises["type_magasin"] = "Franchise"
    franchises["Date"] = pd.to_datetime(franchises["Date"], errors="coerce")
    franchises["Nom_magasin"] = franchises["Code_magasin"]

    cols = [
        "Date", "Code_magasin", "Nom_magasin", "Region",
        "Enseigne", "CA_N", "CA_N_1", "Budget", "type_magasin"
    ]

    data = pd.concat([succ[cols], franchises[cols]], ignore_index=True)

    for col in ["CA_N", "CA_N_1", "Budget"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=["Date", "Code_magasin", "CA_N"])
    data["CA_N_1"] = data["CA_N_1"].fillna(0)
    data["Budget"] = data["Budget"].fillna(0)

    data["mois"] = data["Date"].dt.month
    data["jour"] = data["Date"].dt.date

    return data


def format_euro(value):
    return f"{value:,.0f} €".replace(",", " ")


def format_percent(value):
    if pd.isna(value) or np.isinf(value):
        return "N/A"
    return f"{value:.1f} %"


# =========================
# HEADER
# =========================

st.markdown('<div class="main-title">📊 Dashboard Performance Retail</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Analyse avancée des performances commerciales : Succursales vs Franchises</div>',
    unsafe_allow_html=True
)

st.divider()


# =========================
# SIDEBAR
# =========================

st.sidebar.title("⚙️ Paramètres")
uploaded_file = st.sidebar.file_uploader(
    "Importer le fichier Excel",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Importe le fichier Excel pour lancer l’analyse.")
    st.stop()

data = load_data(uploaded_file)

st.sidebar.success("Fichier chargé avec succès")

st.sidebar.header("🔎 Filtres")
min_date = data["Date"].min().date()
max_date = data["Date"].max().date()

selected_date_range = st.sidebar.date_input(
    "Plage de dates",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(selected_date_range) == 2:
    start_date, end_date = selected_date_range
else:
    start_date, end_date = min_date, max_date

type_options = sorted(data["type_magasin"].dropna().unique())
region_options = sorted(data["Region"].dropna().unique())
enseigne_options = sorted(data["Enseigne"].dropna().unique())

selected_types = st.sidebar.multiselect(
    "Type de réseau",
    options=type_options,
    default=type_options
)

selected_regions = st.sidebar.multiselect(
    "Région",
    options=region_options,
    default=region_options
)

selected_enseignes = st.sidebar.multiselect(
    "Enseigne",
    options=enseigne_options,
    default=enseigne_options
)

filtered = data[
    (data["type_magasin"].isin(selected_types)) &
    (data["Region"].isin(selected_regions)) &
    (data["Enseigne"].isin(selected_enseignes)) &
    (data["Date"].dt.date >= start_date) &
    (data["Date"].dt.date <= end_date)
]

if filtered.empty:
    st.warning("Aucune donnée disponible avec les filtres sélectionnés.")
    st.stop()


# =========================
# KPI
# =========================

total_ca = filtered["CA_N"].sum()
total_ca_n1 = filtered["CA_N_1"].sum()
total_budget = filtered["Budget"].sum()
nb_magasins = filtered["Code_magasin"].nunique()

croissance = ((total_ca - total_ca_n1) / total_ca_n1 * 100) if total_ca_n1 != 0 else np.nan
realisation_budget = (total_ca / total_budget * 100) if total_budget != 0 else np.nan
ecart_budget = total_ca - total_budget

st.markdown('<div class="section-title">Vue globale</div>', unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric("CA N", format_euro(total_ca))
kpi2.metric("CA N-1", format_euro(total_ca_n1), delta=format_percent(croissance))
kpi3.metric("Budget", format_euro(total_budget), delta=format_euro(ecart_budget))
kpi4.metric("Magasins actifs", nb_magasins)

kpi5, kpi6 = st.columns(2)
kpi5.metric("Croissance vs N-1", format_percent(croissance))
kpi6.metric("Réalisation budget", format_percent(realisation_budget))

st.divider()


# =========================
# TABS
# =========================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Évolution",
    "🏬 Réseaux",
    "🌍 Régions",
    "🏆 Magasins",
    "🚨 Alertes"
])


# =========================
# TAB 1 EVOLUTION
# =========================

with tab1:
    st.subheader("Évolution du chiffre d’affaires")

    evolution = filtered.groupby(["Date", "type_magasin"])["CA_N"].sum().unstack()

    fig, ax = plt.subplots(figsize=(12, 5))
    evolution.plot(ax=ax)
    ax.set_title("Évolution du CA par type de réseau")
    ax.set_xlabel("Date")
    ax.set_ylabel("CA N")
    ax.grid(True)
    st.pyplot(fig)

    st.markdown("""
    **Lecture business :**  
    Cette vue permet d’identifier les tendances de chiffre d’affaires, les pics d’activité
    et les écarts de dynamique entre succursales et franchises.
    """)


# =========================
# TAB 2 RESEAUX
# =========================

with tab2:
    st.subheader("Analyse par type de réseau")

    perf_type = filtered.groupby("type_magasin").agg(
        CA_N=("CA_N", "sum"),
        CA_N_1=("CA_N_1", "sum"),
        Budget=("Budget", "sum"),
        nb_magasins=("Code_magasin", "nunique")
    ).reset_index()

    perf_type["croissance_%"] = np.where(
        perf_type["CA_N_1"] != 0,
        (perf_type["CA_N"] - perf_type["CA_N_1"]) / perf_type["CA_N_1"] * 100,
        np.nan
    )

    perf_type["realisation_budget_%"] = np.where(
        perf_type["Budget"] != 0,
        perf_type["CA_N"] / perf_type["Budget"] * 100,
        np.nan
    )

    perf_type["CA_moyen_magasin"] = perf_type["CA_N"] / perf_type["nb_magasins"]

    st.dataframe(perf_type, use_container_width=True)

    fig, ax = plt.subplots(figsize=(8, 4))
    perf_type.set_index("type_magasin")["CA_N"].plot(kind="bar", ax=ax)
    ax.set_title("CA par type de réseau")
    ax.set_ylabel("CA N")
    ax.set_xlabel("")
    st.pyplot(fig)


# =========================
# TAB 3 REGIONS
# =========================

with tab3:
    st.subheader("Performance par région")

    perf_region = filtered.groupby("Region").agg(
        CA_N=("CA_N", "sum"),
        CA_N_1=("CA_N_1", "sum"),
        Budget=("Budget", "sum"),
        nb_magasins=("Code_magasin", "nunique")
    ).reset_index()

    perf_region["croissance_%"] = np.where(
        perf_region["CA_N_1"] != 0,
        (perf_region["CA_N"] - perf_region["CA_N_1"]) / perf_region["CA_N_1"] * 100,
        np.nan
    )

    perf_region["realisation_budget_%"] = np.where(
        perf_region["Budget"] != 0,
        perf_region["CA_N"] / perf_region["Budget"] * 100,
        np.nan
    )

    perf_region = perf_region.sort_values("CA_N", ascending=False)

    st.dataframe(perf_region, use_container_width=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    perf_region.set_index("Region")["CA_N"].plot(kind="bar", ax=ax)
    ax.set_title("CA par région")
    ax.set_ylabel("CA N")
    ax.set_xlabel("")
    st.pyplot(fig)


# =========================
# TAB 4 MAGASINS
# =========================

with tab4:
    st.subheader("Analyse magasins")

    perf_magasin = filtered.groupby(
        ["Code_magasin", "Nom_magasin", "type_magasin", "Region", "Enseigne"]
    ).agg(
        CA_N=("CA_N", "sum"),
        CA_N_1=("CA_N_1", "sum"),
        Budget=("Budget", "sum")
    ).reset_index()

    perf_magasin["croissance_%"] = np.where(
        perf_magasin["CA_N_1"] != 0,
        (perf_magasin["CA_N"] - perf_magasin["CA_N_1"]) / perf_magasin["CA_N_1"] * 100,
        np.nan
    )

    perf_magasin["realisation_budget_%"] = np.where(
        perf_magasin["Budget"] != 0,
        perf_magasin["CA_N"] / perf_magasin["Budget"] * 100,
        np.nan
    )

    q25 = perf_magasin["CA_N"].quantile(0.25)
    q75 = perf_magasin["CA_N"].quantile(0.75)

    def segment_store(ca):
        if ca >= q75:
            return "Top performer"
        elif ca <= q25:
            return "Low performer"
        else:
            return "Mid performer"

    perf_magasin["segment"] = perf_magasin["CA_N"].apply(segment_store)

    subtab1, subtab2, subtab3 = st.tabs(["Top 10", "Flop 10", "Segmentation"])

    with subtab1:
        st.dataframe(
            perf_magasin.sort_values("CA_N", ascending=False).head(10),
            use_container_width=True
        )

    with subtab2:
        st.dataframe(
            perf_magasin.sort_values("CA_N", ascending=True).head(10),
            use_container_width=True
        )

    with subtab3:
        segment_summary = perf_magasin.groupby("segment").agg(
            nb_magasins=("Code_magasin", "count"),
            CA_N=("CA_N", "sum"),
            croissance_moyenne=("croissance_%", "mean"),
            realisation_budget_moyenne=("realisation_budget_%", "mean")
        ).reset_index()

        st.dataframe(segment_summary, use_container_width=True)

        fig, ax = plt.subplots(figsize=(8, 4))
        segment_summary.set_index("segment")["nb_magasins"].plot(kind="bar", ax=ax)
        ax.set_title("Nombre de magasins par segment")
        ax.set_xlabel("")
        ax.set_ylabel("Nombre de magasins")
        st.pyplot(fig)


# =========================
# TAB 5 ALERTES
# =========================

with tab5:
    st.subheader("Alertes business")

    perf_magasin_alert = filtered.groupby(
        ["Code_magasin", "Nom_magasin", "type_magasin", "Region", "Enseigne"]
    ).agg(
        CA_N=("CA_N", "sum"),
        CA_N_1=("CA_N_1", "sum"),
        Budget=("Budget", "sum")
    ).reset_index()

    perf_magasin_alert["croissance_%"] = np.where(
        perf_magasin_alert["CA_N_1"] != 0,
        (perf_magasin_alert["CA_N"] - perf_magasin_alert["CA_N_1"]) / perf_magasin_alert["CA_N_1"] * 100,
        np.nan
    )

    perf_magasin_alert["realisation_budget_%"] = np.where(
        perf_magasin_alert["Budget"] != 0,
        perf_magasin_alert["CA_N"] / perf_magasin_alert["Budget"] * 100,
        np.nan
    )

    alertes = perf_magasin_alert[
        (perf_magasin_alert["croissance_%"] < -20) |
        (perf_magasin_alert["realisation_budget_%"] < 80)
    ].sort_values("CA_N", ascending=False)

    st.write("""
    Les alertes identifient les magasins avec :
    - une baisse supérieure à 20 % par rapport à N-1 ;
    - ou une réalisation budget inférieure à 80 %.
    """)

    st.dataframe(alertes, use_container_width=True)


# =========================
# FOOTER
# =========================

st.divider()

st.markdown("""
### Conclusion business

Cette application permet de consolider deux sources hétérogènes — succursales et franchises — afin de piloter la performance commerciale.  
Elle aide à suivre le CA, comparer la performance à N-1, mesurer l’atteinte du budget, identifier les régions fortes et détecter les magasins nécessitant une action prioritaire.
""")