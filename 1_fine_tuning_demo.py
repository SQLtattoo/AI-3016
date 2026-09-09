"""
AI-3016 Demo 1: Fine-tuning GPT-4o with Microsoft Foundry
=====================================================

This demo shows how to:
1. Prepare training data for fine-tuning
2. Upload datasets to Microsoft Foundry
3. Create and monitor a fine-tuning job
4. Test the fine-tuned model

Prerequisites:
- Microsoft Foundry project with deployed GPT-4o model
- Training and validation datasets (already created)
- Azure AI SDK installed
"""

import os
import json
import time
import argparse
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

load_dotenv()

class FineTuningDemo:
    def __init__(self):
        # Microsoft Foundry configuration
        self.project_scope = {
            "subscription_id": os.getenv("AZURE_SUBSCRIPTION_ID"),
            "resource_group_name": os.getenv("AZURE_RESOURCE_GROUP"),
            "project_name": os.getenv("AZURE_AI_PROJECT_NAME")
        }
        
        # Initialize AI Project Client
        self.ai_client = AIProjectClient(
            credential=DefaultAzureCredential(),
            **self.project_scope
        )
        
        # Model configuration
        self.base_model = "gpt-4o"  # Base model to fine-tune
        self.fine_tuned_model_name = "al-zahra-bank-assistant"
        
    def validate_datasets(self):
        """Validate training and validation datasets format"""
        print("🔍 Validating datasets...")
        
        datasets = ["training_data.jsonl", "validation_data.jsonl"]
        for dataset in datasets:
            if not os.path.exists(dataset):
                raise FileNotFoundError(f"Dataset {dataset} not found!")
                
            with open(dataset, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"✅ {dataset}: {len(lines)} examples")
                
                # Validate first example
                first_example = json.loads(lines[0])
                required_keys = ["messages"]
                if not all(key in first_example for key in required_keys):
                    raise ValueError(f"Invalid format in {dataset}")
                    
                # Check message structure
                messages = first_example["messages"]
                if len(messages) != 3:  # system, user, assistant
                    raise ValueError(f"Expected 3 messages, got {len(messages)}")
                    
                roles = [msg["role"] for msg in messages]
                if roles != ["system", "user", "assistant"]:
                    raise ValueError(f"Invalid message roles: {roles}")
                    
        print("✅ All datasets validated successfully!")
        
    def upload_datasets(self):
        """Upload training datasets to Microsoft Foundry"""
        print("📤 Uploading datasets to Microsoft Foundry...")
        
        # Upload training data
        training_data = self.ai_client.data.upload(
            name="al-zahra-training-data",
            path="training_data.jsonl",
            description="Training data for BankOne Bank assistant fine-tuning"
        )
        print(f"✅ Training data uploaded: {training_data.id}")
        
        # Upload validation data
        validation_data = self.ai_client.data.upload(
            name="al-zahra-validation-data", 
            path="validation_data.jsonl",
            description="Validation data for BankOne Bank assistant fine-tuning"
        )
        print(f"✅ Validation data uploaded: {validation_data.id}")
        
        return training_data.id, validation_data.id
        
    def create_fine_tuning_job(self, training_data_id, validation_data_id):
        """Create and start fine-tuning job"""
        print("🚀 Creating fine-tuning job...")
        
        fine_tune_job = self.ai_client.fine_tuning.jobs.create(
            model=self.base_model,
            training_file=training_data_id,
            validation_file=validation_data_id,
            suffix=self.fine_tuned_model_name,
            hyperparameters={
                "n_epochs": 3,  # Number of training epochs
                "batch_size": 1,  # Batch size for training
                "learning_rate_multiplier": 0.1  # Learning rate multiplier
            }
        )
        
        print(f"✅ Fine-tuning job created: {fine_tune_job.id}")
        print(f"📊 Status: {fine_tune_job.status}")
        
        return fine_tune_job.id
        
    def monitor_fine_tuning_job(self, job_id):
        """Monitor fine-tuning job progress"""
        print("👀 Monitoring fine-tuning job...")
        
        while True:
            job = self.ai_client.fine_tuning.jobs.get(job_id)
            print(f"🔄 Status: {job.status}")
            
            if job.status == "succeeded":
                print("🎉 Fine-tuning completed successfully!")
                print(f"🏷️  Fine-tuned model: {job.fine_tuned_model}")
                return job.fine_tuned_model
                
            elif job.status == "failed":
                print("❌ Fine-tuning failed!")
                if hasattr(job, 'error'):
                    print(f"Error: {job.error}")
                return None
                
            elif job.status in ["cancelled", "canceled"]:
                print("⏹️  Fine-tuning was cancelled!")
                return None
                
            print("⏳ Waiting 30 seconds before checking again...")
            time.sleep(30)
            
    def test_base_model(self):
        """Test the base model for comparison"""
        print("🧪 Testing base model...")
        
        # Use your deployed GPT-4o endpoint
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        client = ChatCompletionsClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
        
        test_query = "What is the minimum investment for your exclusive portfolio service?"
        
        response = client.complete(
            messages=[
                SystemMessage("You are an AI assistant for BankOne Private Bank in Abu Dhabi. Provide discreet, professional advice on investments and loans for high-net-worth clients."),
                UserMessage(test_query)
            ],
            model=self.base_model,
            temperature=0.7
        )
        
        print(f"🤖 Base model response:")
        print(f"Q: {test_query}")
        print(f"A: {response.choices[0].message.content}")
        print("-" * 50)
        
    def test_fine_tuned_model(self, fine_tuned_model_id):
        """Test the fine-tuned model"""
        print("🎯 Testing fine-tuned model...")
        
        # Deploy the fine-tuned model first
        deployment = self.ai_client.deployments.create(
            name=f"{self.fine_tuned_model_name}-deployment",
            model=fine_tuned_model_id,
            sku={
                "name": "Standard",
                "capacity": 1
            }
        )
        
        print(f"🚀 Model deployed: {deployment.endpoint_url}")
        
        # Test the fine-tuned model
        client = ChatCompletionsClient(
            endpoint=deployment.endpoint_url,
            credential=DefaultAzureCredential()
        )
        
        test_queries = [
            "What is the minimum investment for your exclusive portfolio service?",
            "Do you offer Sharia-compliant investment options?",
            "Can I get a loan secured against my art collection?"
        ]
        
        for query in test_queries:
            response = client.complete(
                messages=[
                    SystemMessage("You are an AI assistant for BankOne Private Bank in Abu Dhabi. Provide discreet, professional advice on investments and loans for high-net-worth clients."),
                    UserMessage(query)
                ],
                model=fine_tuned_model_id,
                temperature=0.7
            )
            
            print(f"🎯 Fine-tuned model response:")
            print(f"Q: {query}")
            print(f"A: {response.choices[0].message.content}")
            print("-" * 50)
            
    def run_demo(self):
        """Run the complete fine-tuning demo"""
        print("🎬 Starting Fine-tuning Demo for AI-3016")
        print("=" * 60)
        
        try:
            # Step 1: Validate datasets
            self.validate_datasets()
            
            # Step 2: Upload datasets
            training_id, validation_id = self.upload_datasets()
            
            # Step 3: Test base model first
            self.test_base_model()
            
            # Step 4: Create fine-tuning job
            job_id = self.create_fine_tuning_job(training_id, validation_id)
            
            # Step 5: Monitor job
            fine_tuned_model = self.monitor_fine_tuning_job(job_id)
            
            if fine_tuned_model:
                # Step 6: Test fine-tuned model
                self.test_fine_tuned_model(fine_tuned_model)
                
                print("🎉 Fine-tuning demo completed successfully!")
                print(f"📝 Your fine-tuned model: {fine_tuned_model}")
            else:
                print("❌ Fine-tuning demo failed!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Legacy AI-3016 fine-tuning workflow demo")
    parser.add_argument("--dry-run", action="store_true", help="Validate datasets and explain the workflow without uploading files or creating a job")
    args = parser.parse_args()

    if args.dry_run:
        print("🎬 AI-3016 Demo 1: Fine-tuning workflow dry run")
        print("=" * 60)
        for dataset in ["training_data.jsonl", "validation_data.jsonl"]:
            with open(dataset, "r", encoding="utf-8") as file:
                rows = [json.loads(line) for line in file]
            print(f"✅ {dataset}: {len(rows)} JSONL training examples")
        print("✅ No files uploaded and no fine-tuning job started")
        print("Use 1a_fine_tuning_portal_guide.md for the live portal workflow or 1b_fine_tuning_code_first.py --dry-run for code-first narration.")
        exit(0)

    # Set up environment variables (you'll need to provide these)
    required_env_vars = [
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_RESOURCE_GROUP", 
        "AZURE_AI_PROJECT_NAME",
        "AZURE_OPENAI_ENDPOINT"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Please set these environment variables before running the demo.")
        exit(1)
    
    # Run the demo
    demo = FineTuningDemo()
    demo.run_demo()