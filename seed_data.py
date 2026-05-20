import sys
import os
import random

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import SessionLocal
from app.database import models
from app.utils.hashing import get_password_hash
from app.ai.duplicate_detector import duplicate_detector

def seed_database():
    db = SessionLocal()
    print("🌱 Starting database seeding for testing mode...")
    
    # Check if we already have users
    if db.query(models.User).count() > 0:
        print("⚠️ Database already contains users. Please run reset_db.py first if you want a clean seed.")
        db.close()
        return

    # Create 3 users
    users_data = [
        {"name": "Alice Innovator", "email": "alice@test.com", "password": "password123"},
        {"name": "Bob Creator", "email": "bob@test.com", "password": "password123"},
        {"name": "Charlie Engineer", "email": "charlie@test.com", "password": "password123"}
    ]
    
    db_users = []
    
    for u_data in users_data:
        new_user = models.User(
            name=u_data["name"],
            email=u_data["email"],
            password_hash=get_password_hash(u_data["password"]),
            is_email_public=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db_users.append(new_user)
        
        # Create wallet with a high testing balance
        new_wallet = models.Wallet(
            user_id=new_user.id,
            balance=10000.0  # 10k InvenIO testing tokens
        )
        db.add(new_wallet)
        db.commit()
        db.refresh(new_wallet)
        
        # Update user with wallet ID
        new_user.wallet_id = new_wallet.wallet_id
        db.commit()
        
        print(f"✅ Created user {u_data['name']} (Email: {u_data['email']}, Pass: {u_data['password']}) with 10,000 Ʉ")

    # Create 3 specific high-quality ideas
    ideas_data = [
        {
            "title": "Decentralized Quantum Voting",
            "snippet": "A quantum-resistant voting mechanism on the blockchain for secure elections.",
            "problem_statement": "Current voting systems are susceptible to manipulation and future quantum computing attacks.",
            "research_info": "Utilizing lattice-based cryptography instead of traditional RSA ensures post-quantum security.",
            "solution": "A distributed ledger utilizing Dilithium signatures for verifiable, anonymous, and quantum-safe voting.",
            "keywords": "quantum, voting, security",
            "category": "Technology",
            "price": 250.0
        },
        {
            "title": "Renewable Energy Grid Tokenization",
            "snippet": "Peer-to-peer energy trading platform for solar households.",
            "problem_statement": "Households with solar panels waste excess energy without a localized marketplace to sell it.",
            "research_info": "Smart grids coupled with fast-finality blockchains can resolve micro-transactions under 10ms.",
            "solution": "An automated smart contract system where smart meters directly mint and trade EnergyTokens locally.",
            "keywords": "energy, solar, p2p",
            "category": "Energy",
            "price": 100.0
        },
        {
            "title": "Zero-Knowledge Medical Records",
            "snippet": "Share medical history with doctors without exposing identity.",
            "problem_statement": "Patient data is often siloed and sharing it exposes individuals to severe privacy risks.",
            "research_info": "zk-SNARKs allow proving certain conditions (e.g. valid prescription) without revealing the underlying data.",
            "solution": "A HIPAA-compliant IPFS storage network encrypted via zk-proofs, giving temporary viewing keys to authorized practitioners.",
            "keywords": "health, zk-proofs, privacy",
            "category": "Healthcare",
            "price": 500.0
        }
    ]

    categories = ["Technology", "Energy", "Healthcare", "Finance", "Other"]
    adjectives = ["Decentralized", "Quantum", "Zero-Knowledge", "Tokenized", "AI-Driven", "Autonomous", "Scalable", "Peer-to-Peer", "Encrypted", "Predictive", "Immutable"]
    nouns = ["Voting", "Energy Grid", "Medical Records", "Supply Chain", "Credit Scoring", "Data Storage", "Identity", "Logistics", "Derivatives", "Genomics", "Real Estate"]
    
    print("🧠 Generating 55 additional AI ideas...")
    for i in range(55):
        cat = random.choice(categories)
        adj = random.choice(adjectives)
        noun = random.choice(nouns)
        title = f"{adj} {noun} System {random.randint(100, 999)}"
        
        ideas_data.append({
            "title": title,
            "snippet": f"A novel approach to {noun.lower()} using {adj.lower()} technology on the blockchain.",
            "problem_statement": f"Current systems for {noun.lower()} are outdated, lack transparency, and are highly centralized.",
            "research_info": f"Research shows that utilizing {adj.lower()} architectures can reduce overhead by 40% and increase security exponentially.",
            "solution": f"We propose a custom smart contract layer that handles {noun.lower()} autonomously using {adj.lower()} cryptographic proofs.",
            "keywords": f"{noun.lower().replace(' ', '')}, {adj.lower().replace('-', '')}, blockchain",
            "category": cat,
            "price": random.randint(50, 1000) * 1.0
        })

    print(f"⏳ Inserting {len(ideas_data)} ideas and generating AI vector embeddings (this may take a minute)...")
    for i, i_data in enumerate(ideas_data):
        owner = db_users[i % len(db_users)]
        
        new_idea = models.Idea(
            title=i_data["title"],
            snippet=i_data["snippet"],
            problem_statement=i_data["problem_statement"],
            research_info=i_data["research_info"],
            solution=i_data["solution"],
            keywords=i_data["keywords"],
            category=i_data["category"],
            price=i_data["price"],
            sale_type="both",
            plan_1m_price=i_data["price"] * 0.1,
            plan_3m_price=i_data["price"] * 0.25,
            plan_6m_price=i_data["price"] * 0.45,
            owner_id=owner.id,
            is_public=True
        )
        db.add(new_idea)
        db.commit()
        db.refresh(new_idea)
        
        # Add vector for duplicate detection
        combined_text = f"{i_data['title']} {i_data['problem_statement']} {i_data['solution']} {i_data['keywords']}"
        embedding = duplicate_detector.generate_embedding(combined_text)
        new_vector = models.IdeaVector(idea_id=new_idea.idea_id, embedding=embedding)
        db.add(new_vector)
        db.commit()
        
        if i % 10 == 0 or i == len(ideas_data) - 1:
            print(f"✅ Minted {i+1}/{len(ideas_data)} ideas...")

    # Create specific Problems (Bounties)
    problems_data = [
        {
            "title": "Need a decentralized oracle for physical supply chains",
            "description": "Looking for a secure, tamper-proof way to link IoT RFID scanners in shipping containers to a smart contract to verify delivery without a centralized authority.",
            "category": "Technology"
        },
        {
            "title": "Tokenized Carbon Credit Verification",
            "description": "How can we mathematically prove that a tokenized carbon credit hasn't been double-spent or claimed by two different corporations across different registries?",
            "category": "Energy"
        }
    ]

    problem_topics = ["Data Privacy", "Scalability", "Interoperability", "Governance", "Tokenomics", "User Adoption", "Security Audits", "Oracle Networks"]
    print("📢 Generating 25 additional problem statements (bounties)...")
    for i in range(25):
        topic = random.choice(problem_topics)
        adj = random.choice(adjectives)
        title = f"Seeking solution for {adj} {topic} {random.randint(100,999)}"
        problems_data.append({
            "title": title,
            "description": f"We are currently facing challenges implementing {topic.lower()} in a {adj.lower()} environment. We need a secure, fast, and reliable architecture. Open to tokenized solutions.",
            "category": random.choice(categories)
        })

    print(f"⏳ Inserting {len(problems_data)} problems and generating community comments...")
    for i, p_data in enumerate(problems_data):
        author = db_users[i % len(db_users)]
        new_problem = models.Problem(
            title=p_data["title"],
            description=p_data["description"],
            category=p_data["category"],
            user_id=author.id
        )
        db.add(new_problem)
        db.commit()
        db.refresh(new_problem)

        # Add comments from the other two users
        commenter1 = db_users[(i + 1) % len(db_users)]
        commenter2 = db_users[(i + 2) % len(db_users)]

        c1 = models.ProblemComment(
            problem_id=new_problem.id,
            user_id=commenter1.id,
            content=random.choice([
                "This is a fantastic bounty. I've been researching something similar using zero-knowledge proofs.",
                "I agree, this is a major bottleneck right now in the industry.",
                "Would you be open to an off-chain oracle solution for this?",
                "Fascinating problem. I've started drafting a whitepaper on this exact topic."
            ])
        )
        db.add(c1)
        db.commit()

        c2 = models.ProblemComment(
            problem_id=new_problem.id,
            user_id=commenter2.id,
            content=random.choice([
                "I might tokenize a solution for this soon. Keep an eye on my marketplace profile!",
                "Have you considered looking into how Layer 2 rollups handle this?",
                "I have a patent pending for a related architecture, let's connect.",
                "This is exactly what I'm working on. The math is tricky but solvable."
            ])
        )
        db.add(c2)
        db.commit()
        
        if i % 10 == 0 or i == len(problems_data) - 1:
            print(f"✅ Created {i+1}/{len(problems_data)} problems with comments...")

    print("🎉 Seeding complete! The environment is now in Testing Mode.")
    db.close()

if __name__ == "__main__":
    seed_database()
