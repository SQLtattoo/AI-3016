/*
 * AI-3016 Demo 3: Microsoft Foundry SDK Chat Client (C#)
 * 
 * This demo shows how to create a basic chat client using the Microsoft Foundry SDK.
 * Demonstrates:
 * - Microsoft Foundry SDK authentication and configuration
 * - Interactive chat session with conversation history
 * - Streaming responses for better user experience
 * - Error handling and connection management
 * - Clean exit handling
 * 
 * Prerequisites:
 * - Microsoft Foundry project with GPT-4o deployment
 * - Valid .env file with Microsoft Foundry credentials
 * 
 * Usage:
 *     dotnet run
 */

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Azure.AI.Projects;
using Azure.Identity;
using Azure.Core;
using OpenAI.Chat;

namespace AI3016.ChatClientDemo
{
    /// <summary>
    /// Simple chat client using Microsoft Foundry SDK.
    /// </summary>
    public class AzureAIFoundryChatClient
    {
        private readonly string _endpointUrl;
        private readonly string _deploymentName;
        private AIProjectClient _projectClient;
        private ChatClient _chatClient;
        private List<ChatMessage> _conversationHistory;
        private bool _jsonMode;

        public AzureAIFoundryChatClient()
        {
            // Load environment variables
            _endpointUrl = Environment.GetEnvironmentVariable("ENDPOINT_URL") ?? string.Empty;
            _deploymentName = Environment.GetEnvironmentVariable("DEPLOYMENT_NAME") ?? string.Empty;

            // Validate environment variables
            if (string.IsNullOrWhiteSpace(_endpointUrl) || string.IsNullOrWhiteSpace(_deploymentName))
            {
                Console.WriteLine("❌ Error: Missing required environment variables!");
                Console.WriteLine("Please ensure your .env file contains:");
                Console.WriteLine("  - ENDPOINT_URL");
                Console.WriteLine("  - DEPLOYMENT_NAME");
                Environment.Exit(1);
            }

            // Initialize the Microsoft Foundry project client
            try
            {
                var credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
                {
                    ExcludeEnvironmentCredential = true,
                    ExcludeManagedIdentityCredential = true
                });

                _projectClient = new AIProjectClient(new Uri(_endpointUrl), credential);

                // Get chat client from the project
                _chatClient = _projectClient.GetChatClient(_deploymentName);

                Console.WriteLine("✅ Microsoft Foundry client initialized successfully");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Failed to initialize client: {ex.Message}");
                Environment.Exit(1);
            }

            // Initialize conversation history
            _conversationHistory = new List<ChatMessage>();
            _jsonMode = false;
            SetupSystemMessage();
        }

        /// <summary>
        /// Set up the system message for the chat session.
        /// </summary>
        private void SetupSystemMessage()
        {
            var baseContent = @"You are a helpful AI assistant created using Microsoft Foundry SDK.
            You provide clear, accurate, and helpful responses to user questions. 
            Keep your responses concise but informative. If you don't know something, 
            say so honestly rather than making up information.";

            if (_jsonMode)
            {
                baseContent += @"
            
            Always respond with valid JSON in this format:
            {
                ""answer"": ""your detailed response here"",
                ""confidence"": ""high|medium|low""
            }";
            }

            _conversationHistory.Add(ChatMessage.CreateSystemMessage(baseContent));
        }

        /// <summary>
        /// Get a response from the Azure AI model.
        /// </summary>
        /// <param name="userInput">The user's message</param>
        /// <param name="useStreaming">Whether to use streaming responses</param>
        /// <returns>The assistant's response</returns>
        public async Task<string> GetChatResponseAsync(string userInput, bool useStreaming = true)
        {
            try
            {
                // Add user message to history
                _conversationHistory.Add(ChatMessage.CreateUserMessage(userInput));

                if (useStreaming)
                {
                    return await GetStreamingResponseAsync();
                }
                else
                {
                    return await GetStandardResponseAsync();
                }
            }
            catch (Exception ex)
            {
                return $"❌ Error getting response: {ex.Message}";
            }
        }

