/**
 * Sign-in: OpenID Connect Authorization Code flow with PKCE (S256), against any standard provider
 * (Keycloak locally). No client secret in the browser; tokens live in memory and sessionStorage (cleared when
 * the tab closes), never localStorage. VITE_AUTH=dev keeps the demo "acting as" switcher instead.
 */

type Tokens = { access: string; refresh?: string; id?: string; expiresAt: number };
type Discovery = { authorization_endpoint: string; token_endpoint: string; end_session_endpoint?: string };
export type SignedInUser = { email: string; name: string };

const env = import.meta.env as Record<string, string | undefined>;
export const AUTH_MODE: "oidc" | "dev" = env.VITE_AUTH === "oidc" ? "oidc" : "dev";
const ISSUER = (env.VITE_OIDC_ISSUER ?? "http://localhost:8081/realms/ufme").replace(/\/$/, "");
const CLIENT_ID = env.VITE_OIDC_CLIENT_ID ?? "ufme-web";
const CALLBACK = "/auth/callback";
// Same-origin proxy of ISSUER (see vite.config.ts); "" = call the provider directly (e.g. behind one domain).
const PROXY = env.VITE_OIDC_PROXY ?? "/idp";
const KEY = "ufme.auth";
const PENDING = "ufme.auth.pending";

let tokens: Tokens | null = null;
let discovery: Promise<Discovery> | null = null;
let refreshing: Promise<string | null> | null = null;

const b64url = (bytes: ArrayBuffer | Uint8Array) =>
  btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const random = (n = 32) => b64url(crypto.getRandomValues(new Uint8Array(n)));
const redirectUri = () => `${window.location.origin}${CALLBACK}`;

function store(t: Tokens | null) {
  tokens = t;
  try {
    if (t) sessionStorage.setItem(KEY, JSON.stringify(t));
    else sessionStorage.removeItem(KEY);
  } catch {
    /* storage blocked: keep the in-memory copy */
  }
}

function restore(): Tokens | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    return null;
  }
}

// Endpoint paths relative to the realm. The provider builds absolute URLs from whichever host asked (behind the
// proxy that is the app's own host), so only the path is trusted: browser navigations (sign-in, sign-out) go to
// the provider's public address, background token calls go through the same-origin proxy.
const REALM_PATH = new URL(ISSUER).pathname;
const relative = (url: string) => {
  const path = new URL(url, window.location.origin).pathname;
  return path.startsWith(REALM_PATH) ? path.slice(REALM_PATH.length) : path;
};

function config(): Promise<Discovery> {
  discovery ??= fetch(`${PROXY || ISSUER}/.well-known/openid-configuration`).then(async (r) => {
    if (!r.ok) throw new Error("The sign-in service isn't reachable.");
    const d = (await r.json()) as Discovery;
    return {
      authorization_endpoint: ISSUER + relative(d.authorization_endpoint),
      token_endpoint: (PROXY || ISSUER) + relative(d.token_endpoint),
      end_session_endpoint: d.end_session_endpoint ? ISSUER + relative(d.end_session_endpoint) : undefined,
    };
  });
  return discovery;
}

function fromResponse(body: { access_token: string; refresh_token?: string; id_token?: string; expires_in: number }): Tokens {
  return {
    access: body.access_token,
    refresh: body.refresh_token,
    id: body.id_token ?? tokens?.id,
    expiresAt: Date.now() + body.expires_in * 1000,
  };
}

async function tokenRequest(params: Record<string, string>): Promise<Tokens> {
  const { token_endpoint } = await config();
  const r = await fetch(token_endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ client_id: CLIENT_ID, ...params }),
  });
  if (!r.ok) throw new Error(`Sign-in failed (${r.status}).`);
  return fromResponse(await r.json());
}

