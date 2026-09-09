#!/usr/bin/env python3
"""
AI-3016 Demo 3: OpenAI SDK Chat Client for Azure OpenAI

This demo shows how to create a basic chat client using the OpenAI SDK with
an Azure OpenAI-compatible endpoint hosted by the Foundry resource.
Demonstrates:
- OpenAI SDK authentication with an API key or Microsoft Entra ID
- Interactive chat session with conversation history
- Streaming responses for better user experience
- Error handling and connection management
- Clean exit handling

Prerequisites:
- Microsoft Foundry project with GPT-4o deployment
- Valid .env file with Microsoft Foundry credentials

Usage:
    python 3_chat_client_demo.py
"""

import os
import sys
import argparse
from typing import List, Dict, Any
from dotenv import load_dotenv

from azure_openai_auth import create_azure_openai_client

# Load environment variables
load_dotenv()

class AzureAIFoundryChatClient:
    """Simple OpenAI SDK chat client for an Azure-hosted model."""
    
    def __init__(self):
        """Initialize the OpenAI SDK client and local conversation state."""
        self.endpoint_url = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = os.getenv("DEPLOYMENT_NAME") 
        
        # Validate environment variables
        if not all([self.endpoint_url, self.deployment_name]):
            print("❌ Error: Missing required environment variables!")
            print("Please ensure your .env file contains:")
            print("  - AZURE_OPENAI_ENDPOINT")
            print("  - DEPLOYMENT_NAME")
            sys.exit(1)
            
        # Initialize the Azure OpenAI client for the Foundry/AIServices endpoint.
        try:
            self.openai_client = create_azure_openai_client(api_version="2024-05-01-preview")
            
            print("✅ Azure OpenAI client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize client: {e}")
            sys.exit(1)
            
        # Initialize conversation history
        self.conversation_history: List[Dict[str, str]] = []
        self.json_mode = False  # JSON response format toggle
        self.setup_system_message()
        
    def setup_system_message(self):
        """Set up the system message for the chat session."""
        base_content = """You are a helpful AI assistant created using the OpenAI SDK with Azure OpenAI.
            You provide clear, accurate, and helpful responses to user questions. 
            Keep your responses concise but informative. If you don't know something, 
            say so honestly rather than making up information."""
        
        if self.json_mode:
            base_content += """
            
            Always respond with valid JSON in this format:
            {
                "answer": "your detailed response here",
                "confidence": "high|medium|low"
            }"""
        
        system_message = {
            "role": "system", 
            "content": base_content
        }
        self.conversation_history.append(system_message)
        
    def get_chat_response(self, user_input: str, use_streaming: bool = True) -> str:
        """
        Get a response from the Azure AI model.
        
        Args:
            user_input: The user's message
            use_streaming: Whether to use streaming responses
            
        Returns:
            The assistant's response
        """
        try:
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            if use_streaming:
                return self._get_streaming_response()
            else:
                return self._get_standard_response()
                
        except Exception as e:
            return f"❌ Error getting response: {e}"
    
    def _get_streaming_response(self) -> str:
        """Get a streaming response from the model."""
        print("🤖 Assistant: ", end="", flush=True)
        
        response_content = ""
        
        try:
            # Create a streaming Chat Completions request with the OpenAI SDK.
            params = {
                "model": self.deployment_name,
                "messages": self.conversation_history,
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            # Add JSON format if enabled
            if self.json_mode:
                params["response_format"] = {"type": "json_object"}
            
            response = self.openai_client.chat.completions.create(**params)
            
            # Process streaming response
            for chunk in response:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta and hasattr(delta, 'content') and delta.content:
                        content_piece = delta.content
                        print(content_piece, end="", flush=True)
                        response_content += content_piece
                        
        except Exception as e:
            print(f"\n❌ Streaming error: {e}")
            return self._get_standard_response()
            
        print()  # New line after streaming
        
        # Add assistant response to history
        if response_content:
            self.conversation_history.append({"role": "assistant", "content": response_content})
            
        return response_content
    
    def _get_standard_response(self) -> str:
        """Get a standard (non-streaming) response from the model."""
        try:
            # Create a Chat Completions request with the OpenAI SDK.
            params = {
                "model": self.deployment_name,
                "messages": self.conversation_history,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            # Add JSON format if enabled
            if self.json_mode:
                params["response_format"] = {"type": "json_object"}
            
            response = self.openai_client.chat.completions.create(**params)
            
            if response.choices:
                content = response.choices[0].message.content
                print(f"🤖 Assistant: {content}")
                
                # Add assistant response to history
                self.conversation_history.append({"role": "assistant", "content": content})
                return content
            else:
                return "❌ No response received from the model."
                
        except Exception as e:
            return f"❌ Error getting response: {e}"
    
    def show_conversation_stats(self):
        """Show basic conversation statistics."""
        # Exclude system message from count
        user_messages = len([msg for msg in self.conversation_history if msg.get("role") == "user"])
        assistant_messages = len([msg for msg in self.conversation_history if msg.get("role") == "assistant"])
        
        print(f"\n📊 Conversation Stats:")
        print(f"   User messages: {user_messages}")
        print(f"   Assistant messages: {assistant_messages}")
        print(f"   Total exchanges: {min(user_messages, assistant_messages)}")
    
    def show_history(self):
        """Show conversation history in JSON format."""
        import json
        print("\n📜 Conversation History:")
        print(json.dumps(self.conversation_history, indent=2, ensure_ascii=False))
    
    def clear_history(self):
        """Clear conversation history but keep system message."""
        self.conversation_history = []  # Clear all including system message
        self.setup_system_message()  # Recreate system message with current json_mode
        print("🧹 Conversation history cleared.")

def print_welcome_message():
    """Print a welcome message with instructions."""
    print("=" * 60)
    print("🤖 AI-3016 Demo 3: OpenAI SDK Chat Client for Azure OpenAI")
    print("=" * 60)
    print()
    print("Welcome to the interactive chat demo using the OpenAI SDK with Azure OpenAI!")
    print()
    print("Available commands:")
    print("  📝 Just type your message to chat")
    print("  /stats      - Show conversation statistics") 
    print("  /history    - Show conversation history in JSON format")
    print("  /clear      - Clear conversation history")
    print("  /stream     - Toggle streaming mode")
    print("  /jsonformat - Toggle JSON response format")
    print("  /help       - Show this help message")
    print("  /quit       - Exit the chat")
    print()
    print("Try asking: 'What is Microsoft Foundry?' or 'Tell me about AI'")
    print("-" * 60)

def main():
    """Main chat application loop."""
    parser = argparse.ArgumentParser(description="AI-3016 Microsoft Foundry chat client")
    parser.add_argument("--once", help="Send one prompt and exit; useful for smoke tests")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming responses")
    args = parser.parse_args()

    print_welcome_message()
    
    # Initialize the chat client
    try:
        chat_client = AzureAIFoundryChatClient()
    except SystemExit:
        return
    except Exception as e:
        print(f"❌ Failed to initialize chat client: {e}")
        return
    
    streaming_mode = not args.no_stream
    if args.once:
        chat_client.get_chat_response(args.once, use_streaming=streaming_mode)
        chat_client.show_conversation_stats()
        return
    
    print(f"✨ Chat client ready! (Streaming: {'ON' if streaming_mode else 'OFF'})")
    print("Type your message or '/help' for commands:")
    
    try:
        while True:
            print()
            user_input = input("👤 You: ").strip()
            
            if not user_input:
                continue
                
            # Handle special commands
            if user_input.lower() in ['/quit', '/exit', '/bye']:
                print("👋 Thanks for using the Microsoft Foundry chat demo!")
                chat_client.show_conversation_stats()
                break
                
            elif user_input.lower() == '/help':
                print_welcome_message()
                continue
                
            elif user_input.lower() == '/stats':
                chat_client.show_conversation_stats()
                continue
                
            elif user_input.lower() == '/history':
                chat_client.show_history()
                continue
                
            elif user_input.lower() == '/clear':
                chat_client.clear_history()
                continue
                
            elif user_input.lower() == '/stream':
                streaming_mode = not streaming_mode
                print(f"🔄 Streaming mode: {'ON' if streaming_mode else 'OFF'}")
                continue
                
            elif user_input.lower() == '/jsonformat':
                chat_client.json_mode = not chat_client.json_mode
                chat_client.clear_history()  # Reset system message with new format
                print(f"🔄 JSON format: {'ON' if chat_client.json_mode else 'OFF'}")
                print("   (Conversation history cleared to apply new format)")
                continue
            
            # Get and display response
            response = chat_client.get_chat_response(user_input, use_streaming=streaming_mode)
            
            if not response:
                print("❌ No response received. Please try again.")
                
    except KeyboardInterrupt:
        print("\n\n👋 Chat interrupted. Thanks for using the demo!")
        chat_client.show_conversation_stats()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()