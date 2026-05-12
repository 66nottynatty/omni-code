# Contributing to OmniCode

First off, thank you for considering contributing to OmniCode! It's people like you that make OmniCode such a great tool.

## Code of Conduct

By participating in this project, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).

## How Can I Contribute?

### Reporting Bugs

*   **Check the existing issues** to see if the bug has already been reported.
*   If you can't find an open issue addressing the problem, **open a new one**. Use the "Bug Report" template.
*   **Be specific!** Include details about your environment, steps to reproduce, and what you expected to happen vs. what actually happened.

### Suggesting Enhancements

*   **Check the existing issues** to see if the enhancement has already been suggested.
*   **Open a new issue** using the "Feature Request" template.
*   Explain why this enhancement would be useful and how it should work.

### Pull Requests

1.  **Fork the repository**.
2.  **Create a new branch** for your changes.
3.  **Make your changes**.
4.  **Run the tests** (see below).
5.  **Submit a Pull Request**.

## Local Development Setup

### Prerequisites

*   Docker & Docker Compose v2
*   Node.js 20+
*   Python 3.12+

### Backend Setup

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create a virtual environment and install dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```
4.  Initialize the database:
    ```bash
    python init_db.py
    ```
5.  Run the backend:
    ```bash
    uvicorn main:app --reload
    ```

### Frontend Setup

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the frontend:
    ```bash
    npm run dev
    ```

### Using Docker

You can also run the entire stack using Docker Compose:

```bash
docker-compose up
```

## Running Tests

### Backend Tests

```bash
cd backend
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

## Branching Strategy

*   `main`: The stable branch.
*   Feature branches: `feature/your-feature-name`
*   Bug fix branches: `fix/your-bug-name`

## Database Migrations

Currently, we use a simple `init_db.py` script to create the database schema. In the future, we plan to move to Alembic for proper migration management. If you change the models, please update `init_db.py` and consider how to handle migrations for existing users.

## Commit Messages

Use clear and descriptive commit messages. We prefer [Conventional Commits](https://www.conventionalcommits.org/).
