#!/usr/bin/env python3
"""
AI-3016 Demo 1B: Fine-tuning GPT-4o via Code (Automated)

⏱️ Demo Duration: 20 minutes
🎯 Audience: Developer-focused students
🚀 Environment: Programmatic Azure OpenAI interaction

This script demonstrates the complete fine-tuning workflow using the OpenAI SDK
with an Azure OpenAI endpoint.
Designed to complement the portal-guided demo (1a_fine_tuning_portal_guide.md).
"""

import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# OpenAI SDK and shared Azure authentication helper
import requests
from dotenv import load_dotenv
from azure_openai_auth import create_azure_openai_client

# Configuration and utilities
import logging

load_dotenv()

# Configure logging for demo visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FineTuningDemo:
    """
    Automated fine-tuning demonstration class.
    
    This class encapsulates the entire fine-tuning workflow:
    1. Environment setup and validation
    2. Data upload and validation
    3. Fine-tuning job creation and monitoring
    4. Model deployment and testing
    """
    
    def __init__(self, student_initials: str = "demo"):
        """Initialize the fine-tuning demo with student-specific naming."""
        self.student_initials = student_initials
        self.timestamp = datetime.now().strftime("%m%d")
        
        # Resource naming (matches portal guide conventions)
        self.job_name = f"{student_initials}-bank-ft-{self.timestamp}"
        self.model_name = f"{student_initials}-bank-assistant-v1"
        
        # Azure OpenAI configuration
        self.client = None
        self.training_file_id = None
        self.validation_file_id = None
        self.fine_tuned_model = None
        
        # Demo tracking
        self.demo_start_time = time.time()
        self.demo_steps = []
        
    def setup_azure_client(self) -> bool:
        """
        Step 1: Initialize Azure OpenAI client with environment variables.
        
        Expected environment variables:
        - AZURE_OPENAI_ENDPOINT
        - AZURE_OPENAI_API_KEY
        - AZURE_OPENAI_API_VERSION (default: 2024-05-01-preview)
        """
        logger.info("🔧 Setting up Azure OpenAI client...")
        
        try:
            # Get configuration from environment
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
            
            if not os.getenv("AZURE_OPENAI_ENDPOINT"):
                logger.error("❌ Missing required environment variable: AZURE_OPENAI_ENDPOINT")
                return False
            
            self.client = create_azure_openai_client(api_version=api_version)
            logger.info(f"✅ Connected to Azure OpenAI successfully!")
            
            self._add_demo_step("Azure OpenAI client setup", "✅ Success")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup Azure OpenAI client: {str(e)}")
            self._add_demo_step("Azure OpenAI client setup", f"❌ Failed: {str(e)}")
            return False
    
    def upload_training_data(self) -> bool:
        """
        Step 2: Upload training and validation datasets.
        
        Uploads the JSONL files created by bank-dataset-generator.py
        """
        logger.info("📤 Uploading training datasets...")
        
        try:
            # Check if data files exist
            training_file = Path("training_data.jsonl")
            validation_file = Path("validation_data.jsonl")
            
            if not training_file.exists():
                logger.error("❌ training_data.jsonl not found!")
                logger.error("   Run: python bank-dataset-generator.py first")
                return False
                
            if not validation_file.exists():
                logger.error("❌ validation_data.jsonl not found!")
                return False
            
            # Upload training data
            logger.info("   Uploading training_data.jsonl...")
            with open(training_file, 'rb') as f:
                training_response = self.client.files.create(
                    file=f,
                    purpose="fine-tune"
                )
            self.training_file_id = training_response.id
            logger.info(f"   ✅ Training file uploaded: {self.training_file_id}")
            
            # Upload validation data
            logger.info("   Uploading validation_data.jsonl...")
            with open(validation_file, 'rb') as f:
                validation_response = self.client.files.create(
                    file=f,
                    purpose="fine-tune"
                )
            self.validation_file_id = validation_response.id
            logger.info(f"   ✅ Validation file uploaded: {self.validation_file_id}")
            
            # Validate file uploads
            self._validate_uploaded_files()
            
            self._add_demo_step("Data upload", "✅ Training and validation files uploaded")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload training data: {str(e)}")
            self._add_demo_step("Data upload", f"❌ Failed: {str(e)}")
            return False
    
    def _validate_uploaded_files(self):
        """Validate uploaded files and show sample data."""
        try:
            # Get file info
            training_info = self.client.files.retrieve(self.training_file_id)
            validation_info = self.client.files.retrieve(self.validation_file_id)
            
            logger.info(f"   📊 Training file: {training_info.bytes} bytes, status: {training_info.status}")
            logger.info(f"   📊 Validation file: {validation_info.bytes} bytes, status: {validation_info.status}")
            
            # Show sample training data
            with open("training_data.jsonl", 'r', encoding='utf-8') as f:
                first_line = f.readline()
                sample_data = json.loads(first_line)
                
            logger.info("   📝 Sample training data structure:")
            logger.info(f"      Messages: {len(sample_data.get('messages', []))}")
            if sample_data.get('messages'):
                for msg in sample_data['messages'][:2]:  # Show first 2 messages
                    logger.info(f"      - {msg['role']}: {msg['content'][:50]}...")
                    
        except Exception as e:
            logger.warning(f"⚠️ Could not validate files: {str(e)}")
    
    def create_fine_tuning_job(self) -> bool:
        """
        Step 3: Create and configure fine-tuning job.
        
        Uses conservative hyperparameters suitable for demonstration.
        """
        logger.info("🚀 Creating fine-tuning job...")
        
        try:
            # Fine-tuning job configuration
            job_config = {
                "training_file": self.training_file_id,
                "validation_file": self.validation_file_id,
                "model": "gpt-4o-2024-08-06",  # Latest fine-tunable GPT-4o
                "suffix": f"{self.student_initials}-bank-assistant",
                "hyperparameters": {
                    "n_epochs": 3,           # Conservative for demo
                    "batch_size": 1,         # Stable learning
                    "learning_rate_multiplier": 0.1  # Safe learning rate
                }
            }
            
            logger.info("   📋 Job configuration:")
            logger.info(f"      Model: {job_config['model']}")
            logger.info(f"      Epochs: {job_config['hyperparameters']['n_epochs']}")
            logger.info(f"      Batch size: {job_config['hyperparameters']['batch_size']}")
            logger.info(f"      Learning rate: {job_config['hyperparameters']['learning_rate_multiplier']}")
            
            # Create fine-tuning job
            job_response = self.client.fine_tuning.jobs.create(**job_config)
            
            self.job_id = job_response.id
            logger.info(f"   ✅ Fine-tuning job created: {self.job_id}")
            logger.info(f"   🎯 Job status: {job_response.status}")
            
            self._add_demo_step("Fine-tuning job creation", f"✅ Job ID: {self.job_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create fine-tuning job: {str(e)}")
            self._add_demo_step("Fine-tuning job creation", f"❌ Failed: {str(e)}")
            return False
    
    def monitor_training_progress(self, max_wait_minutes: int = 5) -> bool:
        """
        Step 4: Monitor fine-tuning job progress.
        
        For demo purposes, we'll monitor for a limited time then explain the process.
        """
        logger.info("📊 Monitoring training progress...")
        
        try:
            start_time = time.time()
            max_wait_seconds = max_wait_minutes * 60
            
            while time.time() - start_time < max_wait_seconds:
                # Get job status
                job_status = self.client.fine_tuning.jobs.retrieve(self.job_id)
                
                logger.info(f"   🔄 Status: {job_status.status}")
                
                if job_status.status == "succeeded":
                    self.fine_tuned_model = job_status.fine_tuned_model
                    logger.info(f"   🎉 Training completed! Model: {self.fine_tuned_model}")
                    self._add_demo_step("Training monitoring", "✅ Training completed successfully")
                    return True
                    
                elif job_status.status == "failed":
                    logger.error(f"   ❌ Training failed: {job_status.error}")
                    self._add_demo_step("Training monitoring", f"❌ Training failed: {job_status.error}")
                    return False
                    
                elif job_status.status in ["validating_files", "queued", "running"]:
                    # Show progress information
                    if hasattr(job_status, 'trained_tokens') and job_status.trained_tokens:
                        logger.info(f"   📈 Trained tokens: {job_status.trained_tokens}")
                    
                    # Wait before next check
                    time.sleep(30)
                    
                else:
                    logger.info(f"   ⏳ Current status: {job_status.status}")
                    time.sleep(30)
            
            # Time limit reached - explain what would happen
            logger.info(f"   ⏰ Demo time limit reached ({max_wait_minutes} minutes)")
            logger.info("   🎓 In production, training typically takes 10-30 minutes")
            logger.info("   📧 You would receive email notification when complete")
            
            self._add_demo_step("Training monitoring", f"⏰ Demo time limit reached - training continues")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error monitoring training: {str(e)}")
            self._add_demo_step("Training monitoring", f"❌ Error: {str(e)}")
            return False
    
    def demonstrate_model_comparison(self):
        """
        Step 5: Compare base model vs fine-tuned model responses.
        
        For demo purposes, we'll simulate responses if fine-tuning isn't complete.
        """
        logger.info("🔍 Demonstrating model comparison...")
        
        # Test queries for banking domain
        test_queries = [
            "What are the wire transfer limits for my account?",
            "How do I set up overdraft protection?",
            "Tell me about your CD rates and terms."
        ]
        
        logger.info("   📝 Test queries for banking assistant:")
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"\n   🤔 Query {i}: {query}")
            
            # Base model response (simulated for demo)
            logger.info("   📄 Base GPT-4o response:")
            logger.info("      'I can help with general banking questions, but I don't have")
            logger.info("       specific information about your bank's policies or current rates.'")
            
            # Fine-tuned model response (simulated or actual)
            logger.info("   🎯 Fine-tuned banking assistant response:")
            if self.fine_tuned_model:
                # Actual fine-tuned model call would go here
                logger.info("      [Would call fine-tuned model with banking-specific knowledge]")
            else:
                # Simulated response based on training data
                if "wire transfer" in query.lower():
                    logger.info("      'For wire transfers, domestic limits are $25,000 per day")
                    logger.info("       and international limits are $15,000 per day. Additional")
                    logger.info("       verification is required for amounts over $10,000.'")
                elif "overdraft" in query.lower():
                    logger.info("      'Overdraft protection automatically transfers from your")
                    logger.info("       savings to checking account with a $5 fee per transfer.")
                    logger.info("       You need to maintain a $50 minimum in savings.'")
                elif "cd" in query.lower() or "certificate" in query.lower():
                    logger.info("      'Our CDs offer terms from 3 to 36 months with rates")
                    logger.info("       from 3.5% to 4.2% APY. Minimum deposit is $1,000")
                    logger.info("       with early withdrawal penalties.'")
        
        self._add_demo_step("Model comparison", "✅ Demonstrated base vs fine-tuned responses")
    
    def explain_production_deployment(self):
        """
        Step 6: Explain production deployment considerations.
        """
        logger.info("🏭 Production deployment considerations...")
        
        production_topics = [
            ("Model Deployment", [
                "Deploy fine-tuned model to dedicated endpoint",
                "Configure auto-scaling based on usage",
                "Set up monitoring and alerting",
                "Implement A/B testing framework"
            ]),
            ("Performance Monitoring", [
                "Track response quality metrics",
                "Monitor latency and throughput",
                "Set up cost tracking and budgets",
                "Implement feedback collection system"
            ]),
            ("Continuous Improvement", [
                "Regular model evaluation and updates",
                "Incremental training with new data",
                "Version management and rollback procedures",
                "User feedback integration"
            ]),
            ("Security & Compliance", [
                "Implement proper authentication",
                "Set up data privacy controls",
                "Ensure regulatory compliance",
                "Regular security audits"
            ])
        ]
        
        for topic, items in production_topics:
            logger.info(f"\n   🎯 {topic}:")
            for item in items:
                logger.info(f"      • {item}")
        
        self._add_demo_step("Production deployment", "✅ Explained deployment considerations")
    
    def cleanup_demo_resources(self):
        """Clean up demo resources to manage costs."""
        logger.info("🧹 Cleanup recommendations...")
        
        cleanup_items = [
            "Delete fine-tuning job if not needed",
            "Remove uploaded training files",
            "Undeploy test endpoints",
            "Archive successful models for future use"
        ]
        
        for item in cleanup_items:
            logger.info(f"   • {item}")
        
        logger.info("\n   💡 Cost management tips:")
        logger.info("      • Fine-tuning costs ~$2-5 per job")
        logger.info("      • Inference costs ~$0.01 per 1K tokens")
        logger.info("      • Delete unused resources promptly")
        
        self._add_demo_step("Cleanup", "✅ Cleanup recommendations provided")
    
    def _add_demo_step(self, step_name: str, result: str):
        """Track demo steps for summary."""
        elapsed = time.time() - self.demo_start_time
        self.demo_steps.append({
            "step": step_name,
            "result": result,
            "elapsed_minutes": round(elapsed / 60, 1)
        })
    
    def print_demo_summary(self):
        """Print a comprehensive demo summary."""
        total_time = time.time() - self.demo_start_time
        
        logger.info("\n" + "="*60)
        logger.info("📋 FINE-TUNING DEMO SUMMARY")
        logger.info("="*60)
        
        logger.info(f"🎯 Student: {self.student_initials}")
        logger.info(f"⏱️ Total demo time: {total_time/60:.1f} minutes")
        logger.info(f"🏷️ Model name: {self.model_name}")
        
        logger.info("\n📊 Demo Steps Completed:")
        for step in self.demo_steps:
            logger.info(f"   {step['elapsed_minutes']:4.1f}min - {step['step']}: {step['result']}")
        
        logger.info("\n🎓 Key Learning Points:")
        learning_points = [
            "✅ Fine-tuning workflow from data to deployment",
            "✅ Hyperparameter configuration and impact",
            "✅ Training monitoring and progress tracking",
            "✅ Model comparison and evaluation techniques",
            "✅ Production deployment considerations",
            "✅ Cost management and cleanup procedures"
        ]
        
        for point in learning_points:
            logger.info(f"   {point}")
        
        logger.info("\n🔗 Related Files:")
        logger.info("   • training_data.jsonl - Multi-turn conversation training data")
        logger.info("   • validation_data.jsonl - Validation dataset")
        logger.info("   • 1a_fine_tuning_portal_guide.md - Portal version of this demo")
        logger.info("   • bank-dataset-generator.py - Training data generator")

