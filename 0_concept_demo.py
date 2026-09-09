"""
AI-3016 Simplified Demo - Concept Overview
=========================================

This script demonstrates the core concepts of fine-tuning and RAG patterns
without requiring full Azure setup. Perfect for classroom presentations!
"""

import json
import random
from typing import List, Dict

class ConceptDemo:
    def __init__(self):
        self.fine_tuning_data = self.load_training_data()
        self.knowledge_base = self.create_knowledge_base()
        
    def load_training_data(self) -> List[Dict]:
        """Load and display training data format"""
        try:
            with open("training_data.jsonl", "r", encoding="utf-8") as f:
                data = [json.loads(line) for line in f.readlines()[:5]]  # First 5 examples
            return data
        except FileNotFoundError:
            # Fallback sample data with multi-turn conversation
            return [
                {
                    "messages": [
                        {"role": "system", "content": "You are an AI assistant for BankOne Private Bank.", "weight": 0.1},
                        {"role": "user", "content": "Can I use my art collection as collateral?", "weight": 0.5},
                        {"role": "assistant", "content": "Yes, we specialize in asset-backed lending using fine art. What type of artwork do you have?", "weight": 1.0},
                        {"role": "user", "content": "I have a Picasso and contemporary works worth about 12 million.", "weight": 0.5},
                        {"role": "assistant", "content": "Excellent collection. We typically offer 50-60% loan-to-value ratios for pieces of this caliber.", "weight": 1.0}
                    ]
                },
                {
                    "messages": [
                        {"role": "system", "content": "You are an AI assistant for BankOne Private Bank.", "weight": 0.1},
                        {"role": "user", "content": "What is the minimum investment for your portfolio service?", "weight": 0.5},
                        {"role": "assistant", "content": "Our exclusive portfolio service starts at USD 5 million.", "weight": 1.0}
                    ]
                }
            ]
    
    def create_knowledge_base(self) -> List[Dict]:
        """Create sample knowledge base for RAG demo"""
        return [
            {
                "id": "1",
                "title": "Investment Portfolio Services",
                "content": "BankOne Private Bank offers exclusive portfolio management with USD 5 million minimum investment.",
                "category": "investments"
            },
            {
                "id": "2", 
                "title": "Sharia-Compliant Investments",
                "content": "We provide comprehensive Islamic banking solutions that adhere to Sharia principles.",
                "category": "islamic-banking"
            },
            {
                "id": "3",
                "title": "Asset-Backed Lending",
                "content": "We offer loans secured by fine art, yachts, and other luxury assets with flexible terms.",
                "category": "loans"
            }
        ]
    
    def demo_fine_tuning_concept(self):
        """Demonstrate fine-tuning concepts"""
        print("🎯 DEMO 1: Fine-tuning Concepts")
        print("=" * 50)
        
        print("📚 What is Fine-tuning?")
        print("   • Adapting model behavior with representative examples")
        print("   • Teaching consistent tone, format, and task behavior")
        print("   • Not a replacement for retrieving current or authoritative facts")
        
        print("\n📊 Training Data Format:")
        # Show both single-turn and multi-turn examples
        single_turn = None
        multi_turn = None
        
        for sample in self.fine_tuning_data:
            if len(sample["messages"]) == 3:  # Single-turn
                single_turn = sample
            elif len(sample["messages"]) > 3:  # Multi-turn
                multi_turn = sample
            
            if single_turn and multi_turn:
                break
        
        if single_turn:
            print("\n📋 Single-turn Example:")
            print(json.dumps(single_turn, indent=2)[:500] + "...")
            
        if multi_turn:
            print("\n🔄 Multi-turn Example:")
            print(json.dumps(multi_turn, indent=2)[:700] + "...")
        
        print(f"\n📈 Dataset Stats:")
        print(f"   • Training examples: {len(self.fine_tuning_data)}")
        print(f"   • Format: JSONL (JSON Lines)")
        print(f"   • Message types: Single-turn + Multi-turn conversations")
        print(f"   • Message weights: System (0.1), User (0.5), Assistant (1.0)")
        
        print("\n🔄 Fine-tuning Process:")
        steps = [
            "1. Prepare mixed single/multi-turn training data",
            "2. Add message weights to emphasize assistant learning", 
            "3. Upload datasets to Microsoft Foundry",
            "4. Create fine-tuning job with hyperparameters",
            "5. Monitor training progress and validation metrics",
            "6. Deploy the fine-tuned model",
            "7. Compare behavior and format consistency with the base model"
        ]
        for step in steps:
            print(f"   {step}")
            
        print("\n✨ Enhanced Benefits:")
        benefits = [
            "• More consistent responses for trained interaction patterns",
            "• Weighted learning focuses on assistant responses",
            "• More consistent tone and response structure",
            "• Better performance on represented tasks",
            "• Less repeated prompt instruction for learned behavior"
        ]
        for benefit in benefits:
            print(f"   {benefit}")
            
        print("\n🎯 Message Weight Strategy:")
        print("   • System messages (weight 0.1): Minimal learning impact")
        print("   • User messages (weight 0.5): Context understanding")  
        print("   • Assistant messages (weight 1.0): Primary learning focus")
        print("   • Result: Model learns to generate better responses while understanding context")
    
    def demo_rag_concept(self):
        """Demonstrate RAG pattern concepts"""
        print("\n🔍 DEMO 2: RAG Pattern Concepts")
        print("=" * 50)
        
        print("📚 What is RAG (Retrieval-Augmented Generation)?")
        print("   • Combines retrieval of relevant documents with LLM generation")
        print("   • Grounds answers in indexed domain-specific information")
        print("   • Can enable source attribution and easier fact-checking")
        
        print("\n🏗️ RAG Architecture:")
        architecture = [
            "Documents → Chunking → Embeddings → Vector Store",
            "User Query → Search → Retrieved Context → LLM → Response"
        ]
        for step in architecture:
            print(f"   {step}")
        
        print("\n📄 Knowledge Base Sample:")
        for doc in self.knowledge_base:
            print(f"   • {doc['title']} ({doc['category']})")
        
        print(f"\n🔍 Simulated Search Process:")
        query = "What is the minimum investment?"
        print(f"   Query: '{query}'")
        print(f"   🎯 Best Match: Investment Portfolio Services")
        print(f"   📊 Relevance Score: 0.89")
        
        print("\n💬 Response Comparison:")
        print("   🤖 Without RAG (Generic):")
        print("   'Investment minimums vary by institution and product type...'")
        
        print("\n   📚 With RAG (Specific):")
        print("   'Our exclusive portfolio service starts at USD 5 million...'")
        
        print("\n✨ RAG Benefits:")
        benefits = [
            "• Better grounding in retrieved knowledge-base content",
            "• Update indexed information without retraining the model",
            "• Source attribution when the application surfaces citations",
            "• Reduced hallucination risk, not a guarantee of accuracy"
        ]
        for benefit in benefits:
            print(f"   {benefit}")
    
    def demo_comparison(self):
        """Compare fine-tuning vs RAG"""
        print("\n⚖️  Fine-tuning vs RAG Comparison")
        print("=" * 50)
        
        comparison = {
            "Use Case": {
                "Fine-tuning": "Consistent behavior, style, and format",
                "RAG": "Retrieval of domain-specific or current facts"
            },
            "Data Requirements": {
                "Fine-tuning": "Representative prompt/response examples",
                "RAG": "Indexed knowledge documents or data"
            },
            "Update Frequency": {
                "Fine-tuning": "Retrain when learned behavior must change",
                "RAG": "Refresh the index when source information changes"
            },
            "Cost": {
                "Fine-tuning": "Training, hosting, and inference costs",
                "RAG": "Indexing, search, embedding, and inference costs"
            },
            "Latency": {
                "Fine-tuning": "Fast (direct model inference)",
                "RAG": "Slower (search + generation)"
            },
            "Transparency": {
                "Fine-tuning": "No source evidence added at inference time",
                "RAG": "Can be traced when retrieved sources are exposed"
            }
        }
        
        for aspect, values in comparison.items():
            print(f"\n📊 {aspect}:")
            print(f"   🎯 Fine-tuning: {values['Fine-tuning']}")
            print(f"   🔍 RAG: {values['RAG']}")
    
    def demo_azure_services(self):
        """Overview of Azure services used"""
        print("\n☁️  Azure Services Overview")
        print("=" * 50)
        
        services = {
            "Microsoft Foundry": {
                "Purpose": "Model deployment, fine-tuning orchestration",
                "Features": ["Model catalog", "Fine-tuning jobs", "Deployment endpoints", "Monitoring"]
            },
            "Azure OpenAI": {
                "Purpose": "Access to GPT models and embeddings",
                "Models": ["GPT-4o (chat)", "text-embedding-ada-002", "Other foundation models"]
            },
            "Azure AI Search": {
                "Purpose": "Vector search and hybrid retrieval",
                "Features": ["Vector indexing", "Semantic search", "Hybrid queries", "Faceted search"]
            },
            "Azure Storage": {
                "Purpose": "Dataset and document storage",
                "Features": ["Blob storage", "Data versioning", "Secure access"]
            }
        }
        
        for service, details in services.items():
            print(f"\n🔧 {service}:")
            print(f"   Purpose: {details['Purpose']}")
            if 'Features' in details:
                print(f"   Features: {', '.join(details['Features'])}")
            if 'Models' in details:
                print(f"   Models: {', '.join(details['Models'])}")
    
    def run_demo(self):
        """Run the complete concept demo"""
        print("🎬 AI-3016 Concept Demo")
        print("Develop Generative AI Apps in Azure")
        print("=" * 60)
        
        self.demo_fine_tuning_concept()
        self.demo_rag_concept()
        self.demo_comparison()
        self.demo_azure_services()
        
        print("\n🎓 Next Steps:")
        print("   1. Set up Microsoft Foundry project")
        print("   2. Deploy required models (GPT-4o, embeddings)")
        print("   3. Run full demos with Azure integration")
        print("   4. Experiment with your own datasets")
        
        print("\n🎉 Demo completed! Ready for hands-on Azure development!")

if __name__ == "__main__":
    demo = ConceptDemo()
    demo.run_demo()