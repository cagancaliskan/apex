/**
 * Metric card component for displaying key statistics.
 */

function MetricCard({ label, value, delta, deltaType, color = 'cyan', icon: Icon }) {
    return (
        <div className="metric-card card-glow">
            <div className="flex items-center justify-between">
                <span className="label">{label}</span>
                {Icon && (
                    <Icon
                        size={18}
                        style={{ color: `var(--accent-${color})`, opacity: 0.7 }}
                    />
                )}
            </div>
            <div className={`value ${color}`}>{value}</div>
            {delta && (
                <div className={`delta ${deltaType}`}>
                    {deltaType === 'positive' ? '↑' : '↓'} {delta}
                </div>
            )}
        </div>
    )
}

export default MetricCard