def main():
    """
    Main demo execution function.
    
    This function runs the complete fine-tuning demonstration workflow.
    Perfect for 20-minute classroom demonstration.
    """
    print("🚀 AI-3016 Demo 1B: Fine-tuning GPT-4o via Code")
    print("=" * 50)
    print("⏱️ Estimated demo time: 20 minutes")
    print("🎯 Focus: Automated fine-tuning workflow")
    print()
    
    parser = argparse.ArgumentParser(description="AI-3016 code-first fine-tuning demo")
    parser.add_argument("--initials", default="demo", help="Initials for resource naming")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup and explain workflow without uploading data or starting fine-tuning")
    args = parser.parse_args()

    student_initials = args.initials.strip().lower()
    if not student_initials:
        student_initials = "demo"
    
    # Initialize demo
    demo = FineTuningDemo(student_initials)
    
    try:
        # Execute demo workflow
        logger.info("🎬 Starting fine-tuning demo workflow...")
        
        # Step 1: Setup Azure client
        if not demo.setup_azure_client():
            logger.error("❌ Cannot proceed without Azure OpenAI connection")
            return

        if args.dry_run:
            demo._add_demo_step("Dry-run mode", "✅ No files uploaded and no fine-tuning job started")
            if not Path("training_data.jsonl").exists() or not Path("validation_data.jsonl").exists():
                logger.error("❌ Training or validation data file is missing")
                return
            demo.demonstrate_model_comparison()
            demo.explain_production_deployment()
            demo.cleanup_demo_resources()
            demo.print_demo_summary()
            logger.info("\n✅ Fine-tuning dry run completed successfully")
            return
        
        # Step 2: Upload training data
        if not demo.upload_training_data():
            logger.error("❌ Cannot proceed without training data")
            return
        
        # Step 3: Create fine-tuning job
        if not demo.create_fine_tuning_job():
            logger.error("❌ Cannot proceed without fine-tuning job")
            return
        
        # Step 4: Monitor training (limited time for demo)
        demo.monitor_training_progress(max_wait_minutes=5)
        
        # Step 5: Demonstrate model comparison
        demo.demonstrate_model_comparison()
        
        # Step 6: Explain production deployment
        demo.explain_production_deployment()
        
        # Step 7: Cleanup recommendations
        demo.cleanup_demo_resources()
        
        # Final summary
        demo.print_demo_summary()
        
        logger.info("\n🎉 Fine-tuning demo completed successfully!")
        logger.info("📚 Check 1a_fine_tuning_portal_guide.md for the manual version")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Demo interrupted by user")
        demo.print_demo_summary()
    except Exception as e:
        logger.error(f"\n❌ Demo failed with error: {str(e)}")
        demo.print_demo_summary()

if __name__ == "__main__":
    main()