import os
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
import seaborn as sns
import matplotlib.pyplot as plt
import os
import json

def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    config_path = os.path.join(script_dir,'..','..', 'config.json')

    with open(config_path, 'r') as config_fh:
        config = json.load(config_fh)
    return config


def main(config):
    # 1. Load your data
    incoming_data_path = config['paths']['incoming_data']
    processed_data_path = config['paths']['data']
    df = pd.read_csv(os.path.join(
        processed_data_path,
        "Validation sets",
        "ports.csv"
    ))  

    features = ["Maritime ports database", "CIA"]
    #df = df.dropna(subset=['CIA'])

    # 2. Normalize the data
    scaler = StandardScaler()
    df['A_scaled'] = scaler.fit_transform(df[['Maritime ports database']])
    df['B_scaled'] = scaler.fit_transform(df[['CIA']])

    # 3. Cluster separately on each dataset
    k = 3  # Choose number of clusters

    kmeans_a = KMeans(n_clusters=k, random_state=42)
    df['Cluster_A'] = kmeans_a.fit_predict(df[['A_scaled']])

    kmeans_b = KMeans(n_clusters=k, random_state=42)
    df['Cluster_B'] = kmeans_b.fit_predict(df[['B_scaled']])

    # 4. Compare cluster agreement
    ari = adjusted_rand_score(df['Cluster_A'], df['Cluster_B'])
    print(f"\n✅ Adjusted Rand Index (ARI): {ari:.3f}")

    # 5. Visualize overlap using heatmap
    cross_tab = pd.crosstab(df['Cluster_A'], df['Cluster_B'])

    plt.figure(figsize=(8, 6))
    sns.heatmap(cross_tab, annot=True, fmt='d', cmap='Blues')
    plt.title('Overlap Between Cluster A (Port DB) and Cluster B (CIA)')
    plt.xlabel('Cluster B (CIA)')
    plt.ylabel('Cluster A (Port DB)')
    plt.tight_layout()
    plt.show()

    # 6. Export cluster assignments
    df.to_csv(os.path.join(
        processed_data_path,
        "Validation sets",
        "port_cluster_comparison_k3.csv"
    ), index=False)

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
