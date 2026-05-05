/**
 * Validate a redirect target so an attacker can't push the browser to an
 * external origin (open-redirect). Only same-origin paths are allowed.
 *
 * Accepts: "/", "/projects", "/projects/abc?x=1#frag"
 * Rejects: "//evil.com", "https://evil.com", "http:foo", "javascript:..."
 *          "/\\evil.com", "" (empty), control chars
 */
export function safeRedirect(raw: string | null | undefined, fallback = '/'): string {
	if (!raw || typeof raw !== 'string') return fallback;
	// Must start with a single forward slash and NOT a slash or backslash next.
	// Single-slash + non-slash next blocks "//host" and protocol-relative URLs.
	if (raw[0] !== '/') return fallback;
	if (raw.length >= 2 && (raw[1] === '/' || raw[1] === '\\')) return fallback;
	// Reject control characters and whitespace that might confuse the
	// browser's URL parser.
	// eslint-disable-next-line no-control-regex
	if (/[\x00-\x1f\x7f\s]/.test(raw)) return fallback;
	return raw;
}
