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

# --- CONFIGURATION GITHUB ---
GITHUB_USER = "Maxim903"
GITHUB_REPO = "Rapport_transparence"  # Remplacez par le nom exact de votre dépôt
BRANCH = (  # Généralement 'main' ou 'master'
    "main"
)


@st.cache_data
def load_all_csvs_recursively():
  """Explore tout le dépôt GitHub récursivement pour trouver et fusionner tous les CSV."""
  # On utilise l'API 'git/trees' avec 'recursive=1' pour obtenir toute l'arborescence du dépôt d'un coup
  api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/git/trees/{BRANCH}?recursive=1"

  headers = {"Accept": "application/vnd.github.v3+json"}
  response = requests.get(api_url, headers=headers)

  if response.status_code != 200:
    st.error(
        f"Erreur lors de la communication avec l'API GitHub (Code"
        f" {response.status_code}). Vérifiez le nom du dépôt, de l'utilisateur"
        f" et de la branche."
    )
    return pd.DataFrame()

  tree_data = response.json().get("tree", [])
  df_list = []

  # Parcourir tous les éléments de l'arborescence du dépôt
  for item in tree_data:
    # Vérifier si c'est un fichier et s'il se termine par .csv
    if item["type"] == "blob" and item["path"].endswith(".csv"):
      # Construire l'URL brute (raw) pour télécharger le fichier CSV
      raw_url = (
          f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}/{item['path']}"
      )

      try:
        df = pd.read_csv(raw_url)

        # --- NORMALISATION AUTOMATIQUE DU SCHÉMA ---
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace("é", "e")
            .str.replace("è", "e")
            .str.replace("ê", "e")
            .str.replace("à", "a")
        )

        # Traçabilité : on stocke le chemin complet du fichier (incluant le dossier)
        df["source_rapport"] = item["path"]
        df_list.append(df)
      except Exception as e:
        st.warning(f"Impossible de lire le fichier {item['path']} : {e}")

  if df_list:
    return pd.concat(df_list, ignore_index=True)
  else:
    return pd.DataFrame()


# --- CHARGEMENT DES DONNÉES ---
df = load_all_csvs_recursively()

if df.empty:
  st.warning(
      "Aucun fichier CSV trouvé dans le dépôt. Vérifiez vos configurations."
  )
else:
  st.success(
      f"Succès ! {df['source_rapport'].nunique()} fichiers CSV détectés et"
      f" chargés à travers tout le dépôt."
  )

  # --- LE RESTE DE VOTRE INTERFACE (Filtres, KPIs, Graphiques) ---
  st.sidebar.header("Filtres d'analyse")
  df_filtered = df.copy()

  # Filtre par fichier/dossier d'origine
  sources = st.sidebar.multiselect(
      "Filtrer par fichier source",
      options=df["source_rapport"].unique(),
      default=df["source_rapport"].unique(),
  )
  df_filtered = df_filtered[df_filtered["source_rapport"].isin(sources)]

  # Affichage du tableau de données
  with st.expander("Afficher le tableau complet des données unifiées"):
    st.dataframe(df_filtered, use_container_width=True)