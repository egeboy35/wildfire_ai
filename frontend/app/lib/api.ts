/**
 * Base URL of the FastAPI backend.
 *
 * Every component reached the API through a hard-coded `http://localhost:8000`,
 * which means the built frontend only ever works when the backend happens to sit
 * on the same machine on that port -- there is no way to point it at a staging
 * host, a container, or a laptop on the same network without editing sources.
 *
 * `NEXT_PUBLIC_` is required for the value to survive into client bundles; all of
 * these components are `'use client'`. The fallback is the previous literal, so a
 * checkout with no environment set behaves exactly as it did before.
 */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
