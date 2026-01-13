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
            return <InfoCard {...component} />;
        case 'action_buttons':
            return <ActionButtons {...component} />;
        case 'table_card':
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
const TableCard: React.FC<any> = ({ title, columns, rows }) => {
    return (
        <div className="glass-dark" style={{
            borderRadius: '0.75rem',
            padding: '1rem',
            overflow: 'hidden',
        }}>
            <div style={{ fontWeight: 600, marginBottom: '0.75rem', fontSize: '0.9rem', color: '#60a5fa' }}>
                {title}
            </div>
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead>
                        <tr style={{ background: 'rgba(255,255,255,0.05)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                            {columns.map((col: string, idx: number) => (
                                <th key={idx} style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600, color: '#94a3b8' }}>
                                    {col}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row: any, rIdx: number) => (
                            <tr key={rIdx} style={{ borderBottom: rIdx < rows.length - 1 ? '1px solid rgba(255,255,255,0.1)' : 'none' }}>
                                {columns.map((col: string, cIdx: number) => (
                                    <td key={cIdx} style={{ padding: '0.75rem', color: '#e2e8f0' }}>
                                        {row[col]}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

// Form Card Component
const FormCard: React.FC<any> = ({ title, fields, submitLabel }) => {
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const formData = new FormData(e.target as HTMLFormElement);
        const data = Object.fromEntries(formData.entries());

        console.log("Form Submitted", data);
        const summary = Object.entries(data).map(([k, v]) => `${k}: ${v}`).join(", ");

        // In a real implementation this would likely post back to the chat API
        // For now we simulate an action
        alert(`Simulating submission to chat:\n${summary}`);
    };

    return (
        <div className="glass-dark" style={{
            borderRadius: '0.75rem',
            padding: '1rem',
        }}>
            <div style={{ fontWeight: 600, marginBottom: '1rem', fontSize: '1rem', color: '#f8fafc' }}>
                {title}
            </div>
            <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '1rem' }}>
                {fields.map((field: any, idx: number) => (
                    <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <label style={{ fontSize: '0.8rem', fontWeight: 500, color: '#94a3b8' }}>
                            {field.label} {field.required && <span style={{ color: '#f87171' }}>*</span>}
                        </label>
                        {field.type === 'textarea' ? (
                            <textarea
                                name={field.name}
                                required={field.required}
                                defaultValue={field.defaultValue}
                                className="input-tech"
                                style={{ resize: 'vertical', minHeight: '80px', fontSize: '0.85rem' }}
                            />
                        ) : field.type === 'select' ? (
                            <select
                                name={field.name}
                                required={field.required}
                                defaultValue={field.defaultValue}
                                className="input-tech"
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
                                className="input-tech"
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
    // Map abstract colors to our theme variables
    const getStyles = (color: string) => {
        const map: any = {
            green: { bg: 'rgba(22, 101, 52, 0.2)', border: 'rgba(22, 101, 52, 0.4)', text: '#4ade80' },
            red: { bg: 'rgba(153, 27, 27, 0.2)', border: 'rgba(153, 27, 27, 0.4)', text: '#fca5a5' },
            yellow: { bg: 'rgba(133, 77, 14, 0.2)', border: 'rgba(133, 77, 14, 0.4)', text: '#fde047' },
            blue: { bg: 'rgba(37, 99, 235, 0.2)', border: 'rgba(37, 99, 235, 0.4)', text: '#60a5fa' },
            gray: { bg: 'rgba(255, 255, 255, 0.05)', border: 'rgba(255, 255, 255, 0.1)', text: '#94a3b8' }
        };
        return map[color] || map.gray;
    };

    const s = getStyles(color);

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
            <div style={{ fontSize: '1.5rem' }}>{icon}</div>
            <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 'bold', color: s.text, marginBottom: '0.25rem', fontSize: '0.9rem' }}>
                    {title}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#e2e8f0', opacity: 0.9 }}>
                    {description}
                </div>
            </div>
        </div>
    );
};

// Info Card Component
const InfoCard: React.FC<any> = ({ title, fields }) => {
    return (
        <div className="glass-dark" style={{
            padding: '1rem',
            borderRadius: '0.75rem',
        }}>
            <div style={{ fontWeight: 600, marginBottom: '0.75rem', fontSize: '0.9rem', color: '#f8fafc' }}>
                {title}
            </div>
            <div style={{ display: 'grid', gap: '0.5rem' }}>
                {fields.map((field: any, index: number) => (
                    <div key={index} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                        <span style={{ color: '#94a3b8' }}>{field.label}:</span>
                        <span style={{ fontWeight: 600, color: '#e2e8f0' }}>{field.value}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

// Action Buttons Component
// Card List Component
const CardList: React.FC<any> = ({ title, cards }) => {
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
                {cards.map((card: any, idx: number) => (
                    <div key={idx}>
                        {card.type === 'status_card' ? <StatusCard {...card} /> : <InfoCard {...card} />}
                    </div>
                ))}
            </div>
        </div>
    );
};

const ActionButtons: React.FC<any> = ({ buttons }) => {
    const handleAction = (action: string) => {
        // Dispatch custom event that ChatPage can listen to
        // Or simpler: alert for now, but ideally we'd pass a callback prop down
        console.log(`Action triggered: ${action}`);
        window.dispatchEvent(new CustomEvent('a2ui-action', { detail: { action } }));
    };

    return (
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {buttons.map((button: any, index: number) => (
                <button
                    key={index}
                    onClick={() => handleAction(button.action)}
                    className={button.style === 'primary' ? 'btn btn-primary' : 'btn btn-secondary'}
                    style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                >
                    {button.label}
                </button>
            ))}
        </div>
    );
};
