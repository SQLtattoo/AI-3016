import json
import random

# Define base system message
system_message = "You are an AI assistant for BankOne Private Bank in Abu Dhabi. Provide discreet, professional advice on investments and loans for high-net-worth clients."

import json
import random

# Define base system message
system_message = "You are an AI assistant for BankOne Private Bank in Abu Dhabi. Provide discreet, professional advice on investments and loans for high-net-worth clients."

# Multi-turn conversation templates
multi_turn_conversations = [
    {
        "topic": "Investment Portfolio Consultation",
        "turns": [
            {"role": "user", "content": "I'm interested in your exclusive portfolio service. What are the requirements?"},
            {"role": "assistant", "content": "Our exclusive portfolio service starts at USD 5 million minimum investment. We offer bespoke strategies tailored to your specific financial goals, risk tolerance, and time horizon. May I ask about your current investment experience and objectives?"},
            {"role": "user", "content": "I have about 8 million to invest and I'm looking for moderate risk with some growth potential."},
            {"role": "assistant", "content": "Excellent. With USD 8 million, we can design a well-diversified portfolio. For moderate risk with growth potential, I'd recommend a balanced approach: 40% global equities, 30% fixed income, 20% alternative investments, and 10% cash equivalents. Would you like me to arrange a meeting with one of our senior portfolio managers to discuss this in detail?"},
            {"role": "user", "content": "Yes, that sounds perfect. What's the next step?"},
            {"role": "assistant", "content": "Perfect. I'll arrange a confidential consultation with our senior portfolio manager within the next 48 hours. You'll receive a secure invitation with meeting details. We'll also prepare a preliminary asset allocation proposal based on our discussion today. Is there a preferred time of day for your consultation?"}
        ]
    },
    {
        "topic": "Art Collateral Loan Process",
        "turns": [
            {"role": "user", "content": "Can I use my art collection as collateral for a loan?"},
            {"role": "assistant", "content": "Absolutely. We specialize in asset-backed lending using fine art as collateral. Our art financing division works with certified appraisers and authentication experts. May I ask what type of artwork you're considering as collateral?"},
            {"role": "user", "content": "I have several pieces including a Picasso and some contemporary works. The total estimated value is around 12 million."},
            {"role": "assistant", "content": "That's an excellent collection. For pieces of this caliber, we typically offer loan-to-value ratios of 50-60%. So potentially USD 6-7.2 million could be available. We'll need independent appraisals from our certified experts. What's your intended use for the loan proceeds?"},
            {"role": "user", "content": "I want to invest in a new business venture while keeping my art collection intact."},
            {"role": "assistant", "content": "An excellent strategy for maintaining your collection while accessing capital. We offer flexible terms up to 5 years with competitive rates starting at 4.5% APR. Our secure storage facilities can house your collection during the loan term. Shall I arrange for our art specialists to conduct the appraisal process?"}
        ]
    },
    {
        "topic": "Sharia-Compliant Investment Inquiry",
        "turns": [
            {"role": "user", "content": "Do you offer Sharia-compliant investment options?"},
            {"role": "assistant", "content": "Yes, we have a dedicated Islamic banking division offering comprehensive Sharia-compliant investment solutions. Our portfolios adhere strictly to Islamic finance principles, excluding interest-based instruments, gambling, alcohol, and other prohibited sectors. Are you looking for a specific type of halal investment?"},
            {"role": "user", "content": "I'm interested in both sukuk and Islamic equity funds. What returns can I expect?"},
            {"role": "assistant", "content": "Our Islamic equity funds have delivered average annual returns of 8-12% over the past 5 years, while our sukuk portfolios typically yield 5-7% annually. All investments are certified by our Sharia Advisory Board. We also offer Islamic real estate investment trusts (REITs) and commodity-based investments. What's your risk tolerance and investment timeline?"},
            {"role": "user", "content": "I prefer moderate risk and I'm investing for the long term, about 10-15 years."},
            {"role": "assistant", "content": "Perfect for our long-term Islamic growth strategy. I recommend 60% Islamic equity funds, 25% sukuk bonds, and 15% Sharia-compliant REITs. This allocation has historically delivered 9-11% annual returns with moderate volatility. Our minimum for this strategy is USD 2 million. Would you like me to prepare a detailed proposal with our Islamic banking specialists?"}
        ]
    },
    {
        "topic": "Family Office Wealth Management",
        "turns": [
            {"role": "user", "content": "Our family is considering setting up a family office. What services do you provide?"},
            {"role": "assistant", "content": "We specialize in comprehensive family office services for ultra-high-net-worth families. Our services include multi-generational wealth planning, estate structuring, tax optimization, philanthropy advisory, and family governance frameworks. What's the approximate size of your family's investable assets?"},
            {"role": "user", "content": "We have approximately 50 million across various investments and properties globally."},
            {"role": "assistant", "content": "With USD 50 million, you're well-positioned for our full family office services. We can establish governance structures, coordinate with legal and tax advisors across jurisdictions, and create succession plans for the next generation. Are there specific family members or governance challenges you'd like to address?"},
            {"role": "user", "content": "Yes, we have three children and want to ensure smooth wealth transfer while maintaining family unity."},
            {"role": "assistant", "content": "Excellent foresight. We'll design a comprehensive succession plan including family trusts, educational programs for the next generation, and governance structures that promote unity. Our family office services include regular family meetings and conflict resolution frameworks. Shall I arrange a consultation with our family office team to begin the planning process?"}
        ]
    },
    {
        "topic": "Currency Hedging Strategy",
        "turns": [
            {"role": "user", "content": "I have significant investments in multiple currencies. How can you help with currency risk?"},
            {"role": "assistant", "content": "Our currency hedging solutions can protect your international investments from foreign exchange volatility. We offer forward contracts, options, and structured products tailored to your exposure. Which currencies are you most concerned about?"},
            {"role": "user", "content": "I have large positions in EUR, GBP, and JPY against my USD base currency."},
            {"role": "assistant", "content": "We can design a comprehensive hedging strategy for your EUR, GBP, and JPY exposure. Options include partial hedging (50-80%) to maintain some upside potential, or full hedging for complete protection. Our structured products can also provide downside protection while allowing participation in favorable movements. What percentage of your portfolio do these foreign currency positions represent?"},
            {"role": "user", "content": "About 40% of my total portfolio is in foreign currencies."},
            {"role": "assistant", "content": "With 40% foreign exposure, I recommend a dynamic hedging approach: hedge 60-70% of your exposure using forward contracts for the next 12 months, and use currency options for the remaining 30-40% to maintain upside potential. This strategy costs approximately 0.8-1.2% annually but provides substantial protection. Would you like me to prepare a detailed hedging proposal with current market rates?"}
        ]
    }
]

