<script>
    import { fade } from "svelte/transition";
</script>

<div class="about-container" in:fade>
    <div class="content">
        <h1>À propos</h1>

        <p class="intro">
            MapPoster est un outil open-source permettant de générer des
            affiches de cartes artistiques de n'importe quelle ville.
        </p>

        <section>
            <h2>Crédits & Licences</h2>

            <div class="credit-item">
                <h3>Moteur de génération</h3>
                <p>
                    Basé sur le projet original <a
                        href="https://github.com/originalankur/maptoposter"
                        target="_blank">maptoposter</a
                    >
                    par Ankur.
                    <br />
                    Adapté et amélioré pour le web avec des nouvelles fonctionnalités
                    de couches personnalisées.
                </p>
            </div>

            <div class="credit-item">
                <h3>Données Cartographiques</h3>
                <p>
                    Les données sont issues de <a
                        href="https://www.openstreetmap.org/copyright"
                        target="_blank">OpenStreetMap</a
                    >
                    (© OpenStreetMap contributors).
                    <br />
                    Ces données sont disponibles sous la licence ODbL.
                </p>
            </div>

            <div class="credit-item">
                <h3>Librairies Python</h3>
                <ul class="libs-list">
                    <li>
                        <strong
                            ><a
                                href="https://github.com/gboeing/osmnx"
                                target="_blank">OSMnx</a
                            ></strong
                        >
                        & <strong>NetworkX</strong> pour l'analyse de réseaux
                    </li>
                    <li><strong>Matplotlib</strong> pour le rendu graphique</li>
                </ul>
            </div>
        </section>

        <a href="/" class="btn-back">← Retour au générateur</a>
    </div>
</div>

<style>
    .about-container {
        padding: 0;
        max-width: 820px;
        margin: 0 auto;
        color: var(--text);
    }

    .content {
        background: var(--panel);
        padding: 40px;
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        border: 1px solid var(--border);
    }

    h1 {
        font-size: clamp(2rem, 4vw, 2.75rem);
        letter-spacing: -0.04em;
        margin-bottom: 24px;
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 100%);
        background-clip: text;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    h2 {
        font-size: 1.35rem;
        letter-spacing: -0.02em;
        margin-top: 32px;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border);
    }

    h3 {
        font-size: 1.02rem;
        color: var(--text);
        margin-bottom: 8px;
    }

    p {
        color: var(--muted);
        line-height: 1.65;
        margin-bottom: 16px;
    }

    a {
        color: var(--accent);
        text-decoration: none;
        transition: color 0.2s;
    }

    a:hover {
        color: var(--accent-2);
        text-decoration: underline;
        text-underline-offset: 3px;
    }

    .credit-item {
        margin-bottom: 16px;
        padding: 16px;
        background: var(--panel-2);
        border: 1px solid var(--border);
        border-radius: 12px;
    }

    .libs-list {
        list-style-type: none;
        padding: 0;
        color: var(--muted);
    }

    .libs-list li {
        margin-bottom: 6px;
    }

    .btn-back {
        display: inline-block;
        margin-top: 28px;
        padding: 10px 18px;
        background: var(--panel-2);
        border: 1px solid var(--border);
        color: var(--text);
        border-radius: 10px;
        text-decoration: none;
        font-weight: 600;
        transition:
            border-color 0.18s ease,
            color 0.18s ease;
    }

    .btn-back:hover {
        border-color: rgba(103, 232, 249, 0.4);
        color: var(--accent);
        text-decoration: none;
    }

    @media (max-width: 640px) {
        .content {
            padding: 24px;
        }
    }
</style>
