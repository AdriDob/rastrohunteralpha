import { useEffect, useState } from 'react';
import { getFavorites, addFavorite, removeFavorite } from '../lib/api';

interface Props {
  itemType: string;
  itemId: number;
  label?: string;
}

export default function FavoriteButton({ itemType, itemId, label }: Props) {
  const [favId, setFavId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getFavorites(itemType).then(r => {
      const match = r.items.find(f => f.item_id === itemId);
      if (match) setFavId(match.id);
    }).catch(() => {});
  }, [itemType, itemId]);

  const toggle = async () => {
    setLoading(true);
    try {
      if (favId !== null) {
        await removeFavorite(favId);
        setFavId(null);
      } else {
        const r = await addFavorite(itemType, itemId, label);
        if (r.status === 'created') setFavId(r.id);
      }
    } catch {}
    setLoading(false);
  };

  return (
    <button
      onClick={toggle}
      disabled={loading}
      title={favId ? 'Remove from favorites' : 'Add to favorites'}
      style={{
        background: 'none', border: 'none', cursor: loading ? 'wait' : 'pointer',
        fontSize: 18, padding: '2px 6px', opacity: loading ? 0.5 : 1,
        color: favId !== null ? '#f59e0b' : '#4a4f63',
        transition: 'color 0.15s',
      }}
    >
      {favId !== null ? '★' : '☆'}
    </button>
  );
}
