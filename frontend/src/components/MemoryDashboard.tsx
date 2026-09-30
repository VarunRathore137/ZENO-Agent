import React, { useState, useEffect } from 'react';
import { Database, Plus, Trash2, Sparkles, Target, Briefcase, Heart, Smile, Activity } from 'lucide-react';

export type MemoryCategory = 'identity' | 'preference' | 'goal' | 'project' | 'relationship' | 'emotional' | 'behavior';

export interface Memory {
  id: string;
  category: MemoryCategory;
  text: string;
  created_at?: string;
  updated_at?: string;
}

interface Props {
  apiBase: string;
}

const CATEGORY_META: Record<MemoryCategory, { label: string; icon: React.ComponentType<{ size?: number; className?: string }>; color: string; bg: string }> = {
  identity: { label: 'IDENTITY', icon: Database, color: '#00d4ff', bg: 'rgba(0, 212, 255, 0.1)' },
  preference: { label: 'PREFERENCE', icon: Sparkles, color: '#f472b6', bg: 'rgba(244, 114, 182, 0.1)' },
  goal: { label: 'GOAL', icon: Target, color: '#34d399', bg: 'rgba(52, 211, 153, 0.1)' },
  project: { label: 'PROJECT', icon: Briefcase, color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.1)' },
  relationship: { label: 'RELATIONSHIP', icon: Heart, color: '#c084fc', bg: 'rgba(192, 132, 252, 0.1)' },
  emotional: { label: 'EMOTIONAL', icon: Smile, color: '#fb923c', bg: 'rgba(251, 146, 60, 0.1)' },
  behavior: { label: 'BEHAVIOR', icon: Activity, color: '#818cf8', bg: 'rgba(129, 140, 248, 0.1)' },
};

