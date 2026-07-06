import React from 'react'

export interface ProductSwitcherProps {
  /** List of products the user is enrolled in with their roles */
  products: Array<{ product: string; role: string }>
  /** The currently active product */
  currentProduct: string
  /** Callback when user selects a different product */
  onSwitch: (product: string) => void
  /** Optional className for styling */
  className?: string
}

/** Human-readable display names for each product identifier. */
const PRODUCT_DISPLAY_NAMES: Record<string, string> = {
  analytics: 'Analytics',
  search_saas: 'Search SaaS',
  client_dashboard: 'Client Dashboard',
  admin_dashboard: 'Admin',
  marketplace: 'Marketplace',
}

/** Capitalize the first letter of a role for badge display. */
function formatRole(role: string): string {
  if (!role) return ''
  return role.charAt(0).toUpperCase() + role.slice(1)
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    padding: '8px 0',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    border: 'none',
    borderRadius: '6px',
    background: 'transparent',
    cursor: 'pointer',
    width: '100%',
    textAlign: 'left' as const,
    fontSize: '14px',
    lineHeight: '1.4',
    color: '#1a1a2e',
    transition: 'background-color 0.15s ease',
  },
  itemCurrent: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    border: 'none',
    borderRadius: '6px',
    background: '#f0f4ff',
    cursor: 'default',
    width: '100%',
    textAlign: 'left' as const,
    fontSize: '14px',
    lineHeight: '1.4',
    fontWeight: 600,
    color: '#1a1a2e',
  },
  productName: {
    marginRight: '8px',
  },
  roleBadge: {
    display: 'inline-block',
    fontSize: '11px',
    fontWeight: 500,
    padding: '2px 6px',
    borderRadius: '4px',
    backgroundColor: '#e8ecf0',
    color: '#4a5568',
    whiteSpace: 'nowrap' as const,
  },
}

/**
 * Product switcher menu showing all products the user is enrolled in.
 * Highlights the current product and allows navigation to others.
 *
 * Accessible: keyboard navigable, uses proper ARIA attributes.
 *
 * @example
 * ```tsx
 * <ProductSwitcher
 *   products={[{ product: 'analytics', role: 'admin' }, { product: 'search_saas', role: 'member' }]}
 *   currentProduct="analytics"
 *   onSwitch={(product) => router.push(`/${product}`)}
 * />
 * ```
 */
export function ProductSwitcher({
  products,
  currentProduct,
  onSwitch,
  className,
}: ProductSwitcherProps): JSX.Element {
  return (
    <nav
      className={className}
      role="navigation"
      aria-label="Product switcher"
      style={styles.container}
    >
      <ul role="list" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {products.map(({ product, role }) => {
          const isCurrent = product === currentProduct
          const displayName = PRODUCT_DISPLAY_NAMES[product] || product

          return (
            <li key={product} role="listitem">
              <button
                type="button"
                onClick={() => {
                  if (!isCurrent) onSwitch(product)
                }}
                aria-current={isCurrent ? 'page' : undefined}
                aria-label={`${displayName} — ${formatRole(role)}`}
                disabled={isCurrent}
                style={isCurrent ? styles.itemCurrent : styles.item}
                onMouseEnter={(e) => {
                  if (!isCurrent) {
                    ;(e.currentTarget as HTMLButtonElement).style.backgroundColor = '#f5f7fa'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isCurrent) {
                    ;(e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent'
                  }
                }}
              >
                <span style={styles.productName}>{displayName}</span>
                <span style={styles.roleBadge} aria-hidden="true">
                  {formatRole(role)}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
