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
  h1 {
    margin: 0 0 1.4rem;
    font-size: clamp(1.7rem, 3vw, 2.35rem);
    letter-spacing: -0.04em;
    line-height: 1.1;
  }

  h2 {
    margin: 0 0 0.9rem;
    font-size: 1rem;
    letter-spacing: -0.01em;
  }

  .hint {
    color: var(--muted);
    font-size: 0.84rem;
    margin: 0.4rem 0 1.2rem;
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

  .layout {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 18px;
    align-items: start;
  }

  section,
  aside {
    margin: 0;
    padding: 16px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--panel);
  }

  ul,
  ol {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 8px;
    margin: 0;
  }

  li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--panel-2);
  }

  li strong {
    font-size: 0.9rem;
  }

  .actions {
    display: flex;
    gap: 6px;
    align-items: center;
    flex: none;
  }

  .actions input {
    width: 7rem;
    text-align: center;
  }

  button {
    min-height: 34px;
    padding: 7px 11px;
    border: 1px solid var(--border);
    border-radius: 9px;
    background: var(--panel);
    color: var(--text);
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition:
      border-color 0.18s ease,
      background 0.18s ease,
      color 0.18s ease;
  }

  button:hover:not(:disabled) {
    border-color: rgba(103, 232, 249, 0.4);
    color: var(--accent);
  }

  button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  small {
    display: block;
    margin-top: 2px;
    color: var(--muted);
    font-size: 0.76rem;
  }

  a {
    color: var(--accent);
    text-underline-offset: 3px;
  }

  @media (max-width: 900px) {
    .layout {
      grid-template-columns: 1fr;
    }

    .filters {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 640px) {
    .filters,
    section,
    aside {
      padding: 12px;
    }

    li {
      flex-wrap: wrap;
    }

    .actions {
      width: 100%;
      justify-content: flex-end;
    }

    .actions input {
      width: 7rem;
      min-height: 44px;
      font-size: 16px;
    }

    button {
      min-height: 44px;
    }
  }
</style>
