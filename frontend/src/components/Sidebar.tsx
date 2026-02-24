/**
 * Toolbar Rail Component
 *
 * 48px icon-only navigation rail. No branding, no text labels.
 * Professional engineering tool aesthetic.
 */

import { type FC } from 'react';
import { LayoutDashboard, PlayCircle, Settings } from 'lucide-react';

interface SidebarProps {
    activeItem: string;
    onNavigate: (id: string) => void;
}

const NAV_ITEMS = [
    { id: 'dashboard', icon: LayoutDashboard, tooltip: 'Live Dashboard' },
    { id: 'replay', icon: PlayCircle, tooltip: 'Race Replay' },
    { id: 'settings', icon: Settings, tooltip: 'Settings' },
];

const Sidebar: FC<SidebarProps> = ({ activeItem, onNavigate }) => {
    return (
        <aside className="sidebar">
            <nav style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px', padding: '8px 0', width: '100%' }}>
                {NAV_ITEMS.map((item) => {
                    const Icon = item.icon;
                    return (
                        <button
                            key={item.id}
                            className={`nav-item ${activeItem === item.id ? 'active' : ''}`}
                            onClick={() => onNavigate(item.id)}
                            title={item.tooltip}
                        >
                            <span className="nav-item-icon"><Icon size={18} /></span>
                        </button>
                    );
                })}
            </nav>
        </aside>
    );
};

export default Sidebar;
