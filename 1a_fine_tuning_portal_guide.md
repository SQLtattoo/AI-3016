# AI-3016 Demo 1A: Fine-tuning GPT-4o via Microsoft Foundry Portal

⏱️ **Demo Duration: 20 minutes**  
🎯 **Audience: Mixed skill levels**  
🏢 **Environment: Shared Azure subscription**

---

## 🎬 **Demo Overview**

This guide walks through fine-tuning GPT-4o using the Microsoft Foundry web portal interface. Students will see the complete visual workflow from data upload to model deployment.

> [!IMPORTANT]
> `azd up` does not start a fine-tuning job or deploy a fine-tuned model. Its readiness check runs only the code-first training dry-run. The training and deployment steps below are separate, billable operations; verify the available fine-tuning model versions, regional support, quota, and pricing first. A chat deployment's availability does not establish fine-tuning availability.

### **Learning Objectives:**
- Navigate Microsoft Foundry portal interface
- Upload and validate training datasets
- Configure fine-tuning job parameters
- Monitor training progress
- Understand fine-tuning best practices

---

## ⏰ **20-Minute Timeline**

| Time | Activity | Description |
|------|----------|-------------|
| 0-5 min | **Setup & Data Upload** | Navigate portal, upload training data |
| 5-15 min | **Configure Fine-tuning** | Set parameters, start job, explain options |
| 15-20 min | **Monitor & Discuss** | Check progress, discuss next steps |

---

## 🚀 **Pre-Demo Preparation**

### **Instructor Setup:**
1. ✅ Ensure Microsoft Foundry project is ready
2. ✅ Have `training_data.jsonl` and `validation_data.jsonl` files ready
3. ✅ GPT-4o base model deployed in the project
4. ✅ Test the portal access and permissions

### **Student Requirements:**
- Azure account with access to the shared subscription
- Web browser (Chrome/Edge recommended)
- Basic understanding of JSON format

### **Resource Naming Convention:**
- Model deployment: `{student-initials}-bank-assistant-v1`
- Fine-tuning job: `{student-initials}-bank-ft-{date}`
- Example: `js-bank-assistant-v1`, `js-bank-ft-1104`

---

## 📋 **Step-by-Step Demo Guide**

### **Phase 1: Data Upload (5 minutes)**

