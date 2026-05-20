# InvenIO Backend - Testing Mode

To completely reset your environment and load dummy data (3 test accounts populated with fake tokens and ideas), follow these steps from this directory:

### 1. Activate Environment
```bash
source venv/bin/activate
```

### 2. Reset the Database
This drops all existing tables and rebuilds the clean schema:
```bash
python reset_db.py
```

### 3. Seed the Testing Data
This command populates the database with:
- 3 test accounts equipped with **10,000 Ʉ** each.
- **3 Ideas** (one for each user) with NLP embeddings already calculated for duplicate detection.
- **2 Problem Statements (Bounties)** representing active market demands.
- **Comments** linking users to the bounties.

```bash
python seed_data.py
```

### Test Accounts Available:
You can log in to the frontend using any of these seeded testing accounts:

- **Email:** `alice@test.com` | **Password:** `password123`
- **Email:** `bob@test.com` | **Password:** `password123`
- **Email:** `charlie@test.com` | **Password:** `password123`