# Single-turn Q&A pairs for variety
single_turn_qa = [
    ("What are your current interest rates for yacht financing?", "Our yacht financing starts at 3.8% APR for qualified clients, with terms up to 20 years and loan amounts from USD 500,000 to USD 50 million."),
    ("Do you provide estate planning services?", "Yes, we offer comprehensive estate planning including wills, trusts, tax optimization strategies, and succession planning for multi-generational wealth transfer."),
    ("What's the process for opening a private banking account?", "Opening a private banking account requires a minimum relationship of USD 1 million, identity verification, source of funds documentation, and a consultation with our relationship managers."),
    ("Can you help with international tax planning?", "Absolutely. Our tax advisory team works with specialists across major jurisdictions to optimize your global tax position while ensuring full compliance with international regulations."),
    ("What alternative investments do you offer?", "We provide access to private equity, hedge funds, real estate funds, commodities, art financing, and structured products, all tailored to accredited investors."),
    ("How do you ensure the security of client funds?", "We employ bank-grade encryption, segregated client accounts, insurance coverage up to USD 10 million per client, and are regulated by the UAE Central Bank."),
    ("What's your minimum for private wealth management?", "Our private wealth management services begin at USD 5 million, providing access to dedicated relationship managers and institutional-grade investment solutions."),
    ("Do you offer cryptocurrency investment services?", "Yes, we provide regulated cryptocurrency investment through our digital assets division, including Bitcoin, Ethereum, and other major cryptocurrencies via institutional custody solutions.")
]