#### **Step 1: Access Microsoft Foundry**
1. Navigate to [https://ai.azure.com](https://ai.azure.com)
2. Sign in with Azure credentials
3. Select the correct project workspace
4. Navigate to **"Data"** section in left sidebar

#### **Step 2: Upload Training Data**
1. Click **"+ Create"** → **"Upload data"**
2. Select **"Upload from local file"**
3. **Upload training_data.jsonl:**
   - Name: `{student-initials}-bank-training-data`
   - Description: "Multi-turn banking conversations for fine-tuning"
   - File: Select `training_data.jsonl`
   - Data type: **"Fine-tuning"**
4. Click **"Upload"** and wait for completion

#### **Step 3: Upload Validation Data**
1. Repeat process for `validation_data.jsonl`
2. **Upload validation_data.jsonl:**
   - Name: `{student-initials}-bank-validation-data`
   - Description: "Validation dataset for fine-tuning evaluation"
   - File: Select `validation_data.jsonl`
   - Data type: **"Fine-tuning"**

> 💡 **Teaching Point:** Explain the difference between training and validation datasets while files upload.
> 
> **Training Data vs. Validation Data:**
> 
> **📚 Training Data (training_data.jsonl):**
> - **Purpose:** Teaches the model banking conversation patterns and tone
> - **What happens:** Model learns from these examples during each training epoch
> - **Analogy:** Like practice problems a student studies before an exam
> - **Our dataset:** 50 banking conversations showing professional responses
> 
> **✅ Validation Data (validation_data.jsonl):**
> - **Purpose:** Tests if the model is learning correctly (prevents overfitting)
> - **What happens:** Model is tested on these examples but doesn't learn from them
> - **Analogy:** Like a practice exam to check if studying is working
> - **Our dataset:** 10 banking conversations the model has never seen
> 
> **Key Differences:**
> - Training data → model adjusts weights to match patterns
> - Validation data → model performance measured without adjustment
> - **Best practice ratio:** 80/20 or 90/10 (training/validation)
> - **Our ratio:** 50/10 = 83/17 (ideal for demos)
> 
> **Why Both Matter:**
> - Training loss ↓ = model learning patterns
> - Validation loss ↓ = model generalizing (not just memorizing)
> - If training loss ↓ but validation loss ↑ = **overfitting** (model memorized training data)

---

### **Phase 2: Configure Fine-tuning Job (10 minutes)**

#### **Step 4: Start Fine-tuning Process**
1. Navigate to **"Fine-tuning"** in left sidebar
2. Click **"+ Fine-tune model"** button
3. Select **"gpt-4o-2024-08-06"** as base model (as shown in dropdown)

#### **Step 5: Configure Job Settings**

**Training Method:**
- ✅ **Select "Supervised"** (default and recommended for banking assistant)

**Training Type:**
- ✅ **Select "Standard"** (provides data residency in your region)
- **Note**: Global training is cheaper but doesn't guarantee data residency

**Basic Configuration:**
- **Suffix:** `{student-initials}-bank-assistant` (e.g., "js-bank-assistant")
- **Auto-deploy toggle**: ✅ **Enable "No"** for demo (we'll deploy manually later)

**Data Selection:**
- **Training data:** Select your uploaded training dataset from dropdown
- **Validation data:** Select your uploaded validation dataset from dropdown

**Seed (Optional):**
- ✅ **Use "Random"** for initial demos
- **For reproducible results**: Enter a specific number (e.g., 42)

**Configuration Settings (as shown in the UI):**

> 💡 **Demo Tip:** The interface shows Default/Custom radio buttons for each parameter. Start with defaults, then explain custom values.

**Batch size:**
- ✅ **Select "Default"** for initial demo (Azure auto-calculates optimal size)
- **Custom value**: 1 (if explaining manual settings)

> 💡 **What is Batch Size?**
> 
> **Definition:** Number of training examples processed together before updating the model's weights
> 
> **How it Works:**
> - **Batch size = 1:** Model updates after each conversation (slowest, most precise)
> - **Batch size = 4:** Model updates after every 4 conversations (faster, still stable)
> - **Batch size = 8-32:** Model updates less frequently (fastest, needs larger datasets)
> 
> **For Our Demo (50 examples):**
> - **Default (-1):** Azure calculates optimal size (typically 1-4 for small datasets)
> - **Custom = 1:** Maximum learning precision, ideal for small datasets
> - **Why not higher?** With only 50 examples, larger batches reduce learning opportunities
> 
> **Trade-offs:**
> - **Smaller batch (1-4):** More updates = better learning with small data, slower training
> - **Larger batch (8-32):** Fewer updates = faster training, needs more data for stability
> - **Memory:** Larger batches use more GPU memory
> 
> **Best Practice:** Let Azure's default choose unless you have a specific reason to override

**Learning rate multiplier (0.0-10.0):**
- ✅ **Select "Custom"** and set slider to **0.1**
- **Explanation**: Conservative rate within the recommended range

> 💡 **What is Learning Rate Multiplier?**
> 
> **Definition:** Controls how much the model adjusts its weights during each training step (how fast it learns)
> 
> **The Water Analogy:**
> - **Too high (>1.0):** Like filling a cup too fast - water splashes everywhere (unstable training)
> - **Just right (0.05-0.2):** Steady pour - cup fills perfectly (stable learning)
> - **Too low (<0.01):** Dripping slowly - takes forever to fill (very slow learning)
> 
> **For Our Demo:**
> - **Setting: 0.1** (conservative and safe)
> - **Range: 0.0-10.0** (Azure allows experimentation)
> - **Recommended: 0.05-0.2** for most fine-tuning tasks
> 
> **What Happens at Different Rates:**
> - **0.01-0.05:** Very careful learning, slow but stable, good for complex domains
> - **0.1:** Sweet spot for demos - safe, stable, reasonable speed
> - **0.5-1.0:** Faster learning, higher risk of overshooting optimal weights
> - **>2.0:** Dangerous - model may never converge or produce gibberish
> 
> **Why 0.1 for Banking:**
> - Banking requires precision and accuracy
> - Conservative rate ensures stable learning of professional tone
> - Reduces risk of training instability during demo
> - Students can safely experiment with 0.05-0.2 range later
> 
> **Signs of Wrong Learning Rate:**
> - **Too high:** Loss jumps up and down wildly, never stabilizes
> - **Too low:** Loss decreases very slowly, training takes too long
> - **Just right:** Loss steadily decreases, validation loss follows training loss

**Number of epochs (1-10):**
- ✅ **Select "Custom"** and set slider to **3**
- **Explanation**: Perfect for 50-example dataset

> 💡 **What is an Epoch?**
> 
> **Definition:** One complete pass through the entire training dataset
> 
> **Simple Analogy:**
> - **1 epoch:** Student reads textbook once
> - **3 epochs:** Student reads textbook three times (better retention!)
> - **10 epochs:** Student reads textbook ten times (might memorize instead of understanding)
> 
> **For Our Demo (50 examples):**
> - **Setting: 3 epochs** = Model sees all 50 conversations three times
> - **Total training steps:** ~150 learning opportunities (50 examples × 3 epochs)
> - **Training time:** ~10-15 minutes (demo-friendly)
> 
> **Epoch Guidelines by Dataset Size:**
> - **Small dataset (10-100 examples):** 3-5 epochs ideal
> - **Medium dataset (100-1,000 examples):** 2-4 epochs typical
> - **Large dataset (1,000+ examples):** 1-3 epochs sufficient
> - **Rule of thumb:** More data = fewer epochs needed
> 
> **Why 3 Epochs for Banking:**
> - **First epoch:** Model learns basic banking patterns
> - **Second epoch:** Model refines professional tone and accuracy
> - **Third epoch:** Model polishes responses and generalizes
> - **More epochs?** Risk of overfitting (memorizing instead of learning)
> 
> **Signs to Watch:**
> - **Training loss decreases:** ✅ Model is learning
> - **Validation loss decreases:** ✅ Model is generalizing well
> - **Validation loss increases:** ⚠️ Overfitting - model memorizing training data
> - **Both losses flat:** Model has learned as much as possible
> 
> **Demo Benefits of 3 Epochs:**
> - Completes in reasonable demo time (~10-15 min)
> - Shows clear learning progression in metrics
> - Avoids overfitting with our small dataset
> - Students can see results within class period

#### **Step 6: Advanced Settings Discussion**

> 🎓 **Teaching Moment (3-4 minutes) - Hyperparameter Logic:**
> 
> **Understanding the Interface:**
> - **Default vs Custom**: Azure provides intelligent defaults, but custom gives you control
> - **Sliders**: Visual interface makes it easy to adjust values within safe ranges
> - **Tooltips**: Hover over ℹ️ icons for Azure's built-in explanations
> 
> **Our Recommended Settings for Demo:**
> 
> **📊 Number of Epochs: 3** *(Custom slider setting)*
> - **Perfect for 50-example dataset** (our banking training data)
> - **UI shows range 1-10** - we choose conservative middle ground
> - **Demo-friendly timing** - completes in 10-15 minutes
> - **Avoids overfitting** with small dataset
> 
> **🔄 Batch Size: Default** *(Recommended for demos)*
> - **Let Azure optimize** - shows best practices in action
> - **Educational benefit**: Students see Azure's automatic intelligence
> - **Reduces complexity** - one less parameter to explain initially
> - **If custom**: Would set to 1 for maximum stability with small dataset
> 
> **⚡ Learning Rate: 0.1** *(Custom slider setting)*
> - **UI range is 0.0-10.0** - we choose conservative 0.1
> - **Safe for demos** - low risk of training instability
> - **Good starting point** for banking domain fine-tuning
> - **Students can experiment** with higher values later
> 
> **🎯 Why These UI Choices Work for Education:**
> - **Visual learning** - sliders make concepts concrete
> - **Safe defaults** - Azure prevents dangerous configurations
> - **Guided exploration** - tooltips provide just-in-time learning
> - **Professional interface** - students see real-world tools

#### **Step 7: Submit Fine-tuning Job**
1. Review all settings
2. Click **"Create"** to start the job
3. Note the job ID for tracking

---

### **Phase 3: Monitor & Discuss (5 minutes)**

#### **Step 8: Monitor Progress**
1. Navigate to **"Fine-tuning"** → **"Jobs"**
2. Find your job in the list
3. Click on job name to view details

**Job Status Progression:**
- ⏳ **Queued** → Job waiting to start
- 🔄 **Running** → Training in progress  
- ✅ **Succeeded** → Training completed
- ❌ **Failed** → Error occurred

#### **Step 9: Understand the Interface**

**Key Metrics to Explain (Based on Real Results):**
- **Training Duration:** ~1h 15min for 34K tokens (very reasonable!)
- **Training Loss:** Started at ~1.8, decreased to ~1.4 (model learning banking patterns)
- **Validation Loss:** Stabilized around 1.4-1.7 (good generalization, no overfitting)
- **Token Accuracy:** Improved from ~59% to ~59-68% (solid banking prediction accuracy)
- **Status:** ✅ **Completed Successfully** with stable learning curves

> 💡 **Teaching Point:** "Lower loss = better banking predictions. Validation tracking training = healthy learning pattern."

#### **Step 10: Test the Fine-Tuned Model (Real Results)**

> 🧪 **Live Testing (5 minutes):**
> 
> **Navigate to Chat Playground:**
> 1. Select your fine-tuned banking deployment
> 2. Test with banking scenarios:
>    ```
>    "What's the difference between APR and APY?"
>    Expected: Concise, professional banking explanation
>    ```
> 
> **Compare Communication Styles:**
> - **Fine-tuned:** Concise, professional, banking industry tone
> - **Base model:** Detailed, educational, more verbose explanations
> - **Key insight:** Same knowledge, different communication style
> 
> **Ultimate Combination (Optional):**
> - Add RAG data source to fine-tuned model
> - Test: "What are your current CD rates?"
> - Result: Professional style + current data + citations = **Perfect banking assistant**

#### **Step 11: Discuss Next Steps**

> 🎯 **Wrap-up Discussion (3 minutes):**
> 
> **What happens after training completes:**
> 1. Model is automatically saved
> 2. Deploy to endpoint for testing
> 3. Compare responses: base model vs fine-tuned
> 4. Evaluate performance on banking scenarios
> 
> **Production considerations:**
> - **Fine-tuning + RAG combination** for maximum quality
> - Model teaches communication style, RAG provides current data
> - Professional banking tone with accurate, cited information
> - A/B testing: base vs fine-tuned vs fine-tuned+RAG
> - Performance monitoring and cost optimization

---

## 💰 **Cost Management**

### **Estimated Costs (Based on Real Training):**
- **Fine-tuning:** ~$2-5 per job (our 34K token job: ~$3-4)
- **Training time:** ~1h 15min (very efficient)
- **Inference:** ~$0.01 per 1K tokens (same as base model)
- **Storage:** <$1/month for datasets

### **Cost Optimization Tips:**
1. Start with smaller datasets for experimentation
2. Use validation data to prevent overtraining
3. Delete unused fine-tuned models
4. Set up billing alerts

---

## 🧹 **Cleanup Instructions**

**After Demo (for cost management):**
1. Navigate to **"Deployments"**
2. Delete test deployments if not needed
3. Keep fine-tuned models for comparison
4. Archive datasets for future use

---

## ❓ **Troubleshooting Common Issues**

| Issue | Solution |
|-------|----------|
| **File upload fails** | Check JSONL format, file size <100MB |
| **No GPT-4o model** | Ensure model is deployed in project |
| **Job fails immediately** | Validate data format with error logs |
| **"Quota exceeded"** | Wait or use different region |
| **Permission denied** | Check Azure RBAC permissions |

---

## 🎓 **Teaching Extensions**

### **If Time Permits (5+ extra minutes):**
1. **Compare Training Data:** Show single-turn vs multi-turn examples
2. **Explain Multi-turn Conversations:** How they improve context understanding  
3. **Discuss Use Cases:** When to fine-tune vs RAG vs prompt engineering
4. **Production vs Demo Settings:**

   | Parameter | Demo Value | Production Range | Why Different |
   |-----------|------------|------------------|---------------|
   | **Epochs** | 3 | 1-10 | Production uses validation loss to determine optimal stopping |
   | **Batch Size** | Auto (-1) | Auto or 4-32 | Larger datasets benefit from larger batch sizes |
   | **Learning Rate** | 0.05 | 0.01-0.2 | Production fine-tunes based on model size and data complexity |
   | **Training Time** | 10-15 min | 30min-3hrs | Production datasets are typically 100-10,000+ examples |

### **For Advanced Students:**
1. **Export Model:** Download for external use
2. **API Integration:** How to call fine-tuned model programmatically
3. **Performance Metrics:** Understanding loss curves and validation
4. **Hyperparameter Tuning:** Systematic approaches for optimization

---

## 📝 **Student Takeaways**

By the end of this demo, students should understand:

✅ **How to navigate Microsoft Foundry portal**

✅ **Fine-tuning workflow from data to deployment**  
✅ **Key hyperparameters and their effects**  
✅ **Monitoring and troubleshooting techniques**  
✅ **Cost considerations for production use**

---

## 🔗 **Related Resources**

- **Technical Documentation:** [Azure OpenAI Fine-tuning Guide](https://docs.microsoft.com/azure/cognitive-services/openai/how-to/fine-tuning)
- **Best Practices:** [Fine-tuning Best Practices](https://platform.openai.com/docs/guides/fine-tuning)
- **Pricing:** [Azure OpenAI Pricing](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/)

---

*⏱️ **Total Demo Time: 20 minutes** - Perfect for classroom demonstration with built-in flexibility for questions and discussion.*