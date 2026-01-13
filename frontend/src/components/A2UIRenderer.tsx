import React from 'react';

interface A2UIComponent {
    type: string;
    [key: string]: any;
}

interface A2UIRendererProps {
    components: A2UIComponent[];
}

export const A2UIRenderer: React.FC<A2UIRendererProps> = ({ components }) => {
    if (!components || components.length === 0) return null;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
            {components.map((component, index) => (
                <A2UIComponent key={index} component={component} />
            ))}
        </div>
    );
};

const A2UIComponent: React.FC<{ component: A2UIComponent }> = ({ component }) => {
    switch (component.type) {
        case 'status_card':
            return <StatusCard {...component} />;
        case 'info_card':
        case 'claim_detail': // Added alias
            return <InfoCard {...component} />;
        case 'action_buttons':
            return <ActionButtons {...component} />;
        case 'table_card':
        case 'claims_list': // Added alias
            return <TableCard {...component} />;
        case 'form_card':
            return <FormCard {...component} />;
        case 'card_list':
            return <CardList {...component} />;
        default:
            return null;
    }
};

// ... existing components ...

// Table Card Component
const TableCard: React.FC<any> = ({ title, columns = [], rows = [], data }) => {
    // Handle both 'rows' and 'data' prop names
    const tableRows = rows.length > 0 ? rows : (data || []);

    return (
        <div className="glass-panel" style={{
            borderRadius: '0.75rem',
            padding: '1.25rem',
            overflow: 'hidden',
        }}>
            {title && (
                <div style={{ fontWeight: 600, marginBottom: '0.75rem', fontSize: '0.9rem', color: 'var(--primary)' }}>
                    {title}
                </div>
            )}
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead>
                        <tr style={{ background: 'var(--bg-muted)', borderBottom: '1px solid var(--border-color)' }}>
                            {columns.map((col: any, idx: number) => {
                                const renderHeader = (c: any): React.ReactNode => {
                                    if (c === null || c === undefined) return `Col ${idx}`;
                                    if (typeof c === 'string') return c;
                                    if (typeof c === 'object') {
                                        return c.name || c.label || c.id || JSON.stringify(c);
                                    }
                                    return String(c);
                                };
                                return (
                                    <th key={idx} style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)' }}>
                                        {renderHeader(col)}
                                    </th>
                                );
                            })}
                        </tr>
                    </thead>
                    <tbody>
                        {tableRows.map((row: any, rIdx: number) => (
                            <tr key={rIdx} style={{ borderBottom: rIdx < tableRows.length - 1 ? '1px solid var(--border-color)' : 'none' }}>
                                {columns.map((col: any, cIdx: number) => {
                                    const colKey = typeof col === 'string' ? col : (col.id || col.name);
                                    let cellValue = row[colKey];

                                    // Fuzzy match if exact colKey fails
                                    if (cellValue === undefined && typeof colKey === 'string') {
                                        const lowerKey = colKey.toLowerCase();
                                        const actualKey = Object.keys(row).find(k =>
                                            k.toLowerCase() === lowerKey ||
                                            k.toLowerCase().replace(/_/g, '') === lowerKey.replace(/_/g, '') ||
                                            k.toLowerCase().includes(lowerKey) || // actual_key includes policy
                                            lowerKey.includes(k.toLowerCase())     // policy includes actual_key
                                        );
                                        if (actualKey) cellValue = row[actualKey];
                                    }

                                    // Handle cases where row is an array - use column index
                                    if (cellValue === undefined && Array.isArray(row)) {
                                        cellValue = row[cIdx];
                                    }

                                    // Safely render cell value
                                    const renderValue = (val: any): React.ReactNode => {
                                        if (val === null || val === undefined) return "";
                                        if (typeof val === 'object') {
                                            if (val.name) return val.name;
                                            if (val.label) return val.label;
                                            return JSON.stringify(val);
                                        }
                                        return String(val);
                                    };

                                    return (
                                        <td key={cIdx} style={{ padding: '0.75rem', color: 'var(--text-main)' }}>
                                            {renderValue(cellValue)}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

// Form Card Component
const FormCard: React.FC<any> = ({ title, fields = [], submitLabel }) => {
    const fieldList = Array.isArray(fields) ? fields : [];

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const formData = new FormData(e.target as HTMLFormElement);
        const data = Object.fromEntries(formData.entries());

        console.log("Form Submitted", data);

        // Dispatch custom event that ChatPage can listen to
        window.dispatchEvent(new CustomEvent('a2ui-form-submit', {
            detail: { data }
        }));
    };

    return (
        <div className="glass-panel" style={{
            padding: '1.25rem',
            borderRadius: '0.75rem',
        }}>
            <div style={{ fontWeight: 600, marginBottom: '1rem', fontSize: '1rem', color: 'var(--text-main)' }}>
                {title}
            </div>
            <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '1rem' }}>
                {fieldList.map((field: any, idx: number) => (
                    <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <label style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text-muted)' }}>
                            {field.label} {field.required && <span style={{ color: 'var(--status-error-text)' }}>*</span>}
                        </label>
                        {field.type === 'textarea' ? (
                            <textarea
                                name={field.name}
                                required={field.required}
                                defaultValue={field.defaultValue}
                                className="input-field"
                                style={{ resize: 'vertical', minHeight: '80px', fontSize: '0.85rem' }}
                            />
                        ) : field.type === 'select' ? (
                            <select
                                name={field.name}
                                required={field.required}
                                defaultValue={field.defaultValue}
                                className="input-field"
                                style={{ fontSize: '0.85rem' }}
                            >
                                <option value="">Select...</option>
                                {field.options?.map((opt: string) => (
                                    <option key={opt} value={opt}>{opt}</option>
                                ))}
                            </select>
                        ) : (
                            <input
                                type={field.type}
                                name={field.name}
                                required={field.required}
                                defaultValue={field.defaultValue}
                                className="input-field"
                                style={{ fontSize: '0.85rem' }}
                            />
                        )}
                    </div>
                ))}
                <button
                    type="submit"
                    className="btn btn-primary"
                    style={{ marginTop: '0.5rem', justifyContent: 'center' }}
                >
                    {submitLabel || 'Submit'}
                </button>
            </form>
        </div>
    );
};

// Status Card Component
const StatusCard: React.FC<any> = ({ status, title, description, color, icon }) => {
    // Auto-derive color/icon if missing
    const finalColor = color || (status ? (
        status.toLowerCase().includes('approve') ? 'green' :
            status.toLowerCase().includes('reject') ? 'red' :
                status.toLowerCase().includes('pend') ? 'yellow' :
                    status.toLowerCase().includes('review') ? 'blue' : 'gray'
    ) : 'gray');

    const finalIcon = icon || (status ? (
        status.toLowerCase().includes('approve') ? '✅' :
            status.toLowerCase().includes('reject') ? '❌' :
                status.toLowerCase().includes('pend') ? '⏳' :
                    status.toLowerCase().includes('review') ? '🤖' : '📋'
    ) : '📋');

    // Map abstract colors to our theme variables
    const getStyles = (c: string) => {
        const map: any = {
            green: { bg: 'var(--status-success-bg)', border: 'var(--status-success-text)', text: 'var(--status-success-text)' },
            red: { bg: 'var(--status-error-bg)', border: 'var(--status-error-text)', text: 'var(--status-error-text)' },
            yellow: { bg: 'var(--status-warning-bg)', border: 'var(--status-warning-text)', text: 'var(--status-warning-text)' },
            blue: { bg: 'var(--status-info-bg)', border: 'var(--status-info-text)', text: 'var(--status-info-text)' },
            gray: { bg: 'var(--bg-input)', border: 'var(--border-color)', text: 'var(--text-secondary)' }
        };
        return map[c] || map.gray;
    };

    const s = getStyles(finalColor);

    return (
        <div style={{
            background: s.bg,
            border: `1px solid ${s.border}`,
            borderRadius: '0.75rem',
            padding: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
        }}>
            <div style={{ fontSize: '1.5rem' }}>{finalIcon}</div>
            <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 'bold', color: s.text, marginBottom: '0.25rem', fontSize: '0.9rem' }}>
                    {title}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {description}
                </div>
            </div>
        </div>
    );
};

const InfoCard: React.FC<any> = ({ title, fields = [], details }) => {
    // Support both 'fields' (array) and 'details' (object)
    let fieldList: any[] = [];
    if (Array.isArray(fields)) {
        fieldList = fields;
    } else if (typeof fields === 'object' && fields !== null) {
        fieldList = Object.entries(fields).map(([label, value]) => ({ label, value }));
    } else if (details && typeof details === 'object') {
        fieldList = Object.entries(details).map(([label, value]) => ({ label, value }));
    }

    return (
        <div className="glass-panel" style={{
            padding: '1.25rem',
            borderRadius: '0.75rem',
        }}>
            {title && (
                <div style={{ fontWeight: 600, marginBottom: '0.75rem', fontSize: '0.9rem', color: 'var(--primary)' }}>
                    {title}
                </div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem' }}>
                {fieldList.map((f: any, idx: number) => (
                    <div key={idx} style={{ borderLeft: '2px solid var(--border-color)', paddingLeft: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.025em', marginBottom: '0.15rem' }}>
                            {f.label || f.name}
                        </div>
                        <div style={{ fontWeight: 500, color: 'var(--text-main)', fontSize: '0.85rem' }}>
                            {String(f.value)}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

const ActionButtons: React.FC<any> = ({ buttons = [] }) => {
    const buttonList = Array.isArray(buttons) ? buttons : [];
    const handleAction = (action: string) => {
        console.log(`Action triggered: ${action}`);
        window.dispatchEvent(new CustomEvent('a2ui-action', { detail: { action } }));
    };

    return (
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {buttonList.map((button: any, index: number) => (
                <button
                    key={index}
                    onClick={() => handleAction(button.action)}
                    className={button.style === 'primary' ? 'btn-primary' : 'btn-secondary'}
                    style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                >
                    {button.label}
                </button>
            ))}
        </div>
    );
};

const CardList: React.FC<any> = ({ title, cards = [] }) => {
    const cardList = Array.isArray(cards) ? cards : [];
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {title && (
                <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--primary)' }}>
                    {title}
                </div>
            )}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '1rem'
            }}>
                {cardList.map((card: any, idx: number) => (
                    <div key={idx}>
                        {card.type === 'status_card' ? <StatusCard {...card} /> : <InfoCard {...card} />}
                    </div>
                ))}
            </div>
        </div>
    );
};
