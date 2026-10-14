import io
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Tableau de bord - Transparence des Données", layout="wide"
)

st.title("📊 Tableau de Bord Intelligent : Rapports de Transparence")
st.markdown(
    "Ce tableau de bord analyse dynamiquement l'ensemble des fichiers CSV"
    " présents dans votre dépôt GitHub."
)

# --- CONFIGURATION GITHUB ---
# ⚠️ Remplacez ces valeurs par vos propres identifiants GitHub
GITHUB_USER = "Maxim903"
GITHUB_REPO = "Rapport_transparence"
BRANCH = "main"  # ou 'master'
DOSSIER_DANS_REPO = (
    ""  # Laissez vide si les CSV sont à la racine, ou "dossier" s'ils le sont
)


@st.cache_data
def load_and_normalize_csvs():
  """Interroge l'API GitHub, télécharge les CSV, normalise leurs colonnes et les fusionne."""
  api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{DOSSIER_DANS_REPO}"

  headers = {"Accept": "application/vnd.github.v3+json"}
  response = requests.get(api_url, headers=headers)

  if response.status_code != 200:
    st.error(
        f"Erreur lors de la communication avec l'API GitHub (Code"
        f" {response.status_code}). Vérifiez le nom du dépôt et de l'utilisateur."
    )
    return pd.DataFrame()

  files_data = response.json()
  df_list = []

  for file in files_data:
    if file["name"].endswith(".csv"):
      raw_url = file["download_url"]
      try:
        df = pd.read_csv(raw_url)

        # --- NORMALISATION AUTOMATIQUE DU SCHÉMA ---
        # Nettoie les noms de colonnes : supprime les espaces, met en minuscules,
        # et remplace les accents (ex: "Année" ou "ANNEE " devient "annee")
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace("é", "e")
            .str.replace("è", "e")
            .str.replace("ê", "e")
            .str.replace("à", "a")
        )

        # Ajout d'une colonne de traçabilité pour identifier le fichier d'origine
        df["source_rapport"] = file["name"]
        df_list.append(df)
      except Exception as e:
        st.warning(f"Impossible de lire le fichier {file['name']} : {e}")

  if df_list:
    # Fusion souple : Pandas aligne les colonnes communes et gère les manquantes
    return pd.concat(df_list, ignore_index=True)
  else:
    return pd.DataFrame()


# --- CHARGEMENT DES DONNÉES ---
df = load_and_normalize_csvs()

if df.empty:
  st.warning(
      "Aucun fichier CSV trouvé ou le dépôt est inaccessible. Veuillez"
      " vérifier vos configurations GitHub au début du script (`app.py`)."
  )
else:
  st.success(
      f"Succès ! {df['source_rapport'].nunique()} fichiers CSV chargés et"
      f" harmonisés."
  )

  # --- BARRE LATÉRALE : FILTRES DYNAMIQUES ---
  st.sidebar.header("Filtres d'analyse")

  df_filtered = df.copy()

  # Filtre par source de rapport si présent
  sources = st.sidebar.multiselect(
      "Filtrer par rapport",
      options=df["source_rapport"].unique(),
      default=df["source_rapport"].unique(),
  )
  df_filtered = df_filtered[df_filtered["source_rapport"].isin(sources)]

  # Filtre automatique si une colonne 'annee' ou 'year' existe (après normalisation)
  col_annee = next(
      (c for c in df.columns if c in ["annee", "year", "exercice"]), None
  )
  if col_annee:
    annees = st.sidebar.multiselect(
        "Sélectionner les années",
        options=df[col_annee].dropna().unique(),
        default=df[col_annee].dropna().unique(),
    )
    df_filtered = df_filtered[df_filtered[col_annee].isin(annees)]

  # --- SECTION DES KPI (Indicateurs clés) ---
  st.subheader("Indicateurs Clés")
  col1, col2, col3, col4 = st.columns(4)

  col1.metric("Lignes totales", f"{len(df_filtered):,}")
  col2.metric("Rapports analysés", f"{df_filtered['source_rapport'].nunique()}")
  col3.metric("Colonnes unifiées", f"{len(df_filtered.columns)}")

  # Si une colonne numérique de demandes existe (ex: 'demandes', 'nombre', 'volume')
  col_val = next(
      (
          c
          for c in df.columns
          if any(k in c for k in ["demande", "nombre", "volume", "total"])
          and pd.api.types.is_numeric_dtype(df[c])
      ),
      None,
  )
  if col_val:
    total_val = df_filtered[col_val].sum()
    col4.metric(f"Total ({col_val})", f"{total_val:,.0f}")
  else:
    col4.metric("Indicateur", "N/A")

  st.markdown("---")

  # --- VISUALISATION GRAPHIQUE ADAPTATIVE ---
  st.subheader("Visualisation Graphique")

  # Recherche d'une colonne temporelle (date, annee) et d'une colonne numérique
  col_date = next(
      (c for c in df.columns if any(k in c for k in ["date", "annee", "mois"])),
      None,
  )

  if col_date and col_val:
    fig = px.line(
        df_filtered,
        x=col_date,
        y=col_val,
        color="source_rapport",
        markers=True,
        title=f"Évolution de '{col_val}' par rapport au fil du temps",
    )
    st.plotly_chart(fig, use_container_width=True)
  else:
    st.info(
        "💡 Astuce graphique : Pour afficher un graphique temporel"
        " automatiquement, assurez-vous d'avoir des colonnes de type 'date' ou"
        " 'annee' et une colonne numérique."
    )

  # --- TABLEAU DES DONNÉES BRUTES ---
  with st.expander("Afficher le tableau complet des données unifiées"):
    st.dataframe(df_filtered, use_container_width=True)