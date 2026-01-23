<script lang="ts">
    import { onMount } from "svelte";
    import { fetchHistory } from "$lib/api";

    export let files: string[] = []; // Current session generated
    let history: any[] = [];

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
                    <span class="filename" title={file}
                        >{file.split("/").pop()}</span
                    >
                    <div class="actions">
                        {#if file.endsWith(".zip")}
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
        <div class="section-title">Historique global</div>
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
        margin-top: 24px;
        padding-top: 16px;
        border-top: 1px solid #2c2e33;
    }

    .empty-state {
        color: #5c5f66;
        font-size: 0.85rem;
        font-style: italic;
        text-align: center;
        padding: 12px;
    }

    h4 {
        margin: 0 0 12px 0;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #909296;
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
        background: #2c2e33;
    }

    .posters-scroll::-webkit-scrollbar-thumb {
        background: #5c5f66;
        border-radius: 3px;
    }

    .mini-card {
        background: #373a40;
        border: 1px solid #484b51;
        border-radius: 6px;
        padding: 10px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .filename {
        font-size: 0.8rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 200px;
    }

    .actions a {
        text-decoration: none;
        margin-left: 8px;
        font-size: 1.1rem;
        color: #909296;
        transition: color 0.2s;
    }

    .actions a:hover {
        color: white;
    }

    .zip-btn {
        background: #4dabf7;
        color: white !important;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.75rem !important;
        font-weight: 600;
    }
    .zip-btn:hover {
        background: #339af0;
    }
</style>
