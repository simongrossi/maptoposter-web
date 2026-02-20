export type RankingItem = {
  id: string;
  name: string;
  category: string;
  origin: string;
};

export const availableRankingItems: RankingItem[] = [
  { id: '1', name: 'Asterion', category: 'Attaque', origin: 'Europe' },
  { id: '2', name: 'Nyx', category: 'Soutien', origin: 'Asie' },
  { id: '3', name: 'Helios', category: 'Attaque', origin: 'Amérique' },
  { id: '4', name: 'Mira', category: 'Défense', origin: 'Europe' },
  { id: '5', name: 'Vortex', category: 'Soutien', origin: 'Amérique' },
  { id: '6', name: 'Orion', category: 'Défense', origin: 'Asie' }
];

export const rankingStorageKey = 'ranking-builder-items';

export function insertAtPosition(items: RankingItem[], item: RankingItem, requestedPosition?: number) {
  const next = items.filter((entry) => entry.id !== item.id);

  if (!requestedPosition || Number.isNaN(requestedPosition)) {
    next.push(item);
    return next;
  }

  const clampedIndex = Math.min(Math.max(0, requestedPosition - 1), next.length);
  next.splice(clampedIndex, 0, item);
  return next;
}

export function readRankingFromStorage(storage: Storage | undefined): RankingItem[] {
  if (!storage) return [];

  const raw = storage.getItem(rankingStorageKey);
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw) as RankingItem[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function writeRankingToStorage(storage: Storage | undefined, items: RankingItem[]) {
  if (!storage) return;
  storage.setItem(rankingStorageKey, JSON.stringify(items));
}
