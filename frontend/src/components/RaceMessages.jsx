/**
 * Race messages panel showing recent events.
 */

import { Flag, AlertTriangle, Car, Radio } from 'lucide-react'

function RaceMessages({ messages }) {
    const getMessageIcon = (message) => {
        if (message.flag?.includes('YELLOW')) return <AlertTriangle size={14} />
        if (message.flag?.includes('RED')) return <Flag size={14} />
        if (message.category === 'SafetyCar') return <Car size={14} />
        return <Radio size={14} />
    }

    const getMessageColor = (message) => {
        if (message.flag?.includes('YELLOW')) return 'var(--status-yellow)'
        if (message.flag?.includes('RED')) return 'var(--status-red)'
        if (message.flag?.includes('GREEN')) return 'var(--status-green)'
        return 'var(--text-secondary)'
    }

    if (!messages || messages.length === 0) {
        return (
            <div className="text-muted text-sm" style={{ padding: 'var(--space-md)' }}>
                No race control messages
            </div>
        )
    }

    return (
        <div style={{ maxHeight: '300px', overflow: 'auto' }}>
            {messages.slice(0, 10).map((message, index) => (
                <div
                    key={index}
                    className="flex gap-sm"
                    style={{
                        padding: 'var(--space-sm)',
                        borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
                        fontSize: '0.75rem'
                    }}
                >
                    <span style={{ color: getMessageColor(message), flexShrink: 0 }}>
                        {getMessageIcon(message)}
                    </span>
                    <div style={{ flex: 1 }}>
                        <div style={{ color: 'var(--text-secondary)' }}>
                            {message.message?.substring(0, 80)}
                        </div>
                        <div className="text-muted" style={{ fontSize: '0.65rem' }}>
                            Lap {message.lap_number || '?'}
                        </div>
                    </div>
                </div>
            ))}
        </div>
    )
}

export default RaceMessages