/** Send the browser to the provider's sign-in page; we come back to /auth/callback. */
export async function login(returnTo = window.location.pathname + window.location.search): Promise<never> {
  const { authorization_endpoint } = await config();
  const verifier = random(48);
  const challenge = b64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  const state = random(16);
  sessionStorage.setItem(PENDING, JSON.stringify({ verifier, state, returnTo }));
  const url = new URL(authorization_endpoint);
  url.search = new URLSearchParams({
    response_type: "code",
    client_id: CLIENT_ID,
    redirect_uri: redirectUri(),
    scope: "openid email profile",
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  }).toString();
  window.location.assign(url.toString());
  return new Promise<never>(() => {});
}

/** Sign-in problems the user can do nothing about (the sign-in service starting up, a used or expired code) are
 *  retried automatically; this error means the app should show a message and keep retrying. */
export class SignInUnavailable extends Error {}

const RETRY = "ufme.auth.retry";

function retriesLeft(): boolean {
  const n = Number(sessionStorage.getItem(RETRY) ?? "0");
  sessionStorage.setItem(RETRY, String(n + 1));
  return n < 2;
}

/** Call once before rendering: finishes a callback, restores a session, or starts sign-in. */
export async function initAuth(): Promise<void> {
  if (AUTH_MODE !== "oidc") return;
  try {
    await config();
  } catch {
    discovery = null; // try discovery again next time
    throw new SignInUnavailable("The sign-in service is starting or not reachable. Retrying…");
  }
  if (window.location.pathname === CALLBACK) {
    const params = new URLSearchParams(window.location.search);
    const pending = JSON.parse(sessionStorage.getItem(PENDING) ?? "null") as
      | { verifier: string; state: string; returnTo: string }
      | null;
    sessionStorage.removeItem(PENDING);
    if (params.get("error")) throw new Error(params.get("error_description") ?? params.get("error") ?? "Sign-in failed.");
    const code = params.get("code");
    if (!pending || !code || params.get("state") !== pending.state) {
      return login("/"); // reloaded, bookmarked or stale callback: simply start again
    }
    try {
      store(await tokenRequest({ grant_type: "authorization_code", code, redirect_uri: redirectUri(), code_verifier: pending.verifier }));
    } catch (err) {
      // the code was already used or expired (back button, slow network): start a fresh sign-in, at most twice
      if (retriesLeft()) return login(pending.returnTo || "/");
      throw err;
    }
    sessionStorage.removeItem(RETRY);
    window.history.replaceState(null, "", pending.returnTo || "/");
    return;
  }
  tokens = restore();
  if (!tokens || !(await accessToken())) await login();
  sessionStorage.removeItem(RETRY);
}

/** A valid access token, refreshed shortly before it expires; null if the session is gone. */
export async function accessToken(): Promise<string | null> {
  if (AUTH_MODE !== "oidc") return null;
  if (tokens && tokens.expiresAt - Date.now() > 60_000) return tokens.access;
  if (!tokens?.refresh) return null;
  refreshing ??= tokenRequest({ grant_type: "refresh_token", refresh_token: tokens.refresh })
    .then((t) => {
      store(t);
      return t.access;
    })
    .catch(() => {
      store(null);
      return null;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export function signedInUser(): SignedInUser | null {
  const id = tokens?.id ?? tokens?.access;
  if (!id) return null;
  try {
    const claims = JSON.parse(atob(id.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))) as Record<string, string>;
    return { email: claims.email ?? claims.preferred_username ?? "", name: claims.name ?? claims.email ?? "" };
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  const idToken = tokens?.id;
  store(null);
  const { end_session_endpoint } = await config();
  if (!end_session_endpoint) return void window.location.assign("/");
  const url = new URL(end_session_endpoint);
  url.search = new URLSearchParams({
    client_id: CLIENT_ID,
    post_logout_redirect_uri: `${window.location.origin}/`,
    ...(idToken ? { id_token_hint: idToken } : {}),
  }).toString();
  window.location.assign(url.toString());
}
