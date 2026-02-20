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
  h1 { margin-bottom: 1rem; }
  .filters { display: flex; gap: 1rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
  .hint { color: #666; margin: 0.25rem 0 1rem; }
  ol { display: grid; gap: 0.5rem; }
  li { border: 1px solid #ddd; border-radius: 8px; padding: 0.75rem; }
  small { color: #666; }
</style>
