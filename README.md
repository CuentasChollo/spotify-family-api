### Spotify Family Api

This project manages Spotify family accounts and automates tasks like adding clients, changing emails, deleting members, and retrieving family data. It utilizes Selenium, AWS Lambda, and a PostgreSQL database.

Project Structure
├── .gitignore          # Files and folders to ignore for Git
├── Dockerfile          # Docker configuration for the Lambda environment
├── README.md           # This file
├── local               # Files for local testing
│   ├── event.json      # Sample event data for local execution
│   ├── local_add_family_client.py # Script to simulate adding a family client locally
│   └── maps.py         # Script for generating random addresses (unused in core functionality)
├── models.py           # Database models using SQLAlchemy
├── pyright.toml        # Configuration for Pyright type checker
├── scripts             # Shell scripts for deployment and cleanup
│   ├── cleanup.sh      # Cleans up old Docker images in ECR
│   └── upload.sh       # Builds and uploads the Docker image to ECR
└── src                 # Source code for Lambda functions and utilities
    ├── extra           # Additional scripts, e.g., changing country to India
    │   └── only_change_to_india.py
    ├── lambda_functions # AWS Lambda functions
    │   ├── executors   # Core logic for Lambda functions
    │   │   ├── change_email.py
    │   │   ├── change_email_api.py
    │   │   ├── delete_member.py
    │   │   ├── get_family_raw_memberships.py
    │   │   ├── join_family.py
    │   │   └── retrieve_family_data.py
    │   └── initializers # Lambda functions to initiate asynchronous tasks
    │       ├── init_change_email.py
    │       ├── init_delete_member.py
    │       ├── init_get_family_raw_memberships.py
    │       ├── init_join_family.py
    │       └── init_retrieve_family_data.py
    └── utils            # Utility functions
        ├── challenge_solver.py # Handles CAPTCHA solving and email confirmations
        ├── confirmation_code.py # Extracts confirmation codes from emails
        ├── helper.py       # Helper functions for login, screenshots, etc.
        └── invoice_parser.py # Parses invoices to extract premium end date
content_copy
Use code with caution.
Functionality
Lambda Functions

executors:

change_email.py: Changes the email address of a Spotify family account.

change_email_api.py: Changes the email via Spotify API.

delete_member.py: Removes a member from a Spotify family account.

get_family_raw_memberships.py: Retrieves the raw membership data for a family account.

join_family.py: Adds a new member to a Spotify family account.

retrieve_family_data.py: Retrieves family account data, including address, members, and premium end date.

initializers: These functions initiate asynchronous tasks and store task status in the database. They then trigger the corresponding executor function.

init_change_email.py

init_delete_member.py

init_get_family_raw_memberships.py

init_join_family.py

init_retrieve_family_data.py

Utilities

challenge_solver.py: Solves reCAPTCHA challenges and handles email confirmation challenges.

confirmation_code.py: Retrieves confirmation codes from emails using IMAP.

helper.py: Contains helper functions for common tasks such as login, saving screenshots, and updating task status in the database.

invoice_parser.py: Parses email invoices to extract the premium end date.

Setup and Deployment

This project uses Docker to containerize the Lambda functions and AWS ECR to store the Docker images. See the README.md file for detailed instructions on setup and deployment. The project requires a PostgreSQL database and utilizes environment variables for configuration.

Key Improvements and Considerations

Asynchronous Tasks: The use of initializer and executor functions allows for asynchronous processing of long-running tasks, improving responsiveness.

CAPTCHA Solving: Implements reCAPTCHA solving using selenium-recaptcha-solver and handles email confirmations.

Email Parsing: Parses emails for confirmation codes and invoice data using imaplib and BeautifulSoup.

Database Integration: Uses SQLAlchemy to interact with a PostgreSQL database, storing task status and family account information.

Error Handling: Includes error handling and screenshot capture for debugging.

Stealth Techniques: Employs various techniques to make the Selenium browser appear less like a bot.

API Interaction (Where Possible): The project attempts to use the Spotify API where possible for more efficient and reliable interactions.

Further Development

Improved CAPTCHA Solving: Explore more robust CAPTCHA solving solutions for better reliability.

Enhanced Error Handling: Add more granular error handling and logging.

Testing: Implement comprehensive unit and integration tests.

Secret Management: Use a secure secret management solution instead of storing credentials in environment variables.

This enhanced README provides a more comprehensive overview of the project's structure, functionality, and setup, making it easier for others to understand and contribute. It also highlights key improvements and areas for future development.