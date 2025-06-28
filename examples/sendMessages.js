/**
 * Example usage of the optimized WhatsApp service
 */
const WhatsAppService = require('../services/whatsappService');

async function sendMessages() {
  // Initialize the service with your configuration
  const whatsappService = new WhatsAppService({
    apiKey: process.env.WHATSAPP_API_KEY,
    apiUrl: process.env.WHATSAPP_API_URL,
    batchSize: 20,         // Increase for higher throughput
    concurrencyLimit: 10,  // Adjust based on your API limits
    retryAttempts: 3,
    retryDelay: 1000
  });

  // Example messages
  const messages = [
    {
      to: '1234567890',
      type: 'text',
      content: 'Hello from the optimized sender!'
    },
    // Add more messages as needed
  ];

  // Generate a larger batch of test messages
  const bulkMessages = Array(100).fill().map((_, i) => ({
    to: '1234567890', // Replace with actual numbers in production
    type: 'text',
    content: `Test message ${i + 1}`
  }));

  console.log(`Starting to send ${bulkMessages.length} messages...`);
  const startTime = Date.now();

  try {
    // Send all messages in optimized batches
    await whatsappService.sendBulkMessages(bulkMessages);
    
    const duration = (Date.now() - startTime) / 1000;
    console.log(`All messages sent successfully in ${duration} seconds`);
    console.log(`Average speed: ${bulkMessages.length / duration} messages per second`);
    
    // Log metrics
    console.log('Performance metrics:', whatsappService.getMetrics());
  } catch (error) {
    console.error('Error sending messages:', error);
  }
}

// Run the example
sendMessages().catch(console.error);