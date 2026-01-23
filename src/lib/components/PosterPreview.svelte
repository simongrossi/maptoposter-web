<script lang="ts">
    export let files: string[] = [];
</script>

{#if files.length > 0}
    <div class="results-list">
        <h4>Affiches récentes</h4>
        <div class="posters-scroll">
            {#each files as file}
                <div class="mini-card">
                    <span class="filename" title={file}
                        >{file.split("/").pop()}</span
                    >
                    <div class="actions">
                        <a href={file} target="_blank" title="Voir">👁️</a>
                        <a href={file} download title="Télécharger">⬇️</a>
                    </div>
                </div>
            {/each}
        </div>
    </div>
{/if}

<style>
    .results-list {
        margin-top: 24px;
        padding: 0 24px;
        flex: 1; /* Take remaining space */
        min-height: 0; /* Enable scrolling inside flex item */
        display: flex;
        flex-direction: column;
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
</style>
