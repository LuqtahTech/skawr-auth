import React, { useState, useRef, useEffect } from 'react'
import { AuthClient } from '../utils/auth-client'

export interface SharedLoginPageProps {
  /** Auth configuration (apiBaseUrl is required) */
  config: { apiBaseUrl: string }
  /** Which product to redirect to after login (optional) */
  redirectProduct?: string
  /** Callback on successful login */
  onSuccess?: (user: { id: string; email: string; name?: string }) => void
  /** Callback on login error */
  onError?: (error: Error) => void
  /** Whether to show signup tab (default: true) */
  showSignup?: boolean
  /** Custom branding/title */
  title?: string
}

type TabMode = 'login' | 'signup'

/**
 * Shared login/signup page component that can be embedded by any product frontend.
 * Provides both login and signup forms with error handling.
 *
 * After successful authentication, calls onSuccess with the user data,
 * allowing the embedding product to handle its own redirect logic.
 */
export function SharedLoginPage({
  config,
  redirectProduct,
  onSuccess,
  onError,
  showSignup = true,
  title = 'Sign in to Skawr',
}: SharedLoginPageProps): JSX.Element {
  const [tab, setTab] = useState<TabMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const emailRef = useRef<HTMLInputElement>(null)
  const errorRef = useRef<HTMLDivElement>(null)

  // Focus the email input on mount and tab switch
  useEffect(() => {
    emailRef.current?.focus()
  }, [tab])

  // Focus error message when it appears for screen readers
  useEffect(() => {
    if (error) {
      errorRef.current?.focus()
    }
  }, [error])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const client = new AuthClient({ apiBaseUrl: config.apiBaseUrl })

    try {
      let response
      if (tab === 'login') {
        response = await client.login({ email, password })
      } else {
        response = await client.signup({ email, password, name: name || undefined })
      }

      onSuccess?.({
        id: response.user.id,
        email: response.user.email,
        name: response.user.name,
      })
    } catch (err: unknown) {
      const message = extractErrorMessage(err)
      setError(message)
      onError?.(err instanceof Error ? err : new Error(message))
    } finally {
      setLoading(false)
    }
  }

  const switchTab = (newTab: TabMode) => {
    setTab(newTab)
    setError(null)
    setEmail('')
    setPassword('')
    setName('')
  }

  const hasError = error !== null

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        <h1 style={styles.title}>{title}</h1>

        {showSignup && (
          <div style={styles.tabBar} role="tablist" aria-label="Authentication mode">
            <button
              role="tab"
              aria-selected={tab === 'login'}
              aria-controls="auth-panel"
              id="tab-login"
              style={{
                ...styles.tabButton,
                ...(tab === 'login' ? styles.tabButtonActive : {}),
              }}
              onClick={() => switchTab('login')}
              type="button"
            >
              Log in
            </button>
            <button
              role="tab"
              aria-selected={tab === 'signup'}
              aria-controls="auth-panel"
              id="tab-signup"
              style={{
                ...styles.tabButton,
                ...(tab === 'signup' ? styles.tabButtonActive : {}),
              }}
              onClick={() => switchTab('signup')}
              type="button"
            >
              Sign up
            </button>
          </div>
        )}

        {hasError && (
          <div
            ref={errorRef}
            role="alert"
            aria-live="assertive"
            style={styles.errorBanner}
            tabIndex={-1}
          >
            {error}
          </div>
        )}

        <form
          id="auth-panel"
          role="tabpanel"
          aria-labelledby={tab === 'login' ? 'tab-login' : 'tab-signup'}
          onSubmit={handleSubmit}
          noValidate
          style={styles.form}
        >
          {tab === 'signup' && (
            <div style={styles.fieldGroup}>
              <label htmlFor="auth-name" style={styles.label}>
                Name
              </label>
              <input
                id="auth-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                style={styles.input}
                autoComplete="name"
                placeholder="Your name (optional)"
              />
            </div>
          )}

          <div style={styles.fieldGroup}>
            <label htmlFor="auth-email" style={styles.label}>
              Email
            </label>
            <input
              ref={emailRef}
              id="auth-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              aria-invalid={hasError}
              aria-describedby={hasError ? 'auth-error' : undefined}
              style={{
                ...styles.input,
                ...(hasError ? styles.inputError : {}),
              }}
              autoComplete="email"
              placeholder="you@example.com"
            />
          </div>

          <div style={styles.fieldGroup}>
            <label htmlFor="auth-password" style={styles.label}>
              Password
            </label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              aria-invalid={hasError}
              style={{
                ...styles.input,
                ...(hasError ? styles.inputError : {}),
              }}
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              placeholder="••••••••"
              minLength={8}
            />
          </div>

          {/* Hidden field for redirect product context */}
          {redirectProduct && (
            <input type="hidden" name="redirect_product" value={redirectProduct} />
          )}

          <button
            type="submit"
            disabled={loading || !email || !password}
            style={{
              ...styles.submitButton,
              ...(loading || !email || !password ? styles.submitButtonDisabled : {}),
            }}
            aria-busy={loading}
          >
            {loading
              ? 'Please wait…'
              : tab === 'login'
                ? 'Log in'
                : 'Create account'}
          </button>
        </form>

        {!showSignup && (
          <p style={styles.footerText}>
            Don&apos;t have an account? Contact your administrator.
          </p>
        )}
      </div>
    </div>
  )
}

