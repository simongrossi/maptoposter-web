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
  let searchTerm = '';
  let requestedPositionByItemId: Record<string, number | undefined> = {};

  const categories = ['Toutes', ...new Set(availableRankingItems.map((item) => item.category))];
  const origins = ['Toutes', ...new Set(availableRankingItems.map((item) => item.origin))];

  $: normalizedSearchTerm = searchTerm.trim().toLowerCase();
  $: filteredItems = availableRankingItems.filter((item) => {
    const categoryMatch = selectedCategory === 'Toutes' || item.category === selectedCategory;
    const originMatch = selectedOrigin === 'Toutes' || item.origin === selectedOrigin;
    const searchMatch = !normalizedSearchTerm || item.name.toLowerCase().includes(normalizedSearchTerm);
    return categoryMatch && originMatch && searchMatch;
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

  function removeItem(itemId: string) {
    ranking = ranking.filter((item) => item.id !== itemId);
    writeRankingToStorage(window.localStorage, ranking);
  }

  function moveItem(currentIndex: number, offset: -1 | 1) {
    const targetIndex = currentIndex + offset;
    if (targetIndex < 0 || targetIndex >= ranking.length) return;

    const next = [...ranking];
    const [item] = next.splice(currentIndex, 1);
    next.splice(targetIndex, 0, item);
    ranking = next;
    writeRankingToStorage(window.localStorage, ranking);
  }
</script>

<h1>Builder de classement</h1>

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

<p class="hint">{filteredItems.length} résultat(s) sur {availableRankingItems.length} item(s).</p>

<div class="layout">
  <section>
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
              on:keydown={(event) => {
                if (event.key === 'Enter') addItem(item);
              }}
            />
            <button type="button" on:click={() => addItem(item)}>+ Ajouter</button>
          </div>
        </li>
      {/each}
    </ul>
  </section>

  <aside>
    <h2>Mon classement ({ranking.length})</h2>
    {#if ranking.length === 0}
      <p>Aucun item ajouté.</p>
    {:else}
      <ol>
        {#each ranking as item, index}
          <li>
            <div>
              <strong>#{index + 1} {item.name}</strong>
              <small>{item.category} · {item.origin}</small>
            </div>
            <div class="actions">
              <button type="button" on:click={() => moveItem(index, -1)} disabled={index === 0}>↑</button>
              <button type="button" on:click={() => moveItem(index, 1)} disabled={index === ranking.length - 1}>↓</button>
              <button type="button" on:click={() => removeItem(item.id)}>Retirer</button>
            </div>
          </li>
        {/each}
      </ol>
    {/if}
  </aside>
</div>

<p>
  Retrouvez la liste filtrable dans <a href="/mon-classement">Mon classement</a>.
</p>

<style>
  h1 { margin-bottom: 1rem; }
  h2 { margin: 0 0 0.75rem; }
  .hint { color: #666; margin: 0.25rem 0 1rem; }
  .filters { display: flex; gap: 1rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
  .layout { display: grid; grid-template-columns: 1.2fr 1fr; gap: 1rem; align-items: start; }
  ul, ol { list-style: none; padding: 0; display: grid; gap: 0.5rem; margin: 0; }
  li { display: flex; justify-content: space-between; align-items: center; border: 1px solid #ddd; border-radius: 8px; padding: 0.75rem; gap: 0.75rem; }
  .actions { display: flex; gap: 0.4rem; align-items: center; }
  input { width: 7rem; }
  small { display: block; color: #666; }
  aside { border: 1px solid #ececec; border-radius: 8px; padding: 0.75rem; background: #fafafa; }

  @media (max-width: 900px) {
    .layout { grid-template-columns: 1fr; }
  }
</style>
