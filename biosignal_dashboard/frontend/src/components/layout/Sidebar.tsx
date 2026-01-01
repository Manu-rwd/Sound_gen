/**
 * Sidebar component with tabbed navigation for Devices and Interface controls.
 */
import { useState } from 'react';
import { DeviceToggles } from '../controls/DeviceToggles';
import { StatePanel } from '../controls/StatePanel';
import './Sidebar.css';

const STORAGE_KEY = 'biosignal_dashboard_layout';
const TAB_STORAGE_KEY = 'biosignal_sidebar_active_tab';

export function Sidebar() {
    const [activeTab, setActiveTab] = useState<'devices' | 'interface'>(() => {
        return (localStorage.getItem(TAB_STORAGE_KEY) as 'devices' | 'interface') || 'devices';
    });

    const handleTabChange = (tab: 'devices' | 'interface') => {
        setActiveTab(tab);
        localStorage.setItem(TAB_STORAGE_KEY, tab);
    };

    const handleResetLayout = () => {
        localStorage.removeItem(STORAGE_KEY);
        window.location.reload();
    };

    return (
        <div className="sidebar-container">
            <div className="sidebar-tabs">
                <button
                    className={`sidebar-tab ${activeTab === 'devices' ? 'active' : ''}`}
                    onClick={() => handleTabChange('devices')}
                >
                    Devices
                </button>
                <button
                    className={`sidebar-tab ${activeTab === 'interface' ? 'active' : ''}`}
                    onClick={() => handleTabChange('interface')}
                >
                    Interface
                </button>
            </div>

            <div className="sidebar-content">
                {activeTab === 'devices' ? (
                    <>
                        <DeviceToggles />
                        <div className="sidebar-divider" />
                        <StatePanel />
                    </>
                ) : (
                    <div className="interface-controls">
                        <h3>Dashboard Layout</h3>
                        <p className="control-description">
                            Resetting the layout will restore all panels to their default stacked position and sizes.
                        </p>
                        <button
                            className="reset-layout-btn"
                            onClick={handleResetLayout}
                        >
                            Reset Layout
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