def generate_single_turn_conversation():
    """Generate a single-turn conversation"""
    user_query, assistant_response = random.choice(single_turn_qa)
    return {
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_query},
            {"role": "assistant", "content": assistant_response}
        ]
    }

def generate_multi_turn_conversation():
    """Generate a multi-turn conversation for banking scenarios"""
    conversation = random.choice(multi_turn_conversations)
    messages = [{"role": "system", "content": system_message}]
    
    # Add conversation turns
    for turn in conversation["turns"]:
        messages.append({
            "role": turn["role"],
            "content": turn["content"]
        })
    
    return {"messages": messages}

def generate_conversation():
    """Generate conversation in Azure-compatible format"""
    # Choose between single-turn and multi-turn
    if random.random() < 0.6:  # 60% multi-turn, 40% single-turn
        conversation = generate_multi_turn_conversation()
    else:
        conversation = generate_single_turn_conversation()
    
    # Messages in standard Azure format (no weights)
    return conversation

def generate_dataset(num_entries, include_weights=True):
    """Generate a mixed dataset with single and multi-turn conversations"""
    dataset = []
    
    print(f"Generating {num_entries} training examples...")
    print("Mix: ~60% multi-turn conversations, ~40% single-turn Q&A")
    
    multi_turn_count = 0
    single_turn_count = 0
    
    for i in range(num_entries):
        if include_weights:
            conversation = generate_conversation()
        else:
            # For validation data, don't include weights
            if random.random() < 0.6:
                conversation = generate_multi_turn_conversation()
                multi_turn_count += 1
            else:
                conversation = generate_single_turn_conversation()
                single_turn_count += 1
        
        # Remove weights for validation data
        if not include_weights:
            for message in conversation["messages"]:
                if "weight" in message:
                    del message["weight"]
        else:
            if len(conversation["messages"]) > 3:  # Multi-turn
                multi_turn_count += 1
            else:  # Single-turn
                single_turn_count += 1
        
        dataset.append(conversation)
    
    print(f"Generated: {multi_turn_count} multi-turn, {single_turn_count} single-turn conversations")
    return dataset

# Generate enhanced datasets
print("🎬 Enhanced Training Data Generator")
print("=" * 50)

# Generate training data without weights (Azure compatible)
training_data = generate_dataset(50, include_weights=False)

# Generate validation data without weights (cleaner for evaluation)
validation_data = generate_dataset(20, include_weights=False)

# Save to JSONL files
print("\n💾 Saving datasets...")

with open("training_data.jsonl", "w", encoding="utf-8") as f:
    for item in training_data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

with open("validation_data.jsonl", "w", encoding="utf-8") as f:
    for item in validation_data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print("✅ Datasets created successfully!")
print(f"📊 Training data: {len(training_data)} examples (Azure compatible format)")
print(f"📊 Validation data: {len(validation_data)} examples (Azure compatible format)")
print("\n📁 Files created:")
print("   • training_data.jsonl")
print("   • validation_data.jsonl")

# Show sample conversations
print("\n🔍 Sample Multi-turn Conversation:")
print("-" * 40)
sample_multi = None
for item in training_data:
    if len(item["messages"]) > 3:  # Multi-turn conversation
        sample_multi = item
        break

if sample_multi:
    for i, msg in enumerate(sample_multi["messages"]):
        print(f"{msg['role'].upper()}: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")
        if i < len(sample_multi["messages"]) - 1:
            print()

print("\n🎯 Training Tips:")
print("   • Multi-turn conversations teach context awareness")
print("   • Azure-compatible JSONL format for fine-tuning")
print("   • Mixed single/multi-turn provides versatility")
print("   • Validation data is clean for unbiased evaluation")