export default function MemoryDashboard({ apiBase }: Props) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<MemoryCategory | 'all'>('all');
  
  // Add form state
  const [isAdding, setIsAdding] = useState(false);
  const [newCategory, setNewCategory] = useState<MemoryCategory>('preference');
  const [newText, setNewText] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchMemories = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiBase}/api/memories`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMemories(data.memories || []);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load memories');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemories();
  }, [apiBase]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newText.trim() || saving) return;
    setSaving(true);
    try {
      const res = await fetch(`${apiBase}/api/memories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: newCategory, text: newText.trim() }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setNewText('');
      setIsAdding(false);
      await fetchMemories();
    } catch (err: any) {
      alert(`Failed to save memory: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const res = await fetch(`${apiBase}/api/memories/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setMemories(prev => prev.filter(m => m.id !== id));
    } catch (err: any) {
      alert(`Failed to delete memory: ${err.message}`);
    }
  };

  const filtered = activeCategory === 'all' 
    ? memories 
    : memories.filter(m => m.category === activeCategory);

  const categories = Object.keys(CATEGORY_META) as MemoryCategory[];

  return (
    <div className="panel" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      {/* Panel Header */}
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Database size={15} color="var(--cyan)" />
          <span className="panel-title">MEMORY CORE</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
            ({memories.length} RECORDS)
          </span>
        </div>
        <button 
          className="hud-btn primary" 
          onClick={() => setIsAdding(!isAdding)}
          style={{ display: 'flex', alignItems: 'center', gap: 4 }}
        >
          <Plus size={11} />
          {isAdding ? 'CANCEL' : 'ADD RECORD'}
        </button>
      </div>

      {/* Add Memory Drawer */}
      {isAdding && (
        <form onSubmit={handleAdd} style={{
          padding: '12px 16px',
          background: 'rgba(0, 212, 255, 0.03)',
          borderBottom: '1px solid var(--border-dim)',
          display: 'flex',
          flexDirection: 'column',
          gap: 10
        }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>CATEGORY:</span>
            <select
              value={newCategory}
              onChange={e => setNewCategory(e.target.value as MemoryCategory)}
              style={{
                background: '#080d18',
                border: '1px solid var(--border-glow)',
                color: 'var(--cyan)',
                borderRadius: 'var(--radius-sm)',
                padding: '4px 8px',
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                outline: 'none',
              }}
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>{CATEGORY_META[cat].label}</option>
              ))}
            </select>
          </div>

          <textarea
            value={newText}
            onChange={e => setNewText(e.target.value)}
            placeholder="Enter a fact ZENO should remember about you (e.g. Preferred code editor, project goal, habit)..."
            rows={2}
            style={{
              background: 'rgba(0, 20, 40, 0.5)',
              border: '1px solid var(--border-glow)',
              color: 'var(--text-primary)',
              borderRadius: 'var(--radius-sm)',
              padding: '8px 10px',
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
              resize: 'none',
              outline: 'none',
            }}
          />

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <button
              type="submit"
              className="hud-btn primary"
              disabled={!newText.trim() || saving}
            >
              {saving ? 'RECORDING...' : 'STORE TO CORE'}
            </button>
          </div>
        </form>
      )}

      {/* Category Filter Tabs */}
      <div style={{
        display: 'flex',
        gap: 6,
        padding: '10px 16px',
        borderBottom: '1px solid var(--border-dim)',
        overflowX: 'auto',
      }}>
        <button
          className={`hud-btn ${activeCategory === 'all' ? 'primary' : ''}`}
          onClick={() => setActiveCategory('all')}
          style={{ fontSize: 9, padding: '3px 10px' }}
        >
          ALL ({memories.length})
        </button>
        {categories.map(cat => {
          const count = memories.filter(m => m.category === cat).length;
          return (
            <button
              key={cat}
              className={`hud-btn ${activeCategory === cat ? 'primary' : ''}`}
              onClick={() => setActiveCategory(cat)}
              style={{ fontSize: 9, padding: '3px 10px' }}
            >
              {CATEGORY_META[cat].label} ({count})
            </button>
          );
        })}
      </div>

      {/* Memory List */}
      <div className="panel-body" style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {loading && <div className="hud-loading">SYNCING KNOWLEDGE CORE...</div>}
        {error && <div className="hud-error">ERROR: {error}</div>}

        {!loading && !error && filtered.length === 0 && (
          <div className="hud-loading" style={{ padding: '32px 16px' }}>
            NO MEMORIES RECORDED YET. TALK WITH ZENO TO BUILD UP YOUR PROFILE.
          </div>
        )}

        {!loading && !error && filtered.map(item => {
          const meta = CATEGORY_META[item.category] || CATEGORY_META.preference;
          const Icon = meta.icon;
          return (
            <div
              key={item.id}
              style={{
                background: 'rgba(0, 212, 255, 0.02)',
                border: '1px solid rgba(0, 212, 255, 0.1)',
                borderRadius: 'var(--radius-sm)',
                padding: '10px 14px',
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                gap: 12,
                transition: 'border-color 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', flex: 1 }}>
                <span style={{
                  padding: '3px 6px',
                  borderRadius: 3,
                  background: meta.bg,
                  color: meta.color,
                  fontFamily: 'var(--font-hud)',
                  fontSize: 8,
                  fontWeight: 700,
                  letterSpacing: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  whiteSpace: 'nowrap',
                  marginTop: 2,
                }}>
                  <Icon size={10} />
                  {meta.label}
                </span>

                <div style={{ flex: 1 }}>
                  <p style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    color: 'var(--text-primary)',
                    lineHeight: 1.5,
                  }}>
                    {item.text}
                  </p>
                  {item.updated_at && (
                    <span style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 9,
                      color: 'var(--text-muted)',
                      letterSpacing: 1,
                    }}>
                      LAST UPDATED: {item.updated_at}
                    </span>
                  )}
                </div>
              </div>

              <button
                onClick={() => handleDelete(item.id)}
                title="Delete memory"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'rgba(255, 43, 74, 0.6)',
                  cursor: 'pointer',
                  padding: 4,
                  borderRadius: 3,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                onMouseEnter={e => (e.currentTarget.style.color = 'var(--red)')}
                onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255, 43, 74, 0.6)')}
              >
                <Trash2 size={13} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
