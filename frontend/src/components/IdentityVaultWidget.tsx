import { useEffect, useState } from 'react';
import { getIdentityAccounts } from '../lib/api';
import Panel from './ui/Panel';
import Badge from './ui/Badge';
import type { IdentityAccount } from '../types';

export default function IdentityVaultWidget() {
  const [accounts, setAccounts] = useState<IdentityAccount[]>([]);
  const [connectedCount, setConnectedCount] = useState(0);

  useEffect(() => {
    getIdentityAccounts().then(r => {
      setAccounts(r.accounts);
      setConnectedCount(r.connected_count);
    }).catch(() => {});
  }, []);

  return (
    <Panel
      title="Connected Accounts"
      subtitle={accounts.length > 0 ? `${connectedCount} active · ${accounts.length} total` : ''}
      accent="#6366f1"
      loading={false}
      empty={!accounts.length}
      emptyMessage="No provider accounts configured"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {accounts.map((acct) => (
          <div
            key={acct.provider_name}
            style={{
              padding: '8px 10px', borderRadius: 6,
              background: '#1e2230', border: '1px solid #2a2e3d',
              fontSize: 12, transition: 'all 0.15s',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ color: '#e2e4e9', fontWeight: 600 }}>{acct.provider_name}</span>
                <span style={{ color: '#7c8299', marginLeft: 6 }}>{acct.email}</span>
              </div>
              <Badge
                text={acct.session_state}
                color={acct.session_state === 'connected' ? '#22c55e' : acct.session_state === 'expired' ? '#ef4444' : '#7c8299'}
              />
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 4, color: '#7c8299', fontSize: 10 }}>
              <span>Health: <span style={{ color: acct.health_status === 'healthy' ? '#22c55e' : '#f59e0b' }}>{acct.health_status}</span></span>
              {acct.has_credentials && <span>✓ Credentials stored</span>}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
