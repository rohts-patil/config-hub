import { ConfigJson, ConfigHubOptions, UserObject } from "./types";
import { evaluateFlag, evaluateAllFlags } from "./evaluator";

const DEFAULT_POLL_INTERVAL = 60; // seconds

/**
 * ConfigHub SDK client.
 *
 * Usage:
 * ```ts
 * const client = await ConfigHubClient.create("YOUR_SDK_KEY", {
 *   baseUrl: "http://localhost:8000",
 * });
 * const value = client.getValue("my_flag", false, { identifier: "user-1" });
 * ```
 */
export class ConfigHubClient {
  private sdkKey: string;
  private baseUrl: string;
  private pollIntervalMs: number;
  private fetchFn: typeof fetch;
  private onConfigChanged?: (config: ConfigJson) => void;
  private onFlagEvaluated?: (key: string, value: unknown, user?: UserObject) => void;

  private config: ConfigJson | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private configEtag: string | null = null;

  private constructor(sdkKey: string, options: ConfigHubOptions) {
    this.sdkKey = sdkKey;
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.pollIntervalMs =
      (options.pollIntervalSeconds ?? DEFAULT_POLL_INTERVAL) * 1000;
    this.fetchFn = options.fetchFn ?? globalThis.fetch.bind(globalThis);
    this.onConfigChanged = options.onConfigChanged;
    this.onFlagEvaluated = options.onFlagEvaluated;
  }

  /**
   * Create and initialize a ConfigHub client.
   * Fetches config immediately and starts polling.
   */
  static async create(
    sdkKey: string,
    options: ConfigHubOptions
  ): Promise<ConfigHubClient> {
    const client = new ConfigHubClient(sdkKey, options);
    await client.forceRefresh();
    client.startPolling();
    return client;
  }

  /**
   * Get a single flag value with client-side evaluation.
   *
   * @param key - The setting key.
   * @param defaultValue - Value to return if the flag is not found or config hasn't loaded.
   * @param user - Optional user context for targeting.
   */
  getValue<T>(key: string, defaultValue: T, user?: UserObject): T {
    if (!this.config) return defaultValue;

    const setting = this.config.settings[key];
    if (!setting) return defaultValue;

    const value = evaluateFlag(
      key,
      setting,
      user,
      this.config.segments
    );

    const result = (value ?? defaultValue) as T;
    this.onFlagEvaluated?.(key, result, user);
    return result;
  }

  /**
   * Evaluate all flags for a given user and return a key→value map.
   */
  getAllValues(user?: UserObject): Record<string, unknown> {
    if (!this.config) return {};
    const results = evaluateAllFlags(this.config, user);
    if (this.onFlagEvaluated) {
      for (const [key, value] of Object.entries(results)) {
        this.onFlagEvaluated(key, value, user);
      }
    }
    return results;
  }

  /**
   * Force an immediate refresh of the config JSON from the server.
   */
  async forceRefresh(): Promise<void> {
    const url = `${this.baseUrl}/api/v1/sdk/${this.sdkKey}/config.json`;
    const headers: Record<string, string> = {};
    if (this.configEtag) {
      headers["If-None-Match"] = this.configEtag;
    }

    const res = await this.fetchFn(url, { headers });

    if (res.status === 304) {
      // Config hasn't changed
      return;
    }

    if (!res.ok) {
      throw new Error(
        `ConfigHub SDK: failed to fetch config (HTTP ${res.status})`
      );
    }

    const newConfig: ConfigJson = await res.json();
    const etag = res.headers.get("ETag");
    if (etag) this.configEtag = etag;

    const changed =
      !this.config ||
      JSON.stringify(this.config) !== JSON.stringify(newConfig);

    this.config = newConfig;

    if (changed) {
      this.onConfigChanged?.(newConfig);
    }
  }

  /** Get the currently cached config JSON (or null if not loaded). */
  getConfig(): ConfigJson | null {
    return this.config;
  }

  /** Stop polling and clean up. */
  destroy(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.config = null;
  }

  // ── Private ──

  private startPolling(): void {
    if (this.pollIntervalMs <= 0) return;
    this.pollTimer = setInterval(async () => {
      try {
        await this.forceRefresh();
      } catch {
        // Silently ignore polling errors — will retry next interval
      }
    }, this.pollIntervalMs);
  }
}

