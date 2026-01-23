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

<div class="progress-container">
    <div class="progress-info">
        <span class="progress-text">{progressText}</span>
        <span class="progress-percent">{Math.round(progressPercent)}%</span>
    </div>
    {#if etaText}
        <div class="progress-eta">{etaText}</div>
    {/if}
    <div class="progress-bar-bg">
        <div class="progress-bar-fill" style="width: {progressPercent}%"></div>
    </div>
    <button type="button" class="btn-cancel" on:click={cancel}>
        ⛔ Arrêter
    </button>
</div>

<style>
    .progress-container {
        width: 100%;
        margin-top: 10px;
    }

    .progress-info {
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        color: #c1c2c5;
        margin-bottom: 6px;
    }
    .progress-eta {
        font-size: 0.8rem;
        color: #909296;
        margin-bottom: 8px;
    }

    .progress-bar-bg {
        width: 100%;
        height: 8px;
        background: #373a40;
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 12px;
    }

    .progress-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #4dabf7, #3bc9db);
        transition: width 0.3s ease-out;
    }

    .btn-cancel {
        width: 100%;
        padding: 10px;
        background: #fa5252;
        color: white;
        border: none;
        border-radius: 6px;
        font-size: 0.9rem;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.2s;
    }

    .btn-cancel:hover {
        background: #e03131;
    }
</style>
