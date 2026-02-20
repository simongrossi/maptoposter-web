<script lang="ts">
  import { onMount } from 'svelte';
  import {
    availableRankingItems,
    insertAtPosition,
    readRankingFromStorage,
    writeRankingToStorage,
    type RankingItem
  } from '$lib/ranking';

  let ranking: RankingItem[] = [];
  let selectedCategory = 'Toutes';
  let selectedOrigin = 'Toutes';
  let requestedPositionByItemId: Record<string, number | undefined> = {};

  const categories = ['Toutes', ...new Set(availableRankingItems.map((item) => item.category))];
  const origins = ['Toutes', ...new Set(availableRankingItems.map((item) => item.origin))];

  $: filteredItems = availableRankingItems.filter((item) => {
    const categoryMatch = selectedCategory === 'Toutes' || item.category === selectedCategory;
    const originMatch = selectedOrigin === 'Toutes' || item.origin === selectedOrigin;
    return categoryMatch && originMatch;
  });

  onMount(() => {
    ranking = readRankingFromStorage(window.localStorage);
  });

  function addItem(item: RankingItem) {
    const requestedPosition = requestedPositionByItemId[item.id];
    ranking = insertAtPosition(ranking, item, requestedPosition);
    writeRankingToStorage(window.localStorage, ranking);
    requestedPositionByItemId = { ...requestedPositionByItemId, [item.id]: undefined };
  }
</script>

<h1>Builder de classement</h1>

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

<ul>
  {#each filteredItems as item}
    <li>
      <div>
        <strong>{item.name}</strong>
        <small>{item.category} · {item.origin}</small>
      </div>

      <div class="actions">
        <input
          type="number"
          min="1"
          placeholder="Position"
          bind:value={requestedPositionByItemId[item.id]}
          aria-label={`Position de ${item.name}`}
        />
        <button type="button" on:click={() => addItem(item)}>+ Ajouter</button>
      </div>
    </li>
  {/each}
</ul>

<p>
  Classement actuel: {ranking.length} item(s). Retrouvez la liste ordonnée dans
  <a href="/mon-classement">Mon classement</a>.
</p>

<style>
  h1 { margin-bottom: 1rem; }
  .filters { display: flex; gap: 1rem; margin-bottom: 1rem; }
  ul { list-style: none; padding: 0; display: grid; gap: 0.5rem; }
  li { display: flex; justify-content: space-between; align-items: center; border: 1px solid #ddd; border-radius: 8px; padding: 0.75rem; }
  .actions { display: flex; gap: 0.5rem; align-items: center; }
  input { width: 5.5rem; }
  small { display: block; color: #666; }
</style>
