import click
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler


@click.command()
@click.option("--ports", required=True, type=click.Path(exists=True))
@click.option("--output-clusters", required=True, type=click.Path())
def main(ports, output_clusters):
    """Cluster-compare the maritime port database against CIA port counts"""
    # 1. Load your data
    df = pd.read_csv(ports)

    # 2. Normalize the data
    scaler = StandardScaler()
    df["A_scaled"] = scaler.fit_transform(df[["Maritime ports database"]])
    df["B_scaled"] = scaler.fit_transform(df[["CIA"]])

    # 3. Cluster separately on each dataset
    k = 3  # Choose number of clusters

    kmeans_a = KMeans(n_clusters=k, random_state=42)
    df["Cluster_A"] = kmeans_a.fit_predict(df[["A_scaled"]])

    kmeans_b = KMeans(n_clusters=k, random_state=42)
    df["Cluster_B"] = kmeans_b.fit_predict(df[["B_scaled"]])

    # 4. Compare cluster agreement
    ari = adjusted_rand_score(df["Cluster_A"], df["Cluster_B"])
    print(f"\n✅ Adjusted Rand Index (ARI): {ari:.3f}")

    # 5. Visualize overlap using heatmap
    cross_tab = pd.crosstab(df["Cluster_A"], df["Cluster_B"])

    plt.figure(figsize=(8, 6))
    sns.heatmap(cross_tab, annot=True, fmt="d", cmap="Blues")
    plt.title("Overlap Between Cluster A (Port DB) and Cluster B (CIA)")
    plt.xlabel("Cluster B (CIA)")
    plt.ylabel("Cluster A (Port DB)")
    plt.tight_layout()
    plt.show()

    # 6. Export cluster assignments
    df.to_csv(
        output_clusters,
        index=False,
    )


if __name__ == "__main__":
    main()