        /// <summary>
        /// Get a streaming response from the model.
        /// </summary>
        private async Task<string> GetStreamingResponseAsync()
        {
            Console.Write("🤖 Assistant: ");

            var responseContent = new StringBuilder();

            try
            {
                // Create chat completion options
                var options = new ChatCompletionOptions
                {
                    Temperature = 0.7f,
                    MaxOutputTokenCount = 1000
                };

                // Add JSON format if enabled
                if (_jsonMode)
                {
                    options.ResponseFormat = ChatResponseFormat.JsonObject;
                }

                // Create streaming chat completion
                var streamingResponse = _chatClient.CompleteChatStreamingAsync(_conversationHistory, options);

                // Process streaming response
                await foreach (var update in streamingResponse)
                {
                    foreach (var contentPart in update.ContentUpdate)
                    {
                        Console.Write(contentPart.Text);
                        responseContent.Append(contentPart.Text);
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"\n❌ Streaming error: {ex.Message}");
                return await GetStandardResponseAsync();
            }

            Console.WriteLine();  // New line after streaming

            // Add assistant response to history
            var response = responseContent.ToString();
            if (!string.IsNullOrWhiteSpace(response))
            {
                _conversationHistory.Add(ChatMessage.CreateAssistantMessage(response));
            }

            return response;
        }

        /// <summary>
        /// Get a standard (non-streaming) response from the model.
        /// </summary>
        private async Task<string> GetStandardResponseAsync()
        {
            try
            {
                // Create chat completion options
                var options = new ChatCompletionOptions
                {
                    Temperature = 0.7f,
                    MaxOutputTokenCount = 1000
                };

                // Add JSON format if enabled
                if (_jsonMode)
                {
                    options.ResponseFormat = ChatResponseFormat.JsonObject;
                }

                // Create chat completion
                var response = await _chatClient.CompleteChatAsync(_conversationHistory, options);

                if (response.Value.Content.Count > 0)
                {
                    var content = response.Value.Content[0].Text;
                    Console.WriteLine($"🤖 Assistant: {content}");

                    // Add assistant response to history
                    _conversationHistory.Add(ChatMessage.CreateAssistantMessage(content));
                    return content;
                }
                else
                {
                    return "❌ No response received from the model.";
                }
            }
            catch (Exception ex)
            {
                return $"❌ Error getting response: {ex.Message}";
            }
        }

        /// <summary>
        /// Show basic conversation statistics.
        /// </summary>
        public void ShowConversationStats()
        {
            // Exclude system message from count
            var userMessages = _conversationHistory.Count(msg => msg is ChatUserMessage);
            var assistantMessages = _conversationHistory.Count(msg => msg is ChatAssistantMessage);

            Console.WriteLine("\n📊 Conversation Stats:");
            Console.WriteLine($"   User messages: {userMessages}");
            Console.WriteLine($"   Assistant messages: {assistantMessages}");
            Console.WriteLine($"   Total exchanges: {Math.Min(userMessages, assistantMessages)}");
        }

        /// <summary>
        /// Clear conversation history but keep system message.
        /// </summary>
        public void ClearHistory()
        {
            _conversationHistory.Clear();  // Clear all including system message
            SetupSystemMessage();  // Recreate system message with current json_mode
            Console.WriteLine("🧹 Conversation history cleared.");
        }

        /// <summary>
        /// Toggle JSON mode.
        /// </summary>
        public void ToggleJsonMode()
        {
            _jsonMode = !_jsonMode;
            ClearHistory();  // Reset system message with new format
            Console.WriteLine($"🔄 JSON format: {(_jsonMode ? "ON" : "OFF")}");
            Console.WriteLine("   (Conversation history cleared to apply new format)");
        }

        public bool JsonMode => _jsonMode;
    }

