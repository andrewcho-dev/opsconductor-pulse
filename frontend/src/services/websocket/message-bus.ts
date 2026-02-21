import { logger } from "@/lib/logger";

type Handler = (data: unknown) => void;

export class MessageBus {
  private listeners = new Map<string, Set<Handler>>();

  /**
   * Subscribe to a topic. Returns an unsubscribe function.
   */
  on(topic: string, handler: Handler): () => void {
    if (!this.listeners.has(topic)) {
      this.listeners.set(topic, new Set());
    }
    this.listeners.get(topic)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.listeners.get(topic);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.listeners.delete(topic);
        }
      }
    };
  }

  /**
   * Publish data to all subscribers of a topic.
   */
  emit(topic: string, data: unknown): void {
    const handlers = this.listeners.get(topic);
    if (!handlers) return;
    handlers.forEach((handler) => {
      try {
        handler(data);
      } catch (err) {
        logger.error(`MessageBus handler error on topic "${topic}":`, err);
      }
    });
  }

  /**
   * Remove all listeners (for cleanup).
   */
  clear(): void {
    this.listeners.clear();
  }

  /**
   * Get the number of subscribers for a topic.
   */
  listenerCount(topic: string): number {
    return this.listeners.get(topic)?.size || 0;
  }
}

/** Singleton instance */
export const messageBus = new MessageBus();
