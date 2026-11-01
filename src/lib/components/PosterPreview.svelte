<script lang="ts">
    import { onMount } from "svelte";
    import { fetchHistory } from "$lib/api";

    export let files: string[] = []; // Current session generated
    let history: any[] = [];

    // Les URLs signees contiennent ?expires=...&signature=... : le nom de
    // fichier et le type doivent etre lus sur le chemin seul.
    function fileName(file: string): string {
        return file.split("?")[0].split("/").pop() || "";
    }

    function isZip(file: string): boolean {
        return fileName(file).toLowerCase().endsWith(".zip");
    }

    onMount(async () => {
        history = await fetchHistory();
    });
</script>

<div class="results-container">
    <h4>Affiches récemments générées</h4>

    <!-- Current Session -->
    {#if files.length > 0}
        <div class="section-title">Cette session</div>
        <div class="posters-scroll">
            {#each files as file}
                <div class="mini-card new">
                    <span class="filename" title={fileName(file)}
                        >{fileName(file)}</span
                    >
                    <div class="actions">
                        {#if isZip(file)}
                            <a
                                href={file}
                                class="zip-btn"
                                download
                                title="Télécharger le pack ZIP">📦 ZIP</a
                            >
                        {:else}
                            <a href={file} target="_blank" title="Voir">👁️</a>
                            <a href={file} download title="Télécharger">⬇️</a>
                        {/if}
                    </div>
                </div>
            {/each}
        </div>
    {/if}

    <!-- History -->
    {#if history.length > 0}
        <div class="section-title">Historique de session</div>
        <div class="posters-scroll history-list">
            {#each history as item}
                <div class="mini-card">
                    <div class="details">
                        <span class="city">{item.city}</span>
                        <span class="date"
                            >{new Date(item.date).toLocaleDateString()}</span
                        >
                    </div>
                    <div class="actions">
                        <a href={item.url} target="_blank" title="Voir">👁️</a>
                        <button
                            class="btn-copy"
                            title="Copier le lien"
                            on:click={() =>
                                navigator.clipboard.writeText(item.url)}
                            >📋</button
                        >
                    </div>
                </div>
            {/each}
        </div>
    {:else if files.length === 0}
        <div class="empty-state">Aucune affiche pour le moment.</div>
    {/if}
</div>

<style>
    .results-container {
        margin-top: 22px;
        padding-top: 18px;
        border-top: 1px solid var(--border);
    }

    .empty-state {
        color: var(--muted);
        font-size: 0.84rem;
        font-style: italic;
        text-align: center;
        padding: 12px;
    }

    h4 {
        margin: 0 0 12px 0;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--muted);
    }

    .section-title {
        margin: 14px 0 8px;
        font-size: 0.74rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--muted);
    }

    .posters-scroll {
        overflow-y: auto;
        padding-right: 8px; /* Space for scrollbar */
        flex: 1;
    }

    /* Scrollbar styling */
    .posters-scroll::-webkit-scrollbar {
        width: 6px;
    }

    .posters-scroll::-webkit-scrollbar-track {
        background: transparent;
    }

    .posters-scroll::-webkit-scrollbar-thumb {
        background: var(--border-strong);
        border-radius: 999px;
    }

    .mini-card {
        background: var(--panel-2);
        border: 1px solid var(--border);
        border-radius: 11px;
        padding: 10px 12px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        transition:
            border-color 0.18s ease,
            background 0.18s ease;
    }

    .mini-card:hover {
        background: var(--panel);
        border-color: var(--border-strong);
    }

    .filename {
        font-size: 0.8rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 200px;
    }

    .actions {
        display: flex;
        align-items: center;
        gap: 6px;
        flex: none;
    }

    .actions a {
        text-decoration: none;
        font-size: 1.05rem;
        color: var(--muted);
        transition: color 0.2s;
    }

    .actions a:hover {
        color: var(--text);
    }

    .zip-btn {
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        color: #06121a !important;
        padding: 5px 9px;
        border-radius: 999px;
        font-size: 0.72rem !important;
        font-weight: 700;
    }

    .zip-btn:hover {
        filter: brightness(1.06);
    }

    .date,
    .city {
        color: var(--muted);
        font-size: 0.78rem;
    }

    .city {
        color: var(--text);
        font-weight: 500;
    }
</style>
