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
        default:
            return null;
    }
};

// ... existing components ...

// Table Card Component
const TableCard: React.FC<any> = ({ title, columns, rows }) => {
    return (
        <div style={{
            background: 'white',
            borderRadius: '0.75rem',
            padding: '1rem',
            border: '1px solid #e5e7eb',
            overflow: 'hidden'
        }}>
            <div style={{ fontWeight: 'bold', marginBottom: '0.75rem', fontSize: '0.9rem' }}>
                {title}
            </div>
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                    <thead>
                        <tr style={{ background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                            {columns.map((col: string, idx: number) => (
                                <th key={idx} style={{ padding: '0.5rem', textAlign: 'left', fontWeight: 'bold', color: '#4b5563' }}>
                                    {col}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row: any, rIdx: number) => (
                            <tr key={rIdx} style={{ borderBottom: rIdx < rows.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
                                {columns.map((col: string, cIdx: number) => (
                                    <td key={cIdx} style={{ padding: '0.5rem', color: '#1f2937' }}>
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

        // This functionality requires notifying the parent or sending a message.
        // For now, let's assume we construct a natural language response to send.
        // Ideally, this component should accept an `onSubmit` prop.
        // But since it's rendered generically inside a message, we need a way to hook into the chat input.
        // We'll use a custom event or console log for now as the "Integration" requires ChatPage updates to listen.
        // OR better: we can infer the user just types the info.
        // But to make it "Real", let's assume the user copies the values or we trigger an automated message.

        // Let's implement a 'postMessage' simulation if possible or just alert for now.
        console.log("Form Submitted", data);

        // Hack: Fill the chat input? 
        // We can't easily access the ChatPage state from here without Context.
        // Let's print to console and alert.
        const summary = Object.entries(data).map(([k, v]) => `${k}: ${v}`).join(", ");
        alert(`Submit this info to chat:\n${summary}`);
    };

    return (
        <div style={{
            background: 'white',
            borderRadius: '0.75rem',
            padding: '1rem',
            border: '1px solid #e5e7eb'
        }}>
            <div style={{ fontWeight: 'bold', marginBottom: '1rem', fontSize: '1rem', color: '#111827' }}>
                {title}
            </div>
            <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '1rem' }}>
                {fields.map((field: any, idx: number) => (
                    <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <label style={{ fontSize: '0.8rem', fontWeight: '500', color: '#374151' }}>
                            {field.label} {field.required && <span style={{ color: 'red' }}>*</span>}
                        </label>
                        {field.type === 'textarea' ? (
                            <textarea
                                name={field.name}
                                required={field.required}
                                style={{
                                    padding: '0.5rem',
                                    border: '1px solid #d1d5db',
                                    borderRadius: '0.375rem',
                                    fontSize: '0.875rem',
                                    resize: 'vertical',
                                    minHeight: '80px'
                                }}
                            />
                        ) : field.type === 'select' ? (
                            <select
                                name={field.name}
                                required={field.required}
                                style={{
                                    padding: '0.5rem',
                                    border: '1px solid #d1d5db',
                                    borderRadius: '0.375rem',
                                    fontSize: '0.875rem'
                                }}
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
                                style={{
                                    padding: '0.5rem',
                                    border: '1px solid #d1d5db',
                                    borderRadius: '0.375rem',
                                    fontSize: '0.875rem'
                                }}
                            />
                        )}
                    </div>
                ))}
                <button
                    type="submit"
                    style={{
                        marginTop: '0.5rem',
                        background: '#2563eb',
                        color: 'white',
                        padding: '0.5rem',
                        borderRadius: '0.375rem',
                        fontWeight: '500',
                        border: 'none',
                        cursor: 'pointer'
                    }}
                >
                    {submitLabel || 'Submit'}
                </button>
            </form>
        </div>
    );
};

// Status Card Component
const StatusCard: React.FC<any> = ({ status, title, description, color, icon }) => {
    const colors: Record<string, { bg: string; border: string; text: string }> = {
        green: { bg: '#dcfce7', border: '#22c55e', text: '#166534' },
        red: { bg: '#fee2e2', border: '#ef4444', text: '#991b1b' },
        yellow: { bg: '#fef3c7', border: '#f59e0b', text: '#92400e' },
        blue: { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af' },
        orange: { bg: '#ffedd5', border: '#f97316', text: '#9a3412' },
        gray: { bg: '#f3f4f6', border: '#9ca3af', text: '#374151' }
    };

    const colorScheme = colors[color] || colors.gray;

    return (
        <div style={{
            background: colorScheme.bg,
            border: `2px solid ${colorScheme.border}`,
            borderRadius: '0.75rem',
            padding: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem'
        }}>
            <div style={{ fontSize: '2rem' }}>{icon}</div>
            <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 'bold', color: colorScheme.text, marginBottom: '0.25rem' }}>
                    {title}
                </div>
                <div style={{ fontSize: '0.875rem', color: colorScheme.text, opacity: 0.8 }}>
                    {description}
                </div>
            </div>
        </div>
    );
};

// Info Card Component
const InfoCard: React.FC<any> = ({ title, fields }) => {
    return (
        <div className="glass" style={{
            borderRadius: '0.75rem',
            padding: '1rem',
            background: 'rgba(255, 255, 255, 0.5)'
        }}>
            <div style={{ fontWeight: 'bold', marginBottom: '0.75rem', fontSize: '0.9rem' }}>
                {title}
            </div>
            <div style={{ display: 'grid', gap: '0.5rem' }}>
                {fields.map((field: any, index: number) => (
                    <div key={index} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                        <span style={{ color: '#666' }}>{field.label}:</span>
                        <span style={{ fontWeight: '500' }}>{field.value}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

// Action Buttons Component
const ActionButtons: React.FC<any> = ({ buttons }) => {
    const handleAction = (action: string) => {
        console.log('Action clicked:', action);
        // TODO: Implement action handlers
        alert(`Action: ${action} - This feature is coming soon!`);
    };

    const getButtonStyle = (style: string) => {
        const styles: Record<string, React.CSSProperties> = {
            primary: {
                background: '#3b82f6',
                color: 'white',
                border: 'none'
            },
            secondary: {
                background: 'white',
                color: '#3b82f6',
                border: '2px solid #3b82f6'
            }
        };
        return styles[style] || styles.primary;
    };

    return (
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {buttons.map((button: any, index: number) => (
                <button
                    key={index}
                    onClick={() => handleAction(button.action)}
                    style={{
                        ...getButtonStyle(button.style),
                        padding: '0.5rem 1rem',
                        borderRadius: '0.5rem',
                        cursor: 'pointer',
                        fontSize: '0.875rem',
                        fontWeight: '500'
                    }}
                >
                    {button.label}
                </button>
            ))}
        </div>
    );
};
