<script lang="ts">
  import { onMount } from 'svelte';
  import { readRankingFromStorage, type RankingItem } from '$lib/ranking';

  let ranking: RankingItem[] = [];
  let selectedCategory = 'Toutes';
  let selectedOrigin = 'Toutes';
  let searchTerm = '';

  $: categories = ['Toutes', ...new Set(ranking.map((item) => item.category))];
  $: origins = ['Toutes', ...new Set(ranking.map((item) => item.origin))];
  $: normalizedSearchTerm = searchTerm.trim().toLowerCase();

  $: filteredRanking = ranking.filter((item) => {
    const categoryMatch = selectedCategory === 'Toutes' || item.category === selectedCategory;
    const originMatch = selectedOrigin === 'Toutes' || item.origin === selectedOrigin;
    const searchMatch = !normalizedSearchTerm || item.name.toLowerCase().includes(normalizedSearchTerm);
    return categoryMatch && originMatch && searchMatch;
  });

  onMount(() => {
    ranking = readRankingFromStorage(window.localStorage);
  });
</script>

<h1>Mon classement</h1>

{#if ranking.length === 0}
  <p>Aucun item pour le moment. Ajoutez-en depuis le <a href="/builder">builder</a>.</p>
{:else}
  <div class="filters">
    <label>
      Recherche
      <input bind:value={searchTerm} placeholder="Nom d'item" />
    </label>

    <label>
      Catégorie
      <select bind:value={selectedCategory}>
        {#each categories as category}
          <option value={category}>{category}</option>
        {/each}
      </select>
    </label>

    <label>
      Origine
      <select bind:value={selectedOrigin}>
        {#each origins as origin}
          <option value={origin}>{origin}</option>
        {/each}
      </select>
    </label>
  </div>

  <p class="hint">{filteredRanking.length} résultat(s) sur {ranking.length} item(s).</p>

  <ol>
    {#each filteredRanking as item, index}
      <li>
        <strong>#{index + 1} {item.name}</strong>
        <small>{item.category} · {item.origin}</small>
      </li>
    {/each}
  </ol>
{/if}

<style>
  h1 {
    margin: 0 0 1.4rem;
    font-size: clamp(1.7rem, 3vw, 2.35rem);
    letter-spacing: -0.04em;
    line-height: 1.1;
  }

  .filters {
    display: grid;
    grid-template-columns: 1.6fr 1fr 1fr;
    gap: 12px;
    margin-bottom: 0.5rem;
    padding: 16px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--panel);
  }

  .filters label {
    display: flex;
    flex-direction: column;
    gap: 7px;
    color: var(--muted);
    font-size: 0.74rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .hint {
    color: var(--muted);
    font-size: 0.84rem;
    margin: 0.4rem 0 1.2rem;
  }

  input,
  select {
    width: 100%;
    min-height: 40px;
    padding: 9px 11px;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--panel-2);
    color: var(--text);
    transition:
      border-color 0.18s ease,
      box-shadow 0.18s ease;
  }

  input:focus,
  select:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(103, 232, 249, 0.12);
  }

  ol {
    display: grid;
    gap: 8px;
    list-style: none;
    padding: 0;
    margin: 0;
  }

  li {
    padding: 14px 16px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--panel);
  }

  li strong {
    font-size: 0.94rem;
  }

  small {
    display: block;
    margin-top: 3px;
    color: var(--muted);
    font-size: 0.78rem;
  }

  a {
    color: var(--accent);
    text-underline-offset: 3px;
  }

  @media (max-width: 900px) {
    .filters {
      grid-template-columns: 1fr;
    }
  }
</style>
