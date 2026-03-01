# Dopamine Detox RPG

A gamified productivity web application designed to help users manage their screen time and defeat procrastination through RPG mechanics.

## 🚀 Setup & Installation

### 1. Requirements
Ensure you have Python 3.8+ installed.

### 2. Environment Setup
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configuration
Copy the default environment variables configuration to create your own local `.env`:
```bash
cp .env.example .env
```
Ensure you update the `SECRET_KEY` if deploying to production.

### 4. Database Setup
A consolidated script is provided to safely set up the project database, run migrations, and inject initial items and users. Use this command:
```bash
python scripts/setup_project.py
```

### 5. Running the Application
Start the Flask web server:
```bash
python app.py
```
By default, the application will run at `http://localhost:5000`.

## 📂 Project Structure

- `/app.py`: Main Flask application entry point.
- `/models`: Database schema and SQLAlchemy definitions.
- `/services`: Core logic (Analytics processing, AI/Intelligence mechanics).
- `/scripts`: Administrative scripts (Setup, seeds, deployment).
- `/static`: CSS, Javascript, and Images/Sprites.
- `/templates`: HTML Jinja views.
- `/extension`: The associated Chrome Extension.
