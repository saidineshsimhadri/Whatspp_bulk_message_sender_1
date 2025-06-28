/**
 * Optimized WhatsApp Message Sending Service
 * This implementation includes:
 * - Message batching
 * - Concurrency control
 * - Rate limiting compliance
 * - Retry mechanism with exponential backoff
 * - Performance monitoring
 */

class WhatsAppService {
  constructor(config = {}) {
    // Default configuration
    this.config = {
      batchSize: 10, // Number of messages to batch together
      concurrencyLimit: 5, // Number of concurrent requests
      retryAttempts: 3, // Number of retry attempts
      retryDelay: 1000, // Base delay for retries in ms
      apiKey: config.apiKey || process.env.WHATSAPP_API_KEY,
      apiUrl: config.apiUrl || 'https://graph.facebook.com/v17.0/YOUR_PHONE_NUMBER_ID/messages',
      ...config
    };
    
    this.queue = [];
    this.processing = false;
    this.activeRequests = 0;
    this.metrics = {
      totalSent: 0,
      failures: 0,
      avgSendTime: 0
    };
  }

  /**
   * Add a message to the sending queue
   * @param {Object} message - Message object with recipient and content
   * @returns {Promise} Promise that resolves when message is queued
   */
  async sendMessage(message) {
    return new Promise((resolve, reject) => {
      this.queue.push({
        message,
        resolve,
        reject,
        attempts: 0
      });
      
      // Start processing queue if not already running
      if (!this.processing) {
        this.processQueue();
      }
    });
  }

  /**
   * Send multiple messages at once
   * @param {Array} messages - Array of message objects
   * @returns {Promise} Promise that resolves when all messages are queued
   */
  async sendBulkMessages(messages) {
    return Promise.all(messages.map(msg => this.sendMessage(msg)));
  }

  /**
   * Process the message queue with concurrency control
   */
  async processQueue() {
    if (this.queue.length === 0 || this.processing) return;
    
    this.processing = true;
    
    while (this.queue.length > 0) {
      // Wait if we've reached concurrency limit
      if (this.activeRequests >= this.config.concurrencyLimit) {
        await new Promise(resolve => setTimeout(resolve, 100));
        continue;
      }
      
      // Get batch of messages to process
      const batch = this.queue.splice(0, Math.min(this.config.batchSize, this.queue.length));
      this.activeRequests++;
      
      // Process batch without awaiting to allow concurrency
      this.processBatch(batch)
        .finally(() => {
          this.activeRequests--;
        });
    }
    
    this.processing = false;
  }

  /**
   * Process a batch of messages
   * @param {Array} batch - Batch of message items
   */
  async processBatch(batch) {
    try {
      const startTime = Date.now();
      
      // For individual message sending
      const promises = batch.map(item => this.makeApiRequest(item));
      const results = await Promise.allSettled(promises);
      
      const endTime = Date.now();
      this.updateMetrics(batch.length, results, endTime - startTime);
      
      // Handle results
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          batch[index].resolve(result.value);
        } else {
          this.handleFailure(batch[index], result.reason);
        }
      });
    } catch (error) {
      console.error('Error processing batch:', error);
      // Requeue failed items with backoff
      batch.forEach(item => this.handleFailure(item, error));
    }
  }

  /**
   * Make the actual API request to WhatsApp
   * @param {Object} item - Queue item with message
   * @returns {Promise} API response
   */
  async makeApiRequest(item) {
    const { message } = item;
    item.attempts++;
    
    try {
      const response = await fetch(this.config.apiUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.config.apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          messaging_product: 'whatsapp',
          recipient_type: 'individual',
          to: message.to,
          type: message.type || 'text',
          text: message.type === 'text' ? { body: message.content } : undefined,
          // Add other message types as needed
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`WhatsApp API error: ${errorData.error?.message || response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`API request failed (attempt ${item.attempts}):`, error);
      throw error;
    }
  }

  /**
   * Handle failed message sending
   * @param {Object} item - Queue item that failed
   * @param {Error} error - Error that occurred
   */
  handleFailure(item, error) {
    if (item.attempts < this.config.retryAttempts) {
      // Calculate exponential backoff delay
      const delay = this.config.retryDelay * Math.pow(2, item.attempts - 1);
      
      // Re-queue with delay
      setTimeout(() => {
        this.queue.push(item);
        if (!this.processing) {
          this.processQueue();
        }
      }, delay);
    } else {
      // Max retries reached, reject the promise
      item.reject(error);
    }
  }

  /**
   * Update performance metrics
   * @param {Number} count - Number of messages processed
   * @param {Array} results - Results of processing
   * @param {Number} duration - Time taken in ms
   */
  updateMetrics(count, results, duration) {
    const successful = results.filter(r => r.status === 'fulfilled').length;
    const failed = count - successful;
    
    this.metrics.totalSent += successful;
    this.metrics.failures += failed;
    
    // Update average send time
    const oldTotal = this.metrics.avgSendTime * (this.metrics.totalSent - successful);
    const newAvg = (oldTotal + duration) / this.metrics.totalSent;
    this.metrics.avgSendTime = newAvg;
  }

  /**
   * Get current performance metrics
   * @returns {Object} Current metrics
   */
  getMetrics() {
    return {
      ...this.metrics,
      queueLength: this.queue.length,
      activeRequests: this.activeRequests
    };
  }
}

module.exports = WhatsAppService;