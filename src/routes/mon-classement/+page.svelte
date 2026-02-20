<script lang="ts">
  import { onMount } from 'svelte';
  import { readRankingFromStorage, type RankingItem } from '$lib/ranking';

  let ranking: RankingItem[] = [];
  let selectedCategory = 'Toutes';
  let selectedOrigin = 'Toutes';

  $: categories = ['Toutes', ...new Set(ranking.map((item) => item.category))];
  $: origins = ['Toutes', ...new Set(ranking.map((item) => item.origin))];

  $: filteredRanking = ranking.filter((item) => {
    const categoryMatch = selectedCategory === 'Toutes' || item.category === selectedCategory;
    const originMatch = selectedOrigin === 'Toutes' || item.origin === selectedOrigin;
    return categoryMatch && originMatch;
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

  <ol>
    {#each filteredRanking as item}
      <li>
        <strong>{item.name}</strong>
        <small>{item.category} · {item.origin}</small>
      </li>
    {/each}
  </ol>
{/if}

<style>
  h1 { margin-bottom: 1rem; }
  .filters { display: flex; gap: 1rem; margin-bottom: 1rem; }
  ol { display: grid; gap: 0.5rem; }
  li { border: 1px solid #ddd; border-radius: 8px; padding: 0.75rem; }
  small { color: #666; }
</style>