/**
 * Extract a user-friendly error message from an axios error or generic error.
 */
function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object') {
    // Axios-style error with response data
    const axiosErr = err as { response?: { data?: { detail?: string; message?: string } }; message?: string }
    if (axiosErr.response?.data?.detail) {
      return axiosErr.response.data.detail
    }
    if (axiosErr.response?.data?.message) {
      return axiosErr.response.data.message
    }
    if (axiosErr.message) {
      return axiosErr.message
    }
  }
  if (err instanceof Error) {
    return err.message
  }
  return 'An unexpected error occurred. Please try again.'
}

// --- Inline Styles (no Tailwind — library component) ---

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    padding: '24px',
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    backgroundColor: '#f5f5f5',
  },
  card: {
    width: '100%',
    maxWidth: '400px',
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
    padding: '32px',
  },
  title: {
    margin: '0 0 24px',
    fontSize: '24px',
    fontWeight: 600,
    textAlign: 'center' as const,
    color: '#111827',
  },
  tabBar: {
    display: 'flex',
    borderBottom: '1px solid #e5e7eb',
    marginBottom: '24px',
  },
  tabButton: {
    flex: 1,
    padding: '10px 16px',
    fontSize: '14px',
    fontWeight: 500,
    background: 'none',
    border: 'none',
    borderBottom: '2px solid transparent',
    color: '#6b7280',
    cursor: 'pointer',
    transition: 'color 0.15s, border-color 0.15s',
  },
  tabButtonActive: {
    color: '#2563eb',
    borderBottomColor: '#2563eb',
  },
  errorBanner: {
    padding: '12px 16px',
    marginBottom: '16px',
    borderRadius: '6px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    color: '#dc2626',
    fontSize: '14px',
    lineHeight: '1.4',
    outline: 'none',
  },
  form: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  },
  label: {
    fontSize: '14px',
    fontWeight: 500,
    color: '#374151',
  },
  input: {
    padding: '10px 12px',
    fontSize: '14px',
    borderRadius: '6px',
    border: '1px solid #d1d5db',
    outline: 'none',
    transition: 'border-color 0.15s, box-shadow 0.15s',
    width: '100%',
    boxSizing: 'border-box' as const,
  },
  inputError: {
    borderColor: '#dc2626',
    boxShadow: '0 0 0 1px #dc2626',
  },
  submitButton: {
    marginTop: '8px',
    padding: '12px 16px',
    fontSize: '14px',
    fontWeight: 600,
    borderRadius: '6px',
    border: 'none',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    cursor: 'pointer',
    transition: 'background-color 0.15s',
  },
  submitButtonDisabled: {
    backgroundColor: '#93c5fd',
    cursor: 'not-allowed',
  },
  footerText: {
    marginTop: '16px',
    fontSize: '13px',
    color: '#6b7280',
    textAlign: 'center' as const,
  },
}
