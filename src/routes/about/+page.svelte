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
        padding: 40px;
        max-width: 800px;
        margin: 0 auto;
        color: #e0e0e0;
        font-family: "Inter", sans-serif;
    }

    .content {
        background: #25262b;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        border: 1px solid #2c2e33;
    }

    h1 {
        font-size: 2.5rem;
        margin-bottom: 24px;
        background: linear-gradient(135deg, #4dabf7 0%, #339af0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    h2 {
        font-size: 1.5rem;
        margin-top: 32px;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 1px solid #373a40;
    }

    h3 {
        font-size: 1.1rem;
        color: #fff;
        margin-bottom: 8px;
    }

    p {
        color: #c1c2c5;
        line-height: 1.6;
        margin-bottom: 16px;
    }

    a {
        color: #4dabf7;
        text-decoration: none;
        transition: color 0.2s;
    }

    a:hover {
        color: #74c0fc;
        text-decoration: underline;
    }

    .credit-item {
        margin-bottom: 24px;
        padding: 16px;
        background: #2c2e33;
        border-radius: 8px;
    }

    .libs-list {
        list-style-type: none;
        padding: 0;
        color: #c1c2c5;
    }

    .libs-list li {
        margin-bottom: 6px;
    }

    .btn-back {
        display: inline-block;
        margin-top: 32px;
        padding: 10px 20px;
        background: #373a40;
        color: white;
        border-radius: 6px;
        text-decoration: none;
        font-weight: 500;
        transition: background 0.2s;
    }

    .btn-back:hover {
        background: #4dabf7;
        color: white;
        text-decoration: none;
    }
</style>
