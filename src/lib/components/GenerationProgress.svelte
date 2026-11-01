<script lang="ts">
    import { createEventDispatcher } from "svelte";

    // Props
    export let progressPercent = 0;
    export let progressText = "";
    export let etaText = "";

    const dispatch = createEventDispatcher();

    function cancel() {
        dispatch("cancel");
    }
</script>

<div
    class="progress-container"
    role="status"
    aria-live="polite"
    aria-label="Génération en cours"
>
    <div class="progress-info">
        <span class="progress-text">{progressText}</span>
        <span class="progress-percent">{Math.round(progressPercent)}%</span>
    </div>
    {#if etaText}
        <div class="progress-eta">{etaText}</div>
    {/if}
    <div
        class="progress-bar-bg"
        role="progressbar"
        aria-valuemin="0"
        aria-valuemax="100"
        aria-valuenow={Math.round(progressPercent)}
    >
        <div class="progress-bar-fill" style="width: {progressPercent}%"></div>
    </div>
    <button type="button" class="btn-cancel" on:click={cancel}>
        Arrêter
    </button>
</div>

<style>
    .progress-container {
        width: 100%;
        margin-top: 10px;
        padding: 14px;
        border: 1px solid var(--border);
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.02);
    }

    .progress-info {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        font-size: 0.84rem;
        color: var(--text);
        margin-bottom: 6px;
    }

    .progress-percent {
        color: var(--accent);
        font-weight: 700;
        font-variant-numeric: tabular-nums;
    }

    .progress-eta {
        font-size: 0.78rem;
        color: var(--muted);
        margin-bottom: 8px;
    }

    .progress-bar-bg {
        width: 100%;
        height: 8px;
        background: var(--border);
        border-radius: 999px;
        overflow: hidden;
        margin-bottom: 12px;
    }

    .progress-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--accent), var(--accent-2));
        border-radius: 999px;
        transition: width 0.3s ease-out;
    }

    .btn-cancel {
        width: 100%;
        padding: 10px;
        background: rgba(251, 113, 133, 0.12);
        color: #fecdd3;
        border: 1px solid rgba(251, 113, 133, 0.28);
        border-radius: 10px;
        font-size: 0.88rem;
        font-weight: 600;
        cursor: pointer;
        transition:
            background 0.18s ease,
            border-color 0.18s ease;
    }

    .btn-cancel:hover {
        background: rgba(251, 113, 133, 0.2);
        border-color: rgba(251, 113, 133, 0.45);
    }
</style>