    class Program
    {
        static void PrintWelcomeMessage()
        {
            Console.WriteLine("============================================================");
            Console.WriteLine("🤖 AI-3016 Demo 3: Microsoft Foundry SDK Chat Client");
            Console.WriteLine("============================================================");
            Console.WriteLine();
            Console.WriteLine("Welcome to the interactive chat demo using Microsoft Foundry SDK!");
            Console.WriteLine();
            Console.WriteLine("Available commands:");
            Console.WriteLine("  📝 Just type your message to chat");
            Console.WriteLine("  /stats      - Show conversation statistics");
            Console.WriteLine("  /clear      - Clear conversation history");
            Console.WriteLine("  /stream     - Toggle streaming mode");
            Console.WriteLine("  /jsonformat - Toggle JSON response format");
            Console.WriteLine("  /help       - Show this help message");
            Console.WriteLine("  /quit       - Exit the chat");
            Console.WriteLine();
            Console.WriteLine("Try asking: 'What is Microsoft Foundry?' or 'Tell me about AI'");
            Console.WriteLine("------------------------------------------------------------");
        }

        static async Task Main(string[] args)
        {
            // Load .env file if it exists
            LoadEnvironmentVariables();

            PrintWelcomeMessage();

            // Initialize the chat client
            AzureAIFoundryChatClient chatClient;
            try
            {
                chatClient = new AzureAIFoundryChatClient();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Failed to initialize chat client: {ex.Message}");
                return;
            }

            bool streamingMode = true;

            Console.WriteLine($"✨ Chat client ready! (Streaming: {(streamingMode ? "ON" : "OFF")})");
            Console.WriteLine("Type your message or '/help' for commands:");

            try
            {
                while (true)
                {
                    Console.WriteLine();
                    Console.Write("👤 You: ");
                    var userInput = Console.ReadLine()?.Trim();

                    if (string.IsNullOrWhiteSpace(userInput))
                        continue;

                    // Handle special commands
                    switch (userInput.ToLower())
                    {
                        case "/quit":
                        case "/exit":
                        case "/bye":
                            Console.WriteLine("👋 Thanks for using the Microsoft Foundry chat demo!");
                            chatClient.ShowConversationStats();
                            return;

                        case "/help":
                            PrintWelcomeMessage();
                            continue;

                        case "/stats":
                            chatClient.ShowConversationStats();
                            continue;

                        case "/clear":
                            chatClient.ClearHistory();
                            continue;

                        case "/stream":
                            streamingMode = !streamingMode;
                            Console.WriteLine($"🔄 Streaming mode: {(streamingMode ? "ON" : "OFF")}");
                            continue;

                        case "/jsonformat":
                            chatClient.ToggleJsonMode();
                            continue;
                    }

                    // Get and display response
                    var response = await chatClient.GetChatResponseAsync(userInput, streamingMode);

                    if (string.IsNullOrWhiteSpace(response))
                    {
                        Console.WriteLine("❌ No response received. Please try again.");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"\n❌ Unexpected error: {ex.Message}");
            }
        }

        /// <summary>
        /// Load environment variables from .env file if it exists.
        /// </summary>
        static void LoadEnvironmentVariables()
        {
            var envPath = Path.Combine(Directory.GetCurrentDirectory(), ".env");
            if (!File.Exists(envPath))
                return;

            foreach (var line in File.ReadAllLines(envPath))
            {
                var trimmedLine = line.Trim();
                if (string.IsNullOrWhiteSpace(trimmedLine) || trimmedLine.StartsWith("#"))
                    continue;

                var parts = trimmedLine.Split('=', 2);
                if (parts.Length == 2)
                {
                    var key = parts[0].Trim();
                    var value = parts[1].Trim().Trim('"', '\'');
                    Environment.SetEnvironmentVariable(key, value);
                }
            }
        }
    }
}
